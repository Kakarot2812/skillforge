# SkillForge AI — Product Requirements Document

## 1. Product Overview

SkillForge AI is an evidence-based AI skill-gap and career intelligence platform.

The platform analyzes:

1. User resume evidence
2. User GitHub repositories and project code artifacts
3. Target career role
4. Industry skill demand and market trajectories

The system creates an auditable, evidence-based candidate skill profile, identifies concrete gaps between demonstrated capabilities and current market requirements, prioritizes those gaps deterministically, and prepares evidence-backed career guidance. In its full evolution, the platform converts these insights into personalized learning roadmaps, curated resources, and closed-loop project verification.

---

## 2. Current Status

- **v1.0.0 MVP is frozen**: Successfully delivered and tagged as `v1.0.0-mvp`.
- **Deterministic foundation**: The deterministic evidence-based intelligence pipeline is the established operational source of truth.
- **Post-MVP branch**: Post-MVP development begins from branch `post-mvp-foundation`.
- **Immediate milestone**: Development advances with **P1 — Real-Time Industry Demand**.
- **Layered architecture**: Future AI capabilities will be layered strictly on top of verified deterministic intelligence. P1 has not yet been implemented.

---

## 3. Problem

Students and early-career developers frequently encounter critical blind spots in career preparation:

- **Unknown market requirements**: Unclear which skills are truly required and trending for their target role versus legacy perceptions.
- **Unverified skill inventory**: Uncertainty about which skills they genuinely possess versus passive exposure.
- **Claimed vs. demonstrated gap**: Resume claims lack concrete, inspectable code artifacts and project evidence.
- **Lack of prioritization**: Inability to identify which missing skills should be learned first based on market demand and gap severity.
- **Generic learning guidance**: Conventional career platforms offer static, one-size-fits-all roadmaps disconnected from candidate strengths and live industry demand.
- **Absence of proof**: Lack of practical projects that demonstrably prove competency to prospective employers.

SkillForge AI replaces static advice with evidence-grounded analysis derived from the candidate's actual artifacts and dynamic industry market data.

---

## 4. Target Users

### Primary Users

- Computer science students
- College and university engineering students
- Fresh graduates entering the tech workforce
- Early-career developers seeking role transitions or skill upgrades

### Secondary Users

- Career-switchers transitioning into technical roles
- Placement preparation cohorts and bootcamps
- Colleges, universities, and technical training institutions

---

## 5. Core User Journey

The end-to-end user journey bridges candidate profile intake, deterministic intelligence, and future AI-guided execution:

```text
Resume
   ↓
GitHub
   ↓
Target Role
   ↓
Candidate Evidence
   ↓
Industry Demand
   ↓
Deterministic Skill Gap
   ↓
Priority
   ↓
Evidence Audit
   ↓
Future AI Guidance (Post-MVP)
   ↓
Roadmap / Resources (Post-MVP)
   ↓
GitHub Verification (Post-MVP)
   ↓
Re-analysis (Post-MVP)
```

*Note: Steps from Candidate Evidence through Evidence Audit represent the completed v1.0.0 MVP baseline. Subsequent steps (AI Guidance, Roadmap/Resources, GitHub Verification, and automated Re-analysis) represent post-MVP product capabilities.*

---

## 6. Core Features

### 6.1 Resume Analysis (MVP Baseline)

The resume intelligence engine ingests, validates, and extracts candidate claims:

- Document upload and validation gate (strict MIME type and magic-bytes verification for PDF and DOCX, 5 MB payload limit)
- Section extraction (Skills, Experience, Projects, Education, Certifications)
- Skill phrase extraction with raw mention preservation
- Canonical taxonomy normalization against platform skill aliases
- Candidate-scoped claimed skills storage (`UserClaimedSkill`) with explicit resume linkage and isolation

### 6.2 GitHub Code Analysis (MVP Baseline)

The repository analysis engine inspects connected GitHub repositories to detect concrete evidence of technical skills:

- Fork exclusion and ownership verification ensuring candidate provenance
- Path traversal safeguards and safe tree inspection
- Multi-ecosystem manifest parsing (`requirements.txt`, `pyproject.toml`, `package.json`, `pom.xml`, `go.mod`, Dockerfiles, docker-compose, GitHub Actions CI workflows)
- Creation of auditable `ProjectEvidence` records linking skill, file path, artifact name, matched content snippet, and confidence score
- Strict candidate profile scoping and IDOR prevention

The system maintains a fundamental distinction:

- **Claimed Skill**: A skill documented in a resume without verified code artifacts.
- **Demonstrated Skill**: A skill verified through actual GitHub repository evidence and code artifacts.

