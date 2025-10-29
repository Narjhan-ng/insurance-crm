"""
Eligibility Check API
Pre-qualification for insurance policies
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any

from app.api.dependencies import get_db_session
from app.models.prospect import Prospect
from app.services.eligibility_service import EligibilityService


router = APIRouter()


# ============================================================================
# Request/Response Schemas
# ============================================================================

class EligibilityCheckRequest(BaseModel):
    """Request to check eligibility"""
    prospect_id: int
    insurance_type: str  # life, auto, home, health


class ProviderEligibility(BaseModel):
    """Provider eligibility result"""
    provider: str
    is_eligible: bool
    reason: str | None = None
    base_premium: float | None = None
    coverage_max: float | None = None
    notes: str | None = None


class EligibilityCheckResponse(BaseModel):
    """Eligibility check response"""
    prospect_id: int
    insurance_type: str
    eligible_count: int
    ineligible_count: int
    providers: List[ProviderEligibility]
    best_provider: str | None = None
    lowest_premium: float | None = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/check", response_model=EligibilityCheckResponse)
async def check_eligibility(
    request: EligibilityCheckRequest,
    db: Session = Depends(get_db_session)
):
    """
    Check insurance eligibility across all providers.

    BUSINESS FLOW:
    1. Fetch prospect details (age, risk category)
    2. Check eligibility rules for each provider
    3. Return eligible + ineligible providers with reasons
    4. Include base premium estimates

    WHY this matters:
    - Don't waste time quoting ineligible providers
    - Pre-screen before AI quote generation
    - Better customer experience (instant feedback)
    - Focus on providers likely to accept

    EXAMPLE USE CASE:
    Broker creates prospect (age 72, wants life insurance)
    → Calls eligibility check
    → Generali: Eligible (max age 75)
    → Allianz: Eligible (max age 80)
    → AXA: NOT eligible (max age 65) ❌
    → UnipolSai: NOT eligible (max age 70) ❌

    Result: Only generate quotes for Generali + Allianz

    Args:
        request: Eligibility check request
        db: Database session

    Returns:
        Eligibility results for all providers

    Raises:
        HTTPException 404: Prospect not found
        HTTPException 400: Invalid insurance type
    """
    # Validate insurance type
    valid_types = ["life", "auto", "home", "health"]
    if request.insurance_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid insurance type. Must be one of: {', '.join(valid_types)}"
        )

    # Fetch prospect
    prospect = db.query(Prospect).filter(Prospect.id == request.prospect_id).first()

    if not prospect:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prospect with id {request.prospect_id} not found"
        )

    # Perform eligibility check
    eligibility_results = EligibilityService.check_eligibility(
        prospect=prospect,
        insurance_type=request.insurance_type,
        db=db
    )

    # Convert to response format
    provider_results = [
        ProviderEligibility(**result.to_dict())
        for result in eligibility_results
    ]

    # Count eligible vs ineligible
    eligible_count = sum(1 for r in provider_results if r.is_eligible)
    ineligible_count = sum(1 for r in provider_results if not r.is_eligible)

    # Find best provider (lowest premium)
    best_provider, lowest_premium = EligibilityService.get_best_provider(
        prospect, request.insurance_type
    )

    return EligibilityCheckResponse(
        prospect_id=request.prospect_id,
        insurance_type=request.insurance_type,
        eligible_count=eligible_count,
        ineligible_count=ineligible_count,
        providers=provider_results,
        best_provider=best_provider,
        lowest_premium=float(lowest_premium) if lowest_premium else None
    )


@router.get("/providers")
async def list_providers():
    """
    List all insurance providers and their offerings.

    Returns basic information about available providers.

    Returns:
        Dictionary of providers and their supported insurance types
    """
    providers = {
        "generali": {
            "name": "Generali Italia",
            "offerings": ["life", "auto", "home", "health"],
            "description": "Major Italian insurance provider"
        },
        "unipolsai": {
            "name": "UnipolSai Assicurazioni",
            "offerings": ["life", "auto", "home", "health"],
            "description": "Leading Italian insurance group"
        },
        "allianz": {
            "name": "Allianz Italia",
            "offerings": ["life", "auto", "home", "health"],
            "description": "Global insurance leader"
        },
        "axa": {
            "name": "AXA Assicurazioni",
            "offerings": ["life", "auto", "home", "health"],
            "description": "International insurance group"
        }
    }

    return providers


@router.get("/rules/{provider}/{insurance_type}")
async def get_provider_rules(
    provider: str,
    insurance_type: str
):
    """
    Get eligibility rules for a specific provider and insurance type.

    Useful for debugging or showing customers why they're ineligible.

    Args:
        provider: Provider name (generali, unipolsai, allianz, axa)
        insurance_type: Insurance type (life, auto, home, health)

    Returns:
        Provider eligibility rules

    Raises:
        HTTPException 404: Provider or insurance type not found
    """
    # Validate provider
    if provider not in EligibilityService.PROVIDER_RULES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider}' not found"
        )

    # Get provider rules
    provider_rules = EligibilityService.PROVIDER_RULES[provider]

    # Validate insurance type
    if insurance_type not in provider_rules:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider}' does not offer '{insurance_type}' insurance"
        )

    rules = provider_rules[insurance_type]

    return {
        "provider": provider,
        "insurance_type": insurance_type,
        "age_min": rules.get("age_min"),
        "age_max": rules.get("age_max"),
        "accepted_risk_categories": rules.get("risk_categories"),
        "base_premium_multiplier": float(rules.get("base_premium_multiplier", 1.0)),
        "maximum_coverage": float(rules.get("coverage_max", 0))
    }
