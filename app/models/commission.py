"""
Commission Model
Tracks multi-tier commission system for insurance sales
"""
from sqlalchemy import Column, Integer, String, Numeric, Enum, ForeignKey, DateTime, Date, func
from sqlalchemy.orm import relationship
import enum
from datetime import date

from app.core.database import Base


class CommissionType(str, enum.Enum):
    """
    Commission types in insurance sales lifecycle.

    INITIAL: First-year commission when policy is signed
    RENEWAL_YEAR1: Second year renewal commission
    RENEWAL_RECURRING: Years 3+ recurring commission
    REFERRAL: Commission for referring another broker/affiliate
    """
    INITIAL = "initial"
    RENEWAL_YEAR1 = "renewal_year1"
    RENEWAL_RECURRING = "renewal_recurring"
    REFERRAL = "referral"


class CommissionStatus(str, enum.Enum):
    """
    Commission payment status.

    PENDING: Commission calculated but not approved
    APPROVED: Approved by manager, ready for payment
    PAID: Commission has been paid out
    """
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"


class Commission(Base):
    """
    Commission record for insurance sales.

    BUSINESS LOGIC:
    Multi-tier commission structure:
    - Broker: Direct sales commission (15% initial, 10% year1, 5% recurring)
    - Manager: Override commission on team sales (5% initial, 3% year1, 2% recurring)
    - Affiliate: Referral commission (3% initial, 2% year1, 1% recurring)

    WHY multi-tier:
    - Incentivizes brokers to sell
    - Rewards managers for building teams
    - Encourages referrals for growth

    EXAMPLE CALCULATION:
    Policy annual premium: €1,000
    - Broker earns: €150 (15%)
    - Manager earns: €50 (5%)
    - Affiliate earns: €30 (3%)
    Total commission: €230 (23% of premium)

    RENEWAL COMMISSIONS:
    Year 1: Policy signed - Initial commission
    Year 2: First renewal - renewal_year1 commission (lower %)
    Year 3+: Recurring renewals - renewal_recurring commission (lowest %)

    This ensures:
    - High incentive for new sales
    - Ongoing income for retention
    - Reduces % as acquisition cost is amortized
    """
    __tablename__ = "commissions"

    id = Column(Integer, primary_key=True, index=True)

    # Related entities
    prospect_id = Column(Integer, ForeignKey("prospects.id"), nullable=False)
    broker_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    affiliate_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Commission details
    commission_type = Column(Enum(CommissionType), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)  # Commission amount in €
    percentage = Column(Numeric(5, 2), nullable=False)  # Commission % (e.g., 15.00)
    base_amount = Column(Numeric(10, 2), nullable=False)  # Base amount (annual premium)

    # Status tracking
    status = Column(Enum(CommissionStatus), default=CommissionStatus.PENDING, nullable=False)

    # Period tracking (for reporting)
    period_year = Column(Integer, nullable=True)  # Year of commission (e.g., 2025)
    period_month = Column(Integer, nullable=True)  # Month of commission (1-12)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    prospect = relationship("Prospect", back_populates="commissions")
    broker = relationship("User", foreign_keys=[broker_id])
    manager = relationship("User", foreign_keys=[manager_id])
    affiliate = relationship("User", foreign_keys=[affiliate_id])

    def __repr__(self):
        return f"<Commission(id={self.id}, type={self.commission_type}, amount={self.amount}, status={self.status})>"

    @property
    def is_paid(self) -> bool:
        """Check if commission has been paid"""
        return self.status == CommissionStatus.PAID

    @property
    def is_pending(self) -> bool:
        """Check if commission is pending approval"""
        return self.status == CommissionStatus.PENDING

    def approve(self):
        """Approve commission for payment"""
        if self.status == CommissionStatus.PENDING:
            self.status = CommissionStatus.APPROVED

    def mark_as_paid(self, paid_at: date = None):
        """
        Mark commission as paid.

        Args:
            paid_at: Payment date (defaults to today)
        """
        self.status = CommissionStatus.PAID
        self.paid_at = paid_at or date.today()
