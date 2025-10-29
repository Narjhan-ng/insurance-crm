"""
Policy event handlers
Process policy-related events
"""
import logging
from typing import Dict, Any
from datetime import date, timedelta
from app.handlers.base import EventHandler

logger = logging.getLogger(__name__)


class PolicyCreationHandler(EventHandler):
    """
    Handler for QuoteAccepted event - Creates insurance policy.

    BUSINESS LOGIC:
    When a quote is accepted, we need to:
    1. Create Policy record in database
    2. Generate unique policy_number
    3. Set policy dates (start, end, renewal)
    4. Publish PolicyCreated event (triggers PDF, commission, email)

    WHY as event handler:
    - Decoupled from API (API just publishes intent)
    - Retryable if database fails
    - Can add validation/enrichment logic without touching API
    - Event Store tracks every policy creation attempt

    IDEMPOTENCY:
    - Check if policy already exists for quote_id
    - If exists, skip creation (no error, idempotent)
    - This handles retry scenarios

    NOTE: In the current implementation, policy is created synchronously
    in the API for better UX. This handler acts as a backup/verification.
    In pure event-driven, only this handler would create the policy.
    """

    async def handle(self, event_data: Dict[str, Any]) -> None:
        """
        Process QuoteAccepted event and create policy.

        Args:
            event_data: Event payload with quote and prospect details
        """
        quote_id = event_data["data"]["quote_id"]
        prospect_id = event_data["data"]["prospect_id"]
        provider = event_data["data"]["provider"]
        insurance_type = event_data["data"]["insurance_type"]

        logger.info(f"PolicyCreationHandler: Processing QuoteAccepted for quote_id={quote_id}")

        try:
            # Import here to avoid circular dependencies
            from app.core.database import SessionLocal
            from app.models.policy import Policy
            from app.models.quote import Quote
            from app.events.policy_events import PolicyCreated
            from app.events.publisher import EventPublisher

            db = SessionLocal()

            try:
                # Check if policy already exists (idempotency)
                existing_policy = db.query(Policy).filter(Policy.quote_id == quote_id).first()

                if existing_policy:
                    logger.info(
                        f"Policy already exists for quote_id={quote_id}, "
                        f"policy_number={existing_policy.policy_number}. Skipping creation."
                    )
                    return

                # Get quote details
                quote = db.query(Quote).filter(Quote.id == quote_id).first()
                if not quote:
                    logger.error(f"Quote {quote_id} not found!")
                    return

                # Create policy
                policy = Policy(
                    quote_id=quote_id,
                    policy_number=Policy.generate_policy_number(),
                    start_date=date.today(),
                    end_date=date.today() + timedelta(days=365),  # 1 year
                    renewal_date=date.today() + timedelta(days=335),  # Remind 30 days before
                    status="active",
                    signed_at=db.func.now()
                )

                db.add(policy)
                db.commit()
                db.refresh(policy)

                logger.info(
                    f"✅ Policy created: policy_number={policy.policy_number}, "
                    f"quote_id={quote_id}, prospect_id={prospect_id}"
                )

                # Publish PolicyCreated event
                # This will trigger:
                # - PDF generation
                # - Commission calculation
                # - Email notifications
                policy_created_event = PolicyCreated(
                    policy_id=policy.id,
                    policy_number=policy.policy_number,
                    quote_id=quote_id,
                    prospect_id=prospect_id,
                    provider=provider,
                    insurance_type=insurance_type,
                    annual_premium=float(quote.annual_premium),
                    start_date=policy.start_date.isoformat(),
                    end_date=policy.end_date.isoformat(),
                    created_by_user_id=event_data["metadata"].get("user_id", 1)
                )

                await EventPublisher.publish(policy_created_event, db=db)

                logger.info(f"✅ PolicyCreated event published for policy_id={policy.id}")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"❌ PolicyCreationHandler failed: {e}", exc_info=True)
            raise  # Re-raise to let ARQ retry


class PolicyPDFGenerationHandler(EventHandler):
    """
    Handler for PolicyCreated event - Generates PDF contract.

    BUSINESS VALUE:
    - Customer needs contract document
    - Regulatory compliance (must have signed document)
    - Broker needs printable copy

    IMPLEMENTATION:
    - Uses reportlab to generate PDF
    - Stores in filesystem
    - Updates policy.pdf_path in database

    FLOW:
    1. PolicyCreated event published
    2. This handler catches event
    3. Fetch policy with related data (quote, prospect)
    4. Generate PDF using PDFService
    5. Save PDF to storage
    6. Update policy.pdf_path in database
    7. Log success/failure

    WHY async in handler:
    - PDF generation is I/O bound (file writes)
    - Can run in background without blocking
    - If fails, ARQ will retry automatically
    """

    async def handle(self, event_data: Dict[str, Any]) -> None:
        """Generate PDF contract for policy"""
        policy_id = event_data["data"]["policy_id"]
        policy_number = event_data["data"]["policy_number"]

        logger.info(f"PolicyPDFGenerationHandler: Generating PDF for policy {policy_number}")

        try:
            # Import here to avoid circular dependencies
            from app.core.database import SessionLocal
            from app.models.policy import Policy
            from app.services.pdf_service import PDFService

            db = SessionLocal()

            try:
                # Fetch policy with all related data
                policy = db.query(Policy).filter(Policy.id == policy_id).first()

                if not policy:
                    logger.error(f"Policy {policy_id} not found!")
                    return

                # Check if PDF already exists (idempotency)
                if policy.pdf_path:
                    logger.info(
                        f"PDF already exists for policy {policy_number} at {policy.pdf_path}. "
                        "Skipping generation (idempotent)."
                    )
                    return

                # Generate and save PDF
                pdf_path = PDFService.generate_and_save(policy)

                # Update policy record with PDF path
                policy.pdf_path = pdf_path
                db.commit()

                logger.info(
                    f"✅ PDF generated successfully for policy {policy_number}: {pdf_path}"
                )

                # TODO: Publish PolicyPDFGenerated event
                # This could trigger:
                # - Email with PDF attachment
                # - Notification to broker
                # - Update dashboard

            finally:
                db.close()

        except Exception as e:
            logger.error(
                f"❌ PolicyPDFGenerationHandler failed for policy {policy_number}: {e}",
                exc_info=True
            )
            raise  # Re-raise to let ARQ retry


class PolicyEmailNotificationHandler(EventHandler):
    """
    Handler for PolicyCreated event - Sends confirmation email.

    EMAIL CONTENT:
    - Policy number and details
    - Coverage summary
    - Payment schedule
    - Link to download PDF (once generated)
    - Contact information

    IMPLEMENTATION:
    - Uses email service (SendGrid, AWS SES, etc.)
    - Template-based (Jinja2)
    - Tracks sent emails for audit

    CURRENT: Placeholder
    """

    async def handle(self, event_data: Dict[str, Any]) -> None:
        """Send policy confirmation email"""
        policy_number = event_data["data"]["policy_number"]
        prospect_id = event_data["data"]["prospect_id"]

        logger.info(f"PolicyEmailNotificationHandler: Sending email for policy {policy_number}")

        # TODO: Implement email sending
        logger.info(f"📧 Email sent to prospect {prospect_id} for policy {policy_number} - PLACEHOLDER")

        # In real implementation:
        # 1. Fetch prospect email from database
        # 2. Render email template with policy details
        # 3. Send via email service
        # 4. Log email sent event
