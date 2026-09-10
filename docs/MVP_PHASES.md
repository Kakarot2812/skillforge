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

## P4 — Personalized Roadmap & Resources

### Purpose
Convert deterministic skill gaps and priorities into a personalized learning path.

Potential roadmap elements:
- Target skill
- Prerequisites
- Learning objective
- Resources
- Practical project
- Estimated effort
- Verification criteria

Resources should be selected according to the candidate's existing skill level and verified gaps.

## P5 — GitHub Skill Verification Loop

### Purpose
Create a closed feedback loop between learning/project completion and demonstrated skill evidence.

### Conceptual Flow
```
    Skill Gap
       ↓
    Learning / Project
       ↓
    GitHub Repository
       ↓
    Repository Analysis
       ↓
    New Evidence
       ↓
    Skill Re-evaluation
```

The system should use new GitHub evidence to re-evaluate demonstrated skills without allowing the LLM to override deterministic classification.

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