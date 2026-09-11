# SkillForge AI — Data Flow Architecture

This document defines the data flow, data movement, transformations, evidence boundaries, and ownership scopes of SkillForge AI. It is organized into two primary divisions:

1. **v1.0.0 MVP Data Flow (Frozen Baseline)**: The operational, deterministic pipeline implemented and verified in the frozen `v1.0.0-mvp` release.
2. **Post-MVP Data Flow (Planned Evolution)**: The planned architectural data flows for real-time market ingestion, local open-weight LLM reasoning (Qwen 3 8B), and closed-loop verification on the `post-mvp-foundation` branch.

---

# Part 1: v1.0.0 MVP Data Flow (Frozen Baseline)

## 1. Implemented Candidate Analysis Flow

SkillForge AI v1.0.0 MVP implements an end-to-end deterministic data flow that extracts candidate evidence, cross-references it with structured industry demand data, computes skill gaps and priority ranks, and generates an auditable evidence trail.

```text
User
  ↓
Resume Upload ───────────────┐
                             ↓
                      Resume Evidence
                             │
GitHub Connection ───────────┤
                             ↓
                      Candidate Evidence
                             ↓
                   Canonical Skill Model
                             ↓
                  Industry Skill Demand
                             ↓
                  Deterministic Skill Gap
                             ↓
                    Priority Calculation
                             ↓
                       Evidence Audit
                             ↓
                    Career Intelligence UI
```

---

## 2. Evidence Pipeline Sub-Flows & Data Boundaries

### 2.1 Flow 1: Resume Ingestion & Claimed Skill Evidence

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
       │ 4. Entity Extraction & Canonical Taxonomy Normalization
       ▼
[Skill Taxonomy Matcher] ◄─── Canonical aliases & pgvector semantic matching
       │
       │ 5. Associate evidence strictly with candidate / resume scope
       ▼
[PostgreSQL Database] (resumes, resume_evidence)
```

**Data Boundaries & Validation**:
- **Upload & Validation**: Resume documents (PDF/DOCX) are uploaded and validated for MIME type, file integrity, and payload size.
- **Text Extraction**: Text extraction engines (PyMuPDF / pdfplumber) extract clean raw text and layout blocks.
- **Section Parsing**: Text is segmented into standard resume sections (Header, Education, Experience, Skills, Projects).
- **Taxonomy Normalization**: Extracted skills are normalized against the canonical skill taxonomy using alias dictionaries and pgvector cosine similarity.
- **Scope Isolation**: Resume-derived evidence is associated strictly with the candidate and resume scope. Candidate data remains isolated to the correct user profile.

---

### 2.2 Flow 2: GitHub Repository & Demonstrated Evidence Extraction

```text
[Client Browser]
       │
       │ 1. POST /api/v1/github/connect (GitHub username / token)
       ▼
[FastAPI Backend]
       │
       │ 2. GET /users/{username}/repos (Query public repositories)
       ▼
[GitHub REST API]
       │
       │ 3. Exclude forks (is_fork == False) & verify repository ownership
       ▼
