"""
Dashboard API endpoints
Role-based KPI and analytics
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from pydantic import BaseModel
from typing import Dict, List, Any
from datetime import datetime, date, timedelta

from app.api.dependencies import get_db_session, get_current_user
from app.models.user import User, UserRole
from app.models.prospect import Prospect, ProspectStatus
from app.models.quote import Quote, QuoteStatus
from app.models.policy import Policy, PolicyStatus
from app.models.commission import Commission, CommissionStatus


router = APIRouter()


# ============================================================================
# Response Schemas
# ============================================================================

class PipelineStats(BaseModel):
    """Sales pipeline statistics"""
    new_prospects: int
    contacted: int
    quoted: int
    policies_signed: int
    conversion_rate: float


class CommissionSummary(BaseModel):
    """Commission summary"""
    total_pending: float
    total_approved: float
    total_paid: float
    count_pending: int
    count_approved: int
    count_paid: int


class BrokerPerformance(BaseModel):
    """Individual broker performance metrics"""
    broker_id: int
    broker_name: str
    prospects_count: int
    quotes_count: int
    policies_count: int
    commission_total: float
    conversion_rate: float


class DashboardResponse(BaseModel):
    """Main dashboard response (role-specific)"""
    user_role: str
    period_start: date
    period_end: date
    metrics: Dict[str, Any]


# ============================================================================
# Helper Functions
# ============================================================================

def get_date_range(period: str) -> tuple[date, date]:
    """
    Get date range based on period string.

    Args:
        period: 'today', 'week', 'month', 'quarter', 'year'

    Returns:
        Tuple of (start_date, end_date)
    """
    today = date.today()

    if period == "today":
        return today, today
    elif period == "week":
        start = today - timedelta(days=today.weekday())
        return start, today
    elif period == "month":
        start = today.replace(day=1)
        return start, today
    elif period == "quarter":
        quarter_month = ((today.month - 1) // 3) * 3 + 1
        start = today.replace(month=quarter_month, day=1)
        return start, today
    elif period == "year":
        start = today.replace(month=1, day=1)
        return start, today
    else:
        # Default to current month
        start = today.replace(day=1)
        return start, today


def calculate_pipeline_stats(db: Session, user: User, start_date: date, end_date: date) -> PipelineStats:
    """
    Calculate sales pipeline statistics.

    WHY pipeline matters:
    - Shows conversion funnel health
    - Identifies bottlenecks (lots of contacts, few quotes?)
    - Predicts future revenue

    Args:
        db: Database session
        user: Current user (filters by role/ownership)
        start_date: Period start
        end_date: Period end

    Returns:
        Pipeline statistics
    """
    # Base query - filter by user role
    query = db.query(Prospect)

    if user.role == UserRole.BROKER:
        # Brokers see only their prospects
        query = query.filter(Prospect.assigned_broker == user.id)
    elif user.role == UserRole.MANAGER:
        # Managers see their team's prospects
        team_ids = db.query(User.id).filter(User.supervisor_id == user.id).all()
        team_ids = [user.id] + [t[0] for t in team_ids]  # Include manager's own
        query = query.filter(Prospect.assigned_broker.in_(team_ids))
    # HEAD_OF_SALES and ADMIN see everything

    # Filter by date range
    query = query.filter(
        and_(
            Prospect.created_at >= start_date,
            Prospect.created_at <= end_date
        )
    )

    # Count by status
    total = query.count()
    new_prospects = query.filter(Prospect.status == ProspectStatus.NEW).count()
    contacted = query.filter(Prospect.status == ProspectStatus.CONTACTED).count()
    quoted = query.filter(Prospect.status == ProspectStatus.QUOTED).count()
    policies_signed = query.filter(Prospect.status == ProspectStatus.POLICY_SIGNED).count()

    # Calculate conversion rate (new -> signed)
    conversion_rate = (policies_signed / total * 100) if total > 0 else 0.0

    return PipelineStats(
        new_prospects=new_prospects,
        contacted=contacted,
        quoted=quoted,
        policies_signed=policies_signed,
        conversion_rate=round(conversion_rate, 2)
    )


def calculate_commission_summary(db: Session, user: User, start_date: date, end_date: date) -> CommissionSummary:
    """
    Calculate commission summary.

    Args:
        db: Database session
        user: Current user
        start_date: Period start
        end_date: Period end

    Returns:
        Commission summary
    """
    # Base query
    query = db.query(Commission)

    if user.role == UserRole.BROKER:
        query = query.filter(Commission.broker_id == user.id)
    elif user.role == UserRole.MANAGER:
        # Manager sees their commissions + team's
        team_ids = db.query(User.id).filter(User.supervisor_id == user.id).all()
        team_ids = [user.id] + [t[0] for t in team_ids]
        query = query.filter(Commission.broker_id.in_(team_ids))

    # Filter by date
    query = query.filter(
        and_(
            Commission.created_at >= start_date,
            Commission.created_at <= end_date
        )
    )

    # Aggregate by status
    pending = query.filter(Commission.status == CommissionStatus.PENDING).all()
    approved = query.filter(Commission.status == CommissionStatus.APPROVED).all()
    paid = query.filter(Commission.status == CommissionStatus.PAID).all()

    return CommissionSummary(
        total_pending=sum(c.amount for c in pending),
        total_approved=sum(c.amount for c in approved),
        total_paid=sum(c.amount for c in paid),
        count_pending=len(pending),
        count_approved=len(approved),
        count_paid=len(paid)
    )


def get_top_brokers(db: Session, user: User, start_date: date, end_date: date, limit: int = 5) -> List[BrokerPerformance]:
    """
    Get top performing brokers.

    Only available for MANAGER, HEAD_OF_SALES, ADMIN.

    Args:
        db: Database session
        user: Current user
        start_date: Period start
        end_date: Period end
        limit: Number of top brokers to return

    Returns:
        List of broker performance metrics
    """
    # Only managers and above can see this
    if user.role not in [UserRole.MANAGER, UserRole.HEAD_OF_SALES, UserRole.ADMIN]:
        return []

    # Get brokers to analyze
    if user.role == UserRole.MANAGER:
        # Manager sees their team only
        brokers = db.query(User).filter(User.supervisor_id == user.id).all()
    else:
        # HEAD_OF_SALES and ADMIN see all brokers
        brokers = db.query(User).filter(User.role == UserRole.BROKER).all()

    broker_stats = []

    for broker in brokers:
        # Count prospects
        prospects_count = db.query(Prospect).filter(
            and_(
                Prospect.assigned_broker == broker.id,
                Prospect.created_at >= start_date,
                Prospect.created_at <= end_date
            )
        ).count()

        # Count quotes
        quotes_count = db.query(Quote).join(Prospect).filter(
            and_(
                Prospect.assigned_broker == broker.id,
                Quote.created_at >= start_date,
                Quote.created_at <= end_date
            )
        ).count()

        # Count policies
        policies_count = db.query(Policy).join(Quote).join(Prospect).filter(
            and_(
                Prospect.assigned_broker == broker.id,
                Policy.signed_at >= start_date,
                Policy.signed_at <= end_date
            )
        ).count()

        # Sum commissions
        commission_total = db.query(func.sum(Commission.amount)).filter(
            and_(
                Commission.broker_id == broker.id,
                Commission.created_at >= start_date,
                Commission.created_at <= end_date
            )
        ).scalar() or 0.0

        # Calculate conversion rate
        conversion_rate = (policies_count / prospects_count * 100) if prospects_count > 0 else 0.0

        broker_stats.append(BrokerPerformance(
            broker_id=broker.id,
            broker_name=broker.username,
            prospects_count=prospects_count,
            quotes_count=quotes_count,
            policies_count=policies_count,
            commission_total=float(commission_total),
            conversion_rate=round(conversion_rate, 2)
        ))

    # Sort by commission total (descending)
    broker_stats.sort(key=lambda x: x.commission_total, reverse=True)

    return broker_stats[:limit]


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/", response_model=DashboardResponse)
async def get_dashboard(
    period: str = Query("month", description="Time period: today, week, month, quarter, year"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    Get role-based dashboard with KPIs.

    ROLE-SPECIFIC VIEWS:

    **BROKER**:
    - My prospects pipeline
    - My commissions (pending/paid)
    - My conversion rate

    **MANAGER**:
    - Team prospects pipeline
    - Team commissions
    - Top brokers in team
    - Team conversion rate

    **HEAD_OF_SALES / ADMIN**:
    - Company-wide pipeline
    - Total commissions
    - Top brokers overall
    - Department performance

    WHY role-based:
    - Security: Users only see data they're allowed to
    - Relevance: Brokers care about their numbers, managers about team
    - Performance: Don't load unnecessary data

    Args:
        period: Time period for metrics
        current_user: Authenticated user
        db: Database session

    Returns:
        Dashboard data tailored to user role
    """
    start_date, end_date = get_date_range(period)

    # Calculate common metrics
    pipeline = calculate_pipeline_stats(db, current_user, start_date, end_date)
    commissions = calculate_commission_summary(db, current_user, start_date, end_date)

    # Role-specific metrics
    metrics: Dict[str, Any] = {
        "pipeline": pipeline.dict(),
        "commissions": commissions.dict()
    }

    # Add top brokers for managers and above
    if current_user.role in [UserRole.MANAGER, UserRole.HEAD_OF_SALES, UserRole.ADMIN]:
        top_brokers = get_top_brokers(db, current_user, start_date, end_date)
        metrics["top_brokers"] = [b.dict() for b in top_brokers]

    # Add active policies count
    active_policies_query = db.query(Policy).filter(Policy.status == PolicyStatus.ACTIVE)

    if current_user.role == UserRole.BROKER:
        active_policies_query = active_policies_query.join(Quote).join(Prospect).filter(
            Prospect.assigned_broker == current_user.id
        )
    elif current_user.role == UserRole.MANAGER:
        team_ids = db.query(User.id).filter(User.supervisor_id == current_user.id).all()
        team_ids = [current_user.id] + [t[0] for t in team_ids]
        active_policies_query = active_policies_query.join(Quote).join(Prospect).filter(
            Prospect.assigned_broker.in_(team_ids)
        )

    metrics["active_policies"] = active_policies_query.count()

    # Add expiring policies (next 30 days)
    expiring_date = date.today() + timedelta(days=30)
    expiring_policies_query = db.query(Policy).filter(
        and_(
            Policy.status == PolicyStatus.ACTIVE,
            Policy.end_date <= expiring_date,
            Policy.end_date >= date.today()
        )
    )

    if current_user.role == UserRole.BROKER:
        expiring_policies_query = expiring_policies_query.join(Quote).join(Prospect).filter(
            Prospect.assigned_broker == current_user.id
        )
    elif current_user.role == UserRole.MANAGER:
        expiring_policies_query = expiring_policies_query.join(Quote).join(Prospect).filter(
            Prospect.assigned_broker.in_(team_ids)
        )

    metrics["expiring_policies_30days"] = expiring_policies_query.count()

    return DashboardResponse(
        user_role=current_user.role.value,
        period_start=start_date,
        period_end=end_date,
        metrics=metrics
    )


