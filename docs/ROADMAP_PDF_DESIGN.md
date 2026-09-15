# SkillForge AI — AI-Generated Personalized Career Roadmap PDF
## Technical Architecture & Design Contract (Phase 0)

> **Document Status**: APPROVED SPECIFICATION — DESIGN ONLY  
> **Target Release**: Post-MVP Feature  
> **Target Audience**: Backend Engineers, AI/ML Engineers, Frontend Engineers, SIH Evaluators  
> **Implementation State**: Phase 0 (Design & Contract Only — No Code or Database Changes)

---

## 1. Executive Summary & Purpose

This document defines the complete technical and design contract for the **AI-Generated Personalized Career Roadmap PDF** feature in SkillForge AI.

The purpose of this feature is to transform SkillForge's deterministic career intelligence—including verified skill gaps, code-demonstrated abilities, topological prerequisite sequencing, and curated learning materials—into a beautifully formatted, publication-quality A4 PDF document.

### Core Architectural Mandate

SkillForge maintains an inviolable boundary between **truth** and **explanation**:

```
Deterministic SkillForge Intelligence
              ↓
    Verified Roadmap Data
              ↓
Gemini 2.5 Flash via LangChain
              ↓
  Structured Pydantic Output
              ↓
Reference Integrity Validation Gate
              ↓
       ReportLab Engine
              ↓
SkillForge Career Roadmap PDF (A4)
```

> [!IMPORTANT]
> **Core Architectural Invariant**:
> **The LLM NEVER decides what is true.**
> - The LLM NEVER determines whether the candidate possesses a skill.
> - The LLM NEVER determines whether evidence is verified or authoritative.
> - The LLM NEVER computes or adjusts the candidate readiness percentage.
> - The LLM NEVER classifies skill gaps (`STRONG`, `PARTIAL`, `MISSING`).
> - The LLM NEVER calculates priority scores, demand scores, or market growth rates.
> - The LLM NEVER fabricates or introduces learning resources or external URLs.
>
> All facts, scores, metrics, milestone sequences, and approved resources are computed by **existing deterministic SkillForge systems**.
>
> **Gemini 2.5 Flash** is strictly restricted to:
> - Tone personalization and executive framing
> - Contextual explanation of milestone sequencing
> - Concise key-topic distillation within verified boundaries
> - Tailored next-step recommendations and motivational narrative
>
> **ReportLab** is strictly responsible for layout, typography, branding, color tokens, and binary PDF generation.

---

## 2. Feature Boundary & Separation of Responsibilities

The roadmap PDF pipeline operates across three strictly decoupled layers:

| Responsibility Area | Deterministic SkillForge | Gemini 2.5 Flash (LangChain) | ReportLab PDF Renderer |
| :--- | :---: | :---: | :---: |
| **Candidate Identity & Role** | **Authoritative Owner** | Read-Only Context | Render Only |
| **Skill Possession & Gaps** | **Authoritative Owner** | Forbidden from Modifying | Render Badges |
| **Readiness Percentage** | **Authoritative Owner** | Forbidden from Modifying | Render Meter |
| **Industry Demand & Growth** | **Authoritative Owner** | Forbidden from Modifying | Render Data Bars |
| **Priority Scoring (HIGH/MED/LOW)** | **Authoritative Owner** | Forbidden from Modifying | Render Priority Flags |
| **Milestone Sequence Order (DAG)** | **Authoritative Owner** | Forbidden from Reordering | Render Timeline |
| **Approved Resources & URLs** | **Authoritative Owner** | Forbidden from Fabricating | Render Resource Cards |
| **Approved Project Challenges** | **Authoritative Owner** | Forbidden from Altering | Render Deliverables Box |
| **Personalized Headline / Subtitle** | Input Data Provider | **Authoritative Generator** | Render Typography |
| **Phase Strategic Rationale** | Input Data Provider | **Authoritative Generator** | Render Text Blocks |
| **Actionable Next Steps** | Input Data Provider | **Authoritative Generator** | Render Ordered List |
| **Motivational Closing Narrative** | Input Data Provider | **Authoritative Generator** | Render Highlight Card |
| **PDF Page Geometry (A4)** | Independent | Independent | **Authoritative Owner** |
| **Layout, Flowables, Pagination** | Independent | Independent | **Authoritative Owner** |
| **Color Tokens & Brand Styling** | Independent | Independent | **Authoritative Owner** |

### Pipeline Boundaries

1. **Existing SkillForge Systems (DB + Service Layer)**:
   - Provide the persistent or in-memory `CanonicalRoadmapData`.
   - Provide the candidate's verified profile (`User`, `UserProfile`).
   - Provide the deterministic gap metrics (`SkillGapSummary`, `PrioritizedGapsSummary`).
   - Provide the approved resources (`ApprovedResource`) and approved projects (`ApprovedProject`).
2. **Gemini 2.5 Flash (via LangChain)**:
   - Receives an immutable, validated `VerifiedRoadmapContext` containing only database-backed facts.
   - Generates structured narrative fields matching `RoadmapPDFPersonalizedNarrative`.
   - Has zero access to the database, zero access to arbitrary web scraping, and zero authority over metrics.
3. **Reference Integrity Validation Gate (Pydantic + Service Layer)**:
   - Validates that Gemini's output adheres strictly to the Pydantic schema.
   - Validates that all referenced skill IDs match skills in the canonical roadmap.
   - Rejects any newly introduced external URLs or unknown resource IDs.
   - Assembles the validated narrative and deterministic data into the complete `RoadmapPDFDocument`.
