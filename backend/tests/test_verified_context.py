"""
Unit tests for SkillForge AI Verified Context Contract (Post-MVP Checkpoint P2-B).

Verifies all 27 required specifications:
1. Valid verified context
2. Canonical skill identity validation
3. Valid STRONG classification
4. Valid PARTIAL classification
5. Valid MISSING classification
6. Invalid classification rejected
7. Valid demand_score range
8. Invalid demand_score rejected
9. Valid growth_rate
10. Valid growth_class
11. Invalid growth_class rejected
12. Valid priority_score
13. Invalid priority_score rejected
14. Provenance validation
15. Malformed provenance rejected
16. Immutable/frozen context behavior
17. Generated response cannot mutate context
18. Arbitrary untyped facts rejected
19. Raw unrestricted candidate payload rejected
20. Missing required verified data rejected
21. Deterministic repeated validation
22. Context size/bounds validation
23. AI request correctly contains verified context
24. AI response clearly separated from verified facts
25. No database access
26. No SkillForge business calculations
27. Contract is independent of Ollama availability
28. Cross-fact consistency validation
"""

from datetime import datetime, timezone
import inspect
import uuid
import pytest
from pydantic import ValidationError

from app.ai.context import (
    DEFAULT_VERIFIED_CONTEXT_SYSTEM_PROMPT,
    AIExplanationRequest,
    AIGeneratedExplanation,
    ContextValidationError,
    FactProvenance,
    GrowthClass,
    MAX_EVIDENCE_LIMIT,
    MAX_SKILLS_LIMIT,
    MAX_SNIPPET_LENGTH,
    PriorityTier,
    ProvenanceError,
    SkillClassification,
    VerifiedCandidateContext,
    VerifiedContext,
    VerifiedEvidenceFact,
    VerifiedMarketFact,
    VerifiedPriorityFact,
    VerifiedSkillFact,
    validate_verified_context,
)


def _build_valid_skill(
    skill_id: uuid.UUID = None,
    name: str = "Python",
    classification: SkillClassification = SkillClassification.STRONG,
    demonstrated_score: float = 0.90,
) -> VerifiedSkillFact:
    return VerifiedSkillFact(
        skill_id=skill_id or uuid.uuid4(),
        skill_name=name,
        canonical_slug=name.lower(),
        classification=classification,
        demonstrated_score=demonstrated_score,
        claimed=True,
        claim_confidence=1.0,
        evidence_count=3,
        evidence_level="HIGH",
        provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
    )


def _build_valid_market(
    skill_id: uuid.UUID = None,
    name: str = "Python",
    demand_score: float = 0.85,
    growth_rate: float = 0.12,
    growth_class: GrowthClass = GrowthClass.RISING,
) -> VerifiedMarketFact:
    return VerifiedMarketFact(
        skill_id=skill_id or uuid.uuid4(),
        skill_name=name,
        source="adzuna",
        demand_score=demand_score,
        growth_rate=growth_rate,
        growth_class=growth_class,
        sample_size=150,
        provenance=FactProvenance.MARKET,
    )


def _build_valid_priority(
    skill_id: uuid.UUID = None,
    name: str = "Python",
    priority_score: float = 0.88,
    priority_level: PriorityTier = PriorityTier.HIGH,
    gap_status: SkillClassification = SkillClassification.STRONG,
    demand_score: float = 0.85,
) -> VerifiedPriorityFact:
    return VerifiedPriorityFact(
        skill_id=skill_id or uuid.uuid4(),
        skill_name=name,
        priority_score=priority_score,
        priority_level=priority_level,
        gap_status=gap_status,
        demand_score=demand_score,
        growth_rate=0.12,
        demonstrated_score=0.90,
        provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
    )


# ===========================================================================
# 1. CORE VERIFIED CONTEXT VALIDATION (1 - 5)
# ===========================================================================

