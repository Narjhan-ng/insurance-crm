"""
Base event infrastructure for event-driven architecture
"""
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import uuid


class DomainEvent(BaseModel):
    """
    Base class for all domain events.

    Domain events represent something that has happened in the business domain.
    They are immutable and named in past tense (e.g., ProspectCreated, QuoteGenerated).

    Key principles:
    - Immutable: Once created, cannot be changed
    - Past tense naming: Represents something that already happened
    - Self-contained: Contains all data needed by handlers
    - Metadata: Who, when, where for audit trail
    """

    # Event metadata
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str  # Set by subclass (e.g., "ProspectCreated")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[int] = None  # Who triggered this event

    # Event payload (defined by subclasses)
    # e.g., prospect_id, quote_id, etc.

    class Config:
        frozen = True  # Make immutable
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DomainEvent":
        """Reconstruct event from dictionary"""
        return cls(**data)

    def __repr__(self):
        return f"<{self.event_type} id={self.event_id} at {self.timestamp}>"
