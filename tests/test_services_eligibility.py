"""
Unit tests for EligibilityService

Tests the provider rules engine that determines:
- Which providers accept a prospect
- Base premium estimates
- Coverage limits

WHY these tests matter:
- Eligibility logic is business-critical (wrong = bad customer experience)
- Rules engine is pure Python (fast to test, no DB needed)
- Edge cases: age limits, risk categories
"""
import pytest
from datetime import date
from decimal import Decimal

from app.services.eligibility_service import EligibilityService, EligibilityProvider
from app.models.prospect import Prospect, ProspectType, RiskCategory


class TestEligibilityService:
    """Test suite for eligibility checking logic."""

    def test_life_insurance_eligible_medium_risk(self, test_prospect):
        """
        Test: Medium-risk prospect (age 45) should be eligible for most providers.

        Business rule: Medium risk accepted by Generali, Allianz, AXA
        """
        # test_prospect fixture: age 45, medium risk
        results = EligibilityService.check_eligibility(
            prospect=test_prospect,
            insurance_type="life",
            coverage_amount=Decimal("250000")
        )

        # Should return 4 results (one per provider)
        assert len(results) == 4

        # Filter eligible providers
        eligible = [r for r in results if r.is_eligible]

        # At least 2 providers should accept medium risk
        assert len(eligible) >= 2

        # Check Generali specifically (always accepts medium risk)
        generali = next((r for r in results if r.provider == "generali"), None)
        assert generali is not None
        assert generali.is_eligible is True
        assert generali.base_premium > 0

    def test_life_insurance_high_risk_limited_options(self, test_high_risk_prospect):
        """
        Test: High-risk prospect (age 75) has limited provider options.

        Business rule: Only Allianz accepts high risk for life insurance
        """
        results = EligibilityService.check_eligibility(
            prospect=test_high_risk_prospect,
            insurance_type="life",
            coverage_amount=Decimal("100000")
        )

        eligible = [r for r in results if r.is_eligible]

        # High risk should have fewer options
        assert len(eligible) <= 2

        # Check if Allianz is eligible (accepts high risk)
        allianz = next((r for r in results if r.provider == "allianz"), None)
        if allianz:
            assert allianz.is_eligible is True

    def test_age_under_minimum_rejected(self, test_db, test_broker):
        """
        Test: Prospect below minimum age is rejected by all providers.

        Edge case: Age 17 (below minimum 18)
        """
        young_prospect = Prospect(
            type=ProspectType.INDIVIDUAL,
            first_name="Giovane",
            last_name="Minorenni",
            birth_date=date(2008, 1, 1),  # Age 17
            email="young@test.com",
            phone="+39 340 1111111",
            tax_code="GVNMNR08A01H501Z",
            risk_category=RiskCategory.LOW,
            assigned_broker=test_broker.id,
            created_by=test_broker.id
        )
        test_db.add(young_prospect)
        test_db.commit()

        results = EligibilityService.check_eligibility(
            prospect=young_prospect,
            insurance_type="life",
            coverage_amount=Decimal("100000")
        )

        # All providers should reject
        eligible = [r for r in results if r.is_eligible]
        assert len(eligible) == 0

        # Check rejection reasons mention age
        for result in results:
            assert "age" in result.reason.lower() or "età" in result.reason.lower()

    def test_age_over_maximum_rejected(self, test_db, test_broker):
        """
        Test: Prospect over maximum age is rejected by most providers.

        Edge case: Age 85 (above most limits)
        """
        elderly_prospect = Prospect(
            type=ProspectType.INDIVIDUAL,
            first_name="Anziano",
            last_name="Senior",
            birth_date=date(1940, 1, 1),  # Age 85
            email="elderly@test.com",
            phone="+39 340 2222222",
            tax_code="NZNSRN40A01H501W",
            risk_category=RiskCategory.HIGH,
            assigned_broker=test_broker.id,
            created_by=test_broker.id
        )
        test_db.add(elderly_prospect)
        test_db.commit()

        results = EligibilityService.check_eligibility(
            prospect=elderly_prospect,
            insurance_type="life",
            coverage_amount=Decimal("50000")
        )

        # Most providers should reject (maybe Allianz accepts up to 80)
        eligible = [r for r in results if r.is_eligible]
        assert len(eligible) <= 1  # At most 1 provider

    def test_coverage_amount_affects_premium(self, test_prospect):
        """
        Test: Higher coverage amount = higher premium estimate.

        Business logic: Premium should scale with coverage
        """
        # Check with low coverage
        low_coverage_results = EligibilityService.check_eligibility(
            prospect=test_prospect,
            insurance_type="life",
            coverage_amount=Decimal("100000")
        )

        # Check with high coverage
        high_coverage_results = EligibilityService.check_eligibility(
            prospect=test_prospect,
            insurance_type="life",
            coverage_amount=Decimal("500000")
        )

        # Compare premiums for same provider (e.g., Generali)
        low_generali = next(
            (r for r in low_coverage_results if r.provider == "generali"),
            None
        )
        high_generali = next(
            (r for r in high_coverage_results if r.provider == "generali"),
            None
        )

        if low_generali and high_generali and low_generali.is_eligible and high_generali.is_eligible:
            # Higher coverage should have higher premium
            assert high_generali.base_premium > low_generali.base_premium

    def test_insurance_type_auto_rules(self, test_prospect):
        """
        Test: Auto insurance has different rules than life insurance.

        Business rule: Age limits may differ per insurance type
        """
        results = EligibilityService.check_eligibility(
            prospect=test_prospect,
            insurance_type="auto",
            coverage_amount=Decimal("50000")
        )

        # Should get results for auto insurance
        assert len(results) > 0

        # Check that results have coverage_limit set
        eligible = [r for r in results if r.is_eligible]
        if eligible:
            assert eligible[0].coverage_limit is not None

    def test_risk_category_affects_eligibility(self, test_db, test_broker):
        """
        Test: Risk category determines which providers accept prospect.

        Business rule: Low risk = more providers, High risk = fewer providers
        """
        # Create low-risk prospect
        low_risk = Prospect(
            type=ProspectType.INDIVIDUAL,
            first_name="Basso",
            last_name="Rischio",
            birth_date=date(1990, 1, 1),  # Age 35
            email="lowrisk@test.com",
            phone="+39 340 3333333",
            tax_code="BSSRSC90A01H501X",
            risk_category=RiskCategory.LOW,
            assigned_broker=test_broker.id,
            created_by=test_broker.id
        )
        test_db.add(low_risk)
        test_db.commit()

        low_risk_results = EligibilityService.check_eligibility(
            prospect=low_risk,
            insurance_type="life",
            coverage_amount=Decimal("200000")
        )

        # Create high-risk prospect (same age)
        high_risk = Prospect(
            type=ProspectType.INDIVIDUAL,
            first_name="Alto",
            last_name="Rischio",
            birth_date=date(1990, 1, 1),  # Age 35
            email="highrisk@test.com",
            phone="+39 340 4444444",
            tax_code="LTRSCH90A01H501V",
            risk_category=RiskCategory.HIGH,
            assigned_broker=test_broker.id,
            created_by=test_broker.id
        )
        test_db.add(high_risk)
        test_db.commit()

        high_risk_results = EligibilityService.check_eligibility(
            prospect=high_risk,
            insurance_type="life",
            coverage_amount=Decimal("200000")
        )

        # Count eligible providers
        low_eligible_count = sum(1 for r in low_risk_results if r.is_eligible)
        high_eligible_count = sum(1 for r in high_risk_results if r.is_eligible)

        # Low risk should have more or equal providers
        assert low_eligible_count >= high_eligible_count

    def test_all_providers_checked(self, test_prospect):
        """
        Test: Eligibility check returns results for all 4 providers.

        Quality check: Ensure we're not missing any provider
        """
        results = EligibilityService.check_eligibility(
            prospect=test_prospect,
            insurance_type="life",
            coverage_amount=Decimal("250000")
        )

        # Should have exactly 4 providers
        assert len(results) == 4

        # Check provider names
        provider_names = {r.provider for r in results}
        expected = {"generali", "unipolsai", "allianz", "axa"}
        assert provider_names == expected

    def test_best_provider_selection(self, test_prospect):
        """
        Test: get_best_provider returns the provider with lowest premium.

        Business logic: "Best" = cheapest premium among eligible providers
        """
        results = EligibilityService.check_eligibility(
            prospect=test_prospect,
            insurance_type="life",
            coverage_amount=Decimal("250000")
        )

        best = EligibilityService.get_best_provider(results)

        if best:
            # Best should be eligible
            assert best.is_eligible is True

            # Best should have lowest premium among eligible
            eligible = [r for r in results if r.is_eligible]
            min_premium = min(r.base_premium for r in eligible)
            assert best.base_premium == min_premium

    def test_zero_eligible_providers(self, test_db, test_broker):
        """
        Test: Graceful handling when no providers accept prospect.

        Edge case: Extreme age + high risk = no options
        """
        extreme_prospect = Prospect(
            type=ProspectType.INDIVIDUAL,
            first_name="Estremo",
            last_name="Caso",
            birth_date=date(1930, 1, 1),  # Age 95
            email="extreme@test.com",
            phone="+39 340 5555555",
            tax_code="STRMCS30A01H501U",
            risk_category=RiskCategory.HIGH,
            assigned_broker=test_broker.id,
            created_by=test_broker.id
        )
        test_db.add(extreme_prospect)
        test_db.commit()

        results = EligibilityService.check_eligibility(
            prospect=extreme_prospect,
            insurance_type="life",
            coverage_amount=Decimal("100000")
        )

        # Should return results (with all ineligible)
        assert len(results) == 4
        assert all(not r.is_eligible for r in results)

        # get_best_provider should return None
        best = EligibilityService.get_best_provider(results)
        assert best is None


class TestEligibilityProviderModel:
    """Test the EligibilityProvider Pydantic model."""

    def test_eligibility_provider_creation(self):
        """Test: Can create EligibilityProvider with valid data."""
        provider = EligibilityProvider(
            provider="generali",
            is_eligible=True,
            reason="Eligible",
            base_premium=Decimal("750.00"),
            coverage_limit=Decimal("500000.00")
        )

        assert provider.provider == "generali"
        assert provider.is_eligible is True
        assert provider.base_premium == Decimal("750.00")

    def test_eligibility_provider_ineligible(self):
        """Test: Ineligible provider has reason but no premium."""
        provider = EligibilityProvider(
            provider="axa",
            is_eligible=False,
            reason="Age exceeds maximum (65)",
            base_premium=None,
            coverage_limit=None
        )

        assert provider.is_eligible is False
        assert "age" in provider.reason.lower()
        assert provider.base_premium is None
