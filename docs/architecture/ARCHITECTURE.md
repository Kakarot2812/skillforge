# SkillForge AI — System Architecture

This document defines the system architecture of SkillForge AI. It is structured into two clearly distinguished baselines:

1. **v1.0.0 MVP Architecture (Frozen Baseline)**: The operational, deterministic evidence-based architecture implemented in the frozen `v1.0.0-mvp` release.
2. **Post-MVP Architecture (Planned Evolution)**: The architectural roadmap for extending the system on the `post-mvp-foundation` branch with real-time market data ingestion, local open-weight LLM reasoning, conversational interfaces, and closed-loop verification.

---

# Part 1: v1.0.0 MVP Architecture (Frozen Baseline)

## 1. MVP Architectural Overview

The SkillForge AI v1.0.0 MVP implements an end-to-end deterministic intelligence pipeline. It extracts structured evidence from candidate artifacts (resumes and GitHub repositories), cross-references candidate evidence with structured industry demand data, and calculates skill gaps and priority ranks using auditable mathematical formulas.

```text
Resume
  ↓
Resume Evidence Extraction
  ↓
GitHub Evidence Extraction
  ↓
Candidate Evidence
  ↓
Industry Skill Demand
  ↓
Deterministic Skill Gap Engine
  ↓
Priority Engine
  ↓
Evidence Audit
  ↓
Candidate Career Insight
```

The MVP intelligence layer is entirely **deterministic**.

### Core MVP Architectural Principles

- **Claimed vs. Evidenced Skills**: Resume data provides claimed and self-evidenced skills extracted through structured parsing and matched to canonical taxonomy.
- **Demonstrated Evidence**: GitHub repository analysis provides demonstrated code evidence (manifests, workflows, Docker configs), not an assumption of mastery.
- **Canonical Skill Representation**: Resume and GitHub evidence are normalized into a single common skill representation using canonical taxonomy and alias matching.
- **Structured Demand Baseline**: Industry demand is represented as structured, baseline skill-demand data in the database.
- **Deterministic Classification**: Skill gap classification (e.g., STRONG, MODERATE, CRITICAL_GAP, MISSING) is deterministic and rule-governed.
- **Deterministic Priority Calculation**: Skill priority scoring uses a bounded mathematical formula combining demand, growth, and candidate evidence levels.
- **Evidence Auditability**: The evidence audit layer records and explains why every classification, score, and priority rank was produced.
- **Decoupled Intelligence**: The LLM is NOT responsible for deciding skill possession, demand score, gap classification, or priority score.

---

## 2. Candidate Evidence States

The MVP architecture supports three distinct candidate evidence ingestion states:

- **Resume Only**: Candidate provides a resume document (PDF/DOCX) without connecting GitHub. Claimed skills are extracted; demonstrated evidence remains empty; gap classification accounts for missing practical depth.
- **GitHub Only**: Candidate connects GitHub profile without uploading a resume. Public repositories are inspected for manifest, infra, and CI files; demonstrated skills are aggregated; claimed resume evidence remains empty.
- **Resume + GitHub**: Candidate provides both resume and GitHub evidence. The system synthesizes both sources into a unified candidate evidence matrix, cross-validating claimed skills against demonstrated repository artifacts.

---

## 3. High-Level MVP System Components

```text
                         USER
                           │
                           ▼
                ┌─────────────────────┐
                │ Next.js Frontend    │
                │ TypeScript          │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ FastAPI Backend     │
                └──────────┬──────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
 Resume Service      GitHub Service      Demand Engine
 (Parser/Extract)     (Repo & Tree API)   (Structured Data)
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
                  ┌─────────────────┐
                  │ Candidate       │
                  │ Evidence Matrix │
                  └────────┬────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
      User Skill Evidence        Industry Demand Data
              │                         │
              └────────────┬────────────┘
                           ▼
                  ┌─────────────────┐
                  │ Skill Gap       │
                  │ Engine          │
                  └────────┬────────┘
                           ▼
                  ┌─────────────────┐
                  │ Priority Engine │
                  └────────┬────────┘
                           ▼
                  ┌─────────────────┐
                  │ Evidence Audit  │
                  │ & Insights      │
                  └─────────────────┘
```

