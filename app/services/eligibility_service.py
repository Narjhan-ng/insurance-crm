"""
Eligibility Service
Pre-qualification check for insurance policies across providers
"""
from typing import List, Dict, Any, Tuple
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.prospect import Prospect


class EligibilityProvider:
    """
    Represents an insurance provider's eligibility result.

    Contains provider-specific rules and base premium estimates.
    """
    def __init__(
        self,
        provider: str,
        is_eligible: bool,
        reason: str = None,
        base_premium: Decimal = None,
        coverage_max: Decimal = None,
        notes: str = None
    ):
        self.provider = provider
        self.is_eligible = is_eligible
        self.reason = reason
        self.base_premium = base_premium
        self.coverage_max = coverage_max
        self.notes = notes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "is_eligible": self.is_eligible,
            "reason": self.reason,
            "base_premium": float(self.base_premium) if self.base_premium else None,
            "coverage_max": float(self.coverage_max) if self.coverage_max else None,
            "notes": self.notes
        }


class EligibilityService:
    """
    Service for checking insurance eligibility across providers.

    WHY eligibility check matters:
    - Don't quote if customer isn't eligible (waste of time)
    - Different providers have different rules (age, risk, type)
    - Pre-screening improves conversion (only quote eligible prospects)
    - Better customer experience (instant feedback)

    BUSINESS FLOW:
    1. Prospect provides basic info (age, type, risk)
    2. Eligibility check runs against all providers
    3. Returns list of eligible providers with base estimates
    4. Broker focuses on eligible providers for quoting
    5. Saves time + improves success rate

    PROVIDER RULES (Simplified):
    This mirrors how real insurance companies work:
    - Age limits vary by provider and product
    - Risk categories affect eligibility
    - Business vs individual has different rules

    TELCO EQUIVALENT:
    In Telco CRM, this was "Coverage Check" - checking if 4 ISPs
    could provide service at an address. Same concept, different domain.
    """

    # Provider eligibility rules (hardcoded for now, could be database)
    # In production, this would come from provider APIs or database
    PROVIDER_RULES = {
        "generali": {
            "life": {
                "age_min": 18,
                "age_max": 75,
                "risk_categories": ["low", "medium"],
                "base_premium_multiplier": Decimal("1.0"),
                "coverage_max": Decimal("500000")
            },
            "auto": {
                "age_min": 18,
                "age_max": None,
                "risk_categories": ["low", "medium", "high"],
                "base_premium_multiplier": Decimal("1.1"),
                "coverage_max": Decimal("100000")
            },
            "home": {
                "age_min": 18,
                "age_max": None,
                "risk_categories": ["low", "medium"],
                "base_premium_multiplier": Decimal("1.0"),
                "coverage_max": Decimal("1000000")
            },
            "health": {
                "age_min": 0,
                "age_max": 85,
                "risk_categories": ["low", "medium"],
                "base_premium_multiplier": Decimal("1.2"),
                "coverage_max": Decimal("250000")
            }
        },
        "unipolsai": {
            "life": {
                "age_min": 21,
                "age_max": 70,
                "risk_categories": ["low"],
                "base_premium_multiplier": Decimal("0.95"),
                "coverage_max": Decimal("400000")
            },
            "auto": {
                "age_min": 21,
                "age_max": None,
                "risk_categories": ["low", "medium"],
                "base_premium_multiplier": Decimal("1.0"),
                "coverage_max": Decimal("150000")
            },
            "home": {
                "age_min": 18,
                "age_max": None,
                "risk_categories": ["low", "medium", "high"],
                "base_premium_multiplier": Decimal("1.05"),
                "coverage_max": Decimal("800000")
            },
            "health": {
                "age_min": 18,
                "age_max": 80,
                "risk_categories": ["low", "medium"],
                "base_premium_multiplier": Decimal("1.15"),
                "coverage_max": Decimal("200000")
            }
        },
        "allianz": {
            "life": {
                "age_min": 18,
                "age_max": 80,
                "risk_categories": ["low", "medium", "high"],
                "base_premium_multiplier": Decimal("1.1"),
                "coverage_max": Decimal("750000")
            },
            "auto": {
                "age_min": 18,
                "age_max": None,
                "risk_categories": ["low", "medium", "high"],
                "base_premium_multiplier": Decimal("1.05"),
                "coverage_max": Decimal("120000")
            },
            "home": {
                "age_min": 18,
                "age_max": None,
                "risk_categories": ["low", "medium"],
                "base_premium_multiplier": Decimal("0.98"),
                "coverage_max": Decimal("1200000")
            },
            "health": {
                "age_min": 0,
                "age_max": 75,
                "risk_categories": ["low"],
                "base_premium_multiplier": Decimal("1.25"),
                "coverage_max": Decimal("300000")
            }
        },
        "axa": {
            "life": {
                "age_min": 20,
                "age_max": 65,
                "risk_categories": ["low", "medium"],
                "base_premium_multiplier": Decimal("0.92"),
                "coverage_max": Decimal("600000")
            },
            "auto": {
                "age_min": 23,
                "age_max": None,
                "risk_categories": ["low", "medium"],
                "base_premium_multiplier": Decimal("0.95"),
                "coverage_max": Decimal("180000")
            },
            "home": {
                "age_min": 25,
                "age_max": None,
                "risk_categories": ["low"],
                "base_premium_multiplier": Decimal("1.02"),
                "coverage_max": Decimal("900000")
            },
            "health": {
                "age_min": 18,
                "age_max": 70,
                "risk_categories": ["low", "medium"],
                "base_premium_multiplier": Decimal("1.18"),
                "coverage_max": Decimal("220000")
            }
        }
    }

    # Base premium estimates by insurance type (annual)
    BASE_PREMIUMS = {
        "life": Decimal("800"),
        "auto": Decimal("600"),
        "home": Decimal("500"),
        "health": Decimal("1200")
    }

    @classmethod
    def calculate_age(cls, birth_date: date) -> int:
        """Calculate age from birth date"""
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    @classmethod
    def check_eligibility(
        cls,
        prospect: Prospect,
        insurance_type: str,
        db: Session = None
    ) -> List[EligibilityProvider]:
        """
        Check eligibility across all providers for a given insurance type.

        Args:
            prospect: Prospect object with age, risk_category, etc.
            insurance_type: Type of insurance (life, auto, home, health)
            db: Database session (optional, for future use)

        Returns:
            List of EligibilityProvider objects (both eligible and ineligible)

        Example:
            prospect = db.query(Prospect).filter(Prospect.id == 123).first()
            results = EligibilityService.check_eligibility(prospect, "life")

            for result in results:
                if result.is_eligible:
                    print(f"{result.provider}: Eligible, premium ~€{result.base_premium}")
                else:
                    print(f"{result.provider}: Not eligible - {result.reason}")
        """
        results = []

        # Calculate prospect age if birth_date provided
        age = None
        if prospect.birth_date:
            age = cls.calculate_age(prospect.birth_date)

        # Check each provider
        for provider_name, provider_rules in cls.PROVIDER_RULES.items():
            # Get rules for this insurance type
            type_rules = provider_rules.get(insurance_type)

            if not type_rules:
                # Provider doesn't offer this insurance type
                results.append(EligibilityProvider(
                    provider=provider_name,
                    is_eligible=False,
                    reason=f"Provider does not offer {insurance_type} insurance"
                ))
                continue

            # Check age eligibility
            if age is not None:
                min_age = type_rules.get("age_min")
                max_age = type_rules.get("age_max")

                if min_age and age < min_age:
                    results.append(EligibilityProvider(
                        provider=provider_name,
                        is_eligible=False,
                        reason=f"Age {age} below minimum {min_age}"
                    ))
                    continue

                if max_age and age > max_age:
                    results.append(EligibilityProvider(
                        provider=provider_name,
                        is_eligible=False,
                        reason=f"Age {age} exceeds maximum {max_age}"
                    ))
                    continue

            # Check risk category
            if prospect.risk_category:
                allowed_risks = type_rules.get("risk_categories", [])
                if prospect.risk_category.value not in allowed_risks:
                    results.append(EligibilityProvider(
                        provider=provider_name,
                        is_eligible=False,
                        reason=f"Risk category '{prospect.risk_category.value}' not accepted"
                    ))
                    continue

            # Calculate estimated base premium
            base_premium = cls.BASE_PREMIUMS.get(insurance_type, Decimal("1000"))
            multiplier = type_rules.get("base_premium_multiplier", Decimal("1.0"))
            estimated_premium = base_premium * multiplier

            # Adjust for risk category
            if prospect.risk_category:
                risk_multipliers = {
                    "low": Decimal("0.9"),
                    "medium": Decimal("1.0"),
                    "high": Decimal("1.3")
                }
                estimated_premium *= risk_multipliers.get(
                    prospect.risk_category.value,
                    Decimal("1.0")
                )

            # ELIGIBLE!
            results.append(EligibilityProvider(
                provider=provider_name,
                is_eligible=True,
                base_premium=estimated_premium,
                coverage_max=type_rules.get("coverage_max"),
                notes=f"Estimated annual premium based on {insurance_type} insurance"
            ))

        return results

    @classmethod
    def get_eligible_providers(
        cls,
        prospect: Prospect,
        insurance_type: str
    ) -> List[str]:
        """
        Get list of provider names that prospect is eligible for.

        Convenience method that returns only provider names.

        Args:
            prospect: Prospect object
            insurance_type: Insurance type

        Returns:
            List of provider names (e.g., ["generali", "allianz"])

        Example:
            eligible = EligibilityService.get_eligible_providers(prospect, "life")
            # Returns: ["generali", "allianz", "axa"]
        """
        results = cls.check_eligibility(prospect, insurance_type)
        return [r.provider for r in results if r.is_eligible]

    @classmethod
    def get_best_provider(
        cls,
        prospect: Prospect,
        insurance_type: str
    ) -> Tuple[str, Decimal]:
        """
        Get provider with lowest estimated premium.

        Args:
            prospect: Prospect object
            insurance_type: Insurance type

        Returns:
            Tuple of (provider_name, estimated_premium) or (None, None) if none eligible

        Example:
            provider, premium = EligibilityService.get_best_provider(prospect, "auto")
            # Returns: ("axa", Decimal("570.00"))
        """
        results = cls.check_eligibility(prospect, insurance_type)
        eligible = [r for r in results if r.is_eligible]

        if not eligible:
            return None, None

        # Sort by premium (lowest first)
        eligible.sort(key=lambda x: x.base_premium)

        best = eligible[0]
        return best.provider, best.base_premium
