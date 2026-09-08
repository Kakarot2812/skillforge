# SkillForge AI — Data Flow Architecture

## 1. System-Wide Data Flow Overview

SkillForge AI processes heterogeneous input streams (PDF/DOCX resumes, GitHub source code, structured job market data) into structured skills, empirical demand signals, and personalized learning roadmaps.

```text
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   User Resume   │       │   GitHub Repos  │       │ Raw Market Data │
│   (PDF / DOCX)  │       │  (Public API)   │       │  (Job Postings) │
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │                         │                         │
         ▼                         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ Resume Parser   │       │ GitHub Analyzer │       │  Demand Pipeline│
│ (PyMuPDF / LLM) │       │ (Manifests / CI)│       │ (Clean & Norm)  │
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │                         │                         │
         ▼                         ▼                         ▼
  Claimed Skills          Demonstrated Skills         Demand Scores
         │                         │                         │
         └────────────┬────────────┘                         │
                      ▼                                      │
            ┌───────────────────┐                            │
            │  Evidence Matrix  │                            │
            └─────────┬─────────┘                            │
                      │                                      │
                      └───────────────┬──────────────────────┘
                                      ▼
                           ┌─────────────────────┐
                           │   Skill Gap Engine  │
                           └──────────┬──────────┘
                                      │
                                      ▼
                           ┌─────────────────────┐
                           │   Roadmap Engine    │
                           └──────────┬──────────┘
                                      │
                                      ▼
                           ┌─────────────────────┐
                           │  Resource Matching  │
                           │      (RAG / DB)     │
                           └──────────┬──────────┘
                                      │
                                      ▼
                           ┌─────────────────────┐
                           │  Next.js Dashboard  │
                           └─────────────────────┘
```

---

## 2. Detailed Pipeline Sub-Flows

### 2.1 Flow 1: Resume Ingestion & Claimed Skill Extraction

```text
[Client Browser]
       │
       │ 1. POST /api/v1/resumes/upload (multipart/form-data)
       ▼
[FastAPI Backend]
       │
       │ 2. Text Extraction (PyMuPDF / pdfplumber)
       ▼
[Raw Document Text]
       │
       │ 3. Structural Section Segmentation (Header, Skills, Experience, Projects)
       ▼
[Section Splitter]
       │
       │ 4. Entity Extraction & Normalization
       ▼
[Skill Taxonomy Matcher] ◄─── pgvector semantic similarity & canonical aliases
       │
       │ 5. Store parsed resume & claimed skill relations
       ▼
[PostgreSQL Database] (resumes, user_claimed_skills)
```

1. **Upload**: User uploads a resume document.
2. **Text Extraction**: The backend extracts clean raw text and layout blocks.
3. **Segmentation**: Regex and NLP segment the text into standard resume sections.
4. **Extraction**: Known skill patterns are identified; ambiguous phrases are sent to the LLM for structured extraction.
5. **Taxonomy Normalization**: Extracted terms are matched against canonical skills using alias lookups and pgvector cosine similarity.
6. **Storage**: Claimed skills are persisted in PostgreSQL linked to the user.

---

### 2.2 Flow 2: GitHub Repository & Evidence Extraction

```text
[Client Browser]
       │
       │ 1. POST /api/v1/github/connect (GitHub username / token)
       ▼
[FastAPI Backend]
       │
       │ 2. GET /users/{username}/repos
       ▼
[GitHub REST API]
       │
       │ 3. Return repository list (filter out forks)
       ▼
[GitHub Service]
       │
       │ 4. Inspect file trees:
       │    - Dependency manifests (package.json, requirements.txt, etc.)
       │    - Infrastructure files (Dockerfile, docker-compose.yml)
       │    - CI/CD configurations (.github/workflows/*.yml)
       ▼
[Evidence Heuristic Engine]
       │
       │ 5. Calculate Concrete Project Evidence
       ▼
[PostgreSQL Database] (github_repositories, project_evidence)
       │
       │ 6. Deterministic Demonstrated Skill Aggregation
       ▼
[PostgreSQL Database] (demonstrated_skills)
       │
       │ 7. Future Skill Gap Engine (Phase 5)
       ▼
```

1. **Connection**: User submits their GitHub username or OAuth authorization (`POST /api/v1/github/connect`).
2. **Discovery**: Backend queries the GitHub API for original repositories, excluding forks (`is_fork == False`).
3. **Tree Inspection**: System queries git trees recursively via `/git/trees/{branch}` with entry safety limits.
4. **Manifest / Infra / CI Inspection**: Parses concrete artifacts:
   - Python: `requirements.txt`, `pyproject.toml`
   - JavaScript/TypeScript: `package.json`
   - Java: `pom.xml`
   - Go: `go.mod`
   - Docker: `Dockerfile`, `docker-compose.yml`
   - CI/CD: `.github/workflows/*.yml`
