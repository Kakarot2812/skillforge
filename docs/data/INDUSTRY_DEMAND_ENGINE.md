# SkillForge AI — Industry Demand Engine

## 1. Purpose & Core Principles

The Industry Demand Engine determines which technical skills are currently required for specific career roles and how demand changes over time.

### Core Architectural Principle
> **"The system must avoid hard-coded lists of 'trending skills.'
> Demand must be evidence-driven, contextual, and mathematically verifiable."**

SkillForge AI strictly separates the authoritative numerical demand calculation from generative text models. The Large Language Model (LLM) is prohibited from calculating, inventing, or modifying industry demand scores.

---

# Part 1: v1.0.0 MVP — Frozen Demand Engine

## 2. v1.0.0 MVP — Frozen Baseline

In the frozen v1.0.0 MVP, the demand engine consumes **structured industry skill-demand baseline data** stored in PostgreSQL table `skill_demand` (`backend/app/db/models.py`).

The MVP demand engine does **not** have a live job-market web crawler or continuous ingestion pipeline. Instead, it provides a deterministic analytical access and aggregation layer over structured, verified market records.

### Conceptual MVP Demand Flow
```text
Structured Skill Demand Baseline (PostgreSQL: skill_demand)
        ↓
Role / Skill / Location Filtering
        ↓
Demand Metrics & SQL Aggregations
        ↓
Trend & Growth Signal Classification
        ↓
Demand API (/api/v1/demand, /api/v1/intelligence)
        ↓
Skill Gap Engine (/api/v1/gaps)
        ↓
Priority Engine
```

---

## 3. MVP Demand Data & Storage

- **Storage Model**: Stored in the `skill_demand` table, foreign-keyed to `job_roles` and canonical `skills`.
- **Nature of Data**: Structured baseline data reflecting real-world job posting distributions across canonical roles.
- **Not Real-Time**: MVP demand is **not** continuously streamed or ingested from live job boards. It must never be described as real-time.
- **Freshness**: Every demand record explicitly tracks its data update date (`data_updated_at`, e.g., `"2026-09-01"`).
- **Data Integrity Constraints**:
  - `demand_score`: Check constraint enforces $0.0 \le \text{demand\_score} \le 1.0$.
  - `sample_size`: Check constraint enforces $\text{sample\_size} > 0$.
  - Uniqueness: Unique constraint enforces `(role_id, skill_id, location)`.

---

## 4. MVP Demand Calculation & Intelligence Algorithms

The implemented demand engine provides three deterministic calculation mechanisms:

### 4.1 Stored Demand & Role Aggregations
Demand scores are stored directly in `skill_demand` as normalized ratios ($0.0 \le \text{score} \le 1.0$) representing the proportion of role openings demanding a given skill. The service (`demand_service.py`) calculates SQL-level role aggregates:
- $\text{Average Demand} = \text{AVG}(\text{demand\_score})$
- $\text{Highest Demand} = \text{MAX}(\text{demand\_score})$
- $\text{Lowest Demand} = \text{MIN}(\text{demand\_score})$
- $\text{Average Growth Rate} = \text{AVG}(\text{growth\_rate})$

### 4.2 Global Sample-Size-Weighted Skill Demand Ranking
When ranking skills across the entire market without filtering to a single role, the service (`demand_intelligence_service.py`) calculates sample-size-weighted demand to prevent smaller niche roles from skewing rankings:
$$\text{Weighted Demand} = \frac{\sum_{i=1}^{N} (\text{demand\_score}_i \cdot \text{sample\_size}_i)}{\sum_{i=1}^{N} \text{sample\_size}_i}$$

### 4.3 Deterministic Growth & Trend Classification
Market trajectory classification is rule-based and deterministic:
$$\text{Trend} = \begin{cases} \text{RISING} & \text{if } \text{growth\_rate} > 0.05 \\ \text{DECLINING} & \text{if } \text{growth\_rate} < -0.05 \\ \text{STABLE} & \text{if } -0.05 \le \text{growth\_rate} \le 0.05 \end{cases}$$

