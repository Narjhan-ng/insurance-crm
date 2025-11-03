"""
Advisory Service with LangGraph multi-step workflow

This service implements a sophisticated AI-powered advisory system using LangGraph
to orchestrate multiple analysis steps with conditional routing.

WHY LangGraph vs Simple Chain:
- Complex decision trees (eligibility-based routing)
- Multiple AI calls with shared state
- Better observability (each node is traceable)
- Easier to add new analysis steps
- Can implement retry/fallback logic per node
"""
import logging
from typing import TypedDict, List, Dict, Optional, Annotated
from datetime import date, datetime
from decimal import Decimal

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from app.models.prospect import Prospect, RiskCategory
from app.services.eligibility_service import EligibilityService, EligibilityProvider
from config.settings import settings


logger = logging.getLogger(__name__)


# ============================================================================
# PYDANTIC OUTPUT MODELS (for structured AI responses)
# ============================================================================

class RiskAnalysis(BaseModel):
    """AI-generated risk assessment"""
    risk_score: float = Field(description="Overall risk score 0-100, where 0=very low risk, 100=very high risk")
    risk_factors: List[str] = Field(description="List of identified risk factors")
    mitigation_suggestions: List[str] = Field(description="Suggestions to reduce risk")
    overall_assessment: str = Field(description="Brief summary of risk profile")


class ProviderRecommendation(BaseModel):
    """AI recommendation for a single provider"""
    provider: str = Field(description="Provider name")
    rank: int = Field(description="Ranking position (1=best)")
    score: float = Field(description="Match score 0-100")
    pros: List[str] = Field(description="Advantages for this specific prospect")
    cons: List[str] = Field(description="Disadvantages or considerations")
    key_features: List[str] = Field(description="Notable coverage features")
    reasoning: str = Field(description="Why this ranking for THIS prospect")


class AdvisoryRecommendations(BaseModel):
    """Complete advisory output from AI"""
    recommendations: List[ProviderRecommendation] = Field(description="Ranked provider recommendations")
    primary_recommendation_reasoning: str = Field(description="Detailed explanation for #1 choice")
    risk_alignment: str = Field(description="How recommendations align with prospect's risk profile")


class PersonalizedMessage(BaseModel):
    """Personalized communication for prospect"""
    message: str = Field(description="Personalized advisory message adapted to prospect profile")
    tone: str = Field(description="Detected tone used (professional/friendly/educational)")
    call_to_action: str = Field(description="Clear next step for prospect")


# ============================================================================
# LANGGRAPH STATE DEFINITION
# ============================================================================

class AdvisoryState(TypedDict):
    """
    Shared state across all LangGraph nodes.

    WHY TypedDict:
    - Type safety for state keys
    - IDE autocomplete support
    - Clear documentation of data flow
    - LangGraph validates structure
    """

    # INPUT DATA
    prospect_id: int
    insurance_type: str
    prospect: Optional[Prospect]  # Full prospect object from DB

    # NODE 1 OUTPUT: Profile extraction
    age: int
    risk_category: str
    has_preexisting_conditions: bool
    occupation_risk: str
    profile_summary: str

    # NODE 2 OUTPUT: Eligibility check
    eligible_providers: List[EligibilityProvider]
    eligibility_count: int

    # NODE 3B OUTPUT: Risk analysis (from AI)
    risk_analysis: Optional[RiskAnalysis]

    # NODE 4 OUTPUT: Recommendations (from AI)
    advisory_recommendations: Optional[AdvisoryRecommendations]

    # NODE 5 OUTPUT: Personalization (from AI)
    personalized_message: Optional[PersonalizedMessage]

    # METADATA
    workflow_path: List[str]  # Track which nodes were executed
    error: Optional[str]
    stage: str  # Current workflow stage


# ============================================================================
# LANGGRAPH NODES (each node is a function that updates state)
# ============================================================================

