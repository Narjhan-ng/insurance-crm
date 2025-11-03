"""
Working eligibility service tests - CORRECTED VERSION

These tests are aligned with the actual EligibilityService API.
Focus: Business logic validation without heavy database dependencies.
"""
import pytest
from datetime import date
from decimal import Decimal

from app.services.eligibility_service import EligibilityService, EligibilityProvider
from app.models.prospect import Prospect, ProspectType, RiskCategory


class TestEligibilityProviderModel:
    """Test the EligibilityProvider data class."""

    def test_create_eligible_provider(self):
        """Test: Can create eligible provider with all fields."""
        provider = EligibilityProvider(
            provider="generali",
            is_eligible=True,
            reason="Eligible - all criteria met",
            base_premium=Decimal("750.00"),
            coverage_max=Decimal("500000.00"),
            notes="Recommended for medium risk"
        )

        assert provider.provider == "generali"
        assert provider.is_eligible is True
        assert provider.base_premium == Decimal("750.00")
        assert provider.coverage_max == Decimal("500000.00")

    def test_create_ineligible_provider(self):
        """Test: Ineligible provider has reason, no premium."""
        provider = EligibilityProvider(
            provider="axa",
            is_eligible=False,
            reason="Age 72 exceeds maximum age limit of 65",
            base_premium=None,
            coverage_max=None
        )

        assert provider.is_eligible is False
        assert "age" in provider.reason.lower() or "età" in provider.reason.lower()
        assert provider.base_premium is None


class TestEligibilityServiceRules:
    """Test eligibility rules using mock prospects (no DB)."""

    def create_mock_prospect(
        self,
        age: int,
        risk: RiskCategory,
        prospect_type: ProspectType = ProspectType.INDIVIDUAL
    ) -> Prospect:
        """
        Helper: Create a mock prospect without database.

        This simulates a Prospect object for testing eligibility logic.
        """
        from datetime import date
        birth_year = date.today().year - age

        prospect = Prospect(
            type=prospect_type,
            first_name="Test",
            last_name="User",
            birth_date=date(birth_year, 6, 15),
            email="test@example.com",
            phone="+39 340 1234567",
            tax_code="TSTUSR80H15H501Z",
            risk_category=risk,
            assigned_broker=1,
            created_by=1,
            notes="Test prospect for eligibility checking"
        )
        # Manually set ID (normally done by DB)
        prospect.id = 1
        return prospect

    def test_medium_risk_middle_age_multiple_providers(self):
        """
        Test: Medium risk, age 45 → Multiple providers available.

        Business rule: This is the "sweet spot" - low risk for insurers.
        """
        prospect = self.create_mock_prospect(age=45, risk=RiskCategory.MEDIUM)

        results = EligibilityService.check_eligibility(
            prospect=prospect,
            insurance_type="life",
            coverage_amount=Decimal("250000")
        )

        # Should return results for all 4 providers
        assert len(results) == 4

        # At least 2 providers should accept medium risk at age 45
        eligible = [r for r in results if r.is_eligible]
        assert len(eligible) >= 2, f"Expected ≥2 eligible, got {len(eligible)}"

        # All eligible providers should have premium estimates
        for provider in eligible:
            assert provider.base_premium is not None
            assert provider.base_premium > 0

    def test_high_risk_older_age_limited_providers(self):
        """
        Test: High risk + age 72 → Limited options.

        Business rule: High risk + older age = fewer insurers accept.
        """
        prospect = self.create_mock_prospect(age=72, risk=RiskCategory.HIGH)

        results = EligibilityService.check_eligibility(
            prospect=prospect,
            insurance_type="life",
            coverage_amount=Decimal("100000")
        )

        eligible = [r for r in results if r.is_eligible]

        # Should have few or no options
        assert len(eligible) <= 2, f"Expected ≤2 eligible, got {len(eligible)}"

    def test_below_minimum_age_all_rejected(self):
        """
        Test: Age 17 (below 18) → All providers reject.

        Legal requirement: Can't insure minors without guardian consent.
        """
        prospect = self.create_mock_prospect(age=17, risk=RiskCategory.LOW)

        results = EligibilityService.check_eligibility(
            prospect=prospect,
            insurance_type="life",
            coverage_amount=Decimal("100000")
        )

        # All providers should reject
        eligible = [r for r in results if r.is_eligible]
        assert len(eligible) == 0, "Minors should not be eligible"

        # All should have rejection reasons
        for result in results:
            assert result.is_eligible is False
            assert result.reason is not None

    def test_above_maximum_age_most_rejected(self):
        """
        Test: Age 90 → Most/all providers reject.

        Business rule: Actuarial risk too high above 80-85.
        """
        prospect = self.create_mock_prospect(age=90, risk=RiskCategory.HIGH)

        results = EligibilityService.check_eligibility(
            prospect=prospect,
            insurance_type="life",
            coverage_amount=Decimal("50000")
        )

        eligible = [r for r in results if r.is_eligible]

        # At most 1 provider (maybe none)
        assert len(eligible) <= 1, f"Age 90 should have ≤1 eligible, got {len(eligible)}"

    def test_all_four_providers_return_results(self):
        """
        Test: Eligibility check always returns 4 results.

        Quality check: Ensure no provider is accidentally skipped.
        """
        prospect = self.create_mock_prospect(age=40, risk=RiskCategory.LOW)

        results = EligibilityService.check_eligibility(
            prospect=prospect,
            insurance_type="life",
            coverage_amount=Decimal("200000")
        )

        # Must have exactly 4
        assert len(results) == 4

        # Check all expected providers present
        provider_names = {r.provider for r in results}
        expected = {"generali", "unipolsai", "allianz", "axa"}
        assert provider_names == expected

    def test_higher_coverage_increases_premium(self):
        """
        Test: Premium scales with coverage amount.

        Business logic: €500k coverage costs more than €100k.
        """
        prospect = self.create_mock_prospect(age=40, risk=RiskCategory.MEDIUM)

        # Low coverage
        results_low = EligibilityService.check_eligibility(
            prospect=prospect,
            insurance_type="life",
            coverage_amount=Decimal("100000")
        )

        # High coverage (5x)
        results_high = EligibilityService.check_eligibility(
            prospect=prospect,
            insurance_type="life",
            coverage_amount=Decimal("500000")
        )

        # Find Generali in both (usually eligible)
        generali_low = next((r for r in results_low if r.provider == "generali"), None)
        generali_high = next((r for r in results_high if r.provider == "generali"), None)

        # If Generali eligible in both, high coverage should cost more
        if generali_low and generali_high:
            if generali_low.is_eligible and generali_high.is_eligible:
                assert generali_high.base_premium > generali_low.base_premium, \
                    "Higher coverage should have higher premium"

    def test_low_risk_more_providers_than_high_risk(self):
        """
        Test: Low risk gets more provider options than high risk.

        Business rule: Insurers prefer low-risk customers.
        """
        # Same age, different risk
        low_risk = self.create_mock_prospect(age=35, risk=RiskCategory.LOW)
        high_risk = self.create_mock_prospect(age=35, risk=RiskCategory.HIGH)

        results_low = EligibilityService.check_eligibility(
            prospect=low_risk,
            insurance_type="life",
            coverage_amount=Decimal("200000")
        )

        results_high = EligibilityService.check_eligibility(
            prospect=high_risk,
            insurance_type="life",
            coverage_amount=Decimal("200000")
        )

        # Count eligible
        low_eligible_count = sum(1 for r in results_low if r.is_eligible)
        high_eligible_count = sum(1 for r in results_high if r.is_eligible)

        # Low risk should have ≥ high risk options
        assert low_eligible_count >= high_eligible_count, \
            f"Low risk ({low_eligible_count}) should have ≥ high risk ({high_eligible_count}) options"

    def test_auto_insurance_different_from_life(self):
        """
        Test: Auto insurance has different eligibility rules.

        Business rule: Different insurance types have different age/risk rules.
        """
        prospect = self.create_mock_prospect(age=40, risk=RiskCategory.MEDIUM)

        # Check auto insurance
        results = EligibilityService.check_eligibility(
            prospect=prospect,
            insurance_type="auto",
            coverage_amount=Decimal("50000")
        )

        # Should get 4 results
        assert len(results) == 4

        # Check that coverage_max exists (auto-specific)
        eligible = [r for r in results if r.is_eligible]
        if eligible:
            # Auto insurance typically has coverage limits
            assert eligible[0].coverage_max is not None