def test_1_valid_verified_context():
    """1. Full valid VerifiedContext passes deterministic validation."""
    skill_id = uuid.uuid4()
    candidate = VerifiedCandidateContext(
        candidate_id=uuid.uuid4(),
        target_role_name="Backend Engineer",
        has_resume=True,
        has_github=True,
    )
    skill = _build_valid_skill(skill_id=skill_id, name="Python")
    evidence = VerifiedEvidenceFact(
        skill_id=skill_id,
        skill_name="Python",
        source=FactProvenance.GITHUB,
        evidence_type="dependency_manifest",
        artifact_path="backend/requirements.txt",
        snippet="fastapi>=0.100.0\nsqlalchemy>=2.0.0",
        confidence_score=1.0,
    )
    market = _build_valid_market(skill_id=skill_id, name="Python")
    priority = _build_valid_priority(skill_id=skill_id, name="Python")

    context = VerifiedContext(
        candidate=candidate,
        skills=[skill],
        evidence=[evidence],
        market=[market],
        priorities=[priority],
    )

    validate_verified_context(context)
    assert context.total_facts_count == 5


def test_2_canonical_skill_identity_validation():
    """2. Missing or blank canonical skill identity fields are rejected."""
    # Blank skill_name
    with pytest.raises(ContextValidationError, match="empty skill_name"):
        validate_verified_context(
            VerifiedContext(
                skills=[
                    VerifiedSkillFact(
                        skill_id=uuid.uuid4(),
                        skill_name="   ",
                        canonical_slug="python",
                        classification=SkillClassification.STRONG,
                    )
                ]
            )
        )

    # Blank canonical_slug
    with pytest.raises(ContextValidationError, match="empty canonical_slug"):
        validate_verified_context(
            VerifiedContext(
                skills=[
                    VerifiedSkillFact(
                        skill_id=uuid.uuid4(),
                        skill_name="Python",
                        canonical_slug="  ",
                        classification=SkillClassification.STRONG,
                    )
                ]
            )
        )

    # Invalid UUID string
    with pytest.raises(ValidationError):
        VerifiedSkillFact(
            skill_id="not-a-uuid",
            skill_name="Python",
            canonical_slug="python",
            classification=SkillClassification.STRONG,
        )


def test_3_valid_strong_classification():
    """3. STRONG classification is valid and accepted."""
    skill = _build_valid_skill(classification=SkillClassification.STRONG)
    context = VerifiedContext(skills=[skill])
    validate_verified_context(context)
    assert skill.classification == SkillClassification.STRONG


def test_4_valid_partial_classification():
    """4. PARTIAL classification is valid and accepted."""
    skill = _build_valid_skill(classification=SkillClassification.PARTIAL)
    context = VerifiedContext(skills=[skill])
    validate_verified_context(context)
    assert skill.classification == SkillClassification.PARTIAL


def test_5_valid_missing_classification():
    """5. MISSING classification is valid and accepted."""
    skill = _build_valid_skill(classification=SkillClassification.MISSING)
    context = VerifiedContext(skills=[skill])
    validate_verified_context(context)
    assert skill.classification == SkillClassification.MISSING


def test_6_invalid_classification_rejected():
    """6. Invalid classifications (e.g. EXPERT, WEAK, GOOD) are strictly rejected."""
    with pytest.raises(ValidationError):
        VerifiedSkillFact(
            skill_id=uuid.uuid4(),
            skill_name="Python",
            canonical_slug="python",
            classification="EXPERT",
        )


# ===========================================================================
# 2. NUMERICAL BOUNDS & RANGE VALIDATION (7 - 13)
# ===========================================================================

def test_7_valid_demand_score_range():
    """7. Valid demand scores [0.0, 1.0] are accepted."""
    for score in [0.0, 0.25, 0.80, 1.0]:
        market = _build_valid_market(demand_score=score)
        context = VerifiedContext(market=[market])
        validate_verified_context(context)
        assert market.demand_score == score