def profile_extractor_node(state: AdvisoryState) -> AdvisoryState:
    """
    NODE 1: Extract and normalize prospect profile data.

    INPUT: prospect object
    OUTPUT: Structured profile fields (age, risk_category, etc.)
    LOGIC: Pure Python, no AI

    WHY separate node:
    - Centralizes profile logic
    - Can be unit tested independently
    - Validates data before AI calls
    """
    logger.info(f"[NODE 1] Extracting profile for prospect {state['prospect_id']}")

    prospect = state["prospect"]

    # Calculate age
    if prospect.birth_date:
        today = date.today()
        age = today.year - prospect.birth_date.year
        if today.month < prospect.birth_date.month or (
            today.month == prospect.birth_date.month and today.day < prospect.birth_date.day
        ):
            age -= 1
    else:
        age = 40  # Default fallback

    # Determine risk factors by analyzing notes and risk category
    has_conditions = False
    if prospect.notes:
        # Check for common medical condition keywords
        medical_keywords = [
            'diabete', 'diabetes', 'ipertensione', 'hypertension',
            'cardiaco', 'cardiac', 'malattia', 'disease', 'cronica', 'chronic',
            'asma', 'asthma', 'tumore', 'cancer', 'terapia', 'therapy'
        ]
        notes_lower = prospect.notes.lower()
        has_conditions = any(keyword in notes_lower for keyword in medical_keywords)


    # Also consider high risk category as indicator
    if prospect.risk_category == RiskCategory.HIGH:
        has_conditions = True

    # Occupation risk assessment
    # TODO: In production, map prospect.occupation to risk levels
    occupation_risk = "standard"
    if prospect.risk_category == RiskCategory.HIGH:
        occupation_risk = "high"

    # Create summary
    profile_summary = f"{age}-year-old {prospect.type.value} prospect, " \
                      f"risk category: {prospect.risk_category.value}"

    # Update state
    state["age"] = age
    state["risk_category"] = prospect.risk_category.value
    state["has_preexisting_conditions"] = has_conditions
    state["occupation_risk"] = occupation_risk
    state["profile_summary"] = profile_summary
    state["workflow_path"].append("profile_extractor")
    state["stage"] = "profile_extracted"

    logger.info(f"[NODE 1] Profile extracted: {profile_summary}")

    return state


def eligibility_checker_node(state: AdvisoryState) -> AdvisoryState:
    """
    NODE 2: Check eligibility with all providers.

    INPUT: Profile data (age, risk_category, insurance_type)
    OUTPUT: List of eligible providers with pricing
    LOGIC: Uses existing EligibilityService

    WHY separate node:
    - Eligibility is prerequisite for recommendations
    - Results determine conditional routing (eligible vs not)
    - Can be mocked for testing
    """
    logger.info(f"[NODE 2] Checking eligibility for {state['insurance_type']}")

    eligibility_service = EligibilityService()

    # Check eligibility
    eligible_providers = eligibility_service.check_eligibility(
        insurance_type=state["insurance_type"],
        age=state["age"],
        risk_category=state["risk_category"]
    )

    # Filter to only eligible
    eligible_only = [p for p in eligible_providers if p.is_eligible]

    # Update state
    state["eligible_providers"] = eligible_only
    state["eligibility_count"] = len(eligible_only)
    state["workflow_path"].append("eligibility_checker")
    state["stage"] = "eligibility_checked"

    logger.info(f"[NODE 2] Found {len(eligible_only)} eligible providers")

    return state


