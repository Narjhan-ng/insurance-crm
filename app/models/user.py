"""
User model for authentication and role-based access
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class UserRole(str, enum.Enum):
    """User role enumeration"""
    ADMIN = "admin"
    HEAD_OF_SALES = "head_of_sales"
    MANAGER = "manager"
    BROKER = "broker"
    AFFILIATE = "affiliate"


class User(Base):
    """User model for system authentication and access control"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    supervisor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    supervisor = relationship("User", remote_side=[id], backref="subordinates")
    prospects = relationship("Prospect", foreign_keys="Prospect.assigned_broker", back_populates="broker")
    prospects_created = relationship("Prospect", foreign_keys="Prospect.created_by", back_populates="creator")
    commissions_broker = relationship("Commission", foreign_keys="Commission.broker_id", back_populates="broker")
    commissions_manager = relationship("Commission", foreign_keys="Commission.manager_id", back_populates="manager")
    commissions_affiliate = relationship("Commission", foreign_keys="Commission.affiliate_id", back_populates="affiliate")

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
