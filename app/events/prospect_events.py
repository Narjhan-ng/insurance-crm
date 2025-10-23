"""
Prospect domain events
"""
from typing import Optional, Literal
from app.events.base import DomainEvent


class ProspectCreated(DomainEvent):
    """
    Event published when a new prospect is created in the system.

    This event triggers:
    - Broker assignment notification
    - Welcome email to prospect
    - Audit log entry
    - Analytics tracking

    Payload:
    - prospect_id: ID of the newly created prospect
    - prospect_type: Type of prospect (individual/family/business)
    - assigned_broker_id: ID of assigned broker (if any)
    - first_name: Prospect's first name (for personalization)
    - email: Prospect's email (for notifications)
    """

    event_type: Literal["ProspectCreated"] = "ProspectCreated"

    # Payload
    prospect_id: int
    prospect_type: str  # individual, family, business
    assigned_broker_id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None

    @property
    def full_name(self) -> str:
        """Get prospect's full name for notifications"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or "Prospect"


class ProspectStatusChanged(DomainEvent):
    """
    Event published when prospect status changes.

    Triggers:
    - Status-specific workflows
    - Notification to broker
    - Dashboard updates
    """

    event_type: Literal["ProspectStatusChanged"] = "ProspectStatusChanged"

    prospect_id: int
    old_status: str
    new_status: str
    changed_by: Optional[int] = None


class ProspectAssignedToBroker(DomainEvent):
    """
    Event published when a prospect is assigned to a broker.

    Triggers:
    - Broker notification
    - Update broker's prospect list
    - Dashboard refresh
    """

    event_type: Literal["ProspectAssignedToBroker"] = "ProspectAssignedToBroker"

    prospect_id: int
    broker_id: int
    previous_broker_id: Optional[int] = None
