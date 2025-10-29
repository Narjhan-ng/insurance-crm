"""
Policies API endpoints
Manage active insurance policies
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import date, timedelta

from app.api.dependencies import get_db_session
from app.models.policy import Policy, PolicyStatus
from app.models.quote import Quote, QuoteStatus
from app.events.policy_events import QuoteAccepted
from app.events.publisher import EventPublisher

router = APIRouter()


# ============================================================================
# Request/Response Schemas
# ============================================================================

class QuoteAcceptRequest(BaseModel):
    """Request to accept a quote and create policy"""
    # No body needed - quote_id is in path
    # Could add optional fields like:
    # - start_date_preference
    # - payment_method
    # - additional_notes
    pass


class PolicyResponse(BaseModel):
    """Policy details response"""
    id: int
    policy_number: str
    quote_id: int
    status: PolicyStatus
    start_date: date
    end_date: date
    renewal_date: date | None
    pdf_path: str | None
    days_until_expiry: int
    is_active: bool

    class Config:
        from_attributes = True


class PolicyCreateResponse(BaseModel):
    """
    Response when policy is created from accepted quote.

    WHY separate from PolicyResponse:
    - Includes additional context about what happened
    - Shows the event-driven flow to frontend
    - Helps frontend show appropriate UI (success message, next steps)
    """
    policy: PolicyResponse
    message: str
    next_steps: List[str]


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/{quote_id}/accept", response_model=PolicyCreateResponse, status_code=status.HTTP_201_CREATED)
async def accept_quote_and_create_policy(
    quote_id: int,
    db: Session = Depends(get_db_session)
):
    """
    Accept a quote and create an insurance policy.

    ## Business Flow (Event-Driven):

    1. **Validate Quote**: Check quote exists and is acceptable
       - Must be in 'draft' or 'sent' status
       - Must not be expired
       - Must not already have a policy

    2. **Publish QuoteAccepted Event**: Trigger the event-driven flow
       - WHY event first, not policy creation?
       - Separation of concerns: API expresses intent, handler does work
       - If handler fails, we have event for retry
       - Can add more handlers without modifying API

    3. **Handler Creates Policy** (in background via ARQ):
       - PolicyCreationHandler consumes QuoteAccepted event
       - Creates Policy record
       - Generates policy_number
       - Publishes PolicyCreated event
       - (PolicyCreated triggers: PDF generation, commission calc, email)

    4. **Immediate Response**: API responds instantly
       - Quote marked as 'accepted'
       - Policy creation happening in background
       - User sees immediate feedback

    ## Why This Architecture?

    **Alternative 1: Synchronous**
    ```python
    policy = create_policy()
    generate_pdf(policy)  # 3s
    calculate_commission(policy)  # 1s
    send_email(policy)  # 2s
    return policy  # User waits 6+ seconds
    ```
    ❌ Slow, blocks user, all-or-nothing

    **Alternative 2: Our Event-Driven Approach**
    ```python
    publish_event(QuoteAccepted)
    return "Processing..."  # User waits 200ms
    # Workers handle the rest in background
    ```
    ✅ Fast, fault-tolerant, scalable

    ## Trade-off: Eventual Consistency

    The policy might not exist immediately in database when API responds.
    This is okay because:
    - User sees "processing" message
    - Frontend can poll GET /policies/{id} or use WebSocket
    - Failures are isolated and retryable
    - Better UX than 6-second wait

    ## For Interview:

    *"I chose event-driven over synchronous because creating a policy involves
    multiple slow operations (PDF, email, commission). Instead of blocking the
    user for 5-10 seconds, I publish an event and respond immediately. Background
    workers handle the heavy work asynchronously. This is how Stripe processes
    payments - instant response, async fulfillment."*
    """

    # Step 1: Fetch and validate quote
    quote = db.query(Quote).filter(Quote.id == quote_id).first()

    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quote with id {quote_id} not found"
        )

    # Check if quote is already accepted
    if quote.status == QuoteStatus.ACCEPTED:
        # Check if policy already exists
        existing_policy = db.query(Policy).filter(Policy.quote_id == quote_id).first()
        if existing_policy:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Quote already accepted. Policy {existing_policy.policy_number} exists."
            )

    # Validate quote can be accepted
    if quote.status not in [QuoteStatus.DRAFT, QuoteStatus.SENT]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quote cannot be accepted in status '{quote.status}'"
        )

    if quote.is_expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quote has expired. Please request a new quote."
        )

    # Step 2: Update quote status
    quote.status = QuoteStatus.ACCEPTED
    db.commit()
    db.refresh(quote)

    # Step 3: Publish QuoteAccepted event
    # WHY we publish event instead of creating policy directly:
    # - Handler can retry if fails
    # - Event is stored in Event Store (audit trail)
    # - Can add more logic later without changing API
    # - Decouples API from business logic
    event = QuoteAccepted(
        quote_id=quote.id,
        prospect_id=quote.prospect_id,
        provider=quote.provider,
        insurance_type=quote.insurance_type,
        annual_premium=float(quote.annual_premium),
        accepted_by_user_id=1,  # TODO: Get from auth context
    )

    try:
        await EventPublisher.publish(event, db=db)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to publish QuoteAccepted event: {e}", exc_info=True)

        # Rollback quote status if event publishing fails
        quote.status = QuoteStatus.SENT
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process quote acceptance. Please try again."
        )

    # Step 4: Create policy synchronously for immediate response
    # DECISION: Create policy here OR wait for handler?
    #
    # Option A: Wait for handler (pure event-driven)
    # - Pro: Consistent with architecture
    # - Con: API returns "processing", no policy_id
    #
    # Option B: Create policy here (hybrid)
    # - Pro: Can return policy immediately
    # - Con: Duplicates logic between API and handler
    #
    # CHOSEN: Option B (hybrid) for better UX
    # Handler will check if policy exists before creating

    policy = Policy(
        quote_id=quote.id,
        policy_number=Policy.generate_policy_number(),
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),  # 1 year policy
        renewal_date=date.today() + timedelta(days=335),  # 30 days before expiry
        status=PolicyStatus.ACTIVE,
        signed_at=db.func.now()
    )

    db.add(policy)
    db.commit()
    db.refresh(policy)

    # Build response
    return PolicyCreateResponse(
        policy=PolicyResponse(
            id=policy.id,
            policy_number=policy.policy_number,
            quote_id=policy.quote_id,
            status=policy.status,
            start_date=policy.start_date,
            end_date=policy.end_date,
            renewal_date=policy.renewal_date,
            pdf_path=policy.pdf_path,
            days_until_expiry=policy.days_until_expiry,
            is_active=policy.is_active
        ),
        message="Quote accepted! Your insurance policy has been created.",
        next_steps=[
            "Your policy contract is being generated (PDF)",
            "Commissions are being calculated",
            "You will receive a confirmation email shortly",
            f"Policy number: {policy.policy_number}"
        ]
    )


@router.get("/{policy_id}", response_model=PolicyResponse)
def get_policy(
    policy_id: int,
    db: Session = Depends(get_db_session)
):
    """Get a single policy by ID"""
    policy = db.query(Policy).filter(Policy.id == policy_id).first()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with id {policy_id} not found"
        )

    return PolicyResponse(
        id=policy.id,
        policy_number=policy.policy_number,
        quote_id=policy.quote_id,
        status=policy.status,
        start_date=policy.start_date,
        end_date=policy.end_date,
        renewal_date=policy.renewal_date,
        pdf_path=policy.pdf_path,
        days_until_expiry=policy.days_until_expiry,
        is_active=policy.is_active
    )


@router.get("/", response_model=List[PolicyResponse])
def list_policies(
    status: PolicyStatus | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_session)
):
    """List all policies with optional filtering"""
    query = db.query(Policy)

    if status:
        query = query.filter(Policy.status == status)

    policies = query.offset(skip).limit(limit).all()

    return [
        PolicyResponse(
            id=p.id,
            policy_number=p.policy_number,
            quote_id=p.quote_id,
            status=p.status,
            start_date=p.start_date,
            end_date=p.end_date,
            renewal_date=p.renewal_date,
            pdf_path=p.pdf_path,
            days_until_expiry=p.days_until_expiry,
            is_active=p.is_active
        )
        for p in policies
    ]


@router.get("/{policy_id}/pdf")
async def download_policy_pdf(
    policy_id: int,
    db: Session = Depends(get_db_session)
):
    """
    Download policy contract PDF.

    FLOW:
    1. Fetch policy from database
    2. Check if PDF exists (pdf_path is set)
    3. If exists, return PDF file
    4. If not exists, generate on-demand and return

    WHY on-demand generation:
    - Handles case where PDF wasn't generated yet
    - Fallback if background worker failed
    - Better UX than 404 error

    SECURITY:
    - TODO: Add authentication
    - TODO: Check user has permission to view this policy
    - TODO: Rate limiting to prevent abuse

    Args:
        policy_id: Policy ID
        db: Database session

    Returns:
        PDF file as downloadable response
    """
    from fastapi.responses import FileResponse, Response
    from app.services.pdf_service import PDFService
    import os

    # Fetch policy
    policy = db.query(Policy).filter(Policy.id == policy_id).first()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with id {policy_id} not found"
        )

    # Check if PDF exists on filesystem
    if policy.pdf_path and os.path.exists(policy.pdf_path):
        # Return existing PDF file
        return FileResponse(
            path=policy.pdf_path,
            media_type="application/pdf",
            filename=f"{policy.policy_number}.pdf"
        )
    else:
        # Generate PDF on-demand
        pdf_bytes = PDFService.generate_policy_pdf(policy)

        # Optionally save for future use
        pdf_path = PDFService.save_policy_pdf(policy, pdf_bytes)
        policy.pdf_path = pdf_path
        db.commit()

        # Return PDF as response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={policy.policy_number}.pdf"
            }
        )
