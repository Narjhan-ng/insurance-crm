"""
Reports API endpoints
Generate and export business intelligence reports
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import date, datetime

from app.api.dependencies import get_db_session, get_current_user, require_role
from app.models.user import User, UserRole
from app.models.report import Report, ReportType, ReportFormat
from app.services.report_service import ReportService


router = APIRouter()


# ============================================================================
# Request/Response Schemas
# ============================================================================

class ReportRequest(BaseModel):
    """Base request for report generation"""
    start_date: date = Field(..., description="Report start date (YYYY-MM-DD)")
    end_date: date = Field(..., description="Report end date (YYYY-MM-DD)")
    format: ReportFormat = Field(
        default=ReportFormat.JSON,
        description="Export format (json, csv, pdf)"
    )


class BrokerPerformanceRequest(ReportRequest):
    """Request for broker performance report"""
    broker_id: int = Field(..., description="Broker user ID")


class ReportResponse(BaseModel):
    """Report metadata response"""
    id: int
    report_type: ReportType
    title: str
    generated_by: int
    generated_at: datetime
    start_date: datetime
    end_date: datetime
    format: ReportFormat
    file_path: Optional[str]
    record_count: Optional[int]

    class Config:
        from_attributes = True


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/sales-summary", response_model=dict)
async def generate_sales_summary_report(
    request: ReportRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Generate sales summary report.

    ## Metrics Included:
    - Total policies sold
    - Total premium amount
    - Average premium per policy
    - Conversion rate (quotes → policies)
    - Breakdown by insurance type
    - Breakdown by provider

    ## Role-Based Access:
    - **Broker**: Only their sales
    - **Manager**: Their team's sales
    - **Head of Sales/Admin**: All sales

    ## Export Formats:
    - JSON: Structured data for API consumption
    - CSV: Spreadsheet-ready for Excel analysis
    - PDF: Formatted report for presentations (TODO)

    ## Business Use Case:
    Head of Sales wants monthly performance review:
    → Generates sales summary for Oct 1-31
    → Views breakdown by insurance type (life, auto, home, health)
    → Sees which providers are performing best
    → Identifies conversion bottlenecks
    → Exports CSV for board presentation

    Args:
        request: Report request with date range and format
        db: Database session
        current_user: Authenticated user

    Returns:
        Report data in requested format
    """
    # Validate date range
    if request.start_date > request.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before end_date"
        )

    # Generate report data
    report_data = ReportService.generate_sales_summary(
        db=db,
        start_date=request.start_date,
        end_date=request.end_date,
        user=current_user
    )

    # Save metadata to database
    ReportService.save_report_metadata(
        db=db,
        report_type=ReportType.SALES_SUMMARY,
        title=f"Sales Summary: {request.start_date} to {request.end_date}",
        user_id=current_user.id,
        start_date=request.start_date,
        end_date=request.end_date,
        format=request.format,
        record_count=report_data['summary']['total_policies']
    )

    # Return based on format
    if request.format == ReportFormat.CSV:
        csv_data = ReportService.export_to_csv(report_data, ReportType.SALES_SUMMARY)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=sales_summary_{request.start_date}_{request.end_date}.csv"
            }
        )
    else:
        return report_data


