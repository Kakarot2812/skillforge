# SkillForge AI — Skill Taxonomy & Normalization Engine

## 1. Purpose & Core Principles

The Skill Taxonomy serves as the **single canonical reference system** across all SkillForge AI modules: resume parsing, GitHub repository inspection, industry market demand, and deterministic skill gap evaluation.

### Core Objectives
1. **Eliminate Fragmentation**: Consolidates variations, synonyms, abbreviations, casing differences, and framework shorthands into a single canonical skill identity.
2. **Deterministic Resolution**: Prevents fragmentation where `"Postgres"`, `"PostgreSQL"`, and `"psql"` are treated as distinct skills.
3. **Unified Evidence Bridge**: Serves as the immutable spine connecting candidate evidence (claims and code artifacts) with industry demand benchmarks.
4. **Deterministic Auditing**: Every normalized match records its matched rule and confidence score.

---

# Part 1: v1.0.0 MVP — Frozen Taxonomy

## 2. v1.0.0 MVP — Frozen Baseline

In the frozen v1.0.0 MVP, the canonical skill taxonomy is persisted in two relational tables in PostgreSQL: `skills` and `skill_aliases` (`backend/app/db/models.py`, Alembic migration `0003_skills_and_aliases.py`).

### Canonical Model Entities
- **`skills`**: Stores canonical technologies with an immutable UUID `id`, unique `name`, unique `slug`, `category`, and `description`.
- **`skill_aliases`**: Stores known variations, abbreviations, and synonyms mapped to a parent `skill_id` with precomputed alphanumeric `normalized_alias` keys.

### The Canonical Skill as Common Nexus
```text
               ┌───────────────────────┐
               │ user_claimed_skills   │ (Resume Evidence)
               └───────────▲───────────┘
                           │ skill_id
                           │
┌──────────────────────┐   │   ┌───────────────────────┐
│   project_evidence   │───┼───►│        skills         │
└──────────────────────┘   │   └───────────▲───────────┘
               skill_id    │               │
                           │               │ skill_id
               ┌───────────▼───────────┐   │
               │  demonstrated_skills  │   │   ┌───────────────────────┐
               └───────────────────────┘   ├───►│     skill_demand      │ (Market Evidence)
                               skill_id    │   └───────────────────────┘
                                           │               │
                                           │ skill_id      │ skill_id
                               ┌───────────▼───────────┐   │
                               │      skill_gaps       │◄──┘
                               └───────────────────────┘
```

1. **Resume Evidence**: Skills extracted from resume text are resolved to canonical `skill_id` records in `user_claimed_skills`.
2. **GitHub Demonstrated Evidence**: Manifest dependencies, Dockerfiles, and CI workflows are resolved to canonical `skill_id` records in `project_evidence` and aggregated into `demonstrated_skills`.
3. **Industry Demand**: Structured role requirements in `skill_demand` are indexed directly by canonical `skill_id`.
4. **Skill Gaps & Priorities**: The deterministic gap engine joins candidate evidence and market demand on `skill_id`.

---

## 3. Implemented Normalization Pipeline

SkillForge AI v1.0.0 MVP implements an **in-memory, rule-based deterministic normalization pipeline** (`backend/app/services/skill_normalizer.py`).

> [!IMPORTANT]
> **Vector embeddings and pgvector are NOT part of the frozen MVP normalization pipeline.**
> MVP normalization relies strictly on exact string matching, dictionary alias lookups, and deterministic alphanumeric key preprocessing.

### Pipeline Flow
```text
Raw Extracted Mention (e.g. "ReactJS", "k8s", "FastAPI microservices")
        │
        ▼
String Preprocessing (trim, lowercase, alphanumeric strip via regex r"[^a-zA-Z0-9#+]")
        │
        ▼
In-Memory Fast Lookup Index (SkillTaxonomyCache)
        ├── 1. Exact Canonical Name Match ────────► Confidence: 0.95 (canonical_exact)
        ├── 2. Exact Alias Match ─────────────────► Confidence: 0.90 (alias_exact)
        ├── 3. Normalized Canonical Match ────────► Confidence: 0.88 (canonical_normalized)
        └── 4. Normalized Alias Match ────────────► Confidence: 0.85 (alias_normalized)
        │
        └── No Match?
                 │
                 ▼
        Full-Text Narrative Scan (word boundary regex \b{skill.name}\b for skills > 2 chars)
                 ├── Matched ─────────────────────► Confidence: 0.80 (text_mention)
                 └── No Match ────────────────────► Unknown / Ignored (No silent hallucination)
```