def no_options_handler_node(state: AdvisoryState) -> AdvisoryState:
    """
    NODE 3A: Handle case where no providers are eligible.

    INPUT: Eligibility results (empty list)
    OUTPUT: Personalized explanation message
    LOGIC: AI generates empathetic explanation

    WHY AI for this:
    - Need empathetic, personalized tone
    - Explain WHY not eligible (vs just saying "no")
    - Suggest alternatives (other insurance types, etc.)
    """
    logger.info(f"[NODE 3A] No eligible providers, generating explanation")

    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        temperature=0.5,  # Slightly creative for empathetic tone
        api_key=settings.ANTHROPIC_API_KEY
    )

    prompt = ChatPromptTemplate.from_template("""
You are a compassionate insurance advisor. A prospect is not eligible for any providers.

Prospect Profile:
- Age: {age}
- Risk Category: {risk_category}
- Insurance Type: {insurance_type}
- Has Pre-existing Conditions: {has_conditions}

Generate a brief, empathetic message explaining:
1. Why they're not currently eligible
2. What factors are limiting eligibility
3. Alternative options they could explore
4. Next steps they can take

Keep it under 200 words, professional but warm tone.
""")

    chain = prompt | llm

    result = chain.invoke({
        "age": state["age"],
        "risk_category": state["risk_category"],
        "insurance_type": state["insurance_type"],
        "has_conditions": state["has_preexisting_conditions"]
    })

    # Store in personalized_message
    state["personalized_message"] = PersonalizedMessage(
        message=result.content,
        tone="empathetic",
        call_to_action="Contact us to discuss alternative options"
    )
    state["workflow_path"].append("no_options_handler")
    state["stage"] = "completed_no_options"

    logger.info(f"[NODE 3A] Generated no-options message")

    return state


def risk_analyzer_node(state: AdvisoryState) -> AdvisoryState:
    """
    NODE 3B: Analyze prospect's risk profile with AI.

    INPUT: Profile data + eligible providers
    OUTPUT: Detailed risk assessment
    LOGIC: Claude 3.5 Sonnet with structured output

    WHY this node:
    - Risk analysis informs recommendations
    - Structured output for consistency
    - Can be used in compliance/audit trail
    """
    logger.info(f"[NODE 3B] Analyzing risk profile")

    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        temperature=0.3,  # Low for consistent analysis
        api_key=settings.ANTHROPIC_API_KEY
    )

    parser = PydanticOutputParser(pydantic_object=RiskAnalysis)

    prompt = ChatPromptTemplate.from_template("""
You are an expert insurance risk analyst. Analyze this prospect's risk profile.

Prospect Profile:
- Age: {age}
- Risk Category: {risk_category}
- Insurance Type: {insurance_type}
- Has Pre-existing Conditions: {has_conditions}
- Occupation Risk: {occupation_risk}

Eligible Providers: {eligible_count} providers available

Provide a comprehensive risk assessment including:
1. Overall risk score (0-100)
2. Specific risk factors identified
3. Mitigation suggestions
4. Overall assessment summary

{format_instructions}
""")

    chain = prompt | llm | parser

    risk_analysis = chain.invoke({
        "age": state["age"],
        "risk_category": state["risk_category"],
        "insurance_type": state["insurance_type"],
        "has_conditions": state["has_preexisting_conditions"],
        "occupation_risk": state["occupation_risk"],
        "eligible_count": state["eligibility_count"],
        "format_instructions": parser.get_format_instructions()
    })

    state["risk_analysis"] = risk_analysis
    state["workflow_path"].append("risk_analyzer")
    state["stage"] = "risk_analyzed"

    logger.info(f"[NODE 3B] Risk analysis complete, score: {risk_analysis.risk_score}")

    return state