### 6.3 Industry Demand Engine (MVP Baseline & Post-MVP Evolution)

The platform rejects static technology lists in favor of structured industry demand signals:

- **Current MVP Baseline**:
  - Utilizes a curated, structured industry-demand dataset across canonical job roles and geographic markets (e.g., India).
  - Calculates deterministic demand scores (0.0 to 1.0), YoY growth rates, and skill frequencies.
  - Maintains explicit data freshness dates and scoring metadata.

- **Post-MVP Evolution (P1)**:
  - Continual ingestion of live market data across diverse industry sources.
  - Automated skill extraction and normalization pipeline for incoming market signals.
  - Refreshed demand scoring and growth trajectories preserving provenance and timestamps.

### 6.4 Skill Gap Engine (MVP Baseline)

The engine deterministically compares:

```text
Candidate Skill Evidence (Resume + GitHub)
                     +
Target Role Requirements & Industry Demand
```

Classification follows strict, non-negotiable thresholds:

- **STRONG**: Verified GitHub code demonstration with confidence >= 0.85 (HIGH evidence tier).
- **PARTIAL**: Candidate has some evidence (resume claim or demonstrated evidence < 0.85) insufficient for full verification.
- **MISSING**: Neither a resume claim nor verified GitHub code evidence exists.

### 6.5 Priority Engine (MVP Baseline)

Actionable skill gaps (`MISSING` and `PARTIAL`) are prioritized using a deterministic mathematical formula:

$$\text{Priority Score} = (\text{Demand Score} \times 0.6) + (\text{Growth Rate} \times 0.2) + (\text{Severity Weight} \times 0.2)$$

Where:
- $\text{Severity Weight} = 1.0$ for `MISSING`, $0.5$ for `PARTIAL`, $0.0$ for `STRONG`.
- Tiering thresholds: `HIGH` (>= 0.67), `MEDIUM` (>= 0.34), `LOW` (< 0.34).
- Deterministic ordering: Priority Tier → Priority Score → Demand Score → Skill Name.

### 6.6 Personalized Roadmap (Future — Post-MVP P4)

*Status: Product Vision / Post-MVP Capability.*

The system will convert prioritized skill gaps into an actionable, step-by-step learning sequence:

- Dependency-aware skill sequencing honoring prerequisites
- Modular learning objectives tailored to starting proficiency
- Actionable milestones with estimated completion effort
- Integrated practical project specifications designed for GitHub verification

### 6.7 Resource Recommendation (Future — Post-MVP P4)

*Status: Product Vision / Post-MVP Capability.*

A curated recommendation engine mapping verified resources to candidate gaps:

- Category coverage: official documentation, structured courses, tutorials, books, and interactive labs
- Level-appropriate matching based on existing candidate skills
- Focus on practical, project-centric learning materials

### 6.8 AI Assistant (Future — Post-MVP P2/P3)

*Status: Product Vision / Post-MVP Capability.*

An evidence-grounded conversational agent powered by local LLM architecture:

- Interacts strictly with verified SkillForge intelligence rather than ungrounded assumptions.
- Illustrative query capabilities:
  - *"Why is Docker a priority for me?"*
  - *"Which evidence caused React to be classified as STRONG?"*
  - *"What should I learn next based on my current target role?"*
- Answers questions using candidate evidence records, gap classifications, and market data.

### 6.9 GitHub Skill Verification Loop (Future — Post-MVP P5)

*Status: Product Vision / Post-MVP Capability.*

Closed-loop progress verification through code commits:

- User completes a recommended project and pushes commits to GitHub.
- The platform rescans the repository, detects new technical artifacts, and recalculates evidence confidence.
- Candidate demonstrated skills and skill gaps update dynamically, demonstrating verifiable growth.

---

## 7. MVP Scope — v1.0.0

The `v1.0.0-mvp` release represents the frozen foundation of SkillForge AI. All listed capabilities are fully implemented and verified by automated regression test suites.

### 7.1 Completed MVP Capabilities

