# SkillForge AI — Feature Specifications

## 1. Feature Overview

SkillForge AI replaces static career advice with dynamic, evidence-based career navigation.

Features are structured into core foundational engines and user-facing modules aligned with the platform's multi-phase architecture:

```text
┌─────────────────────────────────────────────────────────────┐
│                       USER INTERFACE                        │
│   Skill Dashboard  •  Demand Explorer  •  Roadmap View      │
├──────────────────────────────┬──────────────────────────────┤
│      INTELLIGENCE LAYER      │       VERIFICATION LAYER     │
│  Resume Parser  •  GitHub AI │  Project Scanner • CI Checks │
├──────────────────────────────┼──────────────────────────────┤
│        ANALYTICS ENGINE      │         CONTENT LAYER        │
│  Demand Engine  • Gap Score  │  Resource Store  • RAG Chat  │
└──────────────────────────────┴──────────────────────────────┘
```

---

## 2. Core Functional Features

### 2.1 Multi-Format Resume Intelligence (Phase 2)

Extracts structured information from user resumes without requiring strict formatting standards.

- **Supported Formats**: PDF, DOCX, and raw text.
- **Section Segmentation**: Identifies Skills, Experience, Projects, Education, and Certifications.
- **Entity Extraction**: Named Entity Recognition (NER) and contextual LLM extraction for technical tools, libraries, and frameworks.
- **Skill Normalization**: Maps extracted free-form terms (e.g., "Postgres", "PostgreSQL DB", "pg") to canonical skill taxonomy records.
- **Claimed Skill Registry**: Saves extracted skills as *Claimed* with contextual snippet references (e.g., years mentioned, project context).

### 2.2 GitHub Repository Intelligence (Phase 3)

Conducts deep inspection of user codebases via the GitHub API to detect verifiable skill usage.

- **Dependency Manifest Inspection**: Parses configuration files to extract concrete technology adoption:
  - Node/JS/TS: `package.json`, `pnpm-lock.yaml`, `yarn.lock`
  - Python: `requirements.txt`, `Pipfile`, `pyproject.toml`, `setup.py`
  - Java: `pom.xml`, `build.gradle`
  - Go: `go.mod`
  - Rust: `Cargo.toml`
- **Infrastructure & DevOps Detection**: Identifies `Dockerfile`, `docker-compose.yml`, Kubernetes manifests, Terraform configs, and GitHub Actions workflows (`.github/workflows/*.yml`).
- **Codebase Volume & Language Analysis**: Evaluates language distribution and commit frequency across original repositories.
- **Fork & Clone Filtering**: Ignores pure forks to ensure evidence reflects author's original work.
- **Demonstrated Skill Evidence**: Assigns confidence scores based on verifiable file presence, dependency manifests, and commit history.

### 2.3 Evidence-Based Skill Matrix

Unifies claimed and demonstrated signals into a transparent, audit-ready profile.

- **Dual-State Tracking**: Distinguishes between *Claimed* (resume assertion) and *Demonstrated* (codebase proof).
- **Confidence Scoring ($0.0 - 1.0$)**: Weighted calculation factoring in manifest presence, codebase volume, and project recency.
- **Visual Evidence Trail**: Users can click any demonstrated skill to see the exact repository, commit, or manifest file providing proof.

### 2.4 Data-Driven Industry Demand Engine (Phase 4)

Computes empirical market demand from structured job listings rather than static rankings or LLM opinions.

- **Structured Data Pipeline**: Processes job descriptions, role titles, and required qualifications.
- **Demand Metric ($\text{Demand \%}$)**: Percentage of active listings for a target role requiring a specific skill.
- **Trend Detection ($\text{Growth Rate}$)**: Computes month-over-month and quarter-over-quarter percentage changes.
- **Role-Specific Scoping**: Evaluates skills strictly in the context of the selected role (e.g., Python demand for *Backend* vs. *Data Science*).
- **Data Freshness Timestamp**: Displays the exact last updated date for market data to maintain trust.

### 2.5 Multi-Factor Skill Gap & Priority Engine (Phase 5)

Ranks missing or weakly demonstrated skills to optimize learning efficiency.