@router.get("/activity", response_model=Dict[str, Any])
async def get_recent_activity(
    limit: int = Query(10, le=50, description="Number of recent activities"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    Get recent activity feed.

    Shows recent actions:
    - New prospects created
    - Quotes generated
    - Policies signed
    - Commissions earned

    Args:
        limit: Number of activities to return
        current_user: Authenticated user
        db: Database session

    Returns:
        List of recent activities
    """
    activities = []

    # Recent prospects
    prospects_query = db.query(Prospect).order_by(Prospect.created_at.desc())

    if current_user.role == UserRole.BROKER:
        prospects_query = prospects_query.filter(Prospect.assigned_broker == current_user.id)
    elif current_user.role == UserRole.MANAGER:
        team_ids = db.query(User.id).filter(User.supervisor_id == current_user.id).all()
        team_ids = [current_user.id] + [t[0] for t in team_ids]
        prospects_query = prospects_query.filter(Prospect.assigned_broker.in_(team_ids))

    recent_prospects = prospects_query.limit(limit // 2).all()

    for p in recent_prospects:
        activities.append({
            "type": "prospect_created",
            "timestamp": p.created_at.isoformat(),
            "description": f"New prospect: {p.first_name} {p.last_name}",
            "prospect_id": p.id
        })

    # Recent policies
    policies_query = db.query(Policy).order_by(Policy.signed_at.desc())

    if current_user.role == UserRole.BROKER:
        policies_query = policies_query.join(Quote).join(Prospect).filter(
            Prospect.assigned_broker == current_user.id
        )
    elif current_user.role == UserRole.MANAGER:
        policies_query = policies_query.join(Quote).join(Prospect).filter(
            Prospect.assigned_broker.in_(team_ids)
        )

    recent_policies = policies_query.limit(limit // 2).all()

    for pol in recent_policies:
        activities.append({
            "type": "policy_signed",
            "timestamp": pol.signed_at.isoformat() if pol.signed_at else "",
            "description": f"Policy signed: {pol.policy_number}",
            "policy_id": pol.id
        })

    # Sort by timestamp (most recent first)
    activities.sort(key=lambda x: x["timestamp"], reverse=True)

    return {
        "activities": activities[:limit],
        "count": len(activities)
    }