4. **ReportLab Renderer**:
   - Consumes only the validated `RoadmapPDFDocument`.
   - Never calls any external service, database, or LLM.
   - Generates a deterministic A4 document stream.
5. **FastAPI Endpoint Layer**:
   - Exposes `GET /api/v1/roadmaps/{roadmap_id}/pdf`.
   - Validates candidate authentication (`X-User-Id`) and ownership (IDOR defense).
   - Handles upstream timeouts and failures gracefully.
   - Streams `application/pdf` binary with proper content headers.
6. **Frontend Layer (Next.js)**:
   - Adds a "Download PDF" / "Generate Roadmap PDF" action to `RoadmapSection.tsx`.
   - Manages UI states: `idle`, `generating`, `success`, `error`.
   - Never invokes Gemini or PDF generation directly.

---

## 3. Pydantic Contract: `RoadmapPDFDocument`

The contract is divided into two parts:
1. **`RoadmapPDFPersonalizedNarrative`**: The structured output schema generated by Gemini 2.5 Flash.
2. **`RoadmapPDFDocument`**: The comprehensive document model consumed by the ReportLab renderer, combining deterministic facts with validated narrative.

### 3.1 Gemini Output Schema: `RoadmapPDFPersonalizedNarrative`

```python
from typing import List, Optional, Tuple
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class RoadmapPhaseNarrative(BaseModel):
    """Personalized explanatory text for a single sequenced roadmap phase."""
    skill_id: UUID = Field(
        ...,
        description="Canonical UUID of the roadmap milestone skill being explained."
    )
    phase_title: str = Field(
        ...,
        min_length=3,
        max_length=80,
        description="Concise, action-oriented title for this roadmap phase (e.g., 'Mastering Asynchronous API Architecture')."
    )
    personalized_rationale: str = Field(
        ...,
        min_length=20,
        max_length=400,
        description="Personalized explanation of why the candidate must learn this skill at this stage based on their verified gaps."
    )
    key_topics: Tuple[str, ...] = Field(
        default_factory=tuple,
        min_length=2,
        max_length=5,
        description="2 to 5 specific, high-yield technical competencies to master in this phase."
    )

    model_config = ConfigDict(frozen=True, extra="forbid")


class RoadmapPDFPersonalizedNarrative(BaseModel):
    """
    Structured narrative generated exclusively by Gemini 2.5 Flash.
    Strictly forbids score fabrication, URL generation, or skill reclassification.
    """
    personalized_subtitle: str = Field(
        ...,
        min_length=10,
        max_length=120,
        description="Engaging candidate-tailored subtitle (e.g., 'Targeted Mastery Pathway for Senior Backend Roles in High-Scale Systems')."
    )
    executive_summary: str = Field(
        ...,
        min_length=40,
        max_length=500,
        description="High-level narrative summarizing candidate's current baseline, key gaps, and strategic trajectory."
    )
    phases: Tuple[RoadmapPhaseNarrative, ...] = Field(
        ...,
        min_length=1,
        max_length=25,
        description="Ordered phase narratives matching the exact milestones in the canonical roadmap."
    )
    immediate_next_steps: Tuple[str, ...] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="2 to 5 concrete actions for the candidate to take within the next 7-14 days."
    )
    closing_encouragement: str = Field(
        ...,
        min_length=20,
        max_length=300,
        description="Professional, motivational closing statement tailored to the candidate's career trajectory."
    )

    model_config = ConfigDict(frozen=True, extra="forbid")
```

### 3.2 Complete Document Contract: `RoadmapPDFDocument`