- **Gap Identification**: Compares user evidence against target role demand profiles.
- **Prioritization Formula**: Combines market demand, growth velocity, evidence deficit, and prerequisite standing.
- **Prerequisite Awareness**: Ensures fundamental prerequisites are prioritized before advanced downstream frameworks.
- **Categorized Gap Severity**:
  - `High Priority`: Core role necessity with substantial market demand and zero evidence.
  - `Medium Priority`: Valuable complementary tool or trending framework.
  - `Low Priority`: Niche or optional skill for entry-level criteria.

### 2.6 Dynamic Career Roadmap Generator (Phase 6)

Builds a structured, sequential pathway from the user's current baseline to career readiness.

- **Directed Acyclic Graph (DAG) Sequencing**: Topologically sorts skills based on prerequisite constraints.
- **Phased Milestones**: Groups skills into logical milestones (e.g., Foundations, Core Backend, Cloud Infrastructure, Capstone Project).
- **Workload Personalization**: Adjusts milestone durations according to user's available hours per week.
- **Adaptive Re-planning**: Dynamically updates remaining milestones as skills are verified or modified.

### 2.7 Curated Learning Resource Directory (Phase 6)

Connects each roadmap skill to vetted, high-quality learning material.

- **Multi-Modal Content**: Links to official documentation, structured courses, hands-on tutorials, and benchmark books.
- **Difficulty Mapping**: Recommends resources matching the user's proficiency (Beginner, Intermediate, Advanced).
- **Time Estimates**: Displays expected completion duration per resource.

### 2.8 Practical Project Challenge System (Phase 6)

Assigns hands-on project briefs designed to close verified skill gaps.

- **Architectural Specifications**: Detailed project goals, required technologies, and API contracts.
- **Evaluation Rubric**: Explicit acceptance criteria required for automated verification.
- **Starter Templates**: Optional boilerplate repositories to accelerate setup.

### 2.9 Automated GitHub Verification Loop (Phase 8)

Closes the feedback loop by verifying completed projects directly in GitHub.

- **Repository Webhook / On-Demand Sync**: Scans the submitted repository upon user request.
- **Criteria Verification**: Confirms target dependencies, file structures, and implementation tests exist.
- **Automatic Status Elevation**: Promotes skill from *Gap* to *Demonstrated* upon successful verification.
- **Roadmap Advancement**: Unlocks subsequent phases and updates user readiness score.

### 2.10 Contextual AI Assistant (Phase 7)

Interactive career copilot providing grounded assistance.

- **RAG-Backed Grounding**: Retrieves accurate context from official documentation, project guides, and market reports.
- **Strict Boundary**: The assistant explains and contextualizes system-calculated scores; it **never** invents or modifies numerical demand percentages.
- **Capabilities**: Explains architectural concepts, reviews code snippets, clarifies project briefs, and guides debugging.

### 2.11 SkillForge Analytics Dashboard (Phase 9)

Central command center for tracking skill progression and industry standing.

- **Skill Radar Chart**: Visual representation of demonstrated versus target competencies.
- **Demand Matrix**: Interactive table of high-demand skills for the selected career track.
- **Gap Breakdown View**: Color-coded severity breakdown of missing skills.
- **Milestone Progress Tracker**: Visual timeline showing completed, active, and upcoming roadmap goals.

---

## 3. Non-Functional Requirements

### 3.1 Performance
- **Resume Parsing**: Completed in $\le 5$ seconds.
- **GitHub Repo Scan**: Initial metadata analysis in $\le 10$ seconds for up to 20 repositories.
- **Roadmap Generation**: Graph generation and resource association in $\le 3$ seconds.
- **API Response Times**: Standard query endpoints $\le 200\text{ ms}$.

### 3.2 Security & Data Privacy
- **Stateless Analysis Option**: Users can opt out of permanent resume storage.
- **GitHub Permissions**: Read-only access requested strictly for public metadata and repository content.
- **No Secret Leakage**: No API keys, credentials, or personal tokens exposed in responses or logs.

### 3.3 Reliability & Scalability
- **Deterministic Analytics**: Gap and demand calculations produce consistent results given identical inputs.
- **Modular Services**: Decoupled service architecture allows independent scaling of parser, GitHub scanner, and demand engine.