def test_8_invalid_demand_score_rejected():
    """8. Demand scores outside [0.0, 1.0] are rejected."""
    with pytest.raises(ValidationError):
        _build_valid_market(demand_score=-0.01)

    with pytest.raises(ValidationError):
        _build_valid_market(demand_score=1.01)

    with pytest.raises(ValidationError):
        _build_valid_market(demand_score=15.0)


def test_9_valid_growth_rate():
    """9. Growth rates (negative, zero, positive) are accepted."""
    for rate in [-0.75, -0.05, 0.0, 0.05, 0.50, 1.0]:
        market = _build_valid_market(growth_rate=rate)
        context = VerifiedContext(market=[market])
        validate_verified_context(context)
        assert market.growth_rate == rate


def test_10_valid_growth_class():
    """10. RISING, STABLE, DECLINING growth classes are accepted."""
    for cls in [GrowthClass.RISING, GrowthClass.STABLE, GrowthClass.DECLINING]:
        market = _build_valid_market(growth_class=cls)
        context = VerifiedContext(market=[market])
        validate_verified_context(context)
        assert market.growth_class == cls


def test_11_invalid_growth_class_rejected():
    """11. Arbitrary growth classes are rejected."""
    with pytest.raises(ValidationError):
        VerifiedMarketFact(
            skill_id=uuid.uuid4(),
            skill_name="Python",
            demand_score=0.5,
            growth_class="EXPLODING",
        )


def test_12_valid_priority_score():
    """12. Valid priority scores in [0.0, 1.0] are accepted."""
    for score in [0.0, 0.45, 0.92, 1.0]:
        prio = _build_valid_priority(priority_score=score)
        context = VerifiedContext(priorities=[prio])
        validate_verified_context(context)
        assert prio.priority_score == score


def test_13_invalid_priority_score_rejected():
    """13. Priority scores outside [0.0, 1.0] are rejected."""
    with pytest.raises(ValidationError):
        _build_valid_priority(priority_score=-0.1)

    with pytest.raises(ValidationError):
        _build_valid_priority(priority_score=1.05)


# ===========================================================================
# 3. PROVENANCE VALIDATION (14 - 15)
# ===========================================================================

def test_14_provenance_validation():
    """14. Authoritative provenances (RESUME, GITHUB, MARKET, DETERMINISTIC_ANALYSIS) are valid."""
    for prov in [FactProvenance.RESUME, FactProvenance.GITHUB, FactProvenance.MARKET, FactProvenance.DETERMINISTIC_ANALYSIS]:
        evidence = VerifiedEvidenceFact(
            skill_id=uuid.uuid4(),
            skill_name="Python",
            source=prov,
            evidence_type="test_evidence",
        )
        assert evidence.source == prov


def test_15_malformed_provenance_rejected():
    """15. Malformed or unverified provenance is rejected."""
    with pytest.raises(ValidationError):
        VerifiedEvidenceFact(
            skill_id=uuid.uuid4(),
            skill_name="Python",
            source="INTERNET_SEARCH",
            evidence_type="test_evidence",
        )


# ===========================================================================
# 4. IMMUTABILITY & SEPARATION (16 - 18)
# ===========================================================================

def test_16_immutable_frozen_context_behavior():
    """16. VerifiedContext and fact models are frozen/immutable."""
    skill = _build_valid_skill()
    context = VerifiedContext(skills=[skill])

    # Mutating context attributes raises error
    with pytest.raises(ValidationError):
        context.skills = []

    # Mutating fact attributes raises error
    with pytest.raises(ValidationError):
        skill.classification = SkillClassification.MISSING

    with pytest.raises(ValidationError):
        skill.demonstrated_score = 0.5