```python
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Tuple
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class PDFSkillGapStatus(str, Enum):
    STRONG = "STRONG"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"


class PDFPriorityLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ---------------------------------------------------------------------------
# Section 1: Candidate Information
# ---------------------------------------------------------------------------

class CandidateInfoCard(BaseModel):
    """Candidate profile snapshot displayed in the top card."""
    candidate_name: str = Field(..., max_length=128, description="Candidate full name or 'SkillForge Candidate'")
    candidate_email: str = Field(..., max_length=255, description="Candidate contact email")
    target_role_title: str = Field(..., max_length=128, description="Canonical target career role")
    experience_level: Optional[str] = Field(None, max_length=64, description="Candidate experience tier if available")
    location: str = Field("India", max_length=64, description="Target hiring market")
    generated_date: str = Field(..., description="Formatted timestamp (e.g., 'September 15, 2026')")

    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# Section 2: Current Skill Readiness
# ---------------------------------------------------------------------------

class SkillReadinessCard(BaseModel):
    """Deterministic readiness metrics card."""
    readiness_percentage: int = Field(..., ge=0, le=100, description="Readiness percentage [0, 100]")
    strong_verified_count: int = Field(..., ge=0, description="Count of STRONG verified competencies")
    partial_count: int = Field(..., ge=0, description="Count of PARTIAL demonstrated/claimed competencies")
    missing_count: int = Field(..., ge=0, description="Count of MISSING competencies")
    total_demanded_skills: int = Field(..., ge=1, description="Total required competencies for target role")
    has_resume: bool = Field(..., description="Whether resume evidence was evaluated")
    has_github: bool = Field(..., description="Whether GitHub code evidence was evaluated")

    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# Section 3: Top Skill Gaps
# ---------------------------------------------------------------------------

class TopSkillGapItem(BaseModel):
    """Deterministic prioritized gap entry."""
    skill_id: UUID = Field(..., description="Canonical skill UUID")
    skill_name: str = Field(..., max_length=128, description="Canonical skill name")
    gap_status: PDFSkillGapStatus = Field(..., description="Deterministic gap classification")
    priority_level: PDFPriorityLevel = Field(..., description="Deterministic priority tier")
    priority_score: float = Field(..., ge=0.0, le=1.0, description="Deterministic priority score [0.0, 1.0]")
    demand_score: float = Field(..., ge=0.0, le=1.0, description="Market demand score [0.0, 1.0]")
    growth_rate: float = Field(..., description="YoY market growth rate")

    model_config = ConfigDict(frozen=True, extra="forbid")


class TopSkillGapsCard(BaseModel):
    """High-priority skill gaps requiring immediate remediation."""
    high_priority_count: int = Field(..., ge=0, description="Count of HIGH priority gaps")
    total_actionable_gaps: int = Field(..., ge=0, description="Sum of MISSING + PARTIAL gaps")
    gaps: Tuple[TopSkillGapItem, ...] = Field(..., max_length=10, description="Top prioritized gaps")

    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# Section 4: Roadmap Phases & Approved Resources / Projects
# ---------------------------------------------------------------------------

class ApprovedResourceRef(BaseModel):
    """Curated learning resource reference; verified against approved_resources table."""
    resource_id: UUID = Field(..., description="Database UUID referencing approved_resources.id")
    title: str = Field(..., max_length=255, description="Curated title")
    url: str = Field(..., max_length=1024, description="Whitelisted URL")
    resource_type: str = Field(..., max_length=64, description="OFFICIAL_DOCS, TUTORIAL, GUIDE, etc.")
    provider: str = Field(..., max_length=128, description="Authoritative publisher/provider")
    difficulty: str = Field(..., max_length=32, description="BEGINNER, INTERMEDIATE, ADVANCED")
    estimated_minutes: Optional[int] = Field(None, ge=0, description="Estimated duration in minutes")

    model_config = ConfigDict(frozen=True, extra="forbid")


class ApprovedProjectRef(BaseModel):
    """Approved engineering challenge; verified against approved_projects table."""
    project_id: UUID = Field(..., description="Database UUID referencing approved_projects.id")
    title: str = Field(..., max_length=255, description="Project title")
    difficulty: str = Field(..., max_length=32, description="BEGINNER, INTERMEDIATE, ADVANCED")
    deliverables: Tuple[str, ...] = Field(default_factory=tuple, max_length=10, description="Expected code deliverables")
    verification_criteria: Tuple[str, ...] = Field(default_factory=tuple, max_length=10, description="GitHub verification criteria")
    estimated_hours: Optional[int] = Field(None, ge=0, description="Estimated effort in hours")

    model_config = ConfigDict(frozen=True, extra="forbid")


class RoadmapPhaseItem(BaseModel):
    """Full milestone representation in the PDF document."""
    order_index: int = Field(..., ge=1, description="1-indexed sequence order")
    phase_number: int = Field(..., ge=1, description="Display phase number")
    skill_id: UUID = Field(..., description="Canonical skill UUID")
    skill_name: str = Field(..., max_length=128, description="Canonical skill name")
    canonical_slug: str = Field(..., max_length=128, description="Canonical skill slug")
    category: Optional[str] = Field(None, max_length=64, description="Skill taxonomy category")
    gap_status: PDFSkillGapStatus = Field(..., description="MISSING or PARTIAL")
    priority_level: Optional[PDFPriorityLevel] = Field(None, description="Priority tier (None for transitive dependencies)")
    priority_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Priority score (None for transitive dependencies)")
    is_transitive_prerequisite: bool = Field(False, description="Whether dynamically scheduled as a prerequisite")
    
    # LLM-generated narrative fields (validated)
    phase_title: str = Field(..., max_length=80, description="Action-oriented phase title")
    personalized_rationale: str = Field(..., max_length=400, description="Personalized explanation for candidate")
    key_topics: Tuple[str, ...] = Field(default_factory=tuple, max_length=5, description="Key technical topics")

    # Authoritative deterministic resources & projects
    resources: Tuple[ApprovedResourceRef, ...] = Field(default_factory=tuple, description="Curated approved resources")
    project: Optional[ApprovedProjectRef] = Field(None, description="Approved practical project challenge")

    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# Section 5: Next Steps & Closing
# ---------------------------------------------------------------------------

class ActionableNextStepsCard(BaseModel):
    """Immediate actionable guidance."""
    immediate_steps: Tuple[str, ...] = Field(..., min_length=2, max_length=5, description="Immediate 7-14 day action items")
    weekly_hours_recommendation: int = Field(default=10, ge=4, le=40, description="Recommended weekly study hours")

    model_config = ConfigDict(frozen=True, extra="forbid")


class MotivationalClosingCard(BaseModel):
    """Closing statement and career outlook."""
    executive_takeaway: str = Field(..., max_length=500, description="Strategic summary of candidate's pathway")
    closing_encouragement: str = Field(..., max_length=300, description="Personalized motivational closing")

    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# Root Document Schema Consumed by ReportLab
# ---------------------------------------------------------------------------

class RoadmapPDFDocument(BaseModel):
    """
    Immutable root contract for rendering the SkillForge Career Roadmap PDF.
    Combines deterministic SkillForge facts with validated Gemini narrative.
    """
    document_id: UUID = Field(..., description="Unique document generation tracking ID")
    roadmap_id: UUID = Field(..., description="Canonical CandidateRoadmap UUID")
    version: str = Field("v1.0", description="Contract schema version")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Narrative Banner
    document_title: str = Field("Career Roadmap", description="Document main title")
    personalized_subtitle: str = Field(..., max_length=120, description="Candidate-tailored subtitle")

    # Cards & Sections
    candidate_info: CandidateInfoCard
    skill_readiness: SkillReadinessCard
    top_gaps: TopSkillGapsCard
    phases: Tuple[RoadmapPhaseItem, ...] = Field(..., min_length=1, description="Ordered sequenced phases")
    next_steps: ActionableNextStepsCard
    closing: MotivationalClosingCard

    # Verification Watermark
    verification_hash: str = Field(..., description="SHA-256 hash of deterministic input facts guaranteeing integrity")

    model_config = ConfigDict(frozen=True, extra="forbid")
```