- **Resume Upload & Validation**: Secure upload gate enforcing file size limits, MIME validation, and magic-byte checks for PDF and DOCX documents.
- **Resume Text & Section Extraction**: Deterministic extraction of raw text and semantic sections.
- **Resume Skill Extraction**: Pattern-based extraction of technical skills preserved with raw mention context.
- **Canonical Skill Normalization**: Bidirectional alias resolution mapping raw names to canonical taxonomy entities.
- **GitHub Connection**: User verification and repository synchronization with fork filtering and star tracking.
- **GitHub Repository Analysis**: Tree traversal and manifest parsing across 8+ technical file formats.
- **Demonstrated Skill Detection**: Extraction of project evidence with confidence scoring.
- **Candidate Evidence Aggregation**: Multi-repository independent confirmation utilizing bounded noisy-OR aggregation.
- **Target Role Selection**: Canonical role definitions linked to industry demand profiles.
- **Structured Industry Skill-Demand Dataset**: Curated market demand profiles across roles and locations.
- **Deterministic Demand Scoring**: Role-specific demand percentages, YoY growth rates, and frequency metrics.
- **Deterministic Skill-Gap Classification**: Classification into `STRONG`, `PARTIAL`, and `MISSING` based on mathematical rules.
- **Deterministic Priority Scoring**: Multi-signal scoring and tiering into `HIGH`, `MEDIUM`, and `LOW`.
- **Evidence Audit Trail**: Complete auditable provenance chain linking resume mentions, GitHub code artifacts, and market demand for every gap.
- **Candidate Data Isolation & IDOR Protection**: Strict authorization boundaries preventing cross-user profile leakage.
- **Candidate Readiness Gating**: Deterministic readiness checks ensuring complete profile context prior to downstream calculations.
- **Interactive UI Dashboard**: Next.js client interface delivering visibility into demand exploration, repository connections, gap visualizations, and evidence audit trails.

### 7.2 Deferred / Post-MVP Scope

The following capabilities are deliberately excluded from v1.0.0 and scheduled for post-MVP phases:

- Real-time live market scraping / automated external job-feed ingestion
- Local LLM inference integration (Qwen 3 8B)
- Interactive conversational AI assistant / chatbot
- Automated dynamic personalized roadmap generator
- Automated external resource recommendation engine
- Continuous closed-loop GitHub verification triggers
- Enterprise multi-tenant recruiter and institutional portals
- Mobile application

---

## 8. Post-MVP Roadmap

Post-MVP development is structured into five sequential, focused phases:

```text
P1: Real-Time Industry Demand
             ↓
P2: Local Qwen 3 8B AI Layer
             ↓
P3: Evidence-Grounded Career Chatbot
             ↓
P4: Personalized Roadmap & Resources
             ↓
P5: GitHub Skill Verification Loop
```

### P1 — Real-Time Industry Demand

**Objective**: Transition from the current structured baseline dataset to an extensible, refreshable market data pipeline that continuously reflects live industry hiring requirements.

**Conceptual Pipeline**:

```text
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

The objective is to extend and refresh the market-data foundation without altering downstream deterministic contracts. Note: No specific external job API, commercial provider, or scraping mechanism has been pre-selected; the system is not yet real-time in v1.0.0.

### P2 — Local Qwen 3 8B AI Layer

**Objective**: Deploy an open-weight, locally hosted large language model (Qwen 3 8B) to perform structured extraction, synthesis, and reasoning over verified candidate and market data with zero external API dependencies.

### P3 — Evidence-Grounded Career Chatbot

**Objective**: Introduce a conversational interface allowing candidates to interrogate their skill profile, understand prioritization rationale, and receive natural-language career guidance strictly grounded in SkillForge audit records.

### P4 — Personalized Roadmap & Resources

**Objective**: Automatically generate custom, step-by-step learning roadmaps with prerequisite dependencies, effort estimations, hands-on project briefs, and curated learning resources matched to prioritized gaps.

### P5 — GitHub Skill Verification Loop

**Objective**: Close the loop on skill acquisition by monitoring candidate repositories for completed project milestones, automatically verifying code evidence, and elevating gap classifications from `MISSING`/`PARTIAL` to `STRONG`.

---

## 9. AI Architecture & Guardrails

SkillForge AI enforces a strict architectural boundary between deterministic logic and language model reasoning.

### 9.1 Core Separation of Concerns

```text
┌─────────────────────────────────────────────────────────────┐
│                     DETERMINISTIC CORE                      │
│  (Source of Truth — Python / PostgreSQL / Mathematical Formulas)│
│                                                             │
│  • Candidate Skill Evidence     • Industry Demand Scores    │
│  • GitHub Demonstrated Scores   • YoY Market Growth Signals │
│  • Gap Status (STRONG/PARTIAL)  • Priority Scores & Tiers   │
│  • Evidence Audit Linkages      • Data Isolation Boundaries │
└──────────────────────────────┬──────────────────────────────┘
                               │ Structured, Verified Context
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                          LLM LAYER                          │
│          (Reasoning & Interface — Local Qwen 3 8B)          │
│                                                             │
│  • Evidence Explanations        • Natural-Language Queries  │
│  • Contextual Gap Summaries     • Career Readiness Coaching │
│  • Roadmap Descriptions         • Resource Rationalization  │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Guardrails

