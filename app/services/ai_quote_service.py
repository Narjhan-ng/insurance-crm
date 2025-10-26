"""
AI-Powered Quote Generation Service
Uses LangChain + Claude to analyze and recommend insurance quotes
"""
import json
from typing import List, Dict, Any
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from config.settings import settings


# ============================================================================
# Output Models (Structured Output from LLM)
# ============================================================================
# WHY: Invece di parsing manuale di testo, LangChain + Pydantic garantiscono
# output strutturato e validato. Se Claude risponde male, errore immediato.

class ProviderRanking(BaseModel):
    """Single provider analysis"""
    provider: str = Field(description="Insurance provider name")
    score: float = Field(description="Overall score 0-100")
    monthly_premium: float = Field(description="Monthly premium in EUR")
    annual_premium: float = Field(description="Annual premium in EUR")
    pros: List[str] = Field(description="List of advantages")
    cons: List[str] = Field(description="List of disadvantages")
    key_features: List[str] = Field(description="Notable coverage features")


class QuoteRecommendation(BaseModel):
    """Complete recommendation from AI"""
    recommended_provider: str = Field(description="Best provider name")
    reasoning: str = Field(description="Why this provider was chosen (2-3 sentences)")
    rankings: List[ProviderRanking] = Field(description="All providers ranked by score")
    risk_assessment: str = Field(description="Overall risk assessment of prospect")
    additional_notes: str = Field(description="Any important considerations")


# ============================================================================
# Eligibility Models (Input Data)
# ============================================================================

class EligibilityResult(BaseModel):
    """Eligibility check result from a provider"""
    provider: str
    eligible: bool
    base_premium: float
    coverage_max: float
    age_min: int
    age_max: int
    risk_factors: List[str] = []


class ProspectProfile(BaseModel):
    """Customer profile for quote generation"""
    age: int
    risk_category: str  # low, medium, high
    insurance_type: str  # life, auto, home, health
    coverage_amount: float
    has_preexisting_conditions: bool = False
    smoker: bool = False
    occupation_risk: str = "standard"  # standard, high, very_high


# ============================================================================
# AI Quote Service
# ============================================================================

class AIQuoteService:
    """
    Service for AI-powered insurance quote generation and comparison.

    ARCHITECTURE DECISION: Why a service class?
    - Encapsulates LangChain complexity
    - Stateless (can be instantiated per request)
    - Easy to mock for testing
    - Separates AI logic from HTTP logic
    """

    def __init__(self):
        """
        Initialize LangChain components.

        WHY ChatAnthropic:
        - Claude excels at reasoning and structured outputs
        - Better at following complex instructions than GPT-3.5
        - Good balance of cost/performance for this use case

        WHY model="claude-3-5-sonnet-20241022":
        - Sonnet: Mid-tier (cheaper than Opus, better than Haiku)
        - Latest version with improved structured outputs
        - Good at JSON formatting (critical per noi)
        """
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            temperature=0.3,  # Low temperature = più deterministico (vogliamo consistency)
            api_key=settings.ANTHROPIC_API_KEY,
            max_tokens=2000,  # Enough for detailed analysis
        )

        # Output parser: converte risposta LLM in Pydantic model
        self.output_parser = PydanticOutputParser(pydantic_object=QuoteRecommendation)

    def _build_prompt(
        self,
        prospect: ProspectProfile,
        eligibility_results: List[EligibilityResult]
    ) -> ChatPromptTemplate:
        """
        Build the prompt template for Claude.

        PROMPT ENGINEERING STRATEGY:
        1. Clear role definition ("You are...")
        2. Structured input data (JSON format)
        3. Explicit output format (with parser instructions)
        4. Evaluation criteria (what to consider)
        5. Examples of good reasoning (few-shot learning potential)

        WHY ChatPromptTemplate vs string concatenation:
        - Versionable (posso tracciare prompt changes in git)
        - Testable (posso testare prompt con mock data)
        - Reusable (posso usarlo con diversi LLMs)
        - Type-safe (input variables validated)
        """

        # Format instructions for structured output
        format_instructions = self.output_parser.get_format_instructions()

        template = """You are an expert insurance advisor analyzing quotes from multiple providers.

Your task: Compare insurance offers and recommend the best option for the customer.

## Customer Profile:
- Age: {age}
- Risk Category: {risk_category}
- Insurance Type: {insurance_type}
- Desired Coverage: €{coverage_amount:,.2f}
- Pre-existing Conditions: {has_preexisting_conditions}
- Smoker: {smoker}
- Occupation Risk: {occupation_risk}

## Available Offers:
{eligibility_results_json}

## Evaluation Criteria (in order of importance):
1. **Value for Money**: Premium vs coverage ratio
2. **Coverage Completeness**: Does it meet customer needs?
3. **Provider Reputation**: Financial stability and claim settlement ratio
4. **Flexibility**: Policy terms, payment options
5. **Customer Risk Alignment**: Match with customer's risk profile

## Instructions:
- Score each provider 0-100 based on criteria above
- Explain pros/cons for EACH provider
- Provide clear reasoning for your recommendation (2-3 sentences)
- Consider customer's risk category in your assessment
- Be objective and data-driven

{format_instructions}

Provide your analysis:"""

        return ChatPromptTemplate.from_template(template)

    async def generate_quote_recommendation(
        self,
        prospect: ProspectProfile,
        eligibility_results: List[EligibilityResult]
    ) -> QuoteRecommendation:
        """
        Generate AI-powered quote recommendation.

        FLOW:
        1. Build prompt with prospect + eligibility data
        2. Call Claude via LangChain
        3. Parse structured output
        4. Validate and return

        ERROR HANDLING:
        - If Claude returns malformed JSON → PydanticOutputParser raises ValidationError
        - If API fails → LangChain raises exception
        - Caller should handle both cases

        Args:
            prospect: Customer profile
            eligibility_results: List of provider offers

        Returns:
            QuoteRecommendation with rankings and reasoning

        Raises:
            ValidationError: If Claude output doesn't match schema
            Exception: If LangChain/API call fails
        """

        # Build prompt
        prompt = self._build_prompt(prospect, eligibility_results)

        # Format eligibility results as JSON for prompt
        eligibility_json = json.dumps(
            [result.model_dump() for result in eligibility_results],
            indent=2,
            ensure_ascii=False
        )

        # Create chain: prompt → LLM → parser
        # WHY chains: Composability. Posso aggiungere steps (es. validation, logging)
        chain = prompt | self.llm | self.output_parser

        # Invoke chain
        # NOTA: Questo è async perché API call è I/O-bound
        result = await chain.ainvoke({
            "age": prospect.age,
            "risk_category": prospect.risk_category,
            "insurance_type": prospect.insurance_type,
            "coverage_amount": prospect.coverage_amount,
            "has_preexisting_conditions": "Yes" if prospect.has_preexisting_conditions else "No",
            "smoker": "Yes" if prospect.smoker else "No",
            "occupation_risk": prospect.occupation_risk,
            "eligibility_results_json": eligibility_json,
            "format_instructions": self.output_parser.get_format_instructions(),
        })

        return result