def recommender_node(state: AdvisoryState) -> AdvisoryState:
    """
    NODE 4: Generate ranked provider recommendations.

    INPUT: Risk analysis + eligible providers
    OUTPUT: Ranked recommendations with reasoning
    LOGIC: Claude 3.5 Sonnet with chain-of-thought

    WHY this is the core node:
    - Combines all previous analysis
    - Generates actionable recommendations
    - Provides reasoning for transparency
    """
    logger.info(f"[NODE 4] Generating provider recommendations")

    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        temperature=0.3,
        api_key=settings.ANTHROPIC_API_KEY
    )

    parser = PydanticOutputParser(pydantic_object=AdvisoryRecommendations)

    # Build provider details
    provider_details = []
    for p in state["eligible_providers"]:
        provider_details.append(
            f"- {p.provider}: €{p.base_premium}/month, "
            f"coverage up to €{p.coverage_max}, notes: {p.notes}"
        )
    providers_text = "\n".join(provider_details)

    prompt = ChatPromptTemplate.from_template("""
You are an expert insurance advisor generating personalized recommendations.

Prospect Profile:
{profile_summary}

Risk Analysis:
- Risk Score: {risk_score}/100
- Risk Factors: {risk_factors}
- Assessment: {risk_assessment}

Eligible Providers:
{providers}

Generate ranked recommendations (best to worst) considering:
1. VALUE: Best price for coverage needed
2. COVERAGE: Alignment with prospect's risk profile
3. PROVIDER REPUTATION: Established providers preferred
4. FLEXIBILITY: Policy customization options
5. RISK ALIGNMENT: Match prospect's specific risk factors

For each provider, provide:
- Rank (1 = best match)
- Match score (0-100)
- Specific pros for THIS prospect
- Specific cons or considerations
- Key features they should know
- Clear reasoning for ranking

{format_instructions}
""")

    chain = prompt | llm | parser

    recommendations = chain.invoke({
        "profile_summary": state["profile_summary"],
        "risk_score": state["risk_analysis"].risk_score,
        "risk_factors": ", ".join(state["risk_analysis"].risk_factors),
        "risk_assessment": state["risk_analysis"].overall_assessment,
        "providers": providers_text,
        "format_instructions": parser.get_format_instructions()
    })

    state["advisory_recommendations"] = recommendations
    state["workflow_path"].append("recommender")
    state["stage"] = "recommendations_generated"

    logger.info(f"[NODE 4] Generated {len(recommendations.recommendations)} recommendations")

    return state


def personalizer_node(state: AdvisoryState) -> AdvisoryState:
    """
    NODE 5: Personalize the message for this specific prospect.

    INPUT: Recommendations + prospect profile
    OUTPUT: Personalized message with appropriate tone
    LOGIC: Claude 3.5 Sonnet, higher temperature for creativity

    WHY final personalization:
    - Adapt language to prospect type (individual/family/business)
    - Adjust tone based on risk category (reassuring for high-risk)
    - Include clear call-to-action
    - Makes recommendations feel personal, not robotic
    """
    logger.info(f"[NODE 5] Personalizing message")

    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        temperature=0.7,  # Higher for more natural, varied language
        api_key=settings.ANTHROPIC_API_KEY
    )

    parser = PydanticOutputParser(pydantic_object=PersonalizedMessage)

    # Get top recommendation
    top_rec = state["advisory_recommendations"].recommendations[0]

    prompt = ChatPromptTemplate.from_template("""
You are writing a personalized insurance advisory message.

Prospect Profile:
- Type: {prospect_type}
- Age: {age}
- Risk Category: {risk_category}

Top Recommendation:
- Provider: {provider}
- Why: {reasoning}

Write a warm, personalized message (150-200 words) that:
1. Addresses their specific situation
2. Explains why this recommendation fits them
3. Mentions 2-3 key benefits
4. Includes clear next step
5. Feels personal, not templated

Tone: Professional but approachable, reassuring for high-risk prospects.

{format_instructions}
""")

    chain = prompt | llm | parser

    personalized = chain.invoke({
        "prospect_type": state["prospect"].type.value,
        "age": state["age"],
        "risk_category": state["risk_category"],
        "provider": top_rec.provider,
        "reasoning": top_rec.reasoning,
        "format_instructions": parser.get_format_instructions()
    })

    state["personalized_message"] = personalized
    state["workflow_path"].append("personalizer")
    state["stage"] = "completed_success"

    logger.info(f"[NODE 5] Personalization complete")

    return state


# ============================================================================
# CONDITIONAL ROUTING LOGIC
# ============================================================================