def test_17_generated_response_cannot_mutate_context():
    """17. AI response is decoupled and cannot mutate or overwrite verified context."""
    skill_id = uuid.uuid4()
    skill = _build_valid_skill(skill_id=skill_id, classification=SkillClassification.STRONG)
    context = VerifiedContext(skills=[skill])

    # Generate response
    ai_response = AIGeneratedExplanation(
        content="Candidate shows strong Python competence.",
        model="qwen3:8b",
        referenced_skill_ids=[skill_id],
    )

    # Generated response cannot be appended into context facts (immutable tuple)
    with pytest.raises(AttributeError):
        context.skills.append(ai_response)

    # Generated response cannot overwrite context facts by index
    with pytest.raises(TypeError):
        context.skills[0] = ai_response

    # Context cannot be reassigned with generated explanation
    with pytest.raises(ValidationError):
        context.skills = (ai_response,)

    assert context.skills[0].classification == SkillClassification.STRONG


def test_18_arbitrary_untyped_facts_rejected():
    """18. Arbitrary unverified dictionaries and untyped fields are rejected (extra='forbid')."""
    with pytest.raises(ValidationError):
        VerifiedSkillFact(
            skill_id=uuid.uuid4(),
            skill_name="Python",
            canonical_slug="python",
            classification=SkillClassification.STRONG,
            unverified_opinion="Candidate is great",  # Extra untyped field
        )

    with pytest.raises(ValidationError):
        VerifiedContext(
            skills=[],
            arbitrary_llm_facts={"something": 123},  # Extra untyped field
        )


# ===========================================================================
# 5. CONTEXT BOUNDS & PAYLOAD RESTRICTIONS (19 - 22)
# ===========================================================================

def test_19_raw_unrestricted_candidate_payload_rejected():
    """19. Raw document / whole repository content dumping exceeds snippet limit."""
    huge_snippet = "x" * (MAX_SNIPPET_LENGTH + 50)
    with pytest.raises(ValidationError):
        VerifiedEvidenceFact(
            skill_id=uuid.uuid4(),
            skill_name="Python",
            source=FactProvenance.GITHUB,
            evidence_type="source_code",
            snippet=huge_snippet,
        )


def test_20_missing_required_verified_data_rejected():
    """20. Completely empty context (zero verified facts) is rejected."""
    empty_context = VerifiedContext()
    with pytest.raises(ContextValidationError, match="cannot be empty"):
        validate_verified_context(empty_context)


def test_21_deterministic_repeated_validation():
    """21. Validation is strictly deterministic across repeated executions."""
    skill = _build_valid_skill()
    context = VerifiedContext(skills=[skill])

    # Validate 10 times in succession: always succeeds without mutating
    for _ in range(10):
        validate_verified_context(context)

    assert context.total_facts_count == 1


def test_22_context_size_bounds_validation():
    """22. Context exceeding maximum safe bounds is rejected."""
    too_many_skills = [_build_valid_skill(name=f"Skill_{i}") for i in range(MAX_SKILLS_LIMIT + 1)]
    context = VerifiedContext(skills=too_many_skills)

    with pytest.raises(ContextValidationError, match="skills count .* exceeds maximum"):
        validate_verified_context(context)


# ===========================================================================
# 6. AI REQUEST / RESPONSE CONTRACT TESTS (23 - 24)
# ===========================================================================

def test_23_ai_request_correctly_contains_verified_context():
    """23. AIExplanationRequest encapsulates VerifiedContext and boundary system prompt."""
    skill = _build_valid_skill()
    context = VerifiedContext(skills=[skill])
    validate_verified_context(context)

    req = AIExplanationRequest(
        context=context,
        user_prompt="Why is Python classified as STRONG?",
    )

    assert req.context == context
    assert req.user_prompt == "Why is Python classified as STRONG?"
    assert "The LLM never decides what is true" in req.system_instruction
    assert req.temperature == 0.2


def test_24_ai_response_clearly_separated_from_verified_facts():
    """24. AIGeneratedExplanation is clearly marked as EXPLANATORY with only references."""
    skill_id = uuid.uuid4()
    resp = AIGeneratedExplanation(
        content="Python is verified as STRONG based on 3 GitHub repository code artifacts.",
        model="qwen3:8b",
        referenced_skill_ids=[skill_id],
    )

    assert resp.status == "EXPLANATORY"
    assert resp.referenced_skill_ids == [skill_id]
    assert not hasattr(resp, "verified_skill")
    assert not hasattr(resp, "verified_demand")