### Normalization Match Types & Confidence Scores

| Resolution Stage | Code Match Type | Confidence | Description | Example Input $\rightarrow$ Output |
| :--- | :--- | :---: | :--- | :--- |
| **Exact Canonical** | `canonical_exact` | `0.95` | Exact match against `skill.name.lower()`. | `"python"` $\rightarrow$ `Python` |
| **Exact Alias** | `alias_exact` | `0.90` | Exact match against `alias.alias.lower()`. | `"k8s"` $\rightarrow$ `Kubernetes` |
| **Normalized Canonical** | `canonical_normalized` | `0.88` | Match on alphanumeric key `normalize_string_key(name)`. | `"NextJS"` $\rightarrow$ `Next.js` |
| **Normalized Alias** | `alias_normalized` | `0.85` | Match on alphanumeric key `normalize_string_key(alias)`. | `"react.js"` $\rightarrow$ `React` |
| **Narrative Scan** | `text_mention` | `0.80` | Word-boundary regex match within raw section text. | `"proficient with Docker in prod"` $\rightarrow$ `Docker` |

---

## 4. Categories & Domains

In the v1.0.0 MVP database, categories are stored directly as a string attribute (`category`) on the `skills` table. The seeded canonical catalog covers seven distinct technical domains:

1. **Languages**: Core programming and database query languages (`Python`, `TypeScript`, `JavaScript`, `Java`, `Go`, `SQL`, `C++`, `C#`).
2. **Frontend**: UI libraries, frameworks, and presentation languages (`React`, `Next.js`, `Tailwind CSS`, `HTML`, `CSS`).
3. **Backend**: Server runtimes and application microservice frameworks (`FastAPI`, `Node.js`, `Spring Boot`).
4. **Databases**: Relational, document, key-value, and vector datastores (`PostgreSQL`, `MongoDB`, `Redis`, `pgvector`).
5. **DevOps & Cloud**: Container runtimes, cluster orchestrators, cloud platforms, and CI tools (`Docker`, `Kubernetes`, `AWS`, `GitHub Actions`, `Docker Compose`).
6. **Systems**: Version control, testing frameworks, and architectural protocols (`Git`, `REST APIs`, `Pytest`).
7. **AI & ML**: Numerical computing and deep learning libraries (`PyTorch`, `Pandas`).

---

## 5. Canonical Seed Catalog

The following 30 canonical skills and their pre-seeded aliases represent the official baseline seeded in Alembic migration `0003_skills_and_aliases.py`:

| Canonical Skill | Slug | Category | Pre-Seeded Aliases |
| :--- | :--- | :--- | :--- |
| **Python** | `python` | Languages | `py`, `python3`, `cpython` |
| **TypeScript** | `typescript` | Languages | `ts`, `type-script` |
| **JavaScript** | `javascript` | Languages | `js`, `es6`, `ecmascript` |
| **Java** | `java` | Languages | `jdk`, `java8`, `java17`, `jvm` |
| **Go** | `go` | Languages | `golang`, `go-lang` |
| **SQL** | `sql` | Languages | `structured-query-language`, `ansi-sql` |
| **C++** | `cpp` | Languages | `c-plus-plus`, `cplusplus` |
| **C#** | `csharp` | Languages | `c-sharp`, `csharp`, `dotnet` |
| **React** | `react` | Frontend | `reactjs`, `react.js`, `react-dom`, `react js` |
| **Next.js** | `nextjs` | Frontend | `next.js`, `next13`, `next14`, `next js` |
| **Tailwind CSS** | `tailwindcss` | Frontend | `tailwind`, `tailwind-css`, `tailwindcss` |
| **HTML** | `html` | Frontend | `html5` |
| **CSS** | `css` | Frontend | `css3` |
| **FastAPI** | `fastapi` | Backend | `fast-api`, `fastapi-framework` |
| **Node.js** | `nodejs` | Backend | `node`, `node.js`, `nodejs` |
| **Spring Boot** | `spring-boot` | Backend | `springboot`, `spring-framework`, `spring` |
| **PostgreSQL** | `postgresql` | Databases | `postgres`, `psql`, `pg`, `postgre sql`, `postgresql database` |
| **MongoDB** | `mongodb` | Databases | `mongo`, `documentdb` |
| **Redis** | `redis` | Databases | `redis-cache`, `key-value-store` |
| **pgvector** | `pgvector` | Databases | `vector-extension`, `postgres-vector` |
| **Docker** | `docker` | DevOps & Cloud | `dockerfile`, `containers` |
| **Kubernetes** | `kubernetes` | DevOps & Cloud | `k8s`, `kube`, `kubectl` |
| **AWS** | `aws` | DevOps & Cloud | `amazon-web-services`, `aws-cloud`, `amazon aws` |
| **GitHub Actions** | `github-actions` | DevOps & Cloud | `gh-actions`, `github-ci` |
| **Docker Compose** | `docker-compose` | DevOps & Cloud | `compose`, `docker-compose-yml` |
| **Git** | `git` | Systems | `git-scm`, `version-control` |
| **REST APIs** | `rest-apis` | Systems | `restful`, `rest-api`, `http-api`, `rest` |
| **Pytest** | `pytest` | Systems | `py-test`, `pytest-runner` |
| **PyTorch** | `pytorch` | AI & ML | `torch`, `torchvision` |
| **Pandas** | `pandas` | AI & ML | `pandas-dataframe`, `pd` |