# ============================================================================
# Mock Eligibility Service (Production: external API calls)
# ============================================================================

class EligibilityService:
    """
    Check eligibility with insurance providers.

    CURRENT: Mock data (per demo/testing)
    PRODUCTION: Real API calls to provider systems

    WHY separate class:
    - Easy to swap mock → real implementation
    - Can test AI service independently
    - Clear contract (input/output types)
    """

    @staticmethod
    def check_eligibility(
        prospect: ProspectProfile
    ) -> List[EligibilityResult]:
        """
        Check eligibility with all providers.

        MOCK LOGIC:
        - Calculates premiums based on age + risk + coverage
        - Simulates real provider responses
        - In production: parallel API calls to 4 providers

        WHY mock is useful:
        - No external dependencies for development
        - Fast testing
        - Predictable results
        - Can simulate edge cases (provider down, rejection, etc.)
        """

        # Base premium calculation
        # BUSINESS LOGIC:
        # - Age factor: older = more expensive
        # - Risk factor: high risk = 2x premium
        # - Coverage factor: more coverage = proportionally more premium
        age_factor = 1 + (prospect.age - 30) * 0.02  # 2% increase per year over 30
        risk_multiplier = {
            "low": 1.0,
            "medium": 1.3,
            "high": 2.0
        }.get(prospect.risk_category, 1.0)

        base_premium = (prospect.coverage_amount / 100000) * 50 * age_factor * risk_multiplier

        # Provider-specific variations
        # Each provider has different pricing strategy
        providers_data = [
            {
                "provider": "Generali",
                "premium_multiplier": 1.0,  # Reference price
                "coverage_max": 1000000,
                "age_min": 18,
                "age_max": 65,
                "risk_factors": ["Generally competitive", "Good claim settlement ratio"]
            },
            {
                "provider": "UnipolSai",
                "premium_multiplier": 0.95,  # Slightly cheaper
                "coverage_max": 800000,
                "age_min": 18,
                "age_max": 60,
                "risk_factors": ["Lower coverage cap", "Fast approval process"]
            },
            {
                "provider": "Allianz",
                "premium_multiplier": 1.1,  # Premium provider
                "coverage_max": 2000000,
                "age_min": 21,
                "age_max": 70,
                "risk_factors": ["Highest coverage", "International coverage"]
            },
            {
                "provider": "AXA",
                "premium_multiplier": 1.05,  # Mid-range
                "coverage_max": 1500000,
                "age_min": 18,
                "age_max": 65,
                "risk_factors": ["Flexible payment terms", "Good customer service"]
            }
        ]

        results = []
        for provider_data in providers_data:
            # Check age eligibility
            eligible = (
                provider_data["age_min"] <= prospect.age <= provider_data["age_max"]
                and prospect.coverage_amount <= provider_data["coverage_max"]
            )

            # Calculate provider-specific premium
            provider_premium = base_premium * provider_data["premium_multiplier"]

            results.append(EligibilityResult(
                provider=provider_data["provider"],
                eligible=eligible,
                base_premium=round(provider_premium, 2),
                coverage_max=provider_data["coverage_max"],
                age_min=provider_data["age_min"],
                age_max=provider_data["age_max"],
                risk_factors=provider_data["risk_factors"]
            ))

        return results