def route_after_eligibility(state: AdvisoryState) -> str:
    """
    Decide next node based on eligibility results.

    WHY conditional routing:
    - No point doing AI analysis if no providers available
    - Different user experience for eligible vs not eligible
    - Saves AI costs when outcome is already determined
    """
    if state["eligibility_count"] == 0:
        logger.info("[ROUTING] No eligible providers -> no_options_handler")
        return "no_options_handler"
    else:
        logger.info(f"[ROUTING] {state['eligibility_count']} providers -> risk_analyzer")
        return "risk_analyzer"


# ============================================================================
# LANGGRAPH WORKFLOW BUILDER
# ============================================================================

class AdvisoryService:
    """
    Main advisory service using LangGraph workflow.

    ARCHITECTURE:
    - Build graph once at initialization
    - Execute graph for each advisory request
    - Graph is stateless (state passed in/out)
    - Each node can be tested independently
    """

    def __init__(self):
        """Initialize the LangGraph workflow"""
        self.graph = self._build_graph()
        logger.info("AdvisoryService initialized with LangGraph workflow")

    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph workflow.

        GRAPH STRUCTURE:
        START -> profile_extractor -> eligibility_checker -> [conditional]
                                                            ├─> no_options_handler -> END
                                                            └─> risk_analyzer -> recommender -> personalizer -> END
        """
        workflow = StateGraph(AdvisoryState)

        # Add nodes
        workflow.add_node("profile_extractor", profile_extractor_node)
        workflow.add_node("eligibility_checker", eligibility_checker_node)
        workflow.add_node("no_options_handler", no_options_handler_node)
        workflow.add_node("risk_analyzer", risk_analyzer_node)
        workflow.add_node("recommender", recommender_node)
        workflow.add_node("personalizer", personalizer_node)

        # Set entry point
        workflow.set_entry_point("profile_extractor")

        # Add edges (unconditional)
        workflow.add_edge("profile_extractor", "eligibility_checker")
        workflow.add_edge("no_options_handler", END)
        workflow.add_edge("risk_analyzer", "recommender")
        workflow.add_edge("recommender", "personalizer")
        workflow.add_edge("personalizer", END)

        # Add conditional edge
        workflow.add_conditional_edges(
            "eligibility_checker",
            route_after_eligibility,
            {
                "no_options_handler": "no_options_handler",
                "risk_analyzer": "risk_analyzer"
            }
        )

        return workflow.compile()

    async def generate_advisory(
        self,
        prospect: Prospect,
        insurance_type: str
    ) -> AdvisoryState:
        """
        Generate advisory recommendations for a prospect.

        FLOW:
        1. Initialize state with input data
        2. Execute LangGraph workflow
        3. Return final state with recommendations

        Args:
            prospect: Prospect object from database
            insurance_type: Type of insurance (life/auto/home/health)

        Returns:
            Final state with recommendations and personalized message
        """
        logger.info(f"Generating advisory for prospect {prospect.id}, type: {insurance_type}")

        # Initialize state
        initial_state: AdvisoryState = {
            "prospect_id": prospect.id,
            "insurance_type": insurance_type,
            "prospect": prospect,
            "age": 0,
            "risk_category": "",
            "has_preexisting_conditions": False,
            "occupation_risk": "",
            "profile_summary": "",
            "eligible_providers": [],
            "eligibility_count": 0,
            "risk_analysis": None,
            "advisory_recommendations": None,
            "personalized_message": None,
            "workflow_path": [],
            "error": None,
            "stage": "initialized"
        }

        try:
            # Execute workflow
            final_state = self.graph.invoke(initial_state)

            logger.info(f"Advisory generated successfully. Path: {final_state['workflow_path']}")
            return final_state

        except Exception as e:
            logger.error(f"Advisory generation failed: {e}", exc_info=True)
            initial_state["error"] = str(e)
            initial_state["stage"] = "error"
            return initial_state
