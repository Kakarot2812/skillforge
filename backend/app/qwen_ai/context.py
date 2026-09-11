"""
SkillForge context contract for the Qwen AI layer.

Other SkillForge modules (skill-gap engine, demand engine, roadmap engine,
resume/GitHub evidence, RAG) produce *facts*; they pass them here as a
``SkillForgeContext``. This module only validates and renders those facts into
a delimited prompt block. It performs no business calculations of its own.

Every field is optional so modules that do not exist yet can simply be omitted.
Unknown fields are rejected (extra="forbid") so integration mistakes surface as
422 errors instead of being silently ignored.
"""
import re
from dataclasses import dataclass, field
from typing import Annotated, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Limits (hard caps that protect the prompt size and the model's context).
# ---------------------------------------------------------------------------
MAX_LIST_ITEMS = 100
MAX_EVIDENCE_ITEMS = 20
MAX_EVIDENCE_CONTENT_CHARS = 4000
EVIDENCE_RENDER_CHARS = 1500  # per-item excerpt actually shown to the model

ShortText = Annotated[str, Field(min_length=1, max_length=120)]
MetadataValue = Union[str, int, float, bool, None]


class _ContextModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _upper(value: Optional[str]) -> Optional[str]:
    return value.upper() if isinstance(value, str) else value


class UserProfileContext(_ContextModel):
    """Non-identifying profile facts. Do not send names, emails or phone numbers."""

    experience_level: Optional[str] = Field(None, max_length=40)
    years_of_experience: Optional[float] = Field(None, ge=0, le=60)
    location: Optional[str] = Field(None, max_length=64)
    weekly_hours_commitment: Optional[int] = Field(None, ge=0, le=100)
    career_goal: Optional[str] = Field(None, max_length=300)


class SkillContextItem(_ContextModel):
    name: ShortText
    level: Optional[str] = Field(None, max_length=40, description="e.g. beginner / intermediate / advanced")
    evidence_type: Optional[str] = Field(None, max_length=20, description="CLAIMED (resume) or DEMONSTRATED (GitHub)")
    evidence_level: Optional[str] = Field(None, max_length=20, description="HIGH / MEDIUM / LOW")

    @field_validator("evidence_type", "evidence_level")
    @classmethod
    def normalise_codes(cls, value: Optional[str]) -> Optional[str]:
        return _upper(value)


class SkillGapContextItem(_ContextModel):
    """Mirrors the deterministic output of the skill-gap / prioritisation engine."""

    skill: ShortText
    status: Optional[str] = Field(None, max_length=20, description="STRONG / PARTIAL / MISSING")
    priority_level: Optional[str] = Field(None, max_length=20, description="HIGH / MEDIUM / LOW")
    priority_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    demand_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    claimed: Optional[bool] = None
    demonstrated: Optional[bool] = None

    @field_validator("status", "priority_level")
    @classmethod
    def normalise_codes(cls, value: Optional[str]) -> Optional[str]:
        return _upper(value)


class MarketDemandContextItem(_ContextModel):
    skill: ShortText
    demand_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    growth_rate: Optional[float] = Field(None, ge=-1.0, le=10.0)
    location: Optional[str] = Field(None, max_length=64)
    sample_size: Optional[int] = Field(None, ge=0)
    data_freshness: Optional[str] = Field(None, max_length=40)


class RoleRequirementContextItem(_ContextModel):
    skill: ShortText
    importance: Optional[str] = Field(None, max_length=20, description="REQUIRED / PREFERRED")
    source: Optional[str] = Field(None, max_length=200)

    @field_validator("importance")
    @classmethod
    def normalise_codes(cls, value: Optional[str]) -> Optional[str]:
        return _upper(value)


class RoadmapStepContextItem(_ContextModel):
    """One step produced by the deterministic roadmap engine (order is authoritative)."""

    skill: ShortText
    priority: Optional[str] = Field(None, max_length=20)
    order: Optional[int] = Field(None, ge=0)
    status: Optional[str] = Field(None, max_length=30)
    estimated_hours: Optional[float] = Field(None, ge=0, le=10000)
    rationale: Optional[str] = Field(None, max_length=500)

    @field_validator("priority", "status")
    @classmethod
    def normalise_codes(cls, value: Optional[str]) -> Optional[str]:
        return _upper(value)


class ProjectContextItem(_ContextModel):
    name: ShortText
    description: Optional[str] = Field(None, max_length=500)
    skills: List[ShortText] = Field(default_factory=list, max_length=30)
    url: Optional[str] = Field(None, max_length=300)


class EvidenceItem(_ContextModel):
    """Retrieved evidence (RAG chunk, resume excerpt, GitHub artifact, job posting)."""

    source: str = Field(min_length=1, max_length=300)
    title: Optional[str] = Field(None, max_length=200)
    content: str = Field(min_length=1, max_length=MAX_EVIDENCE_CONTENT_CHARS)
    evidence_type: Optional[str] = Field(None, max_length=30, description="e.g. rag / resume / github / job_posting")
    metadata: Dict[str, MetadataValue] = Field(default_factory=dict, max_length=20)


class SkillForgeContext(_ContextModel):
    """Facts supplied by SkillForge. Qwen explains these; it never alters them."""

    user: Optional[UserProfileContext] = None
    target_role: Optional[str] = Field(None, max_length=120)
    target_company: Optional[str] = Field(None, max_length=120)
    location: Optional[str] = Field(None, max_length=64)
    current_skills: List[SkillContextItem] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    missing_skills: List[ShortText] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    priority_skills: List[ShortText] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    skill_gaps: List[SkillGapContextItem] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    market_data: List[MarketDemandContextItem] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    job_requirements: List[RoleRequirementContextItem] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    roadmap: List[RoadmapStepContextItem] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    projects: List[ProjectContextItem] = Field(default_factory=list, max_length=30)
    evidence: List[EvidenceItem] = Field(default_factory=list, max_length=MAX_EVIDENCE_ITEMS)

    @field_validator("current_skills", mode="before")
    @classmethod
    def coerce_skill_strings(cls, value: object) -> object:
        """Allow the shorthand ["Python", "SQL"] as well as full objects."""
        if isinstance(value, list):
            return [{"name": v} if isinstance(v, str) else v for v in value]
        return value

    def is_empty(self) -> bool:
        return not any(getattr(self, name) for name in type(self).model_fields)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
_DELIMITER_TAGS = re.compile(r"</?\s*(skillforge_context|retrieved_evidence|evidence)\b[^>]*>", re.IGNORECASE)


def _inline(text: object) -> str:
    """Single-line, delimiter-safe rendering of an untrusted value."""
    return " ".join(_DELIMITER_TAGS.sub("", str(text)).split())


def _block(text: str) -> str:
    """Multi-line, delimiter-safe rendering of untrusted evidence content."""
    return _DELIMITER_TAGS.sub("", text).strip()


def _attrs(pairs: List[Tuple[str, object]]) -> str:
    shown = [f"{k}={_inline(v)}" for k, v in pairs if v is not None and v != ""]
    return f" ({', '.join(shown)})" if shown else ""


@dataclass
class RenderedContext:
    text: Optional[str]
    sections: List[str] = field(default_factory=list)
    evidence: List[Tuple[str, EvidenceItem]] = field(default_factory=list)  # (id, item) actually shown
    truncated: bool = False


def _section_lines(ctx: SkillForgeContext) -> List[Tuple[str, List[str]]]:
    """Ordered (section_name, lines) pairs, most important first."""
    out: List[Tuple[str, List[str]]] = []

    target = []
    if ctx.target_role:
        target.append(f"Target role: {_inline(ctx.target_role)}")
    if ctx.target_company:
        target.append(f"Target company: {_inline(ctx.target_company)}")
    if ctx.location:
        target.append(f"Location: {_inline(ctx.location)}")
    if target:
        out.append(("target", target))

    if ctx.user and ctx.user.model_dump(exclude_none=True):
        u = ctx.user
        out.append(("user", ["User profile" + _attrs([
            ("experience_level", u.experience_level),
            ("years_of_experience", u.years_of_experience),
            ("location", u.location),
            ("weekly_hours", u.weekly_hours_commitment),
            ("goal", u.career_goal),
        ])]))

    if ctx.current_skills:
        lines = ["Current skills (only these are known):"]
        lines += [f"- {_inline(s.name)}" + _attrs([("level", s.level), ("evidence", s.evidence_type),
                                                    ("evidence_level", s.evidence_level)])
                  for s in ctx.current_skills]
        out.append(("current_skills", lines))

    if ctx.skill_gaps:
        lines = ["Skill gaps (from SkillForge skill-gap engine):"]
        lines += [f"- {_inline(g.skill)}" + _attrs([
            ("status", g.status), ("priority", g.priority_level), ("priority_score", g.priority_score),
            ("demand_score", g.demand_score), ("claimed", g.claimed), ("demonstrated", g.demonstrated),
        ]) for g in ctx.skill_gaps]
        out.append(("skill_gaps", lines))

    if ctx.missing_skills:
        out.append(("missing_skills", ["Missing skills: " + ", ".join(_inline(s) for s in ctx.missing_skills)]))
    if ctx.priority_skills:
        out.append(("priority_skills",
                    ["Priority skills (highest first): " + ", ".join(_inline(s) for s in ctx.priority_skills)]))

    if ctx.roadmap:
        steps = sorted(enumerate(ctx.roadmap), key=lambda p: (p[1].order is None, p[1].order or 0, p[0]))
        lines = ["Roadmap (SkillForge order is authoritative):"]
        lines += [f"{i}. {_inline(s.skill)}" + _attrs([
            ("priority", s.priority), ("status", s.status), ("estimated_hours", s.estimated_hours),
            ("rationale", s.rationale),
        ]) for i, (_, s) in enumerate(steps, start=1)]
        out.append(("roadmap", lines))

    if ctx.job_requirements:
        lines = ["Role requirements:"]
        lines += [f"- {_inline(r.skill)}" + _attrs([("importance", r.importance), ("source", r.source)])
                  for r in ctx.job_requirements]
        out.append(("job_requirements", lines))

    if ctx.market_data:
        lines = ["Market demand (scores are 0-1 fractions of job postings; growth_rate is year-over-year):"]
        lines += [f"- {_inline(m.skill)}" + _attrs([
            ("demand_score", m.demand_score), ("growth_rate", m.growth_rate), ("location", m.location),
            ("sample_size", m.sample_size), ("data_freshness", m.data_freshness),
        ]) for m in ctx.market_data]
        out.append(("market_data", lines))

    if ctx.projects:
        lines = ["Projects:"]
        lines += [f"- {_inline(p.name)}" + _attrs([
            ("skills", ", ".join(p.skills) if p.skills else None), ("description", p.description),
        ]) for p in ctx.projects]
        out.append(("projects", lines))

    return out


def render_context(ctx: Optional[SkillForgeContext], max_chars: int) -> RenderedContext:
    """Render context into delimited prompt text, respecting a character budget.

    Sections are added in priority order; when the budget runs out, remaining
    lines are dropped and ``truncated`` is set. Only evidence that fits is given
    an id (E1, E2, ...) so returned sources match exactly what the model saw.
    """
    if ctx is None or ctx.is_empty():
        return RenderedContext(text=None)

    result = RenderedContext(text=None)
    budget = max_chars
    body: List[str] = []

    for name, lines in _section_lines(ctx):
        kept = []
        for line in lines:
            if len(line) + 1 > budget:
                result.truncated = True
                break
            kept.append(line)
            budget -= len(line) + 1
        if len(kept) > 1 or (kept and len(lines) == 1):
            body.extend(kept)
            result.sections.append(name)

    evidence_blocks: List[str] = []
    for item in ctx.evidence:
        eid = f"E{len(result.evidence) + 1}"
        content = _block(item.content)
        if len(content) > EVIDENCE_RENDER_CHARS:
            content = content[:EVIDENCE_RENDER_CHARS].rstrip() + " [...]"
        meta = _attrs([(k, v) for k, v in list(item.metadata.items())[:5]])
        header = f'<evidence id="{eid}" source="{_inline(item.source)}"' + (
            f' title="{_inline(item.title)}"' if item.title else "") + (
            f' type="{_inline(item.evidence_type)}"' if item.evidence_type else "") + ">"
        block = f"{header}{meta}\n{content}\n</evidence>"
        if len(block) + 1 > budget:
            result.truncated = True
            break
        evidence_blocks.append(block)
        result.evidence.append((eid, item))
        budget -= len(block) + 1
    if evidence_blocks:
        result.sections.append("evidence")

    parts = []
    if body:
        parts.append("<skillforge_context>\n" + "\n".join(body) + "\n</skillforge_context>")
    if evidence_blocks:
        parts.append("<retrieved_evidence>\n" + "\n".join(evidence_blocks) + "\n</retrieved_evidence>")
    if result.truncated:
        parts.append("Note: some SkillForge context was omitted because of size limits.")
    result.text = "\n\n".join(parts) if parts else None
    return result