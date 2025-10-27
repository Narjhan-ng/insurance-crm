"""
Policy model - Active insurance policies
"""
from sqlalchemy import Column, Integer, String, Date, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum
from datetime import date


class PolicyStatus(str, enum.Enum):
    """Policy lifecycle status"""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Policy(Base):
    """
    Insurance policy model.

    BUSINESS LOGIC:
    - Created when Quote is accepted
    - Has unique policy_number (generated)
    - Tracks renewal dates for automated reminders
    - PDF contract stored in pdf_path

    WHY separate from Quote:
    - Quote = offer/proposal (multiple per prospect)
    - Policy = active contract (one active per type per prospect)
    - Different lifecycle and business rules

    DESIGN DECISION: One-to-One with Quote
    - Each policy comes from exactly one quote
    - Quote can exist without policy (if rejected)
    - Policy always references its originating quote (audit trail)
    """
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    quote_id = Column(Integer, ForeignKey("quotes.id"), nullable=False, unique=True, index=True)

    # Policy identification
    # WHY policy_number is separate from id:
    # - Business-facing identifier (shows on documents)
    # - Format: INS-2025-000123 (readable, sortable)
    # - id is internal database key
    policy_number = Column(String(50), unique=True, nullable=False, index=True)

    # Policy period
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    renewal_date = Column(Date, nullable=True, index=True)  # For automated renewal reminders

    # Status
    status = Column(Enum(PolicyStatus), default=PolicyStatus.ACTIVE, index=True)

    # Contract document
    # WHY store path instead of binary:
    # - Smaller database (BLOBs are heavy)
    # - Can serve via CDN/filesystem
    # - Easy to regenerate if lost
    pdf_path = Column(String(255), nullable=True)

    # Audit timestamps
    signed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    quote = relationship("Quote", back_populates="policy", foreign_keys=[quote_id])

    def __repr__(self):
        return f"<Policy {self.policy_number} ({self.status})>"

    @property
    def is_active(self) -> bool:
        """Check if policy is currently active"""
        if self.status != PolicyStatus.ACTIVE:
            return False
        today = date.today()
        return self.start_date <= today <= self.end_date

    @property
    def days_until_expiry(self) -> int:
        """Calculate days until policy expires"""
        if self.status != PolicyStatus.ACTIVE:
            return 0
        today = date.today()
        if today > self.end_date:
            return 0
        return (self.end_date - today).days

    @property
    def is_near_renewal(self) -> bool:
        """Check if policy is within 30 days of renewal"""
        return 0 < self.days_until_expiry <= 30

    @classmethod
    def generate_policy_number(cls) -> str:
        """
        Generate unique policy number.

        FORMAT: INS-YYYY-NNNNNN
        - INS: Insurance prefix
        - YYYY: Year
        - NNNNNN: Sequential 6-digit number

        WHY this format:
        - Human-readable
        - Sortable chronologically
        - Easy to reference in support calls

        PRODUCTION: Use database sequence or Redis counter for thread-safety
        CURRENT: Simple implementation (not production-grade)
        """
        from datetime import datetime
        import random

        year = datetime.now().year
        # In production: SELECT MAX(id) FROM policies or use Redis INCR
        sequence = random.randint(100000, 999999)  # Mock for now

        return f"INS-{year}-{sequence:06d}"
