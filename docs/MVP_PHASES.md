# SkillForge AI — Implementation Phases & Post-MVP Roadmap

```
    v1.0.0 MVP
         ↓
    Frozen Deterministic Foundation
         ↓
    P1 Real-Time Industry Demand
         ↓
    P2 Local Qwen 3 8B
         ↓
    P3 Evidence-Grounded Chatbot
         ↓
    P4 Personalized Roadmap + Resources
         ↓
    P5 GitHub Verification Loop
```

---

## v1.0.0 MVP Implementation Phases

- These phases represent the original MVP development plan.
- `v1.0.0-mvp` is now frozen.
- The implemented deterministic evidence-based foundation is the baseline for post-MVP development.
- Some originally planned product capabilities such as advanced roadmap generation, RAG/AI assistant, and GitHub verification are now treated as post-MVP evolution rather than completed v1.0.0 capabilities.

```
PHASE 0 — COMPLETED
Documentation & Architecture
       ↓
PHASE 1 — COMPLETED
Repository + Backend + Frontend + Database
       ↓
PHASE 2 — COMPLETED
Resume Intelligence
       ↓
PHASE 3 — COMPLETED
GitHub Intelligence
       ↓
PHASE 4 — COMPLETED
Industry Demand Engine
       ↓
PHASE 5 — COMPLETED
Skill Gap + Priority Engine
       ↓
PHASE 6 — POST-MVP
Roadmap + Resources
       ↓
PHASE 7 — POST-MVP
RAG + AI Assistant
       ↓
PHASE 8 — POST-MVP
GitHub Verification Loop
       ↓
PHASE 9 — COMPLETED / MVP UI
Dashboard + UX Polish
       ↓
PHASE 10 — COMPLETED
Testing + Deployment + SIH Demo
```

---

# Post-MVP Development Roadmap

Post-MVP development is intentionally separated from the historical MVP implementation phases. Work proceeds from the `post-mvp-foundation` branch, building upon the frozen deterministic foundation established in `v1.0.0-mvp`.

## P1 — Real-Time Industry Demand

### Purpose
Transform the current structured industry-demand baseline into a refreshable market-data pipeline.

### Conceptual Flow
```
    Job-Market Sources
            ↓
       Data Ingestion
            ↓
    Skill Extraction
            ↓
    Skill Normalization
            ↓
    Demand Calculation
            ↓
        PostgreSQL
            ↓
        Demand API
            ↓
    Skill Gap / Priority Engine
```

### High-Level Requirements
- Ingest permitted market data.
- Track source and freshness.
- Extract relevant skills.
- Normalize skills into SkillForge's canonical taxonomy.
- Calculate role-specific demand.
- Calculate and track demand growth where sufficient historical data exists.
- Expose refreshed demand through the existing application APIs.
- Preserve deterministic demand calculations.

*(Note: No external provider is preselected, real-time ingestion is not claimed to exist yet, and unselected implementation technologies are not introduced.)*

## P2 — Local Qwen 3 8B AI Layer

### Purpose
Introduce a local LLM layer using Qwen 3 8B to reason over verified SkillForge intelligence.

The LLM should receive structured verified context such as:
- Candidate evidence
- Demonstrated skills
- Demand signals
- Skill gaps
- Priorities
- Evidence audit information

The LLM must NOT become the source of truth.

## P3 — Evidence-Grounded Career Chatbot

### Purpose
Provide natural-language interaction with the verified SkillForge intelligence.

Example questions:
- "Why is Docker a priority for me?"
- "Which evidence caused React to be classified as STRONG?"
- "What should I learn next?"

The chatbot must ground answers in verified SkillForge evidence and market evidence.

It must not invent candidate evidence, demand data, classifications, or priorities.

## P4 — Personalized Roadmap & Resources (Completed)

### Purpose
Convert deterministic skill gaps, priority scores, and prerequisite DAG constraints into a personalized learning path and project curriculum.

### Key Implemented Components
- **Explicit Skill Dependency DAG**: `skill_dependencies` supporting `HARD` (blocking) and `RECOMMENDED` (non-blocking) dependencies.
- **Deterministic Topological Sequencing**: Kahn's algorithm with priority tie-breaking (`priority_score DESC, demand_score DESC, growth_rate DESC, slug ASC`).
- **Transitive Prerequisite Scoring**: Transitive unfulfilled prerequisites are dynamically scheduled with `priority_score = None` and `priority_level = None` (zero score fabrication; prerequisite topology takes precedence).
- **Curated Approved Catalog**: `approved_resources` and `approved_projects` tables serve as the sole authority. Arbitrary web scraping and hallucinated LLM URLs are strictly prohibited.
- **Candidate Ownership & Isolation**: Persisted roadmaps require an authenticated `user_id` to prevent IDOR vulnerabilities. Anonymous candidates execute purely in-memory (`persisted=False`).
- **Milestone Status Lifecycle**: Milestones strictly initialize to `NOT_STARTED`. `VERIFIED` status is reserved exclusively for P5 GitHub verification.
- **Qwen Independence**: Canonical roadmaps are 100% functional without Qwen or RAG. Optional Qwen explanations operate strictly downstream with `status="EXPLANATORY"`.