---

## 4. Gemini 2.5 Flash & LangChain Contract

### 4.1 Model & Provider Specification

- **Provider**: Google Gemini API via `langchain-google-genai` (or official LangChain Google provider adapter)
- **Model Identifier**: `gemini-2.5-flash`
- **Output Mode**: Strict Structured Output (`chat_model.with_structured_output(RoadmapPDFPersonalizedNarrative)`)
- **Temperature**: `0.2` (low temperature for consistency, professional tone, and strict constraint adherence)
- **Backend Configuration**:
  ```ini
  GEMINI_API_KEY=<server-side-secret-only>
  GEMINI_MODEL=gemini-2.5-flash
  GEMINI_TIMEOUT_SECONDS=30.0
  GEMINI_MAX_RETRIES=2
  ```

> [!CAUTION]
> **Zero Client-Side Exposure**:
> The `GEMINI_API_KEY` must NEVER be exposed to the client, sent in frontend bundles, or included in client API responses. The frontend interacts strictly with the FastAPI endpoint.

### 4.2 Prompt Engineering & Invariant Guardrails

Gemini is invoked with a system prompt and a structured user payload:

#### System Prompt
```text
You are the Executive Career Strategist for SkillForge AI.
Your role is to personalize an evidence-grounded Career Roadmap PDF for a software engineering candidate.

INVIOLABLE RULES:
1. The supplied context contains absolute ground truth established deterministically.
2. NEVER modify, dispute, or fabricate skill classifications, readiness percentages, priority scores, or sequence orders.
3. NEVER invent new learning resources, external links, or URLs.
4. Output MUST conform exactly to the requested structured schema.
5. Tone: Professional, empowering, rigorous, and engineering-focused. Avoid buzzwords, fluff, or exaggerated claims.
6. Provide distinct, concise phase titles and specific technical key topics based solely on the verified skills.
```

#### Expected Structured Input Payload
The LLM receives an immutable JSON context:
```json
{
  "candidate": {
    "name": "Candidate Name",
    "target_role": "Cloud/DevOps Engineer",
    "location": "India",
    "readiness_percentage": 38,
    "has_resume": true,
    "has_github": true
  },
  "readiness_metrics": {
    "total_required": 8,
    "strong_verified": 3,
    "partial": 2,
    "missing": 3
  },
  "top_gaps": [
    {
      "skill_name": "Kubernetes",
      "status": "MISSING",
      "priority_level": "HIGH",
      "priority_score": 0.82,
      "demand_score": 0.88,
      "growth_rate": 0.24
    }
  ],
  "milestones": [
    {
      "order_index": 1,
      "skill_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "skill_name": "Docker",
      "gap_status": "PARTIAL",
      "priority_level": "HIGH",
      "is_transitive": false,
      "prerequisites": [],
      "deterministic_reason": "High priority: Skill is only partially demonstrated with high market demand (85%) and rapidly growing (+20% YoY)."
    }
  ]
}
```

### 4.3 Failure Modes & Resilience Strategy

| Failure Scenario | Upstream Error | Handler Action | Client Response |
| :--- | :--- | :--- | :--- |
| **Missing API Key** | `ValueError: GEMINI_API_KEY unset` | Log critical warning; activate deterministic template fallback | 200 OK (Fallback PDF with deterministic text) OR 503 (if fallback disabled) |
| **Gemini Timeout (>30s)** | `TimeoutError` | Fallback to deterministic narrative builder | 200 OK (Deterministic PDF) OR 504 Gateway Timeout |
| **Model Unavailable / 503** | `GoogleAPIError (503)` | Retry 1x; on failure, trigger deterministic fallback | 200 OK (Deterministic PDF) OR 502/503 HTTP error |
| **Malformed Structured Output** | `ValidationError` | Log JSON payload; trigger deterministic fallback | 200 OK (Deterministic PDF) OR 502 Bad Gateway |
| **Hallucinated Reference** | Reference Integrity Failure | Reject LLM output; fallback to deterministic wording | 200 OK (Guaranteed verified PDF) |

> [!TIP]
> **Deterministic Fallback Engine**:
> To guarantee 100% uptime for demo day, the backend must support a **Deterministic Fallback Narrative Generator**. If Gemini fails or times out, the roadmap PDF is still generated using rule-based templates derived from existing SkillForge intelligence (e.g., `generate_gap_explanation`). The user receives a valid, verified PDF without failure.

---

## 5. Two-Tier Validation Boundary

The validation architecture enforces a zero-trust policy toward LLM output:

