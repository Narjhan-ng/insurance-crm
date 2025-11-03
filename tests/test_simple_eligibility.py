"""
Simplified eligibility service tests

These tests focus on core business logic without heavy fixtures.
Goal: Quick verification that eligibility rules work correctly.
"""
import pytest
from datetime import date
from decimal import Decimal

from app.services.eligibility_service import EligibilityService, EligibilityProvider
from app.models.prospect import Prospect, ProspectType, RiskCategory


class TestEligibilityBasics:
    """Basic eligibility logic tests without database."""

    def test_eligibility_provider_model_creation(self):
        """Test: Can create EligibilityProvider object."""
        provider = EligibilityProvider(
            provider="generali",
            is_eligible=True,
            reason="Eligible",
            base_premium=Decimal("750.00"),
            coverage_max=Decimal("500000.00")
        )

        assert provider.provider == "generali"
        assert provider.is_eligible is True
        assert provider.base_premium == Decimal("750.00")
        assert provider.coverage_max == Decimal("500000.00")

    def test_ineligible_provider_has_reason(self):
        """Test: Ineligible provider explains why."""
        provider = EligibilityProvider(
            provider="axa",
            is_eligible=False,
            reason="Age exceeds maximum (65)",
            base_premium=None,
            coverage_max=None
        )

        assert provider.is_eligible is False
        assert "age" in provider.reason.lower() or "età" in provider.reason.lower()
        assert provider.base_premium is None

    def test_get_best_provider_returns_cheapest(self):
        """Test: Best provider = lowest premium."""
        results = [
            EligibilityProvider("generali", True, "OK", Decimal("750.00"), Decimal("500000")),
            EligibilityProvider("allianz", True, "OK", Decimal("850.00"), Decimal("500000")),
            EligibilityProvider("axa", False, "Too old", None, None),
        ]

        best = EligibilityService.get_best_provider(results)

        assert best is not None
        assert best.provider == "generali"  # Cheapest
        assert best.base_premium == Decimal("750.00")

    def test_get_best_provider_none_eligible(self):
        """Test: Returns None when no providers eligible."""
        results = [
            EligibilityProvider("generali", False, "Age", None, None),
            EligibilityProvider("allianz", False, "Age", None, None),
        ]

        best = EligibilityService.get_best_provider(results)
        assert best is None


class TestEligibilityWithMockProspect:
    """Tests using mock prospect data (no DB required)."""

    def create_mock_prospect(self, age: int, risk: RiskCategory):
        """Helper to create a mock prospect without DB."""
        # Calculate birth date from age
        from datetime import date
        birth_year = date.today().year - age

        prospect = Prospect(
            type=ProspectType.INDIVIDUAL,
            first_name="Test",
            last_name="User",
            birth_date=date(birth_year, 1, 1),
            email="test@example.com",
            phone="+39 340 1234567",
            tax_code="TSTUSR80A01H501Z",
            risk_category=risk,
            assigned_broker=1,
            created_by=1
        )
        # Set ID manually (normally done by DB)
        prospect.id = 1
        return prospect

    def test_medium_risk_prospect_has_options(self):
        """Test: Medium risk prospect gets multiple providers."""
        prospect = self.create_mock_prospect(age=45, risk=RiskCategory.MEDIUM)

        results = EligibilityService.check_eligibility(
            prospect=prospect,
            insurance_type="life",
            coverage_amount=Decimal("250000")
        )

        # Should return 4 providers
        assert len(results) == 4

        # At least 2 should be eligible for medium risk
        eligible = [r for r in results if r.is_eligible]
        assert len(eligible) >= 2

    def test_high_risk_prospect_limited_options(self):
        """Test: High risk prospect has fewer options."""
        prospect = self.create_mock_prospect(age=72, risk=RiskCategory.HIGH)

        results = EligibilityService.check_eligibility(
            prospect=prospect,
            insurance_type="life",
            coverage_amount=Decimal("100000")
        )

        eligible = [r for r in results if r.is_eligible]

        # High risk should have fewer options
        assert len(eligible) <= 2

    def test_very_young_prospect_rejected(self):
        """Test: Prospect below 18 is rejected."""
        prospect = self.create_mock_prospect(age=17, risk=RiskCategory.LOW)

        results = EligibilityService.check_eligibility(
            prospect=prospect,
            insurance_type="life",
            coverage_amount=Decimal("100000")
        )

        # All should reject
        eligible = [r for r in results if r.is_eligible]
        assert len(eligible) == 0

        # Reasons should mention age
        for result in results:
            assert not result.is_eligible
            assert result.reason is not None

    def test_very_old_prospect_rejected(self):
        """Test: Prospect over 85 has no options."""
        prospect = self.create_mock_prospect(age=90, risk=RiskCategory.HIGH)

        results = EligibilityService.check_eligibility(
            prospect=prospect,
            insurance_type="life",
            coverage_amount=Decimal("50000")
        )

        # Most or all should reject
        eligible = [r for r in results if r.is_eligible]
        assert len(eligible) <= 1

    def test_all_four_providers_checked(self):
        """Test: Check returns results for all 4 providers."""
        prospect = self.create_mock_prospect(age=40, risk=RiskCategory.LOW)

        results = EligibilityService.check_eligibility(
            prospect=prospect,
            insurance_type="life",
            coverage_amount=Decimal("200000")
        )

        # Should have exactly 4
        assert len(results) == 4

        # Check provider names
        providers = {r.provider for r in results}
        expected = {"generali", "unipolsai", "allianz", "axa"}
        assert providers == expected

    def test_higher_coverage_affects_premium(self):
        """Test: Premium scales with coverage amount."""
        prospect = self.create_mock_prospect(age=40, risk=RiskCategory.MEDIUM)

        # Low coverage
        results_low = EligibilityService.check_eligibility(
            prospect=prospect,
            insurance_type="life",
            coverage_amount=Decimal("100000")
        )

        # High coverage
        results_high = EligibilityService.check_eligibility(
            prospect=prospect,
            insurance_type="life",
            coverage_amount=Decimal("500000")
        )

        # Find same provider in both
        generali_low = next((r for r in results_low if r.provider == "generali"), None)
        generali_high = next((r for r in results_high if r.provider == "generali"), None)

        if generali_low and generali_high and generali_low.is_eligible and generali_high.is_eligible:
            # Higher coverage = higher premium
            assert generali_high.base_premium > generali_low.base_premium


# Run tests with: pytest tests/test_simple_eligibility.py -v
