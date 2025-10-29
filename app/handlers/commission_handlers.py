"""
Commission event handlers
Calculate commissions when policies are created/renewed
"""
import logging
from typing import Dict, Any

from app.handlers.base import EventHandler
from app.services.commission_service import CommissionService


logger = logging.getLogger(__name__)


class CommissionCalculationHandler(EventHandler):
    """
    Handler for PolicyCreated event - Calculate initial commissions.

    BUSINESS FLOW:
    1. Policy is signed (PolicyCreated event published)
    2. This handler catches the event
    3. Calculates commissions for broker, manager, affiliate
    4. Creates commission records in database
    5. Commissions start in PENDING status (awaiting approval)

    WHY event-driven:
    - Decouple policy creation from commission calculation
    - If commission calc fails, policy is still created
    - Can retry commission calculation independently
    - Easy to add new commission rules without touching policy code

    IDEMPOTENCY:
    - Checks if commissions already exist for this policy
    - Skips calculation if already done
    - Safe to replay events

    EXAMPLE SCENARIO:
    Policy signed for €2,000/year premium
    Broker: Alice (ID: 5)
    Manager: Bob (ID: 3, Alice's supervisor)
    No affiliate

    Result:
    - Alice gets €300 commission (15%)
    - Bob gets €100 commission (5%)
    Total: €400 in commissions created

    These commissions are PENDING until manager approves them.
    """

    async def handle(self, event_data: Dict[str, Any]) -> None:
        """
        Process PolicyCreated event and calculate commissions.

        Args:
            event_data: Event payload containing policy details

        Event structure:
        {
            "event_type": "PolicyCreated",
            "data": {
                "policy_id": 123,
                "policy_number": "POL-2025-001",
                "quote_id": 456,
                "prospect_id": 789,
                "annual_premium": 2000.00,
                ...
            },
            "metadata": {
                "user_id": 1,
                ...
            }
        }
        """
        policy_id = event_data["data"]["policy_id"]
        prospect_id = event_data["data"]["prospect_id"]

        logger.info(
            f"CommissionCalculationHandler: Processing PolicyCreated for policy_id={policy_id}"
        )

        try:
            # Import here to avoid circular dependencies
            from app.core.database import SessionLocal
            from app.models.policy import Policy
            from app.models.commission import Commission
            from app.models.user import User

            db = SessionLocal()

            try:
                # Check if commissions already exist (idempotency)
                existing_commissions = db.query(Commission).join(
                    Policy
                ).filter(
                    Policy.id == policy_id
                ).first()

                if existing_commissions:
                    logger.info(
                        f"Commissions already exist for policy_id={policy_id}. "
                        "Skipping calculation (idempotent)."
                    )
                    return

                # Get policy with related data
                policy = db.query(Policy).filter(Policy.id == policy_id).first()

                if not policy:
                    logger.error(f"Policy {policy_id} not found!")
                    return

                # Get broker assigned to this prospect
                broker = CommissionService.get_broker_for_prospect(prospect_id, db)

                if not broker:
                    logger.warning(
                        f"No broker assigned to prospect {prospect_id}. "
                        "Skipping commission calculation."
                    )
                    return

                # Get manager (broker's supervisor)
                manager = None
                if broker.supervisor_id:
                    manager = db.query(User).filter(User.id == broker.supervisor_id).first()

                # Get affiliate (if any)
                # TODO: Implement affiliate tracking in prospect model
                # For now, affiliate is None
                affiliate = None

                # Calculate initial commissions
                commissions = CommissionService.calculate_initial_commissions(
                    policy=policy,
                    broker=broker,
                    db=db,
                    manager=manager,
                    affiliate=affiliate
                )

                # Save commissions to database
                for commission in commissions:
                    db.add(commission)

                db.commit()

                # Log success
                logger.info(
                    f"✅ Created {len(commissions)} commission records for "
                    f"policy {policy.policy_number}:"
                )

                for comm in commissions:
                    logger.info(
                        f"   - {comm.commission_type.value}: "
                        f"€{comm.amount} ({comm.percentage}%) "
                        f"for broker_id={comm.broker_id}"
                    )

                # TODO: Publish CommissionCreated event
                # This could trigger:
                # - Email notification to broker
                # - Update dashboard metrics
                # - Sync to accounting system

            finally:
                db.close()

        except Exception as e:
            logger.error(
                f"❌ CommissionCalculationHandler failed for policy_id={policy_id}: {e}",
                exc_info=True
            )
            raise  # Re-raise to let ARQ retry


class PolicyRenewalCommissionHandler(EventHandler):
    """
    Handler for PolicyRenewed event - Calculate renewal commissions.

    FUTURE IMPLEMENTATION:
    This handler will be triggered when a policy is renewed.

    Event: PolicyRenewed
    Data: policy_id, renewal_year, new_premium

    Logic:
    - Determine renewal year (1 for first renewal, 2+ for recurring)
    - Calculate renewal commissions at lower rates
    - Create commission records

    TODO: Implement when renewal workflow is built
    """

    async def handle(self, event_data: Dict[str, Any]) -> None:
        """
        Process PolicyRenewed event.

        Args:
            event_data: Event payload
        """
        logger.info("PolicyRenewalCommissionHandler: Not yet implemented")
        # TODO: Implement renewal commission calculation
        pass