---

## 6. Disambiguation Rules in MVP

The deterministic normalizer applies strict boundary checks to avoid false positive matches:
- **`Java` vs. `JavaScript`**: Segregated by distinct canonical entries with zero alias overlap.
- **`Go`**: Normalization requires exact lower-case match (`go`, `golang`, `go-lang`). Word-boundary narrative matching is restricted for short 2-letter words to prevent false positives with the English verb "go".
- **`C` vs. `C++` vs. `C#`**: Alphanumeric key regex `r"[^a-zA-Z0-9#+]"` explicitly preserves `+` and `#` characters so `C++` and `C#` are never stripped into plain `C`.
- **Frameworks vs. Languages**: `React` maps strictly to Frontend UI; it does not automatically claim `JavaScript` or `TypeScript` without separate evidence.

---

## 7. Relationship to Demand & Skill Gap Engines

The taxonomy defines canonical identity, but does **not** evaluate proficiency, demand, or gap severity:

```text
Canonical Skill (Taxonomy Spine)
       │
       ├──► Associated with Candidate Evidence (Resumes, Repositories)
       │
       ├──► Associated with Industry Demand (skill_demand table)
       │
       ▼
Deterministic Skill Gap Engine
       ├── Evaluates evidence level against demand threshold
       ├── Classifies status: STRONG, PARTIAL, or MISSING
       └── Calculates priority rank and priority tier
```

The taxonomy itself does **not** assign gap classifications (`STRONG`, `PARTIAL`, `MISSING`) or priority scores; these are computed mathematically by downstream engines.

---

## 8. AI & Architecture Guardrails

> **"The taxonomy defines canonical identity.**
> **The deterministic intelligence layer evaluates evidence.**
> **The AI layer may explain the resulting intelligence but does not redefine authoritative skill identity."**

### Inviolable Rules
1. **No LLM Skill Creation**: The LLM is prohibited from creating new records in the `skills` or `skill_aliases` tables.
2. **No Silent Normalization**: If an ambiguous term cannot be resolved via exact or normalized alias matching, it is not coerced into an arbitrary canonical skill.
3. **Deterministic Authority**: Downstream gap and priority calculations rely strictly on canonical foreign keys (`skill_id`), preventing naming variations from corrupting calculations.

---

# Part 2: Post-MVP Foundation Progress & Planned Evolution

> [!NOTE]
> Post-MVP Phase 1 (P1) is currently under active development on the `post-mvp-foundation` branch.
> Checkpoints P1-A, P1-B, P1-C, and P1-D are implemented. The frozen `v1.0.0-mvp` baseline remains intact.

---

## 9. Checkpoint P1-D Implemented: Deterministic Market Skill Extraction

Checkpoint P1-D implements the first persistent market-data skill extraction pipeline (`backend/app/services/market/extraction/`).