```
Database: CandidateRoadmap + User + SkillGap + ApprovedResource
                        ↓
            Verified Roadmap Context Builder
                        ↓
             Gemini 2.5 Flash (LangChain)
                        ↓
   ┌──────────────────────────────────────────────────┐
   │ TIER 1: Pydantic Schema Validation               │
   │ - Validates structure against                    │
   │   RoadmapPDFPersonalizedNarrative                │
   │ - Enforces string length, counts, and types      │
   └──────────────────────────────────────────────────┘
                        ↓
   ┌──────────────────────────────────────────────────┐
   │ TIER 2: Reference Integrity Gate                 │
   │ - Matches all skill_ids against roadmap.milestones│
   │ - Verifies NO unapproved URLs exist              │
   │ - Reconciles phase count exactly                 │
   │ - Prohibits score or status modification         │
   └──────────────────────────────────────────────────┘
                        ↓
             Full RoadmapPDFDocument
                        ↓
              ReportLab PDF Engine
```

### Invariant Rules Enforced by the Integrity Gate

1. **Exact Phase Alignment**: The number of phase narratives from Gemini must exactly equal the number of milestones in `CandidateRoadmap`.
2. **Skill ID Integrity**: Every `skill_id` in Gemini's phase narratives must match a known milestone `skill_id`. Any foreign UUID triggers immediate rejection.
3. **Immutability of Metrics**: The readiness percentage, counts, gap statuses, priority levels, priority scores, and demand scores are drawn directly from the database and injected into `RoadmapPDFDocument`. Gemini never has the ability to pass or mutate these fields.
4. **Authoritative Resource Whitelist**: Only resources already present in `roadmap.milestones.resources` (which originate from `approved_resources`) are attached to the PDF document. Gemini is forbidden from proposing new URLs.
5. **Authoritative Project Whitelist**: Only projects from `roadmap.milestones.project` (from `approved_projects`) are attached.

---

## 6. ReportLab Design Contract

### 6.1 Page Geometry & Layout Specifications

| Property | Value | Notes |
| :--- | :--- | :--- |
| **Page Size** | `A4` (595.27 pt × 841.89 pt) | Standard international document format |
| **Orientation** | Portrait | Single and multi-page printable layout |
| **Margins** | Left: 36 pt (0.5 in)<br>Right: 36 pt (0.5 in)<br>Top: 36 pt (0.5 in)<br>Bottom: 45 pt (0.625 in) | Printable safe area: 523.27 pt width |
| **Target Page Count** | 2 to 3 pages (dynamic) | Depends on milestone count (typically 4–8 milestones) |
| **Orphan Control** | `KeepTogether` on phase cards | Avoids splitting a milestone card across page breaks |

### 6.2 Brand Design Tokens & Palette

Matching SkillForge's visual identity:

```python
# ReportLab HexColor Tokens
COLOR_PRIMARY_DARK  = HexColor("#0F172A")  # Slate 900 (Header, Footer, Primary Headings)
COLOR_SECONDARY_DARK= HexColor("#1E293B")  # Slate 800 (Card Headers, Strong Accents)
COLOR_EMERALD       = HexColor("#059669")  # Emerald 600 (Verified, Strong, Readiness)
COLOR_EMERALD_LIGHT = HexColor("#ECFDF5")  # Emerald 50 (Background fill for Strong badges)
COLOR_AMBER         = HexColor("#D97706")  # Amber 600 (Partial, Medium Priority)
COLOR_AMBER_LIGHT   = HexColor("#FFFBEB")  # Amber 50 (Background fill for Partial badges)
COLOR_ROSE          = HexColor("#E11D48")  # Rose 600 (Missing, High Priority Focus)
COLOR_ROSE_LIGHT    = HexColor("#FFF1F2")  # Rose 50 (Background fill for High Priority badges)
COLOR_BLUE          = HexColor("#2563EB")  # Blue 600 (Market Benchmark, Resources)
COLOR_BLUE_LIGHT    = HexColor("#EFF6FF")  # Blue 50 (Resource tags fill)
COLOR_BG_CARD       = HexColor("#FFFFFF")  # Pure White card backgrounds
COLOR_BORDER        = HexColor("#E2E8F0")  # Slate 200 subtle borders
COLOR_TEXT_PRIMARY  = HexColor("#0F172A")  # Slate 900
COLOR_TEXT_SECONDARY= HexColor("#475569")  # Slate 600
COLOR_TEXT_MUTED    = HexColor("#94A3B8")  # Slate 400
COLOR_FOOTER_BG     = HexColor("#0F172A")  # Slate 900 (Dark branding footer)
```

### 6.3 Typography Hierarchy

| Style Role | Font Family | Size | Leading | Color | Alignment |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Doc Title** | Helvetica-Bold | 22 pt | 26 pt | `#0F172A` | Left |
| **Doc Subtitle** | Helvetica | 10 pt | 14 pt | `#475569` | Left |
| **Section Header** | Helvetica-Bold | 13 pt | 16 pt | `#0F172A` | Left |
| **Phase Card Title** | Helvetica-Bold | 11 pt | 14 pt | `#0F172A` | Left |
| **Body Text** | Helvetica | 8.5 pt | 11.5 pt | `#334155` | Left / Justified |
| **Badge Text** | Helvetica-Bold | 7 pt | 9 pt | Status Specific | Center |
| **Metric Value** | Helvetica-Bold | 18 pt | 20 pt | Category Specific| Center / Left |
| **Metric Label** | Helvetica | 7.5 pt | 9.5 pt | `#64748B` | Center / Left |
| **Table Header** | Helvetica-Bold | 7.5 pt | 10 pt | `#475569` | Left |
| **Footer Text** | Helvetica | 7 pt | 9 pt | `#94A3B8` | Left / Right |

