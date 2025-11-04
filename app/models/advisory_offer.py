"""
AdvisoryOffer model - AI-generated insurance advisory recommendations
"""
from typing import TYPE_CHECKING
from sqlalchemy import Column, Integer, String, Numeric, Enum, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum

if TYPE_CHECKING:
    from app.models.prospect import Prospect


class AdvisoryStatus(str, enum.Enum):
    """Advisory offer lifecycle status"""
    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class AdvisoryOffer(Base):
    """
    AI-generated advisory recommendation model.

    DESIGN DECISION: Why separate AdvisoryOffer from Quote?
    - Advisory is pre-sales guidance (helps prospect decide)
    - Quote is post-decision pricing (formal offer)
    - Advisory uses LangGraph multi-step analysis
    - Quote uses simple eligibility check + pricing

    WHY individual records per provider (not aggregated)?
    - Track which specific recommendation was accepted
    - Each provider may have different follow-up actions
    - Can query "most accepted provider" for analytics
    - Allows A/B testing different recommendation strategies

    RELATIONSHIP to Quote:
    - Advisory happens FIRST (exploration phase)
    - If prospect likes an advisory, we generate formal Quote
    - advisory_offer.prospect_id links to future quote.prospect_id
    """
    __tablename__ = "advisory_offers"

    id = Column(Integer, primary_key=True, index=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id"), nullable=False, index=True)

    # Provider and product details
    provider = Column(String(50), nullable=False, index=True)
    insurance_type = Column(String(50), nullable=False, index=True)

    # Recommendation ranking
    # WHY rank field: Allows filtering "show me top 3" without parsing JSON
    rank = Column(Integer, nullable=False, comment="1=best match, 2=second best, etc")
    score = Column(Numeric(5, 2), nullable=False, comment="AI confidence score 0-100")

    # Estimated pricing (not binding, just guidance)
    # WHY estimated vs actual: Advisory is exploratory, Quote is binding
    estimated_premium_monthly = Column(Numeric(10, 2), nullable=True)
    estimated_premium_annual = Column(Numeric(10, 2), nullable=True)
    estimated_coverage_amount = Column(Numeric(10, 2), nullable=True)

    # AI-generated analysis (JSON for flexibility)
    # WHY JSON columns:
    # - AI output format may evolve as we improve prompts
    # - Don't need to query inside these fields
    # - Keeps schema simple and flexible
    pros = Column(JSON, nullable=True, comment="List of advantages for this prospect")
    cons = Column(JSON, nullable=True, comment="List of disadvantages/considerations")
    key_features = Column(JSON, nullable=True, comment="Notable coverage features")
    risk_assessment = Column(JSON, nullable=True, comment="Risk analysis specific to prospect")

    # Textual explanations (searchable, for audit)
    reasoning = Column(Text, nullable=True, comment="AI reasoning for this recommendation")
    personalized_message = Column(Text, nullable=True, comment="Personalized message for prospect")

    # Workflow metadata (for debugging and optimization)
    # WHY track workflow stage:
    # - If recommendations fail, we know which LangGraph node caused it
    # - Analytics: which workflow paths lead to best conversions
    # - Debugging: can replay exact graph execution
    workflow_stage = Column(String(50), nullable=True, comment="LangGraph node that generated this")
    ai_confidence = Column(Numeric(5, 2), nullable=True, comment="AI self-assessed confidence")

    # Status tracking
    status = Column(Enum(AdvisoryStatus), default=AdvisoryStatus.DRAFT, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)
    viewed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    prospect = relationship("Prospect", back_populates="advisory_offers")

    def __repr__(self):
        return f"<AdvisoryOffer rank={self.rank} {self.provider} for Prospect {self.prospect_id}>"

    @property
    def is_top_recommendation(self) -> bool:
        """Check if this is the #1 recommended option"""
        return self.rank == 1

    @property
    def is_actionable(self) -> bool:
        """Check if prospect can still act on this advisory"""
        return self.status in [AdvisoryStatus.DRAFT, AdvisoryStatus.SENT, AdvisoryStatus.VIEWED]
