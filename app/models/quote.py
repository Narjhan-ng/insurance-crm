"""
Quote model - insurance quote offers
"""
from sqlalchemy import Column, Integer, String, Numeric, Date, Enum, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class QuoteStatus(str, enum.Enum):
    """Quote lifecycle status"""
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Quote(Base):
    """
    Insurance quote model.

    DESIGN DECISION: Why store individual quotes vs aggregated comparison?
    - Each quote is a separate record (one per provider)
    - Allows tracking individual quote status
    - Can send multiple quotes to customer, they accept one
    - Historical tracking: see which quotes were rejected and why

    ALTERNATIVE: Single "QuoteComparison" record with JSON array of offers
    - Pros: Simpler queries, atomic comparison
    - Cons: Can't track status per quote, harder to reference individual quotes

    CHOSE: Individual quotes for flexibility and tracking
    """
    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True, index=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id"), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    insurance_type = Column(String(50), nullable=False)

    # Pricing
    monthly_premium = Column(Numeric(10, 2), nullable=False)
    annual_premium = Column(Numeric(10, 2), nullable=False)
    coverage_amount = Column(Numeric(10, 2), nullable=False)
    deductible = Column(Numeric(10, 2), nullable=True)

    # Status tracking
    status = Column(Enum(QuoteStatus), default=QuoteStatus.DRAFT, index=True)
    valid_until = Column(Date, nullable=True)

    # AI-generated analysis (stored for audit/compliance)
    # WHY JSON column:
    # - Flexible schema (AI output can evolve)
    # - Don't need to query these fields independently
    # - Keeps model simple (no separate AnalysisResult table)
    ai_score = Column(Numeric(5, 2), nullable=True)  # 0-100 score from AI
    ai_reasoning = Column(JSON, nullable=True)  # {pros: [], cons: [], reasoning: "..."}

    # Coverage details (provider-specific features)
    # WHY JSON: Each provider has different features, hard to normalize
    items = Column(JSON, nullable=True, comment="Coverage details and add-ons")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    prospect = relationship("Prospect", back_populates="quotes")
    policy = relationship("Policy", back_populates="quote", uselist=False)

    def __repr__(self):
        return f"<Quote {self.provider} for Prospect {self.prospect_id} - €{self.monthly_premium}/month>"

    @property
    def is_expired(self) -> bool:
        """Check if quote has expired"""
        if not self.valid_until:
            return False
        from datetime import date
        return date.today() > self.valid_until

    @property
    def is_active(self) -> bool:
        """Check if quote is still actionable"""
        return self.status in [QuoteStatus.DRAFT, QuoteStatus.SENT] and not self.is_expired
