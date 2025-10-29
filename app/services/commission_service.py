"""
Commission Calculation Service
Multi-tier commission system for insurance sales
"""
from typing import List, Tuple
from decimal import Decimal
from datetime import date
from sqlalchemy.orm import Session

from app.models.commission import Commission, CommissionType, CommissionStatus
from app.models.policy import Policy
from app.models.user import User


class CommissionService:
    """
    Service for calculating insurance sales commissions.

    COMMISSION STRUCTURE:
    Mirrors Telco CRM commission system but adapted for insurance.

    RATES:
    - INITIAL (policy signed):
      * Broker: 15% of annual premium
      * Manager: 5% of annual premium
      * Affiliate: 3% of annual premium

    - RENEWAL_YEAR1 (first renewal):
      * Broker: 10%
      * Manager: 3%
      * Affiliate: 2%

    - RENEWAL_RECURRING (years 2+):
      * Broker: 5%
      * Manager: 2%
      * Affiliate: 1%

    WHY these rates:
    - High initial commission incentivizes new sales
    - Lower renewal rates reflect reduced acquisition cost
    - Manager override rewards team building
    - Affiliate commission encourages referrals

    BUSINESS EXAMPLE:
    Policy: €2,000/year premium
    Initial commissions:
    - Broker: €300 (15%)
    - Manager: €100 (5%)
    - Affiliate: €60 (3%)
    Total: €460 (23% of premium)

    Year 2 renewal:
    - Broker: €200 (10%)
    - Manager: €60 (3%)
    - Affiliate: €40 (2%)
    Total: €300 (15% of premium)

    This structure is sustainable and competitive with industry standards.
    """

    # Commission rate structure (percentage of annual premium)
    COMMISSION_RATES = {
        CommissionType.INITIAL: {
            "broker": Decimal("0.15"),      # 15%
            "manager": Decimal("0.05"),     # 5%
            "affiliate": Decimal("0.03")    # 3%
        },
        CommissionType.RENEWAL_YEAR1: {
            "broker": Decimal("0.10"),      # 10%
            "manager": Decimal("0.03"),     # 3%
            "affiliate": Decimal("0.02")    # 2%
        },
        CommissionType.RENEWAL_RECURRING: {
            "broker": Decimal("0.05"),      # 5%
            "manager": Decimal("0.02"),     # 2%
            "affiliate": Decimal("0.01")    # 1%
        }
    }

    @classmethod
    def calculate_initial_commissions(
        cls,
        policy: Policy,
        broker: User,
        db: Session,
        manager: User = None,
        affiliate: User = None
    ) -> List[Commission]:
        """
        Calculate initial commissions when policy is signed.

        FLOW:
        1. Get annual premium from policy's quote
        2. Calculate broker commission (always)
        3. Calculate manager commission (if broker has supervisor)
        4. Calculate affiliate commission (if exists)
        5. Return list of commission records

        IDEMPOTENCY:
        Caller should check if commissions already exist for this policy
        to avoid duplicates.

        Args:
            policy: The signed insurance policy
            broker: The broker who sold the policy
            db: Database session
            manager: Optional manager (broker's supervisor)
            affiliate: Optional affiliate who referred the customer

        Returns:
            List of Commission objects (not yet saved to DB)

        Example:
            policy = get_policy(123)
            broker = get_user(broker_id)
            manager = broker.supervisor

            commissions = CommissionService.calculate_initial_commissions(
                policy, broker, db, manager
            )

            for comm in commissions:
                db.add(comm)
            db.commit()
        """
        commissions = []

        # Get annual premium from policy's quote
        annual_premium = Decimal(str(policy.quote.annual_premium))

        # Current period (for reporting)
        today = date.today()
        period_year = today.year
        period_month = today.month

        # 1. Broker commission (always calculated)
        broker_rate = cls.COMMISSION_RATES[CommissionType.INITIAL]["broker"]
        broker_amount = annual_premium * broker_rate

        broker_commission = Commission(
            prospect_id=policy.quote.prospect_id,
            broker_id=broker.id,
            manager_id=manager.id if manager else None,
            affiliate_id=affiliate.id if affiliate else None,
            commission_type=CommissionType.INITIAL,
            amount=broker_amount,
            percentage=broker_rate * 100,  # Store as percentage (15.00)
            base_amount=annual_premium,
            status=CommissionStatus.PENDING,
            period_year=period_year,
            period_month=period_month
        )
        commissions.append(broker_commission)

        # 2. Manager override commission (if broker has supervisor)
        if manager:
            manager_rate = cls.COMMISSION_RATES[CommissionType.INITIAL]["manager"]
            manager_amount = annual_premium * manager_rate

            manager_commission = Commission(
                prospect_id=policy.quote.prospect_id,
                broker_id=broker.id,  # Track which broker generated this
                manager_id=manager.id,
                commission_type=CommissionType.INITIAL,
                amount=manager_amount,
                percentage=manager_rate * 100,
                base_amount=annual_premium,
                status=CommissionStatus.PENDING,
                period_year=period_year,
                period_month=period_month
            )
            commissions.append(manager_commission)

        # 3. Affiliate referral commission (if exists)
        if affiliate:
            affiliate_rate = cls.COMMISSION_RATES[CommissionType.INITIAL]["affiliate"]
            affiliate_amount = annual_premium * affiliate_rate

            affiliate_commission = Commission(
                prospect_id=policy.quote.prospect_id,
                broker_id=broker.id,
                affiliate_id=affiliate.id,
                commission_type=CommissionType.INITIAL,
                amount=affiliate_amount,
                percentage=affiliate_rate * 100,
                base_amount=annual_premium,
                status=CommissionStatus.PENDING,
                period_year=period_year,
                period_month=period_month
            )
            commissions.append(affiliate_commission)

        return commissions

    @classmethod
    def calculate_renewal_commissions(
        cls,
        policy: Policy,
        broker: User,
        db: Session,
        renewal_year: int,
        manager: User = None,
        affiliate: User = None
    ) -> List[Commission]:
        """
        Calculate renewal commissions for policy renewal.

        Called when policy is renewed (typically annually).

        Args:
            policy: The renewed policy
            broker: Original broker
            db: Database session
            renewal_year: Which renewal year (1 for first renewal, 2+ for recurring)
            manager: Manager at time of renewal
            affiliate: Affiliate at time of original sale

        Returns:
            List of renewal commission records

        Example:
            # First renewal (year 2)
            commissions = CommissionService.calculate_renewal_commissions(
                policy, broker, db, renewal_year=1
            )

            # Subsequent renewals (years 3+)
            commissions = CommissionService.calculate_renewal_commissions(
                policy, broker, db, renewal_year=2
            )
        """
        commissions = []
        annual_premium = Decimal(str(policy.quote.annual_premium))
        today = date.today()

        # Determine commission type based on renewal year
        if renewal_year == 1:
            commission_type = CommissionType.RENEWAL_YEAR1
        else:
            commission_type = CommissionType.RENEWAL_RECURRING

        rates = cls.COMMISSION_RATES[commission_type]

        # Broker renewal commission
        broker_amount = annual_premium * rates["broker"]
        commissions.append(Commission(
            prospect_id=policy.quote.prospect_id,
            broker_id=broker.id,
            manager_id=manager.id if manager else None,
            affiliate_id=affiliate.id if affiliate else None,
            commission_type=commission_type,
            amount=broker_amount,
            percentage=rates["broker"] * 100,
            base_amount=annual_premium,
            status=CommissionStatus.PENDING,
            period_year=today.year,
            period_month=today.month
        ))

        # Manager renewal override
        if manager:
            manager_amount = annual_premium * rates["manager"]
            commissions.append(Commission(
                prospect_id=policy.quote.prospect_id,
                broker_id=broker.id,
                manager_id=manager.id,
                commission_type=commission_type,
                amount=manager_amount,
                percentage=rates["manager"] * 100,
                base_amount=annual_premium,
                status=CommissionStatus.PENDING,
                period_year=today.year,
                period_month=today.month
            ))

        # Affiliate renewal commission
        if affiliate:
            affiliate_amount = annual_premium * rates["affiliate"]
            commissions.append(Commission(
                prospect_id=policy.quote.prospect_id,
                broker_id=broker.id,
                affiliate_id=affiliate.id,
                commission_type=commission_type,
                amount=affiliate_amount,
                percentage=rates["affiliate"] * 100,
                base_amount=annual_premium,
                status=CommissionStatus.PENDING,
                period_year=today.year,
                period_month=today.month
            ))

        return commissions

    @staticmethod
    def get_broker_for_prospect(prospect_id: int, db: Session) -> User:
        """
        Get the broker assigned to a prospect.

        Args:
            prospect_id: Prospect ID
            db: Database session

        Returns:
            User object (broker)
        """
        from app.models.prospect import Prospect

        prospect = db.query(Prospect).filter(Prospect.id == prospect_id).first()
        if not prospect or not prospect.assigned_broker:
            return None

        return db.query(User).filter(User.id == prospect.assigned_broker).first()

    @staticmethod
    def approve_commission(commission_id: int, db: Session) -> Commission:
        """
        Approve a pending commission.

        Typically done by managers or admins.

        Args:
            commission_id: Commission ID to approve
            db: Database session

        Returns:
            Updated commission record
        """
        commission = db.query(Commission).filter(Commission.id == commission_id).first()

        if commission and commission.status == CommissionStatus.PENDING:
            commission.approve()
            db.commit()
            db.refresh(commission)

        return commission

    @staticmethod
    def mark_commission_paid(commission_id: int, db: Session, paid_at: date = None) -> Commission:
        """
        Mark commission as paid.

        Args:
            commission_id: Commission ID
            db: Database session
            paid_at: Payment date (defaults to today)

        Returns:
            Updated commission record
        """
        commission = db.query(Commission).filter(Commission.id == commission_id).first()

        if commission:
            commission.mark_as_paid(paid_at)
            db.commit()
            db.refresh(commission)

        return commission
