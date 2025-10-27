"""
Policy domain events
Events related to insurance policy lifecycle
"""
from app.events.base import DomainEvent


class PolicyCreated(DomainEvent):
    """
    Event: New insurance policy created from accepted quote.

    TRIGGERS:
    - Commission calculation (event handler)
    - PDF contract generation (event handler)
    - Welcome email with policy details (event handler)
    - Notification to broker (event handler)

    BUSINESS IMPACT:
    - Broker earns commission
    - Customer receives contract
    - Policy is now active and billable

    WHY as event:
    - Policy creation has multiple side effects
    - Each side effect is independent
    - Failure isolation (PDF fails? Commission still calculated)
    """

    def __init__(
        self,
        policy_id: int,
        policy_number: str,
        quote_id: int,
        prospect_id: int,
        provider: str,
        insurance_type: str,
        annual_premium: float,
        start_date: str,
        end_date: str,
        created_by_user_id: int,
    ):
        super().__init__(
            event_type="PolicyCreated",
            aggregate_type="policy",
            aggregate_id=str(policy_id),
            data={
                "policy_id": policy_id,
                "policy_number": policy_number,
                "quote_id": quote_id,
                "prospect_id": prospect_id,
                "provider": provider,
                "insurance_type": insurance_type,
                "annual_premium": annual_premium,
                "start_date": start_date,
                "end_date": end_date,
            },
            metadata={
                "user_id": created_by_user_id,
            }
        )


class QuoteAccepted(DomainEvent):
    """
    Event: Customer accepted an insurance quote.

    This is the TRIGGER event that leads to PolicyCreated.

    FLOW:
    1. Customer clicks "Accept Quote" in UI
    2. API publishes QuoteAccepted event
    3. PolicyCreationHandler consumes event
    4. Handler creates Policy record
    5. Handler publishes PolicyCreated event
    6. Multiple handlers react to PolicyCreated

    WHY separate from PolicyCreated:
    - Separation of intent (user action) vs outcome (policy created)
    - Quote acceptance might fail validation
    - Can track "accepted but not yet created" state
    """

    def __init__(
        self,
        quote_id: int,
        prospect_id: int,
        provider: str,
        insurance_type: str,
        annual_premium: float,
        accepted_by_user_id: int,
    ):
        super().__init__(
            event_type="QuoteAccepted",
            aggregate_type="quote",
            aggregate_id=str(quote_id),
            data={
                "quote_id": quote_id,
                "prospect_id": prospect_id,
                "provider": provider,
                "insurance_type": insurance_type,
                "annual_premium": annual_premium,
            },
            metadata={
                "user_id": accepted_by_user_id,
            }
        )


class PolicyExpiring(DomainEvent):
    """
    Event: Policy is expiring soon (within 30 days).

    TRIGGERED BY: Scheduled job (runs daily)

    HANDLERS:
    - Send renewal reminder email
    - Generate renewal quote
    - Notify broker to contact customer

    WHY event:
    - Decouples renewal logic from cron job
    - Can add more renewal actions without modifying scheduler
    """

    def __init__(
        self,
        policy_id: int,
        policy_number: str,
        prospect_id: int,
        days_until_expiry: int,
        provider: str,
        insurance_type: str,
    ):
        super().__init__(
            event_type="PolicyExpiring",
            aggregate_type="policy",
            aggregate_id=str(policy_id),
            data={
                "policy_id": policy_id,
                "policy_number": policy_number,
                "prospect_id": prospect_id,
                "days_until_expiry": days_until_expiry,
                "provider": provider,
                "insurance_type": insurance_type,
            }
        )


class PolicyCancelled(DomainEvent):
    """
    Event: Policy was cancelled by customer or system.

    HANDLERS:
    - Calculate pro-rated refund
    - Adjust commissions (clawback if within period)
    - Send cancellation confirmation
    - Update dashboard metrics
    """

    def __init__(
        self,
        policy_id: int,
        policy_number: str,
        prospect_id: int,
        cancellation_reason: str,
        cancelled_by_user_id: int,
    ):
        super().__init__(
            event_type="PolicyCancelled",
            aggregate_type="policy",
            aggregate_id=str(policy_id),
            data={
                "policy_id": policy_id,
                "policy_number": policy_number,
                "prospect_id": prospect_id,
                "cancellation_reason": cancellation_reason,
            },
            metadata={
                "user_id": cancelled_by_user_id,
            }
        )