### 4.4 Priority Signal Transformation
In the Skill Gap Engine, the growth rate is normalized into a bounded $[0.0, 1.0]$ signal:
$$\text{growth\_signal} = \text{clamp}\left(\frac{\text{growth\_rate} + 1.0}{2.0}, 0.0, 1.0\right)$$
$$\text{priority\_score} = \text{gap\_severity\_weight} \cdot (0.70 \cdot \text{demand\_score} + 0.30 \cdot \text{growth\_signal})$$

---

## 5. Role-Specific Demand & Intelligence

Demand is always evaluated in the context of the target job role. A skill's high demand in one domain does not imply relevance in another.

```text
Target Role (e.g. Backend Engineer)
        ↓
Relevant Skill Demand (from skill_demand)
        ↓
Candidate Skill Gap & Priority Calculation
```

The implemented MVP provides:
- **Role Demand Profile**: Breakdown of required skills and benchmarks for a specific role.
- **Cross-Role Profile**: How a specific skill is demanded across multiple career tracks (`GET /api/v1/intelligence/skills/{skill_id}/roles`).
- **Role Comparison**: Deterministic comparison between 2 and 5 canonical roles identifying shared skills and role-specific specializations (`POST /api/v1/intelligence/roles/compare`).
- **Role Market Signals**: Breakdown of rising, stable, and declining skills, plus top demanded and fastest growing skills (`GET /api/v1/intelligence/roles/{role_id}/signals`).

---

## 6. Location Support in MVP

- **Supported Parameter**: The API and database accept a `location` parameter (validated: 1–64 characters, non-blank).
- **Current MVP Baseline**: The frozen MVP baseline dataset is seeded for national geographic scope (`location = 'India'`).
- **Future Geographic Extension**: City-level filtering (e.g., Delhi NCR, Bengaluru, Hyderabad, Mumbai, Pune) is planned for post-MVP phases once regional ingestion pipelines are operational.

---

## 7. Data Freshness Principle

> **"The system must never imply that historical data is real-time."**

- In the frozen MVP, data freshness reflects the date when the structured baseline dataset was compiled and updated (`data_updated_at: "2026-09-01"`).
- API responses explicitly serialize `data_freshness: "2026-09-01"` in their metadata envelopes.

---

## 8. RAG & LLM Relationship

RAG (Retrieval-Augmented Generation) does **not** calculate, modify, or update industry demand scores.

### Authoritative Architecture Flow
```text
Structured Market Data (PostgreSQL)
        ↓
Deterministic Demand Logic
        ↓
Demand Result & Metrics
```

### Contextual Explanation Flow (Future Layer)
```text
Deterministic Demand Result
           +
Retrieved Market Evidence
           ↓
Local Qwen 3 8B LLM
           ↓
Grounded Natural-Language Explanation
```

> **"RAG retrieves evidence.**
> **The deterministic demand engine determines the authoritative market signal."**

---

## 9. Implemented MVP Output Example

Actual response structure from `GET /api/v1/demand/{role_id}?location=India`:

```json
{
  "data": {
    "role": {
      "role_id": "9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c",
      "title": "Backend Engineer",
      "slug": "backend-engineer",
      "category": "Engineering",
      "description": "Designs, implements, and maintains server-side systems."
    },
    "skills": [
      {
        "skill_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
        "skill_name": "Python",
        "canonical_slug": "python",
        "category": "Programming Languages",
        "demand_score": 0.78,
        "growth_rate": 0.08,
        "sample_size": 14200,
        "location": "India",
        "data_updated_at": "2026-09-01"
      }
    ]
  },
  "meta": {
    "total": 1,
    "location": "India",
    "data_freshness": "2026-09-01",
    "total_demanded_skills": 1,
    "average_demand_score": 0.78,
    "highest_demand_score": 0.78,
    "lowest_demand_score": 0.78,
    "average_growth_rate": 0.08,
    "top_skill": "Python"
  }
}
```

---

# Part 2: Post-MVP Planned Evolution

> [!NOTE]
> All pipelines, models, and processes in Part 2 are **PLANNED FOR POST-MVP EVOLUTION (P1)** on the `post-mvp-foundation` branch. They are not implemented in the frozen `v1.0.0-mvp` release.

