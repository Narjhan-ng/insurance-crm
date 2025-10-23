"""
Event Store model - audit trail for all system events
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class EventStore(Base):
    """
    Event Store for audit trail and event sourcing.
    Records all events that occur in the system.
    """
    __tablename__ = "event_store"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(50), unique=True, nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    aggregate_type = Column(String(50), nullable=False, index=True)
    aggregate_id = Column(String(50), nullable=False, index=True)

    # Event data and metadata
    data = Column(JSON, nullable=False)
    metadata = Column(JSON, nullable=True)

    # Tracking
    user_id = Column(Integer, nullable=True, index=True)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Processing status
    is_processed = Column(Integer, default=0, index=True)  # Boolean as int for better indexing
    processed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<EventStore {self.event_type} ({self.aggregate_type}:{self.aggregate_id})>"

    @property
    def is_processed_bool(self):
        """Get is_processed as boolean"""
        return bool(self.is_processed)

    def mark_as_processed(self):
        """Mark event as processed"""
        self.is_processed = 1
        self.processed_at = func.now()
