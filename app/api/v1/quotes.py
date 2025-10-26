"""
Quotes API endpoints
AI-powered quote generation and comparison
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import date, timedelta

from app.api.dependencies import get_db_session
from app.models.quote import Quote, QuoteStatus
from app.models.prospect import Prospect
from app.services.ai_quote_service import (
    AIQuoteService,
    EligibilityService,
    ProspectProfile,
    QuoteRecommendation
)

router = APIRouter()


# ============================================================================
# Request/Response Schemas
# ============================================================================

class QuoteGenerateRequest(BaseModel):
    """
    Request to generate AI-powered quotes.

    WHY separate request model:
    - Validation layer (FastAPI + Pydantic)
    - API contract decoupled from internal models
    - Can version API (v1, v2) without changing internal logic
    """
    prospect_id: int = Field(..., description="ID of prospect requesting quote")
    insurance_type: str = Field(..., description="Type: life, auto, home, health")
    coverage_amount: float = Field(..., gt=0, description="Desired coverage in EUR")
    has_preexisting_conditions: bool = Field(default=False)
    smoker: bool = Field(default=False)
    occupation_risk: str = Field(default="standard", description="standard, high, very_high")

    class Config:
        json_schema_extra = {
            "example": {
                "prospect_id": 1,
                "insurance_type": "life",
                "coverage_amount": 500000,
                "has_preexisting_conditions": False,
                "smoker": False,
                "occupation_risk": "standard"
            }
        }


class QuoteResponse(BaseModel):
    """Single quote details"""
    id: int
    provider: str
    insurance_type: str
    monthly_premium: float
    annual_premium: float
    coverage_amount: float
    status: QuoteStatus
    ai_score: float | None
    ai_reasoning: dict | None
    valid_until: date | None
    is_recommended: bool = False  # Highlighted as AI recommendation

    class Config:
        from_attributes = True


class QuoteComparisonResponse(BaseModel):
    """
    Complete quote comparison with AI analysis.

    This is what the frontend receives - all info needed to show comparison UI.
    """
    prospect_id: int
    insurance_type: str
    coverage_amount: float
    quotes: List[QuoteResponse]
    recommended_provider: str
    ai_reasoning: str
    risk_assessment: str
    additional_notes: str
    generated_at: str


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/generate", response_model=QuoteComparisonResponse, status_code=status.HTTP_201_CREATED)
async def generate_quotes(
    request: QuoteGenerateRequest,
    db: Session = Depends(get_db_session)
):
    """
    Generate AI-powered insurance quotes from multiple providers.

    ## Flow (explained for interview):

    1. **Fetch Prospect**: Get customer data from database
       - WHY: Need age, risk category for pricing

    2. **Check Eligibility**: Query all 4 providers
       - WHY: Not all providers accept all customers (age limits, risk)
       - CURRENT: Mock data
       - PRODUCTION: Parallel API calls to provider systems

    3. **AI Analysis**: Send data to Claude via LangChain
       - INPUT: Prospect profile + eligibility results
       - OUTPUT: Ranked recommendations with reasoning
       - WHY Claude: Excellent at structured reasoning, consistent JSON output

    4. **Save Quotes**: Store all quotes in database
       - WHY: Audit trail, customer can review later, track acceptances
       - Includes AI reasoning for compliance

    5. **Publish Event**: QuoteGenerated event to Redis
       - WHY: Trigger email notification, update dashboard, etc.
       - Async processing - API responds immediately

    ## What makes this "AI-powered"?

    - **Not just price comparison**: AI evaluates value, risk alignment, flexibility
    - **Explainable**: Provides reasoning (compliance requirement)
    - **Contextual**: Considers customer's specific situation
    - **Learning potential**: Could fine-tune on historical acceptance data

    ## Architecture Decision: Why in API layer?

    Could've done this in background worker. Chose synchronous because:
    - Customer waits for quotes (UX expectation)
    - Claude response is fast (~2-3s)
    - If it fails, customer sees error immediately (better than silent failure)
    - Trade-off: Slightly slower API response, but better UX

    ## Performance Considerations:

    - Claude API call: ~2-3 seconds
    - Database operations: ~50ms
    - Total: ~3 seconds (acceptable for quote generation)
    - Could cache eligibility results per prospect (optimization for later)
    """

    # Step 1: Fetch prospect
    prospect_record = db.query(Prospect).filter(Prospect.id == request.prospect_id).first()
    if not prospect_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prospect with id {request.prospect_id} not found"
        )

    # Calculate age from birth_date
    # WHY: Age is critical for insurance pricing, not stored directly
    if not prospect_record.birth_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prospect must have birth_date set for quote generation"
        )

    from datetime import date
    today = date.today()
    age = today.year - prospect_record.birth_date.year - (
        (today.month, today.day) < (prospect_record.birth_date.month, prospect_record.birth_date.day)
    )

    # Build prospect profile
    prospect_profile = ProspectProfile(
        age=age,
        risk_category=prospect_record.risk_category.value if prospect_record.risk_category else "low",
        insurance_type=request.insurance_type,
        coverage_amount=request.coverage_amount,
        has_preexisting_conditions=request.has_preexisting_conditions,
        smoker=request.smoker,
        occupation_risk=request.occupation_risk
    )

    # Step 2: Check eligibility with providers
    eligibility_service = EligibilityService()
    eligibility_results = eligibility_service.check_eligibility(prospect_profile)

    # Filter only eligible providers
    # WHY: Don't send ineligible options to AI (noise)
    eligible_providers = [r for r in eligibility_results if r.eligible]

    if not eligible_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No providers available for this profile. Check age and coverage limits."
        )

    # Step 3: AI Analysis
    ai_service = AIQuoteService()
    try:
        recommendation: QuoteRecommendation = await ai_service.generate_quote_recommendation(
            prospect=prospect_profile,
            eligibility_results=eligible_providers
        )
    except Exception as e:
        # LOG: In production, log full error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"AI quote generation failed: {e}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate AI recommendation. Please try again."
        )

    # Step 4: Save quotes to database
    # WHY save all quotes (not just recommended):
    # - Customer might disagree with AI
    # - Historical tracking
    # - A/B testing AI recommendations
    quotes_created = []
    valid_until = date.today() + timedelta(days=30)  # Quotes valid for 30 days

    for ranking in recommendation.rankings:
        quote = Quote(
            prospect_id=request.prospect_id,
            provider=ranking.provider,
            insurance_type=request.insurance_type,
            monthly_premium=ranking.monthly_premium,
            annual_premium=ranking.annual_premium,
            coverage_amount=request.coverage_amount,
            status=QuoteStatus.DRAFT,
            valid_until=valid_until,
            ai_score=ranking.score,
            ai_reasoning={
                "pros": ranking.pros,
                "cons": ranking.cons,
                "key_features": ranking.key_features
            },
            items={"key_features": ranking.key_features}  # Store features in items JSON
        )
        db.add(quote)
        quotes_created.append(quote)

    db.commit()

    # Refresh to get IDs
    for quote in quotes_created:
        db.refresh(quote)

    # Step 5: Publish QuoteGenerated event (TODO: implement event)
    # from app.events.quote_events import QuoteGenerated
    # event = QuoteGenerated(...)
    # await EventPublisher.publish(event, db=db)

    # Step 6: Build response
    quote_responses = []
    for quote in quotes_created:
        quote_responses.append(QuoteResponse(
            id=quote.id,
            provider=quote.provider,
            insurance_type=quote.insurance_type,
            monthly_premium=float(quote.monthly_premium),
            annual_premium=float(quote.annual_premium),
            coverage_amount=float(quote.coverage_amount),
            status=quote.status,
            ai_score=float(quote.ai_score) if quote.ai_score else None,
            ai_reasoning=quote.ai_reasoning,
            valid_until=quote.valid_until,
            is_recommended=(quote.provider == recommendation.recommended_provider)
        ))

    return QuoteComparisonResponse(
        prospect_id=request.prospect_id,
        insurance_type=request.insurance_type,
        coverage_amount=request.coverage_amount,
        quotes=quote_responses,
        recommended_provider=recommendation.recommended_provider,
        ai_reasoning=recommendation.reasoning,
        risk_assessment=recommendation.risk_assessment,
        additional_notes=recommendation.additional_notes,
        generated_at=date.today().isoformat()
    )


@router.get("/{quote_id}", response_model=QuoteResponse)
def get_quote(
    quote_id: int,
    db: Session = Depends(get_db_session)
):
    """Get a single quote by ID"""
    quote = db.query(Quote).filter(Quote.id == quote_id).first()

    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quote with id {quote_id} not found"
        )

    return QuoteResponse(
        id=quote.id,
        provider=quote.provider,
        insurance_type=quote.insurance_type,
        monthly_premium=float(quote.monthly_premium),
        annual_premium=float(quote.annual_premium),
        coverage_amount=float(quote.coverage_amount),
        status=quote.status,
        ai_score=float(quote.ai_score) if quote.ai_score else None,
        ai_reasoning=quote.ai_reasoning,
        valid_until=quote.valid_until,
        is_recommended=False
    )


@router.get("/prospect/{prospect_id}", response_model=List[QuoteResponse])
def list_prospect_quotes(
    prospect_id: int,
    db: Session = Depends(get_db_session)
):
    """Get all quotes for a specific prospect"""
    quotes = db.query(Quote).filter(Quote.prospect_id == prospect_id).all()

    return [
        QuoteResponse(
            id=quote.id,
            provider=quote.provider,
            insurance_type=quote.insurance_type,
            monthly_premium=float(quote.monthly_premium),
            annual_premium=float(quote.annual_premium),
            coverage_amount=float(quote.coverage_amount),
            status=quote.status,
            ai_score=float(quote.ai_score) if quote.ai_score else None,
            ai_reasoning=quote.ai_reasoning,
            valid_until=quote.valid_until,
            is_recommended=False
        )
        for quote in quotes
    ]