---

## 10. P1 — Planned Real-Time Industry Demand

In Phase 1 of post-MVP development, the static structured baseline evolves into a continuously refreshed market data pipeline.

### Conceptual Ingestion & Processing Pipeline
```text
Market Sources (Permitted / Licensed Job Postings)
        ↓
Market Data Ingestion
        ↓
Data Cleaning & Normalization
        ↓
Deduplication
        ↓
Job Role Classification
        ↓
Skill Extraction
        ↓
Canonical Skill Normalization (Taxonomy Matcher)
        ↓
Deterministic Demand Calculation
        ↓
Demand Database (PostgreSQL: skill_demand)
        ↓
Demand API
        ↓
Skill Gap & Priority Engines
```

The real-time capability comes from **continuously ingesting updated market data and recalculating deterministic demand metrics**, not from prompting an LLM.

### Checkpoint P1-A Status: Adzuna Integration Foundation
- **Adzuna API Client Foundation**: Implemented an isolated, secure client (`AdzunaClient`) supporting basic job-search requests with India-focused market parameterization (`country="in"`).

### Checkpoint P1-B Status: Adzuna Ingestion + Cleaning & Deduplication
- **Adzuna Ingestion Service (`AdzunaIngestionService`)**: Orchestrates multi-query market job ingestion on top of `AdzunaClient` without direct HTTP calls.
- **Initial Supported Role Queries**:
  1. `backend developer`
  2. `full stack developer`
  3. `frontend developer`
  4. `devops engineer`
  5. `machine learning engineer`
  *(Target market: India `in`, with configurable page limits and results per page)*.
- **Deterministic Cleaning & Normalization**:
  - Trims and collapses inline whitespace across titles, company names, locations, categories, and contract types.
  - Normalizes carriage returns and excessive vertical whitespace in job descriptions while preserving paragraph structure without LLM rewriting.
  - Normalizes empty or whitespace-only optional fields to `None`.
  - Discards malformed records lacking a usable `external_job_id` or `title`.
  - Maps to in-memory `NormalizedMarketJob` data contract preserving raw upstream payload in `raw_data`.
- **Deterministic Deduplication**:
  - Primary deduplication key: `(source, external_job_id)`.
  - Resolves cross-query and cross-page duplicates deterministically by retaining the first valid occurrence in ingestion sequence.
  - Tracks audit metrics via `AdzunaIngestionResult` (`pages_fetched`, `raw_jobs_seen`, `valid_jobs`, `cleaned_jobs`, `duplicates_removed`, `final_jobs`).
- **Scope Boundary**: Output in P1-B was strictly in-memory; database persistence is introduced in P1-C; skill extraction, canonical taxonomy mapping, and demand metric recalculation happen in subsequent checkpoints (P1-D+); 24-hour automated refresh and ATS connectors (Greenhouse/Lever/Ashby) remain unintegrated. The frozen v1.0.0 MVP baseline data and deterministic demand engine remain active and unaffected.

### Checkpoint P1-C Status: Market Job PostgreSQL Persistence
- **Dedicated Persistent Table (`market_jobs`)**: Created via Alembic migration `0012_market_jobs`. Strictly isolated from MVP `skill_demand`.
- **Identity & Uniqueness**: Mandatory database-level unique constraint `uq_market_jobs_source_external_job_id` on `(source, external_job_id)` ensuring complete idempotency across repeated ingestion batches and cross-query overlap.
- **PostgreSQL-Native Upsert (`MarketJobRepository`)**:
  - Employs `INSERT INTO market_jobs ... ON CONFLICT (source, external_job_id) DO UPDATE SET ... WHERE ...`.
  - Non-destructive `COALESCE` update strategy: incoming valid data updates existing records without overwriting useful fields with empty/null values.
  - Returns granular audit metrics: `attempted`, `inserted`, `updated`, `unchanged`, and `failed`.