@router.post("/commission-breakdown", response_model=dict)
async def generate_commission_breakdown_report(
    request: ReportRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Generate commission breakdown report.

    ## Metrics Included:
    - Total commissions by status (pending/paid/cancelled)
    - Breakdown by commission type (initial/renewal)
    - Breakdown by broker
    - Manager override commissions
    - Affiliate referral commissions

    ## Role-Based Access:
    - **Broker**: Only their commissions
    - **Manager**: Their team's commissions + their overrides
    - **Head of Sales/Admin**: All commissions

    ## Business Use Case:
    Manager wants to review team earnings:
    → Generates commission breakdown for Q4
    → Sees total pending vs paid commissions
    → Identifies top-earning brokers
    → Tracks renewal commissions separately
    → Exports CSV for payroll processing

    Args:
        request: Report request with date range and format
        db: Database session
        current_user: Authenticated user

    Returns:
        Commission breakdown data
    """
    # Validate date range
    if request.start_date > request.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before end_date"
        )

    # Generate report data
    report_data = ReportService.generate_commission_breakdown(
        db=db,
        start_date=request.start_date,
        end_date=request.end_date,
        user=current_user
    )

    # Save metadata
    ReportService.save_report_metadata(
        db=db,
        report_type=ReportType.COMMISSION_BREAKDOWN,
        title=f"Commission Breakdown: {request.start_date} to {request.end_date}",
        user_id=current_user.id,
        start_date=request.start_date,
        end_date=request.end_date,
        format=request.format,
        record_count=report_data['summary']['total_count']
    )

    # Return based on format
    if request.format == ReportFormat.CSV:
        csv_data = ReportService.export_to_csv(report_data, ReportType.COMMISSION_BREAKDOWN)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=commission_breakdown_{request.start_date}_{request.end_date}.csv"
            }
        )
    else:
        return report_data


@router.post("/broker-performance", response_model=dict)
async def generate_broker_performance_report(
    request: BrokerPerformanceRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Generate individual broker performance report.

    ## Metrics Included:
    - Prospects assigned vs converted
    - Quotes generated vs accepted
    - Policies sold
    - Total commissions earned
    - Average deal size
    - Conversion funnel metrics

    ## Role-Based Access:
    - **Broker**: Only their own performance
    - **Manager**: Their team members' performance
    - **Head of Sales/Admin**: Any broker's performance

    ## Business Use Case:
    Manager conducting quarterly review:
    → Generates performance report for broker
    → Reviews conversion funnel (prospects → quotes → policies)
    → Identifies bottlenecks (low quote acceptance?)
    → Tracks commission earnings
    → Discusses improvement areas in 1-on-1 meeting

    Args:
        request: Report request with broker_id, date range, and format
        db: Database session
        current_user: Authenticated user

    Returns:
        Broker performance data
    """
    # Validate date range
    if request.start_date > request.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before end_date"
        )

    # Role-based access control
    if current_user.role == UserRole.BROKER:
        # Brokers can only see their own performance
        if request.broker_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own performance report"
            )
    elif current_user.role == UserRole.MANAGER:
        # Managers can see their team's performance
        broker = db.query(User).filter(User.id == request.broker_id).first()
        if not broker or broker.supervisor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your team members' performance"
            )

    # Generate report data
    try:
        report_data = ReportService.generate_broker_performance(
            db=db,
            start_date=request.start_date,
            end_date=request.end_date,
            broker_id=request.broker_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    # Save metadata
    ReportService.save_report_metadata(
        db=db,
        report_type=ReportType.BROKER_PERFORMANCE,
        title=f"Broker Performance: {report_data['broker']['name']} ({request.start_date} to {request.end_date})",
        user_id=current_user.id,
        start_date=request.start_date,
        end_date=request.end_date,
        format=request.format,
        record_count=report_data['funnel']['policies_sold']
    )

    # Return based on format
    if request.format == ReportFormat.CSV:
        csv_data = ReportService.export_to_csv(report_data, ReportType.BROKER_PERFORMANCE)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=broker_performance_{request.broker_id}_{request.start_date}_{request.end_date}.csv"
            }
        )
    else:
        return report_data


@router.get("/history", response_model=List[ReportResponse])
async def get_report_history(
    report_type: Optional[ReportType] = None,
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get report generation history.

    Returns list of previously generated reports with metadata.
    Useful for:
    - Re-downloading past reports
    - Tracking who generated what reports
    - Audit trail for compliance

    ## Role-Based Access:
    - **Broker**: Only their generated reports
    - **Manager**: Their team's reports + their own
    - **Head of Sales/Admin**: All reports

    Args:
        report_type: Filter by report type (optional)
        skip: Pagination offset
        limit: Max results (max 200)
        db: Database session
        current_user: Authenticated user

    Returns:
        List of report metadata
    """
    query = db.query(Report)

    # Filter by report type if specified
    if report_type:
        query = query.filter(Report.report_type == report_type)

    # Role-based filtering
    if current_user.role == UserRole.BROKER:
        query = query.filter(Report.generated_by == current_user.id)
    elif current_user.role == UserRole.MANAGER:
        # Manager sees their team's reports
        team_ids = db.query(User.id).filter(User.supervisor_id == current_user.id).all()
        team_ids = [current_user.id] + [t[0] for t in team_ids]
        query = query.filter(Report.generated_by.in_(team_ids))

    # Order by most recent first
    query = query.order_by(Report.generated_at.desc())

    # Pagination
    reports = query.offset(skip).limit(limit).all()

    return reports


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report_by_id(
    report_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get specific report metadata by ID.

    Args:
        report_id: Report ID
        db: Database session
        current_user: Authenticated user

    Returns:
        Report metadata

    Raises:
        HTTPException 404: Report not found
        HTTPException 403: Insufficient permissions
    """
    report = db.query(Report).filter(Report.id == report_id).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with id {report_id} not found"
        )

    # Role-based access control
    if current_user.role == UserRole.BROKER:
        if report.generated_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own reports"
            )
    elif current_user.role == UserRole.MANAGER:
        # Check if report was generated by team member
        team_ids = db.query(User.id).filter(User.supervisor_id == current_user.id).all()
        team_ids = [current_user.id] + [t[0] for t in team_ids]
        if report.generated_by not in team_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your team's reports"
            )

    return report


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.HEAD_OF_SALES]))
):
    """
    Delete a report (admin only).

    Removes report metadata from database.
    NOTE: Does not delete the actual file if it exists.

    Args:
        report_id: Report ID
        db: Database session
        current_user: Authenticated admin user

    Raises:
        HTTPException 404: Report not found
        HTTPException 403: Insufficient permissions
    """
    report = db.query(Report).filter(Report.id == report_id).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with id {report_id} not found"
        )

    db.delete(report)
    db.commit()

    return None