### 6.4 Visual Section Ordering (Reference Design)

The PDF renderer constructs a `SimpleDocTemplate` story with 14 visual elements:

1. **SkillForge Header / Logo Bar**:
   - Left: Emerald/Dark brand badge with "SkillForge AI" title.
   - Right: Professional document badge "CAREER ROADMAP" with generated date.
2. **Title & Subtitle Area**:
   - `H1`: "Personalized Career Roadmap"
   - Subtitle: Dynamic candidate-tailored subtitle from Gemini.
3. **Personalized Narrative Banner**:
   - Subtle background container (`#F8FAFC`) with emerald left accent border (3 pt).
   - Executive summary explaining the strategic pathway.
4. **Candidate Information Card**:
   - 2-column or 4-column key-value grid:
     - Candidate Name & Email
     - Target Career Role
     - Evaluation Market (`India`)
     - Evidence Sources Evaluated (`Resume Claims` + `GitHub Code Evidence`)
5. **Executive Metrics Grid (2 Cards Side-by-Side)**:
   - **Card A: Current Skill Readiness**:
     - Large percentage display (`38%`)
     - Horizontal segmented coverage progress bar (Emerald for Strong, Amber for Partial, Slate for Missing)
     - Metric breakdown: `X` of `Y` competencies strongly demonstrated
   - **Card B: Top Skill Gaps Summary**:
     - High priority count badge
     - Actionable gap count (Missing + Partial)
     - Immediate focus indicator
6. **Top Skill Gaps Table**:
   - Clean 4-column data table:
     - Skill Name & Taxonomy Category
     - Gap Status (`MISSING` / `PARTIAL` badge)
     - Deterministic Priority Level (`HIGH` / `MEDIUM` badge with score)
     - Market Demand % & YoY Growth %
7. **Learning Roadmap Section Header**:
   - Section divider line + title "Actionable Learning Roadmap"
   - Explanatory caption: "Topological prerequisite sequence optimizing skill acquisition."
8. **Numbered Roadmap Phases (1..N)**:
   - Enclosed in `KeepTogether` to prevent orphan breaks.
   - For each milestone:
     - **Phase Header**: Numbered badge (`PHASE 1`, `PHASE 2`, ...) + Action Phase Title + Skill Name badge + Priority Flag.
     - **Strategic Rationale**: Gemini-personalized explanation grounded in the candidate's specific gap.
     - **Key Competencies**: Bulleted / horizontal pill list of key topics.
     - **Approved Learning Resources Sub-table**:
       - Title, Provider (`Official Docs`, `Coursera`, etc.), Type, Duration, and "Approved" checkmark.
     - **Approved Engineering Challenge Box** (if project attached):
       - Project title, difficulty, code deliverables, and GitHub verification criteria.
9. **Actionable Next Steps Card**:
   - 14-day immediate execution plan with numbered action pills.
   - Recommended weekly commitment (`10 hours/week`).
10. **Motivational Closing Card**:
    - Highlight box with closing encouragement and long-term career outlook.
11. **Dark SkillForge Footer (Canvas Callback)**:
    - Fixed at bottom of every page via `canvas` drawing callback (`onPage` / `onLaterPages`).
    - Left: "SkillForge AI — Evidence-Grounded Career Intelligence Engine".
    - Right: "Page X of Y" (computed via ReportLab two-pass `NumberedCanvas`).
    - Subtle SHA-256 verification watermark for auditability.

---

## 7. FastAPI Endpoint Contract

### 7.1 Proposed Endpoint

```http
GET /api/v1/roadmaps/{roadmap_id}/pdf
```

*(Also aliased to `/api/v1/roadmap/{roadmap_id}/pdf` for routing consistency with existing personalized roadmap endpoints).*

### 7.2 Request Headers & Parameters

| Parameter | Location | Type | Required | Description |
| :--- | :--- | :--- | :---: | :--- |
| `roadmap_id` | Path | `UUID` | Yes | Canonical `CandidateRoadmap` UUID |
| `X-User-Id` | Header | `UUID` (string) | Yes | Authenticated candidate user identity |
| `download` | Query | `boolean` | No | If `true`, sets `Content-Disposition: attachment`; if `false` (default), sets `inline` for browser PDF preview |

### 7.3 Authorization & IDOR Defense

1. **Authentication Check**: If `X-User-Id` header is missing, return `401 Unauthorized`.
2. **Roadmap Existence**: If `CandidateRoadmap` with `id == roadmap_id` does not exist, return `404 Not Found`.
3. **Ownership Verification (IDOR Defense)**:
   ```python
   if roadmap.user_id != authenticated_user_id:
       raise HTTPException(
           status_code=status.HTTP_403_FORBIDDEN,
           detail="Cross-user access denied: target roadmap does not belong to authenticated candidate context."
       )
   ```

### 7.4 Response Headers

```http
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Disposition: inline; filename="SkillForge-Roadmap-Cloud-DevOps-Engineer-2026-09-15.pdf"
Cache-Control: private, max-age=300
X-SkillForge-Version: v1.0
```

### 7.5 Standard HTTP Error Responses

Conforming to `docs/api/API_SPEC.md` error envelope:

```json
{
  "detail": "Error message description",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error",
    "details": {}
  }
}
```