- **Lineage & Provenance**: `raw_data` column (`JSONB`) preserves the complete provider response dictionary for downstream auditability without storing API credentials.
- **Ingestion Pipeline Orchestration (`AdzunaMarketPipeline`)**: Thin orchestration layer bridging P1-B multi-query ingestion with P1-C PostgreSQL persistence, emitting `MarketPipelineResult`.
- **Scope Boundary**: Persists raw/normalized market jobs only; skill extraction, canonical taxonomy mapping, and demand score recalculation are **NOT** part of P1-C (scheduled for P1-D+); 24-hour automated scheduler and ATS integrations (Greenhouse, Lever, Ashby) remain unintegrated. The frozen v1.0.0 MVP baseline data and deterministic demand engine remain active and unaffected.

### Checkpoint P1-D Status: Deterministic Skill Extraction + Canonical Normalization
- **Strictly Deterministic Extraction**: Adheres to the core principle: *"The LLM never decides what is true."* No LLM, embeddings, vector search, or semantic inference are used.
- **Canonical Taxonomy Reuse**: Uses existing canonical `skills` and `skill_aliases` tables. No secondary taxonomy or unauthorized aliases are created.
- **Boundary-Aware Matching (`DeterministicSkillMatcher`)**:
  - Word boundary assertions `(?<![a-zA-Z0-9#+])` and `(?![a-zA-Z0-9#+])` prevent substring false positives (`"Go"` does not match `"good"` or `"algorithm"`; `"C"` does not match in `"cloud"` or `"basic"`).
  - Short skills like `"Go"` enforce strict case and word-boundary rules (`\bGo\b`, `\bGO\b`, `golang`, `go-lang`), rejecting the English verb `"go"`.
  - Multi-word and longer phrases are matched in descending order of length, preventing nested or overlapping duplicate matches (e.g. `"React Native"` vs `"React"`, `"Docker Compose"` vs `"Docker"`).
- **Verbatim Evidence**: Extracts verbatim contextual snippet spans directly from raw job text snapped to word boundaries without LLM rewriting.
- **Dedicated Persistent Table (`market_job_skills`)**: Created via Alembic migration `0013_market_job_skills`.
  - Unique constraint `uq_market_job_skills_job_skill` on `(market_job_id, skill_id)` enforces at most one canonical relationship per job.
  - Foreign keys with `ON DELETE CASCADE` to both `market_jobs` and `skills`.
- **Idempotent Persistence & Reconciliation (`MarketJobSkillRepository`)**:
  - PostgreSQL-native `ON CONFLICT (market_job_id, skill_id) DO UPDATE`.
  - Automatic reconciliation purges stale extracted skills when job descriptions change.
- **Batch Processing Orchestration (`MarketSkillExtractionService`)**:
  - Controlled batch processing with configurable `batch_size` and `max_jobs`.
  - Returns comprehensive audit metrics: `jobs_processed`, `jobs_with_skills`, `jobs_without_skills`, `skills_matched`, `unique_skill_relationships`, `persistence_inserts`, `persistence_updates`, `persistence_unchanged`, `persistence_deletions`, and `top_skills`.
- **Scope Boundary**: Strictly isolated from the MVP `skill_demand` table; demand aggregation, growth rate calculation, and dynamic demand scores are **NOT** part of P1-D (scheduled for Checkpoint P1-E).

### Checkpoint P1-E Status: Deterministic Market Demand Aggregation
- **Strictly Deterministic Aggregation**: Adheres to the core SkillForge principle: *"The LLM never decides what is true."* Uses zero LLMs, Qwen, embeddings, vector similarity, or semantic model inference.
- **Dedicated Persistent Snapshot Table (`market_skill_demand`)**: Created via Alembic migration `0014_market_skill_demand`.
  - Primary Key: `id UUID DEFAULT gen_random_uuid()`
  - Unique Constraint: `uq_market_skill_demand_source_skill` on `(source, skill_id)`.
  - Foreign Key: `skill_id REFERENCES skills(id) ON DELETE CASCADE`.
  - Check Constraints enforce $[0.0, 1.0]$ bounds for `demand_score` and `demand_share`, and non-negative integers for `job_count` and `sample_size`.