[GitHub Service]
       │
       │ 4. Inspect file trees for concrete artifacts:
       │    - Dependency manifests: package.json, requirements.txt, pyproject.toml, pom.xml, go.mod
       │    - Infrastructure files: Dockerfile, docker-compose.yml
       │    - CI/CD workflows: .github/workflows/*.yml
       ▼
[Evidence Engine]
       │
       │ 5. Map artifacts to canonical skills & assign deterministic confidence weights
       ▼
[PostgreSQL Database] (github_repositories, project_evidence)
       │
       │ 6. Deterministic Multi-Repo Demonstrated Skill Aggregation
       ▼
[PostgreSQL Database] (demonstrated_skills)
```

**Data Boundaries & Validation**:
- **Connection & Discovery**: Candidate connects their GitHub account; repository metadata is retrieved via the GitHub REST API.
- **Ownership & Fork Filtering**: Forks (`is_fork == False`) and repositories outside the candidate's ownership are strictly excluded from evidence consideration.
- **Artifact Inspection**: Scans git trees recursively for verifiable code artifacts:
  - Python: `requirements.txt`, `pyproject.toml`
  - JavaScript / TypeScript: `package.json`
  - Java: `pom.xml`
  - Go: `go.mod`
  - Containerization: `Dockerfile`, `docker-compose.yml`
  - CI/CD: `.github/workflows/*.yml`
- **Canonical Skill Normalization**: Discovered technologies are normalized into the exact same canonical skill representation as resume evidence.
- **Evidence Confidence & Aggregation**: Deterministic confidence weights are assigned to code evidence ($0.0 \le \text{score} \le 1.0$). Within a single repository, $\text{repo\_score} = \max(\text{evidence confidence})$. Across multiple independent repositories, signals are aggregated using the independent probability union: $\text{multi\_repo\_score} = 1.0 - \prod (1.0 - \text{repo\_score}_i)$, clamped to $[0.0, 1.0]$.
- **Evidence Principle**: GitHub evidence represents *demonstrated concrete evidence*, not proof of mastery.

---

### 2.3 Candidate Evidence States & Scope Isolation

Candidate evidence from resumes and GitHub repositories can exist independently. The system supports three distinct operational states:

1. **Resume Only**: Candidate provides resume evidence without GitHub. Claimed skills are extracted and normalized; demonstrated skills remain empty.
2. **GitHub Only**: Candidate connects GitHub profile without uploading a resume. Demonstrated skills are extracted from verified repositories; claimed resume skills remain empty.
3. **Resume + GitHub**: Candidate provides both resume and GitHub evidence. The system unifies both streams into a combined evidence profile, cross-validating claimed skills against demonstrated repository artifacts.

**Scope Isolation Invariant**: All candidate-specific data (resumes, repositories, parsed evidence, demonstrated skill aggregations) is strictly partitioned and isolated by user ID and resume ID. Candidate evidence from one profile never leaks into another profile's scope.

---

### 2.4 Deterministic Skill Gap & Priority Scoring Flow

```text
[User Request] (Target Role Selected)
       │
       │ 1. Trigger Gap Analysis for Target Role
       ▼
[FastAPI Skill Gap Engine]
       │
       ├──► 2. Read User Claimed Skills (from resume_evidence)
       ├──► 3. Read User Demonstrated Skills (from demonstrated_skills)
       └──► 4. Read Structured Role Skill Demand (from skill_demand)
       │
       ▼
[Deterministic Synthesis Matrix]
       │
       │ 5. Evaluate Candidate Evidence vs. Role Demand
       ▼
[Deterministic Classification]
       │
       ├──► STRONG: High candidate evidence meeting or exceeding role benchmark
       ├──► PARTIAL: Moderate evidence or claimed skill lacking demonstrated depth
       └──► MISSING: Critical target-role skill with neither claimed nor demonstrated evidence
       │
       ▼
[Deterministic Priority Calculation]
       │
       │ 6. Priority = DemandWeight * DemandScore
       │             + GrowthWeight * GrowthRate
       │             + GapSeverityWeight * (1.0 - EvidenceScore)
       │             + PrerequisiteBonus
       ▼
[Evidence Audit & Output Serialization]
       │
       │ 7. Audit records generated tracing every score to underlying evidence
       ▼
[PostgreSQL Database & Career Intelligence UI]
```

**Deterministic Guardrails**:
- **Skill Gap Classification**: Categorization into `STRONG`, `PARTIAL`, and `MISSING` is strictly deterministic based on candidate evidence levels relative to role demand thresholds. No LLM participates in or influences this classification.
- **Priority Calculation**: Priority rank is calculated deterministically from existing demand, growth, and gap severity weights. No formulas are altered or invented.
- **Evidence Audit**: The audit record synthesizes candidate evidence (resume lines, repository manifests) with market evidence (demand frequency, growth trends) into an explainable, auditable trail fully traceable to verified database records.

---

## 3. Current MVP Data Ownership & Boundaries

The MVP architecture maintains rigorous data ownership boundaries across three distinct categories:

```text
┌────────────────────────────────────────────────────────┐
│                   CANDIDATE EVIDENCE                   │
│  - Resume Evidence (claimed skills, parsed sections)   │
│  - GitHub Evidence (manifests, workflows, Dockerfiles) │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                    MARKET EVIDENCE                     │
│  - Structured Industry Skill Demand Data               │
│  - Role Requirement Baselines                          │
│  - Historical Growth Rates                             │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                  DERIVED INTELLIGENCE                  │
│  - Deterministic Skill Classification (STRONG/PARTIAL/ │
│    MISSING)                                            │
│  - Deterministic Priority Ranks                        │
│  - Traceable Evidence Audit Trails                     │
└────────────────────────────────────────────────────────┘
```

- **Candidate Evidence**: Owned exclusively by the authenticated user and scoped to individual resume/repository uploads.
- **Market Evidence**: Owned by the system as pre-aggregated, structured industry demand records stored in `skill_demand` and `target_roles`.
- **Derived Intelligence**: Computed deterministically from stored candidate evidence and structured market evidence. It is **never** generated arbitrarily by an LLM.
- **No Real-Time Ingestion in MVP**: The frozen v1.0.0 MVP utilizes structured, validated industry demand baselines. Real-time market data ingestion is not part of the frozen MVP.

---

# Part 2: Post-MVP Data Flow — Planned Evolution

> [!NOTE]
> All data flows, pipelines, and models in Part 2 are **POST-MVP / PLANNED**. They are designed for implementation on the `post-mvp-foundation` branch and are not implemented in the frozen `v1.0.0-mvp` release.

---

## 4. Planned Real-Time Industry Demand Pipeline (P1)

In post-MVP Phase 1, the structured industry demand baseline evolves into a continuous, refreshable market data pipeline.

```text
Market Sources
  ↓
Market Data Ingestion
  ↓
Cleaning / Normalization
  ↓
Skill Extraction
  ↓
Canonical Skill Normalization
  ↓
Deterministic Demand Calculation
  ↓
Demand Database
  ↓
Demand API
  ↓
Skill Gap + Priority
```

### Critical Architectural Distinction: RAG vs. Demand Calculation

- **RAG / retrieval does NOT calculate industry demand.**
- The real-time behavior comes from continuously ingesting updated market data and recalculating the deterministic market signal.
- The demand API serves refreshed, mathematically derived demand scores directly to the deterministic skill gap engine.

---

## 5. Planned AI Data Flow with Local Qwen 3 8B (P2 / P3)

In post-MVP Phases 2 and 3, an open-weight local LLM (Qwen 3 8B) is integrated as an explanation, contextual reasoning, and personalization layer over verified SkillForge intelligence.

```text
Candidate Evidence
        +
Verified Market Evidence
        +
Deterministic Skill Gap / Priority
        ↓
Retrieval / Evidence Context
        ↓
Qwen 3 8B Local LLM
        ↓
Response Verification
        ↓
Career Intelligence Response
```

### Purpose of Qwen 3 8B
Qwen 3 8B is planned strictly as an explanation, reasoning, and personalization layer over verified SkillForge evidence.

### AI Safety & Boundary Rules

> **"Deterministic systems decide what is true.**
> **AI explains, reasons over, and personalizes verified evidence."**

**The LLM May**:
- Explain deterministic results and audit trails in clear natural language.
- Reason over verified candidate evidence.
- Explain market evidence and role trends.
- Answer career questions using retrieved evidence context.
- Generate learning suggestions.
- Generate roadmap/resource recommendations based on verified gaps.

**The LLM Must NOT**:
- Invent candidate skills.
- Decide authoritative skill possession.
- Override `STRONG`, `PARTIAL`, or `MISSING` classifications.
- Calculate authoritative demand scores.
- Calculate authoritative priority scores.
- Fabricate market evidence.
- Present unsupported claims as verified facts.

---

## 6. Planned Closed-Loop Verification Flow (P5)

In post-MVP Phase 5, SkillForge introduces a continuous verification loop connecting learning milestones to demonstrated GitHub evidence:

```text
Career Recommendation
  ↓
Learning / Project Work
  ↓
GitHub Project Evidence
  ↓
GitHub Re-analysis
  ↓
Demonstrated Skills Update
  ↓
Skill Gap Recalculation
  ↓
Priority Update
  ↓
Updated Career Recommendation
```

### Closed-Loop Stages
1. **Targeted Learning**: Candidate undertakes recommended projects addressing verified skill gaps.
2. **Project Deployment**: Candidate commits code, dependency manifests, and CI/CD configurations to their GitHub repository.
3. **GitHub Re-Analysis**: GitHub analyzer re-inspects repository trees and extracts new concrete evidence.
4. **Demonstrated Skills Update**: Multi-repo demonstrated skill scores update.
5. **Skill Gap Recalculation**: Skill gaps are deterministically recalculated.
6. **Priority Update**: Priority ranks update deterministically.
7. **Updated Career Recommendation**: System presents refreshed, verified recommendations without manual intervention or LLM override.