## P5 — GitHub Skill Verification Loop (Completed)

### Purpose
Create a closed feedback loop between learning/project completion, candidate-owned GitHub code repositories, and demonstrated skill evidence.

### Architectural Flow
```text
Canonical Roadmap Milestone
        ↓
Approved Project Deliverables
        ↓
Candidate GitHub Repository
        ↓
Deterministic Project Verification (ProjectVerifier)
        ↓
VERIFIED / PARTIAL / UNVERIFIED / FAILED
        ↓
Demonstrated Skill Re-computation
        ↓
Roadmap Milestone State Transition
        ↓
Downstream Unlock
        ↓
Optional Qwen Explanation (AIVerificationExplanationService)
```

### Core Architecture Invariant
> **"Deterministic systems decide what is true.**
> **AI explains, reasons over, and personalizes verified evidence."**

### Key Implemented Components
- **P5-A: Deterministic ProjectVerifier**: Pure, side-effect-free verifier executing locked deliverable matching (exact normalized path or unique basename match; directory-style requires exact match; no suffix matching) and static automated criteria evaluation. Excludes subjective criteria from automated scoring.
- **P5-B: Milestone Verification Persistence**: Migration `0018_milestone_verifications` creating `milestone_verifications` with foreign key cascades, check constraints for status and confidence [0.0, 1.0], and composite index `(milestone_id, created_at)` enabling append-only audit history.
- **P5-C: VerificationService Orchestration**: Deterministic orchestration connecting candidate user validation, roadmap ownership, milestone linkage, non-forked repository ownership, connected GitHub username verification, snapshot commit SHA resolution, GitHub tree/content refresh, demonstrated-skill recomputation, and milestone state transitions.
- **P5-D: Verification API + Security Boundary**: FastAPI endpoints (`POST /api/v1/roadmap/{id}/milestones/{id}/verify`, `GET /api/v1/roadmap/{id}/milestones/{id}/verification`, `POST /api/v1/roadmap/{id}/verify`). Enforces `X-User-Id` authentication, IDOR cross-check, forked repository rejection, and volatile PAT extraction strictly via `Authorization: Bearer <token>` header (never persisted, logged, or returned).
- **P5-E: AI Verification Explanation Layer**: `AIVerificationExplanationService` providing non-authoritative Qwen 3 8B explanations. Defends against prompt injection in untrusted code/deliverables, redacts credentials, and guarantees server-authoritative status and confidence cannot be modified by the LLM.

### Verification Statuses
- **`VERIFIED`**: All required deliverables uniquely matched, automated criteria score $S_{\text{crit}} \ge 0.80$ with zero unsupported criteria, demonstrated skill score $S_{\text{skill}} \ge 0.70$, and composite confidence $C \ge 0.85$. Milestone transitions to `VERIFIED`.
- **`PARTIAL`**: Not verified, and composite confidence $C \ge 0.50$ OR deliverables score $S_{\text{deliv}} \ge 0.50$ OR criteria score $S_{\text{crit}} \ge 0.50$. Milestone transitions from `NOT_STARTED` to `IN_PROGRESS`.
- **`UNVERIFIED`**: Candidate-side failure to meet deliverable or criteria thresholds. Milestone transitions from `NOT_STARTED` to `IN_PROGRESS`.
- **`FAILED`**: Reserved exclusively for external infrastructure and upstream failures (GitHub rate limit 429, timeout 504, upstream 502/503). Persists a `FAILED` audit record without altering roadmap milestone status. Candidate evaluation failures are never mapped to `FAILED`.

---

# Post-MVP Intelligence Principle

The deterministic SkillForge intelligence engine remains the source of truth.

### Responsibility Breakdown

The deterministic layer is responsible for:
- Evidence
- Demonstrated skill scoring
- Industry demand
- Skill-gap classification
- Priority scoring
- Evidence audit

The future LLM layer is responsible for:
- Explanation
- Contextual reasoning
- Natural-language interaction
- Personalized guidance
- Roadmap/resource explanations

### Architectural Invariants

"The LLM does not replace the deterministic intelligence engine. It reasons over verified SkillForge evidence and market signals."

"The LLM must not invent evidence or override deterministic results."