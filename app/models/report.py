"""
Report Model
Track generated reports for sales, commissions, and performance analytics
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class ReportType(str, enum.Enum):
    """Types of reports available in the system"""
    SALES_SUMMARY = "sales_summary"
    COMMISSION_BREAKDOWN = "commission_breakdown"
    BROKER_PERFORMANCE = "broker_performance"
    PIPELINE_ANALYSIS = "pipeline_analysis"
    PROVIDER_COMPARISON = "provider_comparison"


class ReportFormat(str, enum.Enum):
    """Export formats for reports"""
    PDF = "pdf"
    CSV = "csv"
    JSON = "json"


class Report(Base):
    """
    Report tracking model.

    WHY we store reports:
    - Audit trail: Who generated what report when
    - Performance: Cache expensive calculations
    - History: Compare metrics over time
    - Compliance: Required for some insurance regulations

    BUSINESS FLOW:
    1. User requests report (date range, filters)
    2. System generates report data
    3. Report metadata stored in database
    4. File exported (PDF/CSV/JSON)
    5. User can re-download same report later

    EXAMPLE USE CASE:
    Manager wants monthly commission breakdown:
    → Generates report for Oct 1-31
    → System calculates all commissions
    → Exports CSV with broker breakdown
    → Report stored with file_path
    → Manager can download again anytime
    """
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)

    # Report metadata
    report_type = Column(Enum(ReportType), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Generation info
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Date range for report
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    # Export info
    format = Column(Enum(ReportFormat), nullable=False)
    file_path = Column(String(500), nullable=True)  # Path to generated file

    # Filters applied (stored as JSON string)
    filters = Column(Text, nullable=True)

    # Report size/stats
    record_count = Column(Integer, nullable=True)

    # Relationships
    user = relationship("User", back_populates="reports")

    def __repr__(self):
        return f"<Report(id={self.id}, type={self.report_type}, generated_by={self.generated_by})>"