5. **Taxonomy Normalization**: Candidate technologies are matched deterministically against the canonical skill taxonomy and aliases (`skills`, `skill_aliases`). Unknown dependencies are safely ignored.
6. **Confidence Scoring**: Deterministic confidence weights ($0.0 \le \text{score} \le 1.0$) are assigned (dependency: $0.95$, Dockerfile: $0.90$, docker-compose: $0.88$, CI workflow: $0.85$, structure: $0.70$).
7. **Idempotent Reconciliation**: Auditable records are persisted into `project_evidence`, updating existing records in-place and reconciling stale evidence on re-scans.
8. **Demonstrated Skill Aggregation**:
   - Aggregates evidence records grouped by `(user_id, skill_id)`.
   - Within each repository: $\text{repo\_score}_i = \max(\text{evidence confidence})$. Duplicate evidence in the same repository does not inflate scores.
   - Across independent repositories: $\text{multi\_repo\_score} = 1.0 - \prod (1.0 - \text{repo\_score}_i)$, clamped to $[0.0, 1.0]$.
   - Persisted into `demonstrated_skills` (`evidence_level`: `HIGH` $\ge 0.85$, `MEDIUM` $\ge 0.70$, `LOW` $< 0.70$).
   - **Inviolable Principle**: LLMs are strictly forbidden from creating demonstrated skill records, modifying quantitative scores, or inventing repository evidence. Demonstrated skills are strictly backed by concrete code artifacts.

---

### 2.3 Flow 3: Industry Demand Calculation Pipeline

```text
[Raw Job Market Dataset] (Permitted / Licensed Job Postings)
       │
       │ 1. Ingestion & Preprocessing
       ▼
[Data Cleaning Pipeline]
       │
       │ 2. Deduplication & Noise Removal
       ▼
[Role Classification Engine] (Maps posting to canonical target role)
       │
       │ 3. Extract skills from Job Description
       ▼
[Taxonomy Normalizer] ◄─── Canonical Skill Dictionary + pgvector
       │
       │ 4. Aggregate by (Role, Skill, Location, Time Window)
       ▼
[Statistical Aggregator]
       │
       │ 5. Compute Demand Frequency % & Growth Trends
       ▼
[PostgreSQL Database] (skill_demand table)
```

> [!IMPORTANT]
> **Data-Driven Separation**: RAG and LLM systems are **not** permitted to generate or alter numerical demand scores. The demand scores stored in `skill_demand` are derived solely from mathematical aggregations over real job market data.

---

### 2.4 Flow 4: Skill Gap & Priority Scoring Flow

```text
[User Request]
       │
       │ 1. Trigger Gap Analysis for Target Role
       ▼
[FastAPI Skill Engine]
       │
       ├──► 2. Read User Claimed Skills (from resumes)
       ├──► 3. Read User Demonstrated Skills (from project_evidence)
       └──► 4. Read Role Skill Demand (from skill_demand)
       │
       ▼
[Synthesis Matrix]
       │
       │ 5. Compute Evidence Level:
       │    - High: Claimed + Demonstrated
       │    - Medium: Demonstrated Only
       │    - Low: Claimed Only
       │    - Missing: Neither Claimed nor Demonstrated
       ▼
[Priority Scoring Algorithm]
       │
       │ 6. Priority = DemandWeight * DemandScore
       │             + GrowthWeight * GrowthRate
       │             + GapWeight * (1.0 - EvidenceScore)
       │             + PrerequisiteBonus
       ▼
[Ranked Skill Gap List]
```

---

### 2.5 Flow 5: Dynamic Roadmap Generation Flow

```text
[Ranked Skill Gap List]
       │
       │ 1. Retrieve Prerequisite Graph (DAG) from skill_dependencies
       ▼
[Topological Sort Engine]
       │
       │ 2. Sequence missing skills ensuring prerequisites precede dependents
       ▼
[Milestone Clustering]
       │
       │ 3. Group sequenced skills into sequential phases based on user weekly hours
       ▼
[Resource & Project Association]
       │
       ├──► 4. Match vetted resources from learning_resources
       └──► 5. Assign practical project challenges targeting milestone skills
       │
       ▼
[PostgreSQL Database] (roadmaps, roadmap_milestones)
       │
       │ 6. Deliver structured JSON to Frontend
       ▼
[Next.js Interactive Roadmap UI]
```

---

### 2.6 Flow 6: RAG-Backed AI Assistant Flow

```text
[User Chat Prompt in Next.js]
       │
       │ 1. POST /api/v1/assistant/chat
       ▼
[FastAPI Assistant Service]
       │
       │ 2. Load User Context (Profile, Gaps, Active Milestone)
       │ 3. Generate Query Embedding
       ▼
[pgvector Search]
       │
       │ 4. Cosine similarity query on rag_documents table
       │    Filter by relevant skill_ids and doc types
       ▼
[Retrieved Context Chunks]
       │
       │ 5. Assemble Prompt:
       │    - System Instructions (grounding constraints)
       │    - Verified User Skill Data
       │    - Exact Database Demand Metrics (read-only facts)
       │    - Retrieved Resource Snippets
       │    - User Question
       ▼
[LLM (e.g. Gemini / Claude / GPT)]
       │
       │ 6. Stream grounded explanation / advice
       ▼
[Client Browser Chat Window]
```

---

### 2.7 Flow 7: GitHub Verification Loop

```text
[User completes project and clicks "Verify Milestone"]
       │
       │ 1. POST /api/v1/verify/project { milestone_id, repo_url }
       ▼
[FastAPI Verification Service]
       │
       │ 2. Inspect target repository via GitHub API
       ▼
[GitHub API]
       │
       │ 3. Verify target files, dependencies, and code structure
       ▼
[Rubric Evaluation Engine]
       │
       ├──► If PASSED:
       │    - Elevate skill to Demonstrated
       │    - Update roadmap_milestones status to 'verified'
       │    - Recompute skill gap score
       │
       └──► If FAILED:
            - Return specific checklist of missing criteria to user
       ▼
[PostgreSQL Database & Client Dashboard Update]
```