1. **The LLM does not replace the deterministic intelligence engine. It reasons over verified SkillForge evidence and market signals.**
2. **The LLM must not invent evidence or override deterministic results.**
3. The LLM is prohibited from independently assigning skill presence, gap status, priority scores, or market demand figures.
4. All explanations generated by the LLM must cite specific underlying database records (e.g., repository path, manifest snippet, market frequency).
5. If underlying evidence is absent, the LLM must explicitly report that no evidence exists rather than hallucinating candidate capabilities.

---

## 10. Product Principles

### Evidence over claims
A resume claim is a declaration of intent; only verified code artifacts and project implementations demonstrate technical capability.

### Data over LLM opinion
Industry demand, skill gaps, and priority rankings must be derived from verifiable structured market data and mathematical models, never subjective LLM generation.

### Explainability
Every classification, priority tier, and recommendation must provide an inspectable audit trail linking candidate evidence to market signals.

### Dynamic demand
Market requirements evolve continuously. Industry demand data must be refreshable and track data freshness rather than relying on static assumptions.

### Personalized learning
Learning pathways must meet the learner where they are, acknowledging demonstrated strengths and systematically closing prioritized gaps.

### Build to prove
True learning is demonstrated by building. Practical projects committed to source control serve as verifiable proof of acquired competence.

---

## 11. Success Criteria

### 11.1 v1.0.0 MVP Success Criteria (Delivered)

1. **Resume Processing**: Successfully uploads, validates, extracts text/sections, and normalizes technical skills from PDF and DOCX formats.
2. **GitHub Evidence Detection**: Connects user handles, excludes forks, parses manifests/Dockerfiles/CI configurations, and generates `ProjectEvidence` records.
3. **Multi-Repository Aggregation**: Bounded noisy-OR aggregation computes repository-level maximums and combined confidence without score inflation.
4. **Candidate Isolation**: Strict context separation guarantees authenticated and anonymous sessions cannot access unauthorized resumes or repositories.
5. **Demand Scoring**: Returns role-specific demand percentages, YoY growth trends, and freshness timestamps from structured datasets.
6. **Deterministic Skill Gaps**: Classifies all demanded skills into `STRONG`, `PARTIAL`, and `MISSING` based on validated code demonstration.
7. **Deterministic Prioritization**: Computes normalized priority scores and assigns `HIGH`, `MEDIUM`, and `LOW` tiers following canonical mathematical weights.
8. **Auditable Evidence Chain**: Evidence API returns comprehensive audit traces connecting resume snippets, GitHub code matches, and market data.
9. **Candidate Readiness Gating**: Prevents downstream analysis execution when required candidate inputs are missing or invalid.
10. **Integrated Client Dashboard**: Interactive frontend delivers visibility into market intelligence, repository evidence, and gap audits.

### 11.2 Product Evolution Success Criteria (Post-MVP)

1. **Refreshed Industry Demand (P1)**: Ingestion pipeline periodically updates role-specific skill demand from live job market signals while maintaining data provenance.
2. **Local AI Reasoning (P2)**: Local Qwen 3 8B model successfully extracts unstructured insights and explains deterministic results with zero third-party data egress.
3. **Evidence-Grounded Career Assistant (P3)**: Conversational assistant answers candidate career questions with 100% fidelity to verified database records.
4. **Personalized Roadmaps (P4)**: Dynamic roadmap generation sequences prerequisites and learning objectives tailored to individual gap severity.
5. **Resource Recommendations (P4)**: Recommendations link candidates to high-quality learning resources matching their skill gaps.
6. **GitHub Verification Loop (P5)**: Automated rescan verifies newly committed project artifacts, directly elevating demonstrated scores and resolving active skill gaps.

---

## 12. Core Differentiator

SkillForge AI is not a generic career chatbot or a superficial resume keyword scanner.

Its core intelligence is rooted in a deterministic pipeline:

```text
Resume Evidence
      +
GitHub Evidence
      +
Industry Market Data
      ↓
Deterministic Skill Intelligence
      ↓
Skill Gap
      ↓
Priority
      ↓
Evidence-backed Career Guidance
```

The deterministic engine serves as the absolute source of truth. The LLM layer operates as an interpretive and conversational partner—explaining verified outcomes, contextualizing trade-offs, and guiding learners without ever compromising empirical data integrity.