- **Exact Aggregation Inputs**:
  $$\text{market\_jobs} \bowtie \text{market\_job\_skills} \bowtie \text{skills}$$
  Evaluates all market jobs matching the source scope (`source = 'adzuna'`).
- **Unique-Job Counting Rule**:
  $$\text{job\_count} = \text{COUNT}(\text{DISTINCT } \text{market\_job\_id})$$
  Repeated skill mentions within a single job posting count exactly once.
- **Demand Metric Formulas**:
  $$\text{demand\_share} = \begin{cases} \frac{\text{job\_count}}{\text{sample\_size}} & \text{if } \text{sample\_size} > 0 \\ 0.0 & \text{if } \text{sample\_size} = 0 \end{cases}$$
  $$\text{demand\_score} = \text{round}(\text{demand\_share}, 4)$$
  Mathematically compatible with SkillForge demand intelligence scoring.
- **Source Dimension**: Preserved explicitly (`source = 'adzuna'`). Future sources (e.g. ATS connectors) will aggregate independently without source collision.
- **Snapshot Semantics & Recomputability (`MarketSkillDemandRepository`)**:
  - Recomputing over the same market jobs dataset produces identical values.
  - Employs PostgreSQL-native `ON CONFLICT (source, skill_id) DO UPDATE`.
  - Purges stale records (`reconcile=True`) if skills are no longer demanded in current jobs.
- **Strict MVP Isolation**: The frozen 49-record MVP `skill_demand` table, `job_roles`, candidate skill-gaps, and priority calculations are **NOT** modified or connected to live demand at this stage.
- **Deferred to P1-F**: Historical time-series comparisons, growth rate calculations, and 24-hour automated refresh are deferred to Checkpoint P1-F.

---

## 11. P1 Market Evidence & Provenance

Future market records will retain provenance and lineage metadata sufficient to audit:
- **Source Lineage**: Which job posting feed or licensed data provider supplied the observation?
- **Collection Timestamp**: When was the source data scraped or received?
- **Population Scope**: What job title, industry sector, and geographic region was represented?
- **Extracted Mentions**: Which raw text phrases were extracted?
- **Normalization Path**: How was the raw mention mapped to the canonical `skill_id`?
- **Calculation Version**: Which demand calculation formula and run batch generated the final metric?

---

## 12. Future Skill Extraction Design

For post-MVP ingestion, skill extraction may utilize a multi-layered hybrid architecture:
1. **Canonical Dictionary & Rules**: High-precision regex and alias dictionary matching.
2. **NLP & Entity Recognition**: Named entity recognition for technical terminology.
3. **Semantic Embeddings**: Vector similarity matching against canonical skill descriptions.
4. **LLM for Ambiguous Mentions**: LLM assistance strictly for resolving edge-case syntax and novel industry phrasing.

*Guardrail*: Any LLM-assisted extraction remains subject to deterministic taxonomy validation. The LLM will **never** directly assign demand scores or growth rates.

---

## 13. Post-MVP Data Flow Architecture

```text
                    MARKET DATA
                         ↓
               Deterministic Engine
                         ↓
                  Market Signal
                         ↓
              ┌──────────┴──────────┐
              ↓                     ↓
        Skill Gap Engine       Market Evidence
              ↓                     ↓
         Priority             Retrieval / RAG
                                      ↓
                                Qwen 3 8B
                                      ↓
                              Human Explanation
```

The deterministic path remains the authoritative source of truth. The AI layer is reserved strictly for human-facing explanation and reasoning.

---

## 14. Architectural Invariants

1. **Evidence-Driven**: Industry demand must be derived from verifiable market observations, never speculative lists.
2. **Contextual Relevance**: Demand is evaluated relative to specific career tracks and market geographies.
3. **Structured MVP Baseline**: The frozen MVP uses structured baseline data; continuous live ingestion is a post-MVP capability.
4. **Deterministic Calculation**: Demand scores, growth classifications, and priority ranks are computed mathematically.
5. **RAG Decoupling**: RAG does not calculate authoritative demand.
6. **No LLM Overrides**: LLM-generated text cannot alter or override deterministic market metrics.
7. **Traceable Provenance**: Market evidence in the future ingestion pipeline must retain audit lineage.