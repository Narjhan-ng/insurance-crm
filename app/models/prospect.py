"""
Prospect model - insurance leads and customers
"""
from sqlalchemy import Column, Integer, String, Date, Enum, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ProspectType(str, enum.Enum):
    """Type of insurance prospect"""
    INDIVIDUAL = "individual"
    FAMILY = "family"
    BUSINESS = "business"


class ProspectStatus(str, enum.Enum):
    """Prospect lifecycle status"""
    NEW = "new"
    CONTACTED = "contacted"
    QUOTED = "quoted"
    POLICY_SIGNED = "policy_signed"
    DECLINED = "declined"


class RiskCategory(str, enum.Enum):
    """Risk assessment category"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Prospect(Base):
    """Prospect/Lead model for insurance customers"""
    __tablename__ = "prospects"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(ProspectType), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    birth_date = Column(Date, nullable=True)
    email = Column(String(255), index=True)
    phone = Column(String(20))
    tax_code = Column(String(20), unique=True, index=True)
    status = Column(Enum(ProspectStatus), default=ProspectStatus.NEW, index=True)
    risk_category = Column(Enum(RiskCategory), nullable=True)
    assigned_broker = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    broker = relationship("User", foreign_keys=[assigned_broker], back_populates="prospects")
    creator = relationship("User", foreign_keys=[created_by], back_populates="prospects_created")
    quotes = relationship("Quote", back_populates="prospect", cascade="all, delete-orphan")
    commissions = relationship("Commission", back_populates="prospect")
    # advisory_offers = relationship("AdvisoryOffer", back_populates="prospect", cascade="all, delete-orphan")  # TODO: Uncomment when AdvisoryOffer model is implemented

    @property
    def full_name(self):
        """Get prospect's full name"""
        return f"{self.first_name} {self.last_name}".strip()

    def __repr__(self):
        return f"<Prospect {self.full_name} ({self.status})>"