---

## 4. Frontend Architecture

**Technology Stack**:
- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui
- Recharts

**Responsibilities**:
- Authentication and session handling
- Resume upload interface
- GitHub account connection
- Target-role selection
- Deterministic skill-gap visualization
- Industry demand visualization
- Evidence audit inspection interface

---

## 5. Backend Architecture

**Technology Stack**:
- Python
- FastAPI

**Responsibilities**:
- Authentication and API routing
- Resume text extraction and structural parsing
- GitHub integration and repository tree inspection
- Taxonomy lookup and alias normalization
- Deterministic multi-repo evidence scoring
- Industry demand data access
- Deterministic skill gap classification and priority calculation
- Evidence audit generation and response formatting

---

## 6. Database Architecture

**Primary Database**:
- PostgreSQL

**Vector Extension**:
- pgvector

**PostgreSQL Storage**:
- Users and authentication state
- Resumes and extracted section data
- GitHub repositories and scanned project evidence
- Demonstrated skills aggregated across repositories
- Skills, aliases, and prerequisite relationships
- Target roles and structured skill demand baseline
- Evidence audit records and gap calculation results

**pgvector Usage**:
- Stores embeddings used for semantic retrieval and canonical taxonomy normalization.

---

# Part 2: Post-MVP Architecture (Planned Evolution)

> [!NOTE]
> All components, pipelines, and models in Part 2 are **POST-MVP / PLANNED**. They build on top of the frozen `v1.0.0-mvp` foundation on the `post-mvp-foundation` branch and are not implemented in the frozen MVP release.

---

## 7. Post-MVP Architecture Overview

The post-MVP architecture evolves SkillForge AI from a static baseline into a dynamic, evidence-grounded career intelligence platform. The deterministic engine remains the immutable source of truth, while an open-weight local LLM layer (Qwen 3 8B) is introduced strictly for contextual reasoning, explanation, and personalization.

```text
Resume ────────┐
GitHub ────────┤
               ↓
        Candidate Evidence
               │
               ↓
     REAL-TIME MARKET DATA
               ↓
     Deterministic Demand Engine
               ↓
       Skill Gap + Priority
               ↓
      Verified Evidence
               +
      Market Evidence
               ↓
          Qwen 3 8B
          LOCAL LLM
               ↓
        Career Intelligence
          /         \
     Explanation   Roadmap
                     +
                 Resources
```

---

## 8. Planned Post-MVP Pipeline

The conceptual post-MVP pipeline operates as follows:

```text
Job-market sources
→ ingestion
→ cleaning/normalization
→ skill extraction
→ skill normalization
→ deterministic demand calculation
→ PostgreSQL/structured storage
→ retrieval/evidence layer
→ Qwen 3 8B
→ verified career response
```

### Critical Architectural Distinction: Retrieval vs. Demand Calculation

- **RAG/retrieval does NOT itself calculate or update industry demand.**
- The real-time demand capability comes from continuously ingesting and indexing updated market data and then running the deterministic demand engine.
- The LLM/RAG layer should consume verified facts and evidence produced by the deterministic system.

---

## 9. Planned Post-MVP Phases

The post-MVP architecture will be implemented in five distinct phases:

### P1 — Real-Time Industry Demand (Planned)

Purpose: Transform the structured industry-demand baseline into a continuously refreshable market-data pipeline.

**Conceptual Architecture**:
```text
Market Sources
→ Market Data Ingestion
→ Skill Extraction
→ Canonical Skill Normalization
→ Demand Calculation
→ Demand Database
→ Demand API
```

Key high-level requirements:
- Ingest permitted market data.
- Track source and freshness.
- Extract relevant skills.
- Normalize skills into SkillForge's canonical taxonomy.
- Calculate role-specific demand deterministically.
- Calculate/track demand growth where sufficient historical data exists.
- Expose refreshed demand through existing application APIs.
- Preserve deterministic demand calculations.

### P2 — Qwen 3 8B Local AI Layer (Planned)

Purpose: Introduce a local open-weight LLM layer using Qwen 3 8B to reason over verified SkillForge intelligence.