| HTTP Status | Error Code | Trigger Condition |
| :--- | :--- | :--- |
| **400 Bad Request** | `BAD_REQUEST` | Malformed UUID or conflicting parameters |
| **401 Unauthorized** | `UNAUTHENTICATED` | Missing or invalid `X-User-Id` header |
| **403 Forbidden** | `FORBIDDEN` | IDOR mismatch (`roadmap.user_id != x_user_id`) |
| **404 Not Found** | `NOT_FOUND` | Roadmap `roadmap_id` does not exist |
| **422 Unprocessable** | `VALIDATION_ERROR` | Roadmap contains cyclical dependencies or empty milestones |
| **502 Bad Gateway** | `UPSTREAM_GATEWAY_ERROR` | Upstream Gemini API network/protocol failure (if fallback disabled) |
| **503 Service Unavailable** | `SERVICE_UNAVAILABLE` | Gemini service unavailable and deterministic fallback disabled |
| **504 Gateway Timeout** | `GATEWAY_TIMEOUT` | Gemini generation exceeded 30-second deadline |
| **500 Internal Error** | `INTERNAL_SERVER_ERROR` | ReportLab PDF layout or rendering failure |

---

## 8. Frontend Contract (Next.js)

### 8.1 UI Location

The PDF generation trigger resides in `frontend/src/components/roadmap/RoadmapSection.tsx`, within the existing action buttons toolbar alongside "AI Coaching & Strategy" and "Regenerate Roadmap".

### 8.2 Button States & Lifecycle

```
[ IDLE ] ──(Click)──> [ GENERATING (Spinner) ] ──(Success)──> [ SUCCESS (Download/Open) ]
                                 │
                             (Failure)
                                 ↓
                         [ ERROR (Toast/Banner) ]
```

1. **State 1: `idle`**:
   - Enabled when an active `roadmap` object exists.
   - Text: "Download Career Roadmap PDF" / "Export PDF"
   - Icon: `FileDown` (Lucide React)
   - Tooltip: "Generate a publication-quality personalized PDF roadmap"
2. **State 2: `generating`**:
   - Button is disabled (`disabled={generatingPdf}`).
   - Text: "Generating PDF..."
   - Icon: `Loader2` with `animate-spin`
   - Temporary pulse effect on button background.
3. **State 3: `success`**:
   - Triggers direct browser blob download or opens preview in a new browser tab.
   - Brief success toast: "Your personalized career roadmap PDF has been generated."
   - Reverts button to `idle` state.
4. **State 4: `error`**:
   - Displays inline error alert or toast with server error message.
   - Button returns to `idle` state allowing the candidate to retry.

### 8.3 Frontend API Helper (`frontend/src/lib/api.ts`)