# ===========================================================================
# 7. ARCHITECTURAL BOUNDARY & PURITY TESTS (25 - 28)
# ===========================================================================

def test_25_no_database_access():
    """25. Verified context package has zero database dependencies."""
    from app.ai import context as context_package

    source = inspect.getsource(context_package)
    for forbidden in ["sqlalchemy", "SessionLocal", "get_db", "commit", "rollback", "insert", "delete"]:
        assert forbidden not in source, f"Forbidden database reference found: {forbidden}"


def test_26_no_skillforge_business_calculations():
    """26. Verified context contains zero business scoring/classification formulas."""
    from app.ai.context import validation, models

    val_source = inspect.getsource(validation)
    mod_source = inspect.getsource(models)
    full_source = val_source + mod_source

    for forbidden in ["calculate_demand", "classify_growth", "calculate_priority", "extract_skills"]:
        assert forbidden not in full_source, f"Forbidden business logic found: {forbidden}"


def test_27_contract_is_independent_of_ollama_availability():
    """27. Contract creation and validation succeed completely offline without Ollama."""
    skill = _build_valid_skill()
    context = VerifiedContext(skills=[skill])
    validate_verified_context(context)

    # Creating AIExplanationRequest works with Ollama offline
    req = AIExplanationRequest(
        context=context,
        user_prompt="Explain Python gap.",
    )
    assert req.context.skills[0].skill_name == "Python"


def test_28_cross_fact_consistency_validation():
    """28. Contradictory claims within the same context are rejected."""
    skill_id = uuid.uuid4()

    # Skill fact says STRONG, but Priority fact asserts MISSING
    skill = _build_valid_skill(skill_id=skill_id, name="Docker", classification=SkillClassification.STRONG)
    contradictory_priority = _build_valid_priority(
        skill_id=skill_id,
        name="Docker",
        gap_status=SkillClassification.MISSING,  # Contradicts skill fact!
        demand_score=0.85,
    )

    context = VerifiedContext(
        skills=[skill],
        priorities=[contradictory_priority],
    )

    with pytest.raises(ContextValidationError, match="Contradictory gap status"):
        validate_verified_context(context)


def test_29_qwen_client_integration_with_verified_context():
    """29. Demonstrates QwenClient interacting with a request containing VerifiedContext."""
    from unittest.mock import MagicMock
    import httpx
    from app.ai.qwen import QwenClient

    skill_id = uuid.uuid4()
    skill = _build_valid_skill(skill_id=skill_id, name="Python", classification=SkillClassification.STRONG)
    context = VerifiedContext(skills=[skill])
    validate_verified_context(context)

    req = AIExplanationRequest(
        context=context,
        user_prompt="Explain why Python is considered STRONG.",
    )

    context_repr = f"VERIFIED SKILL: {skill.skill_name}, STATUS: {skill.classification.value}"
    prompt_payload = f"Context:\n{context_repr}\n\nCandidate Question: {req.user_prompt}"

    mock_http = MagicMock(spec=httpx.Client)
    mock_http.request.return_value = httpx.Response(
        status_code=200,
        json={
            "model": "qwen3:8b",
            "message": {
                "role": "assistant",
                "content": "Python is classified as STRONG because concrete code evidence was detected.",
            },
            "done": True,
        },
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )

    client = QwenClient(http_client=mock_http)
    chat_resp = client.chat(
        messages=[{"role": "user", "content": prompt_payload}],
        system=req.system_instruction,
    )

    assert chat_resp.content.startswith("Python is classified as STRONG")
    # VerifiedContext remains completely unchanged
    assert context.skills[0].classification == SkillClassification.STRONG