**Architectural Separation**:
```text
Deterministic Engine
→ Verified Facts
→ Retrieval / Evidence Context
→ Qwen 3 8B
→ Response Verification
→ User-facing Career Intelligence
```

The LLM receives structured, verified context:
- Candidate evidence
- Demonstrated skills
- Demand signals
- Skill gaps
- Priorities
- Evidence audit information

The LLM must NOT become the source of truth.

### P3 — Evidence-Grounded Career Chatbot (Planned)

Purpose: Provide natural-language interaction with verified SkillForge intelligence.
- Grounds answers in verified candidate evidence and verified market evidence.
- Explains deterministic classifications, scores, and priorities without hallucination.
- Must not invent candidate evidence, demand data, classifications, or priorities.

### P4 — Personalized Roadmap + Resources (Completed)

Purpose: Convert deterministic skill gaps and priorities into a personalized, sequenced learning path and curriculum.
- Topological milestone sequencing respecting DAG prerequisites via Kahn's algorithm with deterministic tie-breaking.
- Approved resource catalog (`approved_resources`, `approved_projects`) serving as the sole authority without web scraping or hallucinated URLs.
- Transitive prerequisite scheduling with zero score fabrication (`priority_score = None`).
- Candidate ownership and IDOR isolation for persisted roadmaps.

### P5 — GitHub Verification Loop (Completed)

Purpose: Create a closed feedback loop between learning/project completion, candidate-owned GitHub code repositories, and demonstrated skill evidence.

**Architectural Flow**:
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

**Key Architectural Invariants**:
- **Deterministic Truth**: Verification status, confidence, and scores are server-authoritative and determined statically without code execution.
- **Verification Statuses**:
  - `VERIFIED`: Deliverables matched, $S_{\text{crit}} \ge 0.80$, unsupported criteria = 0, $S_{\text{skill}} \ge 0.70$, composite $C \ge 0.85$. Milestone transitions to `VERIFIED`.
  - `PARTIAL`: Composite $C \ge 0.50$ OR $S_{\text{deliv}} \ge 0.50$ OR $S_{\text{crit}} \ge 0.50$. Milestone transitions from `NOT_STARTED` to `IN_PROGRESS`.
  - `UNVERIFIED`: Candidate criteria/deliverables unfulfilled. Milestone transitions to `IN_PROGRESS`.
  - `FAILED`: Reserved strictly for infrastructure/upstream failures (rate limit 429, timeout 504, upstream 502/503). Audit record is preserved; milestone status remains unchanged.
- **Security Boundary**: Volatile PATs accepted only via `Authorization: Bearer <token>` header; never logged, persisted, or returned. Forked repositories rejected. Repository owner matched against connected handle.
- **Explanatory AI (P5-E)**: Local Qwen 3 8B provides non-authoritative explanations. Treats candidate code as untrusted passive data, defends against prompt injection, redacts credentials, and cannot alter deterministic verification results.

---

## 10. AI Safety & Architecture Boundary

To maintain system integrity and reliability, an explicit architectural boundary separates deterministic calculation from generative AI.

### Core Architecture Principle

> **"Deterministic systems decide what is true.**
> **AI explains, reasons over, and personalizes verified evidence."**

### Architectural Guardrails

**The LLM may:**
- explain deterministic results
- reason over verified candidate evidence
- explain market evidence
- answer career questions using retrieved evidence
- generate personalized learning suggestions
- generate roadmap/resource recommendations from available evidence

**The LLM must not:**
- invent candidate skills
- decide whether a candidate possesses a skill
- override deterministic gap classification
- calculate the authoritative demand score
- calculate the authoritative priority score
- fabricate market evidence
- present unsupported claims as verified facts

---

## 11. Future Components (Non-Mandatory)

The following components are identified as potential additions for post-MVP scaling:

- **Redis**: Asynchronous task caching and session acceleration.
- **Celery**: Distributed task queue for asynchronous repository scraping and continuous job market ingestion.
- **Neo4j**: Graph database for deep multi-hop skill dependency graph traversal.
- **Advanced forecasting models**: Time-series statistical models for multi-quarter skill demand forecasting.

These are not part of the frozen v1.0.0 MVP.