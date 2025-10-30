"""
Report Service
Generate sales, commission, and performance reports
"""
from typing import List, Dict, Any, Tuple
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import csv
import json
from io import StringIO

from app.models.report import Report, ReportType, ReportFormat
from app.models.user import User, UserRole
from app.models.prospect import Prospect, ProspectStatus
from app.models.quote import Quote, QuoteStatus
from app.models.policy import Policy, PolicyStatus
from app.models.commission import Commission, CommissionStatus, CommissionType


class ReportService:
    """
    Service for generating various business reports.

    WHY reports matter:
    - **Business Intelligence**: Track performance metrics
    - **Commission Transparency**: Show broker earnings breakdown
    - **Management Decisions**: Data-driven insights
    - **Compliance**: Required for insurance regulations

    REPORT TYPES:
    1. **Sales Summary**: Policies sold, premiums, conversion rates
    2. **Commission Breakdown**: Who earned what, by type
    3. **Broker Performance**: Individual broker metrics
    4. **Pipeline Analysis**: Funnel metrics, bottlenecks
    5. **Provider Comparison**: Which providers perform best

    ARCHITECTURE CHOICE:
    Reports are generated on-demand (not cached) because:
    - Data changes frequently
    - Each report has different filters
    - Storage cost > computation cost for small datasets

    For LARGE datasets (millions of records), we'd use:
    - Materialized views (PostgreSQL)
    - Pre-aggregated summary tables
    - Background report generation workers
    """

    @classmethod
    def generate_sales_summary(
        cls,
        db: Session,
        start_date: date,
        end_date: date,
        user: User
    ) -> Dict[str, Any]:
        """
        Generate sales summary report.

        Metrics:
        - Total policies sold
        - Total premium amount
        - Average premium per policy
        - Conversion rate (quotes → policies)
        - Breakdown by insurance type
        - Breakdown by provider

        Role-based filtering:
        - Broker: Only their sales
        - Manager: Their team's sales
        - Head of Sales/Admin: All sales

        Args:
            db: Database session
            start_date: Report start date
            end_date: Report end date
            user: User generating report (for role-based filtering)

        Returns:
            Dictionary with sales metrics
        """
        # Build base query with role-based filtering
        policy_query = db.query(Policy).join(Quote).join(Prospect)

        if user.role == UserRole.BROKER:
            policy_query = policy_query.filter(Prospect.assigned_broker == user.id)
        elif user.role == UserRole.MANAGER:
            # Manager sees their team's data
            team_ids = db.query(User.id).filter(User.supervisor_id == user.id).all()
            team_ids = [user.id] + [t[0] for t in team_ids]
            policy_query = policy_query.filter(Prospect.assigned_broker.in_(team_ids))

        # Filter by date range
        policy_query = policy_query.filter(
            and_(
                Policy.start_date >= start_date,
                Policy.start_date <= end_date
            )
        )

        # Get all policies
        policies = policy_query.all()

        # Calculate metrics
        total_policies = len(policies)
        total_premium = sum(p.quote.annual_premium for p in policies)
        avg_premium = total_premium / total_policies if total_policies > 0 else Decimal(0)

        # Breakdown by insurance type
        type_breakdown = {}
        for policy in policies:
            ins_type = policy.quote.insurance_type
            if ins_type not in type_breakdown:
                type_breakdown[ins_type] = {"count": 0, "premium": Decimal(0)}
            type_breakdown[ins_type]["count"] += 1
            type_breakdown[ins_type]["premium"] += policy.quote.annual_premium

        # Breakdown by provider
        provider_breakdown = {}
        for policy in policies:
            provider = policy.quote.provider
            if provider not in provider_breakdown:
                provider_breakdown[provider] = {"count": 0, "premium": Decimal(0)}
            provider_breakdown[provider]["count"] += 1
            provider_breakdown[provider]["premium"] += policy.quote.annual_premium

        # Calculate conversion rate (quotes sent → policies)
        quote_query = db.query(Quote).join(Prospect)

        if user.role == UserRole.BROKER:
            quote_query = quote_query.filter(Prospect.assigned_broker == user.id)
        elif user.role == UserRole.MANAGER:
            quote_query = quote_query.filter(Prospect.assigned_broker.in_(team_ids))

        total_quotes_sent = quote_query.filter(
            Quote.status.in_([QuoteStatus.SENT, QuoteStatus.ACCEPTED])
        ).count()

        conversion_rate = (total_policies / total_quotes_sent * 100) if total_quotes_sent > 0 else 0.0

        return {
            "summary": {
                "total_policies": total_policies,
                "total_premium": float(total_premium),
                "average_premium": float(avg_premium),
                "conversion_rate": round(conversion_rate, 2)
            },
            "by_insurance_type": {
                k: {"count": v["count"], "premium": float(v["premium"])}
                for k, v in type_breakdown.items()
            },
            "by_provider": {
                k: {"count": v["count"], "premium": float(v["premium"])}
                for k, v in provider_breakdown.items()
            },
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }

    @classmethod
    def generate_commission_breakdown(
        cls,
        db: Session,
        start_date: date,
        end_date: date,
        user: User
    ) -> Dict[str, Any]:
        """
        Generate commission breakdown report.

        Metrics:
        - Total commissions by status (pending/paid/cancelled)
        - Breakdown by commission type (initial/renewal)
        - Breakdown by broker
        - Manager override commissions
        - Affiliate referral commissions

        Role-based filtering:
        - Broker: Only their commissions
        - Manager: Their team's commissions + their overrides
        - Head of Sales/Admin: All commissions

        Args:
            db: Database session
            start_date: Report start date
            end_date: Report end date
            user: User generating report

        Returns:
            Dictionary with commission metrics
        """
        # Build base query
        commission_query = db.query(Commission).join(Policy)

        if user.role == UserRole.BROKER:
            commission_query = commission_query.filter(Commission.broker_id == user.id)
        elif user.role == UserRole.MANAGER:
            # Manager sees team commissions + their override commissions
            team_ids = db.query(User.id).filter(User.supervisor_id == user.id).all()
            team_ids = [user.id] + [t[0] for t in team_ids]
            commission_query = commission_query.filter(
                (Commission.broker_id.in_(team_ids)) | (Commission.manager_id == user.id)
            )

        # Filter by date
        commission_query = commission_query.filter(
            and_(
                Policy.start_date >= start_date,
                Policy.start_date <= end_date
            )
        )

        commissions = commission_query.all()

        # Calculate totals by status
        status_breakdown = {status.value: Decimal(0) for status in CommissionStatus}
        for comm in commissions:
            status_breakdown[comm.status.value] += comm.amount

        # Calculate totals by type
        type_breakdown = {
            CommissionType.INITIAL.value: Decimal(0),
            CommissionType.RENEWAL_YEAR1.value: Decimal(0),
            CommissionType.RENEWAL_RECURRING.value: Decimal(0)
        }
        for comm in commissions:
            type_breakdown[comm.commission_type.value] += comm.amount

        # Broker breakdown (only brokers, not managers/affiliates)
        broker_breakdown = {}
        for comm in commissions:
            if comm.broker:
                broker_id = comm.broker.id
                broker_name = comm.broker.username

                if broker_id not in broker_breakdown:
                    broker_breakdown[broker_id] = {
                        "name": broker_name,
                        "total": Decimal(0),
                        "count": 0
                    }

                broker_breakdown[broker_id]["total"] += comm.amount
                broker_breakdown[broker_id]["count"] += 1

        # Total metrics
        total_amount = sum(comm.amount for comm in commissions)
        total_count = len(commissions)

        return {
            "summary": {
                "total_amount": float(total_amount),
                "total_count": total_count,
                "average_commission": float(total_amount / total_count) if total_count > 0 else 0.0
            },
            "by_status": {k: float(v) for k, v in status_breakdown.items()},
            "by_type": {k: float(v) for k, v in type_breakdown.items()},
            "by_broker": {
                k: {
                    "name": v["name"],
                    "total": float(v["total"]),
                    "count": v["count"]
                }
                for k, v in broker_breakdown.items()
            },
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }

    @classmethod
    def generate_broker_performance(
        cls,
        db: Session,
        start_date: date,
        end_date: date,
        broker_id: int
    ) -> Dict[str, Any]:
        """
        Generate individual broker performance report.

        Metrics:
        - Prospects assigned vs converted
        - Quotes generated vs accepted
        - Policies sold
        - Total commissions earned
        - Average deal size
        - Conversion funnel metrics

        Args:
            db: Database session
            start_date: Report start date
            end_date: Report end date
            broker_id: Broker user ID

        Returns:
            Dictionary with broker performance metrics
        """
        broker = db.query(User).filter(User.id == broker_id).first()

        if not broker:
            raise ValueError(f"Broker with id {broker_id} not found")

        # Prospects
        prospects_query = db.query(Prospect).filter(
            and_(
                Prospect.assigned_broker == broker_id,
                Prospect.created_at >= start_date,
                Prospect.created_at <= end_date
            )
        )

        total_prospects = prospects_query.count()
        converted_prospects = prospects_query.filter(
            Prospect.status == ProspectStatus.POLICY_SIGNED
        ).count()

        # Quotes
        quotes_query = db.query(Quote).join(Prospect).filter(
            and_(
                Prospect.assigned_broker == broker_id,
                Quote.created_at >= start_date,
                Quote.created_at <= end_date
            )
        )

        total_quotes = quotes_query.count()
        accepted_quotes = quotes_query.filter(Quote.status == QuoteStatus.ACCEPTED).count()

        # Policies
        policies_query = db.query(Policy).join(Quote).join(Prospect).filter(
            and_(
                Prospect.assigned_broker == broker_id,
                Policy.start_date >= start_date,
                Policy.start_date <= end_date
            )
        )

        policies = policies_query.all()
        total_policies = len(policies)
        total_premium = sum(p.quote.annual_premium for p in policies)
        avg_deal_size = total_premium / total_policies if total_policies > 0 else Decimal(0)

        # Commissions
        commissions_query = db.query(Commission).join(Policy).filter(
            and_(
                Commission.broker_id == broker_id,
                Policy.start_date >= start_date,
                Policy.start_date <= end_date
            )
        )

        commissions = commissions_query.all()
        total_commission = sum(c.amount for c in commissions)
        paid_commission = sum(c.amount for c in commissions if c.status == CommissionStatus.PAID)

        # Conversion rates
        prospect_conversion = (converted_prospects / total_prospects * 100) if total_prospects > 0 else 0.0
        quote_conversion = (accepted_quotes / total_quotes * 100) if total_quotes > 0 else 0.0

        return {
            "broker": {
                "id": broker.id,
                "name": broker.username,
                "role": broker.role.value
            },
            "funnel": {
                "prospects": total_prospects,
                "converted_prospects": converted_prospects,
                "prospect_conversion_rate": round(prospect_conversion, 2),
                "quotes_generated": total_quotes,
                "quotes_accepted": accepted_quotes,
                "quote_conversion_rate": round(quote_conversion, 2),
                "policies_sold": total_policies
            },
            "revenue": {
                "total_premium_sold": float(total_premium),
                "average_deal_size": float(avg_deal_size),
                "total_commission_earned": float(total_commission),
                "commission_paid": float(paid_commission),
                "commission_pending": float(total_commission - paid_commission)
            },
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }

    @classmethod
    def export_to_csv(cls, data: Dict[str, Any], report_type: ReportType) -> str:
        """
        Export report data to CSV format.

        Each report type has a different CSV structure optimized
        for spreadsheet analysis.

        Args:
            data: Report data dictionary
            report_type: Type of report

        Returns:
            CSV string
        """
        output = StringIO()
        writer = csv.writer(output)

        if report_type == ReportType.SALES_SUMMARY:
            # Summary section
            writer.writerow(["Sales Summary Report"])
            writer.writerow(["Date Range", f"{data['date_range']['start']} to {data['date_range']['end']}"])
            writer.writerow([])

            writer.writerow(["Metric", "Value"])
            writer.writerow(["Total Policies", data['summary']['total_policies']])
            writer.writerow(["Total Premium", f"€{data['summary']['total_premium']:,.2f}"])
            writer.writerow(["Average Premium", f"€{data['summary']['average_premium']:,.2f}"])
            writer.writerow(["Conversion Rate", f"{data['summary']['conversion_rate']}%"])
            writer.writerow([])

            # By insurance type
            writer.writerow(["Breakdown by Insurance Type"])
            writer.writerow(["Type", "Count", "Premium"])
            for ins_type, metrics in data['by_insurance_type'].items():
                writer.writerow([ins_type, metrics['count'], f"€{metrics['premium']:,.2f}"])
            writer.writerow([])

            # By provider
            writer.writerow(["Breakdown by Provider"])
            writer.writerow(["Provider", "Count", "Premium"])
            for provider, metrics in data['by_provider'].items():
                writer.writerow([provider, metrics['count'], f"€{metrics['premium']:,.2f}"])

        elif report_type == ReportType.COMMISSION_BREAKDOWN:
            writer.writerow(["Commission Breakdown Report"])
            writer.writerow(["Date Range", f"{data['date_range']['start']} to {data['date_range']['end']}"])
            writer.writerow([])

            writer.writerow(["Summary"])
            writer.writerow(["Total Amount", f"€{data['summary']['total_amount']:,.2f}"])
            writer.writerow(["Total Count", data['summary']['total_count']])
            writer.writerow(["Average Commission", f"€{data['summary']['average_commission']:,.2f}"])
            writer.writerow([])

            writer.writerow(["By Broker"])
            writer.writerow(["Broker ID", "Name", "Total", "Count"])
            for broker_id, metrics in data['by_broker'].items():
                writer.writerow([broker_id, metrics['name'], f"€{metrics['total']:,.2f}", metrics['count']])

        elif report_type == ReportType.BROKER_PERFORMANCE:
            writer.writerow(["Broker Performance Report"])
            writer.writerow(["Broker", data['broker']['name']])
            writer.writerow(["Date Range", f"{data['date_range']['start']} to {data['date_range']['end']}"])
            writer.writerow([])

            writer.writerow(["Funnel Metrics"])
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Prospects", data['funnel']['prospects']])
            writer.writerow(["Converted Prospects", data['funnel']['converted_prospects']])
            writer.writerow(["Prospect Conversion Rate", f"{data['funnel']['prospect_conversion_rate']}%"])
            writer.writerow(["Quotes Generated", data['funnel']['quotes_generated']])
            writer.writerow(["Quotes Accepted", data['funnel']['quotes_accepted']])
            writer.writerow(["Quote Conversion Rate", f"{data['funnel']['quote_conversion_rate']}%"])
            writer.writerow(["Policies Sold", data['funnel']['policies_sold']])
            writer.writerow([])

            writer.writerow(["Revenue Metrics"])
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Total Premium Sold", f"€{data['revenue']['total_premium_sold']:,.2f}"])
            writer.writerow(["Average Deal Size", f"€{data['revenue']['average_deal_size']:,.2f}"])
            writer.writerow(["Total Commission Earned", f"€{data['revenue']['total_commission_earned']:,.2f}"])
            writer.writerow(["Commission Paid", f"€{data['revenue']['commission_paid']:,.2f}"])
            writer.writerow(["Commission Pending", f"€{data['revenue']['commission_pending']:,.2f}"])

        return output.getvalue()

    @classmethod
    def save_report_metadata(
        cls,
        db: Session,
        report_type: ReportType,
        title: str,
        user_id: int,
        start_date: date,
        end_date: date,
        format: ReportFormat,
        file_path: str = None,
        record_count: int = None,
        filters: Dict[str, Any] = None
    ) -> Report:
        """
        Save report metadata to database.

        Args:
            db: Database session
            report_type: Type of report
            title: Report title
            user_id: User who generated report
            start_date: Report start date
            end_date: Report end date
            format: Export format
            file_path: Path to saved file (optional)
            record_count: Number of records in report (optional)
            filters: Filters applied (optional)

        Returns:
            Created Report object
        """
        report = Report(
            report_type=report_type,
            title=title,
            generated_by=user_id,
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.max.time()),
            format=format,
            file_path=file_path,
            record_count=record_count,
            filters=json.dumps(filters) if filters else None
        )

        db.add(report)
        db.commit()
        db.refresh(report)

        return report