```typescript
/**
 * Downloads or previews the personalized career roadmap PDF for an active roadmap.
 * Enforces authenticated candidate identity via X-User-Id header.
 */
export async function downloadRoadmapPdf(
  roadmapId: string,
  options: { download?: boolean; filename?: string } = {}
): Promise<{ success: boolean; error?: string }> {
  const { download = false, filename } = options;
  const headers = await resolveCandidateHeaders();

  try {
    const url = `${API_BASE_URL}/api/v1/roadmaps/${roadmapId}/pdf?download=${download}`;
    const res = await fetch(url, {
      method: "GET",
      headers,
    });

    if (!res.ok) {
      let errorMsg = `PDF generation failed (HTTP ${res.status})`;
      try {
        const errJson = await res.json();
        if (errJson?.detail) errorMsg = errJson.detail;
      } catch {
        // fallback
      }
      return { success: false, error: errorMsg };
    }

    const blob = await res.blob();
    const blobUrl = window.URL.createObjectURL(blob);

    if (download) {
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = filename || `SkillForge-Roadmap-${roadmapId.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } else {
      window.open(blobUrl, "_blank");
    }

    // Revoke object URL after timeout
    setTimeout(() => window.URL.revokeObjectURL(blobUrl), 60000);
    return { success: true };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Network error downloading PDF",
    };
  }
}
```

---

## 9. Comprehensive Test Plan (Phase 0)

The future implementation must satisfy 13 strict test suites:

| # | Test Suite | Objective |
| :--- | :--- | :--- |
| **1** | `test_pdf_schema_contracts` | Validates `RoadmapPDFPersonalizedNarrative` and `RoadmapPDFDocument` Pydantic models. Rejects extra fields (`extra="forbid"`), negative readiness, out-of-range priority scores, and missing required attributes. |
| **2** | `test_gemini_structured_output` | Verifies LangChain Gemini 2.5 Flash invocation with mocked responses. Validates exact extraction into `RoadmapPDFPersonalizedNarrative`. |
| **3** | `test_reference_validation_gate` | Verifies that all `skill_id`s in Gemini narrative match canonical milestone IDs in the database. Verifies that milestone order is completely preserved. |
| **4** | `test_hallucinated_resource_rejection` | Injects foreign/invented URLs or unknown resource IDs into the pipeline. Confirms that the validation gate catches and rejects them. |
| **5** | `test_invalid_skill_id_rejection` | Injects an undemanded or non-existent skill UUID into the narrative. Asserts that the validation gate flags an integrity error. |
| **6** | `test_score_immutability` | Confirms that deterministic readiness percentage, demand scores, and priority scores cannot be modified by the LLM output. |
| **7** | `test_reportlab_flowables_generation` | Verifies that the ReportLab renderer correctly translates `RoadmapPDFDocument` into valid Flowables (`Paragraph`, `Table`, `Spacer`, `KeepTogether`). |
| **8** | `test_pdf_a4_dimensions_and_header` | Generates a binary PDF buffer. Validates that the output starts with `%PDF-1.`, has valid A4 page dimensions (595.27 × 841.89 pt), and contains expected page count. |
| **9** | `test_api_pdf_authentication` | Calls `GET /api/v1/roadmaps/{id}/pdf` without `X-User-Id`. Asserts `401 Unauthorized`. |
| **10** | `test_api_pdf_idor_defense` | Calls `GET /api/v1/roadmaps/{id}/pdf` using User B's credentials on User A's roadmap. Asserts `403 Forbidden`. |
| **11** | `test_gemini_failure_resilience` | Simulates Gemini 503, timeout, and API key absence. Verifies that the deterministic fallback engine generates a valid PDF without raising 500 errors. |
| **12** | `test_multi_page_content_overflow` | Feeds a roadmap with 12 milestones and extensive text. Validates that ReportLab handles multi-page flow cleanly without crashing, clipping, or creating orphan headers. |
| **13** | `test_frontend_state_handling` | Mocks the download API in Jest/Playwright. Tests `idle`, `generating`, `success`, and `error` button state transitions and blob download triggering. |

---

## 10. Future Implementation Phase Boundaries

To ensure zero architectural regression, the implementation of this feature is strictly phased:

### Phase 1 — Gemini Integration Foundation
- Add `langchain-google-genai` to `requirements.txt`.
- Add `GEMINI_API_KEY`, `GEMINI_MODEL`, and timeout settings to `backend/app/config.py`.
- Implement a standalone `GeminiClient` in `backend/app/ai/gemini/client.py`.
- Implement unit tests for client initialization and mock structured responses.
- **Zero database changes. Zero API endpoints. Zero PDF rendering.**

### Phase 2 — Verified SkillForge Context Builder
- Implement `backend/app/ai/context/roadmap_context.py`.
- Assembles deterministic facts from `CandidateRoadmap`, `User`, `UserProfile`, and `SkillGap` into an immutable `VerifiedRoadmapContext`.
- Enforces strict grounding invariants and frozen schemas.
- Unit tests verifying complete isolation from unverified claims.

### Phase 3 — Structured Roadmap Generation & Validation Gate
- Implement `backend/app/ai/roadmap/pdf_narrative_service.py`.
- Connects LangChain Gemini 2.5 Flash with `.with_structured_output(RoadmapPDFPersonalizedNarrative)`.
- Implement the Reference Integrity Validation Gate reconciling Gemini output against database entities.
- Implement the deterministic fallback engine for offline/resilience support.
- Unit tests verifying rejection of hallucinated skills and resources.

### Phase 4 — ReportLab PDF Renderer
- Add `reportlab>=4.1.0` to `requirements.txt`.
- Implement `backend/app/services/pdf/` module:
  - `tokens.py`: Color tokens, dimensions, margins, styles.
  - `canvas.py`: Two-pass `NumberedCanvas` with header, dark footer, and page count.
  - `components.py`: Modular flowables (Candidate Card, Readiness Meter, Gap Table, Phase Card, Project Box).
  - `renderer.py`: Root `RoadmapPDFRenderer` transforming `RoadmapPDFDocument` into PDF bytes.
- Unit tests validating A4 output, binary validity, and orphan control.

### Phase 5 — FastAPI PDF Endpoint
- Implement `GET /api/v1/roadmaps/{roadmap_id}/pdf` in `backend/app/api/v1/roadmap.py` (with router alias).
- Enforce `X-User-Id` authentication and IDOR ownership verification.
- Return `StreamingResponse` with `application/pdf` and `Content-Disposition`.
- Wire up typed error handling (401, 403, 404, 502, 503, 504).
- Integration tests covering all HTTP status codes and headers.

### Phase 6 — Frontend Integration
- Add `downloadRoadmapPdf` to `frontend/src/lib/api.ts`.
- Add the "Download Career Roadmap PDF" button to `RoadmapSection.tsx`.
- Implement `idle`, `generating`, `success`, and `error` states.
- Support inline browser preview and direct attachment download.

### Phase 7 — LangChain Agent Upgrade (Post-Demo Polish)
- Upgrade downstream conversational coaching to leverage structured roadmap context.
- Enable candidate to ask interactive follow-up questions regarding their PDF roadmap milestones.

### Phase 8 — End-to-End Testing & SIH Demo Polish
- Run full automated test suite (all 13 test suites).
- Test cross-browser PDF rendering (Chrome, Firefox, Safari).
- Verify performance benchmark: total PDF generation under 4.0 seconds (Gemini + ReportLab).
- Prepare deterministic test seed for flawless offline SIH presentation.

---

## 11. Database Schema Impact Declaration

> [!IMPORTANT]
> **Zero Database Migration Required**:
> The Roadmap PDF feature operates strictly on top of existing database tables:
> - `candidate_roadmaps` (persisted candidate roadmap)
> - `roadmap_milestones` (sequenced milestones)
> - `skills` (canonical skill taxonomy)
> - `users` & `user_profiles` (candidate identity)
> - `skill_gaps` (deterministic gap classifications)
> - `approved_resources` (curated resource catalog)
> - `approved_projects` (curated practical engineering projects)
>
> **NO new database tables, columns, or Alembic migrations are required or authorized for this feature.**
