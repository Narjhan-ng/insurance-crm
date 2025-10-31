"""
Advisory API endpoints - AI-powered insurance recommendations

This module provides endpoints for generating personalized insurance advisory
recommendations using LangGraph multi-step workflow.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import logging

from app.api.dependencies import get_db_session
from app.models.prospect import Prospect
from app.models.advisory_offer import AdvisoryOffer, AdvisoryStatus
from app.services.advisory_service import AdvisoryService

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class GenerateAdvisoryRequest(BaseModel):
    """Request to generate advisory recommendations"""
    prospect_id: int = Field(..., description="ID of the prospect")
    insurance_type: str = Field(..., description="Type of insurance (life/auto/home/health)")

    class Config:
        json_schema_extra = {
            "example": {
                "prospect_id": 1,
                "insurance_type": "life"
            }
        }


class AdvisoryOfferResponse(BaseModel):
    """Single advisory offer response"""
    id: int
    provider: str
    rank: int
    score: float
    estimated_premium_monthly: Optional[float]
    estimated_premium_annual: Optional[float]
    estimated_coverage_amount: Optional[float]
    pros: Optional[List[str]]
    cons: Optional[List[str]]
    key_features: Optional[List[str]]
    reasoning: Optional[str]

    class Config:
        from_attributes = True


class AdvisoryResponse(BaseModel):
    """Complete advisory generation response"""
    success: bool
    prospect_id: int
    insurance_type: str
    workflow_path: List[str]
    recommendations_count: int
    recommendations: List[AdvisoryOfferResponse]
    personalized_message: Optional[str]
    message_tone: Optional[str]
    call_to_action: Optional[str]


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/generate", response_model=AdvisoryResponse, status_code=status.HTTP_201_CREATED)
async def generate_advisory(
    request: GenerateAdvisoryRequest,
    db: Session = Depends(get_db_session)
):
    """
    Generate personalized advisory recommendations using LangGraph workflow.

    ## Process Flow:
    1. **Fetch Prospect** - Load prospect data from database
    2. **Execute LangGraph Workflow**:
       - Profile Extraction: Normalize prospect data
       - Eligibility Check: Verify which providers are available
       - Risk Analysis: AI analyzes prospect's risk profile (if eligible)
       - Recommendations: AI ranks providers with reasoning
       - Personalization: AI adapts message to prospect
    3. **Save to Database** - Store all recommendations
    4. **Return Response** - Structured advisory with personalized message

    ## Conditional Workflow:
    - If NO providers eligible -> Returns empathetic explanation
    - If providers available -> Returns ranked recommendations

    ## Why LangGraph:
    - Multi-step analysis with shared state
    - Conditional routing based on eligibility
    - Better observability (each node traceable)
    - Easier to extend with new analysis steps

    ## Example Response:
    ```json
    {
      "success": true,
      "prospect_id": 1,
      "insurance_type": "life",
      "workflow_path": ["profile_extractor", "eligibility_checker", "risk_analyzer", "recommender", "personalizer"],
      "recommendations_count": 3,
      "recommendations": [
        {
          "id": 1,
          "provider": "Generali",
          "rank": 1,
          "score": 87.5,
          "pros": ["Best value for your age group", "Comprehensive coverage"],
          "reasoning": "Generali offers the best balance..."
        }
      ],
      "personalized_message": "Based on your profile...",
      "call_to_action": "Schedule a call to discuss details"
    }
    ```
    """
    logger.info(f"Generating advisory for prospect {request.prospect_id}, type: {request.insurance_type}")

    # Step 1: Fetch prospect from database
    prospect = db.query(Prospect).filter(Prospect.id == request.prospect_id).first()

    if not prospect:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prospect with ID {request.prospect_id} not found"
        )

    # Step 2: Initialize and execute LangGraph workflow
    try:
        advisory_service = AdvisoryService()
        final_state = await advisory_service.generate_advisory(
            prospect=prospect,
            insurance_type=request.insurance_type
        )

        # Check for workflow errors
        if final_state.get("error"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Advisory generation failed: {final_state['error']}"
            )

    except Exception as e:
        logger.error(f"LangGraph workflow failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate advisory: {str(e)}"
        )

    # Step 3: Save recommendations to database
    saved_offers = []

    # Check if we have recommendations (eligibility success path)
    if final_state.get("advisory_recommendations"):
        recommendations = final_state["advisory_recommendations"].recommendations

        for rec in recommendations:
            # Find matching eligible provider for pricing
            eligible_provider = next(
                (p for p in final_state["eligible_providers"] if p.provider == rec.provider),
                None
            )

            advisory_offer = AdvisoryOffer(
                prospect_id=prospect.id,
                provider=rec.provider,
                insurance_type=request.insurance_type,
                rank=rec.rank,
                score=Decimal(str(rec.score)),
                estimated_premium_monthly=Decimal(str(eligible_provider.base_premium)) if eligible_provider else None,
                estimated_premium_annual=Decimal(str(eligible_provider.base_premium * 12)) if eligible_provider else None,
                estimated_coverage_amount=Decimal(str(eligible_provider.coverage_max)) if eligible_provider else None,
                pros=rec.pros,
                cons=rec.cons,
                key_features=rec.key_features,
                reasoning=rec.reasoning,
                personalized_message=final_state["personalized_message"].message if final_state.get("personalized_message") else None,
                workflow_stage=final_state["stage"],
                ai_confidence=Decimal(str(rec.score)),
                status=AdvisoryStatus.DRAFT
            )

            db.add(advisory_offer)
            saved_offers.append(advisory_offer)

        db.commit()

        # Refresh to get IDs
        for offer in saved_offers:
            db.refresh(offer)

        logger.info(f"Saved {len(saved_offers)} advisory offers for prospect {prospect.id}")

    # Step 4: Build response
    response = AdvisoryResponse(
        success=True,
        prospect_id=prospect.id,
        insurance_type=request.insurance_type,
        workflow_path=final_state["workflow_path"],
        recommendations_count=len(saved_offers),
        recommendations=[
            AdvisoryOfferResponse(
                id=offer.id,
                provider=offer.provider,
                rank=offer.rank,
                score=float(offer.score),
                estimated_premium_monthly=float(offer.estimated_premium_monthly) if offer.estimated_premium_monthly else None,
                estimated_premium_annual=float(offer.estimated_premium_annual) if offer.estimated_premium_annual else None,
                estimated_coverage_amount=float(offer.estimated_coverage_amount) if offer.estimated_coverage_amount else None,
                pros=offer.pros,
                cons=offer.cons,
                key_features=offer.key_features,
                reasoning=offer.reasoning
            )
            for offer in saved_offers
        ],
        personalized_message=final_state.get("personalized_message").message if final_state.get("personalized_message") else None,
        message_tone=final_state.get("personalized_message").tone if final_state.get("personalized_message") else None,
        call_to_action=final_state.get("personalized_message").call_to_action if final_state.get("personalized_message") else None
    )

    return response


@router.get("/prospect/{prospect_id}", response_model=List[AdvisoryOfferResponse])
async def get_prospect_advisories(
    prospect_id: int,
    insurance_type: Optional[str] = None,
    db: Session = Depends(get_db_session)
):
    """
    Get all advisory offers for a specific prospect.

    Optionally filter by insurance type.
    Returns offers ordered by rank (best first).
    """
    logger.info(f"Fetching advisories for prospect {prospect_id}")

    query = db.query(AdvisoryOffer).filter(AdvisoryOffer.prospect_id == prospect_id)

    if insurance_type:
        query = query.filter(AdvisoryOffer.insurance_type == insurance_type)

    offers = query.order_by(AdvisoryOffer.rank).all()

    if not offers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No advisory offers found for prospect {prospect_id}"
        )

    return [
        AdvisoryOfferResponse(
            id=offer.id,
            provider=offer.provider,
            rank=offer.rank,
            score=float(offer.score),
            estimated_premium_monthly=float(offer.estimated_premium_monthly) if offer.estimated_premium_monthly else None,
            estimated_premium_annual=float(offer.estimated_premium_annual) if offer.estimated_premium_annual else None,
            estimated_coverage_amount=float(offer.estimated_coverage_amount) if offer.estimated_coverage_amount else None,
            pros=offer.pros,
            cons=offer.cons,
            key_features=offer.key_features,
            reasoning=offer.reasoning
        )
        for offer in offers
    ]


@router.get("/{advisory_id}", response_model=AdvisoryOfferResponse)
async def get_advisory(
    advisory_id: int,
    db: Session = Depends(get_db_session)
):
    """Get a specific advisory offer by ID"""
    logger.info(f"Fetching advisory {advisory_id}")

    offer = db.query(AdvisoryOffer).filter(AdvisoryOffer.id == advisory_id).first()

    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Advisory offer {advisory_id} not found"
        )

    return AdvisoryOfferResponse(
        id=offer.id,
        provider=offer.provider,
        rank=offer.rank,
        score=float(offer.score),
        estimated_premium_monthly=float(offer.estimated_premium_monthly) if offer.estimated_premium_monthly else None,
        estimated_premium_annual=float(offer.estimated_premium_annual) if offer.estimated_premium_annual else None,
        estimated_coverage_amount=float(offer.estimated_coverage_amount) if offer.estimated_coverage_amount else None,
        pros=offer.pros,
        cons=offer.cons,
        key_features=offer.key_features,
        reasoning=offer.reasoning
    )


@router.patch("/{advisory_id}/status", response_model=AdvisoryOfferResponse)
async def update_advisory_status(
    advisory_id: int,
    status: AdvisoryStatus,
    db: Session = Depends(get_db_session)
):
    """
    Update the status of an advisory offer.

    Statuses: draft, sent, viewed, accepted, declined
    """
    logger.info(f"Updating advisory {advisory_id} status to {status}")

    offer = db.query(AdvisoryOffer).filter(AdvisoryOffer.id == advisory_id).first()

    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Advisory offer {advisory_id} not found"
        )

    offer.status = status

    # Update timestamps based on status
    if status == AdvisoryStatus.SENT and not offer.sent_at:
        offer.sent_at = datetime.utcnow()
    elif status == AdvisoryStatus.VIEWED and not offer.viewed_at:
        offer.viewed_at = datetime.utcnow()

    db.commit()
    db.refresh(offer)

    return AdvisoryOfferResponse(
        id=offer.id,
        provider=offer.provider,
        rank=offer.rank,
        score=float(offer.score),
        estimated_premium_monthly=float(offer.estimated_premium_monthly) if offer.estimated_premium_monthly else None,
        estimated_premium_annual=float(offer.estimated_premium_annual) if offer.estimated_premium_annual else None,
        estimated_coverage_amount=float(offer.estimated_coverage_amount) if offer.estimated_coverage_amount else None,
        pros=offer.pros,
        cons=offer.cons,
        key_features=offer.key_features,
        reasoning=offer.reasoning
    )