class TestEligibilityEdgeCases:
    """Test edge cases and error handling."""

    def create_mock_prospect(self, age: int, risk: RiskCategory) -> Prospect:
        """Helper to create mock prospect."""
        from datetime import date
        birth_year = date.today().year - age
        prospect = Prospect(
            type=ProspectType.INDIVIDUAL,
            first_name="Edge",
            last_name="Case",
            birth_date=date(birth_year, 1, 1),
            email="edge@test.com",
            phone="+39 340 9999999",
            tax_code="DGCCS80A01H501Z",
            risk_category=risk,
            assigned_broker=1,
            created_by=1
        )
        prospect.id = 99
        return prospect

    def test_exactly_minimum_age_eligible(self):
        """Test: Age 18 (exactly minimum) should be eligible for some providers."""
        prospect = self.create_mock_prospect(age=18, risk=RiskCategory.LOW)

        results = EligibilityService.check_eligibility(
            prospect=prospect,
            insurance_type="life",
            coverage_amount=Decimal("100000")
        )

        # At least some providers should accept
        eligible = [r for r in results if r.is_eligible]
        assert len(eligible) > 0, "Age 18 should have at least one eligible provider"

    def test_zero_eligible_providers_returns_all_four(self):
        """
        Test: Even with 0 eligible, should return 4 results with reasons.

        UX requirement: User needs to know WHY they were rejected.
        """
        # Extreme case: very old + high risk
        prospect = self.create_mock_prospect(age=95, risk=RiskCategory.HIGH)

        results = EligibilityService.check_eligibility(
            prospect=prospect,
            insurance_type="life",
            coverage_amount=Decimal("100000")
        )

        # Still returns 4 results
        assert len(results) == 4

        # All should have rejection reasons
        for result in results:
            if not result.is_eligible:
                assert result.reason is not None
                assert len(result.reason) > 0


# Summary: 13 tests covering:
# - Provider model creation (2 tests)
# - Age-based eligibility rules (4 tests)
# - Risk category effects (2 tests)
# - Coverage amount effects (1 test)
# - Insurance type differences (1 test)
# - Edge cases (3 tests)