### Core Principles
- **"The LLM Never Decides What is True"**: P1-D uses strictly deterministic taxonomy matching; no LLMs, Qwen, embeddings, vector similarity, or semantic model inference are used.
- **Single Canonical Taxonomy**: Reuses the exact canonical skills (`skills`) and aliases (`skill_aliases`) from the PostgreSQL database without introducing a second taxonomy or inventing aliases.
- **Boundary Safety & False-Positive Prevention**:
  - Uses token-boundary assertions `(?<![a-zA-Z0-9#+])` and `(?![a-zA-Z0-9#+])` that prevent false positives from sub-word matches (e.g., `"Go"` does not match `"good"`, `"algorithm"`, or `"going"`; `"C"` does not match in `"cloud"` or `"basic"`).
  - Programming symbols (`C++`, `C#`) preserve trailing `+` and `#` symbols.
  - Short skills like `"Go"` enforce strict case and word-boundary safety (`\bGo\b`, `\bGO\b`, `golang`, `go-lang`), rejecting the common English verb `"go"`.
- **Longest-Match-First Overlap Resolution**: Multi-word and longer phrases (e.g. `"React Native"` vs `"React"`, `"Docker Compose"` vs `"Docker"`) are compiled and matched by length descending, claiming character spans and preventing nested duplicate extractions.
- **Title vs Description Precedence**: Mentions in the job `title` are prioritized over `description` mentions for provenance, while description text is scanned for additional complementary skills.
- **Per-Job Deduplication**: Exactly one relationship per canonical `skill_id` is created per market job posting.
- **Verbatim Evidence**: Verbatim context snippets are extracted directly from the raw job posting text around match spans without LLM rewriting.
- **Dedicated Persistence (`market_job_skills`)**:
  - Relationships are persisted in `market_job_skills` table with unique constraint `(market_job_id, skill_id)`.
  - Employs PostgreSQL-native `ON CONFLICT (market_job_id, skill_id) DO UPDATE` for idempotent persistence.
  - Supports deterministic reconciliation to purge stale skills when job descriptions change.
- **Scope Boundary**: P1-D produces verified `market_job_skills` evidence. Demand aggregation, growth rates, and demand score recalculation are strictly deferred to Checkpoint P1-E. The MVP `skill_demand` table remains untouched.

---

## 10. Planned Semantic Normalization Pipeline

In future phases, the deterministic normalizer may be augmented with a semantic fallback layer for unmapped or novel industry technologies:

```text
Raw / Unknown Skill Mention
        ↓
Deterministic Normalizer (Exact / Alias Match)
        ├── Matched ──► Canonical Skill ID
        └── Unmatched
                 ↓
        Dense Text Embedding Generation
                 ↓
        Cosine Similarity Search (PostgreSQL pgvector)
                 ├── Similarity >= Threshold ──► Candidate Canonical Match
                 └── Similarity < Threshold  ──► Novel Skill Review Queue
```

- **Candidate Review**: Unmatched skills that score below strict confidence thresholds will be queued for manual administrator taxonomy review rather than automatically inserted.
- **LLM-Assisted Disambiguation**: An auxiliary LLM prompt may suggest candidate canonical mappings for complex phrasing, but mappings must be validated against the taxonomy before becoming authoritative.

---

## 10. Planned Skill Relationships & Graph Structures

The following graph relationship concepts are planned for post-MVP learning roadmaps and curriculum generation:

### 10.1 Prerequisite Directed Acyclic Graph (DAG)
- Modeling strict learning dependencies (e.g., `Docker` $\rightarrow$ `Kubernetes`, `JavaScript` $\rightarrow$ `TypeScript`).
- Topological sort algorithms for milestone sequencing.
- Prerequisite bonus weighting in roadmap prioritization.

### 10.2 Co-Occurrence Complements
- Tracking technologies frequently deployed together in industry architectures (e.g., `FastAPI` + `PostgreSQL` + `Docker`).
- Suggesting complementary technologies once a primary technology reaches `STRONG` status.

### 10.3 Hierarchical Skill Trees
- Deep multi-level parent-child relationships (e.g., `Databases` $\rightarrow$ `Relational` $\rightarrow$ `PostgreSQL` $\rightarrow$ `JSONB Querying`).
