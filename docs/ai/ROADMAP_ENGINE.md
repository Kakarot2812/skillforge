# SkillForge AI — Career Roadmap Engine

## 1. Purpose & Core Philosophy

The Career Roadmap Engine is a planned post-MVP intelligence component designed to transform prioritized skill gaps into structured, actionable, and personalized learning trajectories.

### Core Philosophy

The roadmap is derived strictly from **empirically verified skill gaps**, rather than generic or subjective career advice:

```text
Candidate Evidence (Resume Claims + GitHub Demonstrated)
       +
Industry Demand (Demand Score + Growth Rate)
       ↓
Skill Gap Classification (STRONG / PARTIAL / MISSING)
       ↓
Deterministic Priority Engine (HIGH / MEDIUM / LOW)
       ↓
Personalized Roadmap (Planned P4)
       ↓
Learning + Project Actions
       ↓
GitHub Verification (Planned P5)
       ↓
Updated Candidate Evidence
```

### Distinction of Responsibility
- **v1.0.0 MVP**: Determines **what** the candidate is missing and **which** gaps should be prioritized based on market demand and verified code evidence.
- **Future Roadmap Engine (P4)**: Determines **how** the candidate should close those gaps through sequenced milestones, curated learning resources, and hands-on project implementations.

---

## 2. Implementation Status & Boundaries

### 2.1 Frozen v1.0.0 MVP Boundary
> [!IMPORTANT]
> **A career roadmap generation engine is NOT implemented in the frozen v1.0.0 MVP release.**
> The frozen v1.0.0 MVP focuses authoritatively on skill gap identification and deterministic priority scoring. All roadmap generation, milestone sequencing, and dynamic replanning belong to post-MVP development.

### 2.2 Post-MVP Checkpoint P4 Implementation (Active)
Checkpoint P4 implements the complete, deterministic **Personalized Roadmap + Resources** engine on the `post-mvp-foundation` branch:
- **Explicit Prerequisite DAG**: `skill_dependencies` table supporting `HARD` (blocking) and `RECOMMENDED` (non-blocking) dependencies.
- **Deterministic Topological Sequencing**: Kahn's algorithm with deterministic tie-breaking (`priority_score DESC, demand_score DESC, growth_rate DESC, slug ASC`).
- **Transitive Prerequisite Scoring**: Transitive unfulfilled prerequisites are dynamically added with `priority_score = None` and `priority_level = None` (zero score fabrication; deterministic prerequisite topology takes precedence).
- **Approved Resource Catalog**: `approved_resources` and `approved_projects` tables serve as the sole curated authority. Arbitrary web scraping and hallucinated LLM URLs are strictly prohibited.
- **Candidate Ownership & Isolation**: Persisted roadmaps require an authenticated `user_id` to prevent IDOR vulnerabilities. Anonymous candidates execute purely in-memory (`persisted=False`).
- **Milestone Status Lifecycle**: Milestones strictly initialize to `NOT_STARTED`. `VERIFIED` status is reserved exclusively for P5 GitHub verification.
- **Qwen Independence**: Canonical roadmaps are 100% functional without Qwen or RAG. Optional Qwen explanations operate strictly downstream with `status="EXPLANATORY"`.


---

## 3. Inputs to the Future Roadmap Engine

The planned roadmap engine will operate as a consumer of verified SkillForge intelligence, integrating six primary input dimensions:

```text
┌─────────────────────────────────────────────────────────────┐
│                 CURRENT MVP OUTPUTS (FACTS)                 │
├──────────────────────────┬──────────────────────────────────┤
│ 1. Candidate Evidence    │ • Resume claims (user_claimed_skills)
│                          │ • Demonstrated skills (demonstrated_skills)
│                          │ • Multi-repo confidence scores
│                          │ • Direct repository artifacts    │
├──────────────────────────┼──────────────────────────────────┤
│ 2. Target Job Role       │ • Selected career target (e.g. Backend Eng)
│                          │ • Role-specific skill benchmarks │
├──────────────────────────┼──────────────────────────────────┤
│ 3. Industry Demand       │ • Demand score (demand_score)
│                          │ • YoY growth rate (growth_rate)  │
├──────────────────────────┼──────────────────────────────────┤
│ 4. Skill Gap State       │ • STRONG (Evidence ≥ 0.85)
│                          │ • PARTIAL (Claimed or lower evidence)
│                          │ • MISSING (Neither claimed nor shown) │
├──────────────────────────┼──────────────────────────────────┤
│ 5. Priority Score        │ • Deterministic priority_score
│                          │ • Priority tier (HIGH, MEDIUM, LOW) │
└──────────────────────────┴──────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│          FUTURE PERSONALIZATION CONTEXT (POST-MVP)          │
├──────────────────────────┬──────────────────────────────────┤
│ 6. Candidate Context     │ • Declared weekly study availability
│                          │ • Current seniority & experience
│                          │ • Preferred learning modalities
│                          │ • Completed roadmap milestones    │
└─────────────────────────────────────────────────────────────┘
```

The roadmap engine never recalculates skill gaps or priority scores; it consumes the authoritative outputs established by the deterministic engines.

---

## 4. Planned Roadmap Generation

Planned for Phase 4 (**P4**), roadmap generation will construct an ordered trajectory of milestones targeted specifically at high-priority gaps.

### Conceptual Generation Pipeline
```text
Verified Skill Gaps + Priority Rankings
        ↓
Filter Out Demonstrated Skills (STRONG gaps omitted or set to review)
        ↓
Identify Missing Skills & Incomplete Evidence (PARTIAL & MISSING)
        ↓
Resolve Prerequisite Ordering (Planned Skill Sequencing)
        ↓
Cluster Skills into Thematic Milestones (e.g. Core API → Containers → CI/CD)
        ↓
Attach Curated Learning Resources & Project Rubrics
        ↓
Generate Personalized Action Plan
```

### Conceptual Output Structure
```text
Roadmap
├── Target Role: Backend Engineer
├── Candidate Context: Intermediate, 10 hours/week
├── Analyzed Skill Gaps: Docker (MISSING, HIGH), PostgreSQL (PARTIAL, HIGH)
├── Ordered Milestones:
│   ├── Milestone 1: Relational Data Modeling & Query Optimization
│   │   ├── Target Skills: PostgreSQL, SQL
│   │   ├── Learning Objectives: Indexes, transactions, connection pooling
│   │   ├── Curated Resources: Official documentation, query tuning guide
│   │   ├── Hands-on Project: Implement connection-pooled transactional service
│   │   └── Verification Criteria: SQLAlchemy models, migration files
│   └── Milestone 2: Production Containerization
│       ├── Target Skills: Docker, Docker Compose
│       ├── Learning Objectives: Multi-stage builds, service orchestration
│       ├── Curated Resources: Dockerfile best practices, Compose specification
│       ├── Hands-on Project: Containerize the Milestone 1 API with database
│       └── Verification Criteria: Valid Dockerfile, docker-compose.yml
└── Progress / Verification State: ACTIVE
```
*(Conceptual example illustrating planned milestone relationships — not an active API contract).*

---

## 5. Planned Skill Sequencing

Technical skills often exhibit natural prerequisite hierarchies. In post-MVP development, skill dependencies may be modeled to ensure candidates build foundational competencies before attempting advanced tooling.

### Conceptual Prerequisite Hierarchy
```text
Skill A (Foundational: e.g. Python)
   ↓
Skill B (Framework: e.g. FastAPI)
   ↓
Skill C (Infrastructure: e.g. Docker)
   ↓
Skill D (Orchestration: e.g. Kubernetes)
```

### Potential Dependency Classifications
- **Hard Prerequisite**: Mandatory foundational knowledge. Downstream skills should not be scheduled until this skill is at least partially established.
- **Recommended Prerequisite**: Helpful complementary knowledge that accelerates learning but does not strictly block progression.

### Sequencing Algorithm (Candidate Future Implementation)
Future sequencing will combine:
1. **Prerequisite Constraints**: Ensuring foundational nodes precede dependent nodes.
2. **Deterministic Priority Scores**: When multiple skills have their prerequisites satisfied, scheduling the skill with the highest deterministic priority first.
3. **Candidate Evidence**: Skipping or accelerating skills already supported by existing repository evidence.

> [!NOTE]
> The roadmap engine will **not** invent an independent priority formula. It will directly consume the authoritative priority score generated by the deterministic priority engine.

---

## 6. Planned Milestone Architecture

Milestones divide the candidate's learning journey into manageable, goal-oriented units designed to culminate in observable engineering deliverables.

### Anatomy of a Planned Milestone
Each milestone will bundle six core elements:
1. **Target Skill(s)**: One to three closely related skills selected from prioritized gaps.
2. **Learning Objectives**: Specific, observable competencies the candidate should develop.
3. **Curated Resources**: High-quality documentation and guides mapped to the target skills.
4. **Practical Project**: A realistic engineering challenge applying the target skills.
5. **Verification Criteria**: Explicit file patterns, manifests, and test requirements that can be evaluated via GitHub.
6. **Completion State**: Lifecycle tracking (`NOT_STARTED` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `VERIFIED`).

---

## 7. Planned Learning Resources & Projects

SkillForge emphasizes active, project-based learning over passive tutorial consumption.

### Curated Learning Resources (P4)
Future learning resources will be curated and linked to canonical skills:
- **Official Documentation**: Authoritative framework and language manuals.
- **Architectural Tutorials**: Focused guides explaining design patterns and production deployment.
- **Interactive Labs**: Hands-on sandbox exercises.

Resource recommendations will be retrieved via the planned RAG layer (P3/P4), ensuring materials are grounded, relevant, and authoritative. RAG retrieves resources; it does **not** evaluate candidate proficiency or calculate priority scores.

### Project-Based Milestone Cycle
Every milestone is designed around hands-on software development:
```text
Skill Gap Identified
        ↓
Focused Learning (Docs & Tutorials)
        ↓
Hands-on Project Development
        ↓
Commit & Push to GitHub
        ↓
Automated GitHub Re-analysis (P5)
        ↓
Demonstrated Skill Evidence Elevated
```

Candidates do not merely read about technologies; they implement them in code repositories.

---

## 8. Future GitHub Verification Loop

Scheduled as Phase 5 (**P5**), the GitHub Verification Loop connects project completion directly back to candidate evidence.

### Verification Flow
```text
Recommended Project Specification
        ↓
Candidate Implements Project Locally
        ↓
Candidate Pushes Commits to GitHub
        ↓
GitHub Intelligence Engine Re-analyzes Repository
        ↓
New Artifact Evidence Detected (Manifests, Dockerfiles, CI Workflows)
        ↓
ProjectEvidence Records Created / Updated
        ↓
Demonstrated Skill Score Recomputed (Bounded Noisy-OR)
        ↓
Skill Gap Engine Re-evaluates Gap Status (e.g. PARTIAL → STRONG)
        ↓
Roadmap Milestone Marked VERIFIED
        ↓
Downstream Dependent Milestones Unlocked
```

### Architectural Reuse
The verification loop will **reuse the existing deterministic GitHub Intelligence Engine** (`github_analyzer.py` and `demonstrated_skill_service.py`) rather than introducing a separate, ad-hoc validation tool. This guarantees that evidence evaluated during milestone verification conforms to the exact same standards applied during initial repository onboarding.

---

## 9. Dynamic Re-planning

A career roadmap is an evolving strategy that adapts to candidate progress and industry movement.

### Future Re-planning Triggers
The roadmap engine will recalculate remaining milestones when:
- **Milestone Completed**: A candidate pushes code that verifies a target skill, unlocking downstream milestones.
- **External Evidence Added**: A candidate connects a new repository demonstrating skills outside the active milestone.
- **Market Demand Shifts (P1)**: The continuous market ingestion pipeline updates regional demand scores or growth trajectories.
- **Target Role Changed**: The candidate selects a new target career role.
- **Pacing Adjusted**: The candidate updates their available weekly study commitment.

### Market-Driven Re-planning Pipeline
```text
Real-Time Market Ingestion (P1)
        ↓
Updated Regional Skill Demand & Growth Signals
        ↓
Deterministic Priority Engine Recomputes Priority Scores
        ↓
Roadmap Engine Evaluates Unstarted Milestones
        ↓
Remaining Trajectory Re-ordered to Reflect Current Market Demand
```

---

## 10. Post-MVP Roadmap Alignment

The Career Roadmap Engine aligns directly with the locked post-MVP sequence:

```text
P1: Real-Time Industry Demand
        ↓ (Supplies continuously updated market demand and growth rates)
P2: Local Qwen 3 8B AI Layer
        ↓ (Provides local, private reasoning and explanation capabilities)
P3: Evidence-Grounded Career Chatbot
        ↓ (Enables candidates to discuss gaps and explore learning advice)
P4: Personalized Roadmap + Resources
        ↓ (Generates sequenced milestones, resource links, and project specs)
P5: GitHub Verification Loop
          (Closes the loop by validating completed projects through GitHub)
```

### Phase Responsibilities
- **P1**: Provides fresh, empirical market signals so roadmap priorities stay synchronized with current industry hiring.
- **P2**: Deploys the local open-weight Qwen 3 8B model to generate contextual milestone descriptions and explain prerequisite relationships.
- **P3**: Integrates the RAG retrieval pipeline to retrieve curated tutorials, reference guides, and project rubrics.
- **P4**: Implements the core roadmap engine, dependency graph, milestone data model, and adaptive scheduling.
- **P5**: Automates milestone verification by re-analyzing candidate repositories upon code submission.

---

## 11. AI Boundary & Invariants

To guarantee architectural integrity and prevent hallucination, the roadmap engine operates within strict boundaries:

> **"The LLM never decides what is true. It only reasons over what SkillForge has already verified."**

> **"Deterministic systems decide what is true. AI explains, reasons over, and personalizes verified evidence."**

### Permitted AI Roles
The future AI layer (Qwen 3 8B) may:
- Personalize milestone narrative descriptions to match candidate interests.
- Explain *why* a specific prerequisite or milestone is sequenced before another.
- Summarize documentation chapters and learning objectives.
- Suggest creative variations on recommended project challenges.

### Prohibited AI Roles
The AI layer must **never**:
- Independently decide whether a candidate possesses a skill.
- Alter a skill gap classification (`STRONG`, `PARTIAL`, `MISSING`).
- Fabricate or modify industry demand percentages or growth rates.
- Compute or override the deterministic priority score.
- Mark a milestone as verified without verified repository artifacts.

---

## 12. MVP vs Post-MVP Capability Matrix

| Capability | v1.0.0 MVP (Frozen Baseline) | Post-MVP (Planned Evolution) |
| :--- | :--- | :--- |
| **Resume Evidence Extraction** | Implemented (Regex, parsing, normalization) | Maintained (Roadmap input) |
| **GitHub Evidence Extraction** | Implemented (Manifest & CI inspection) | Maintained (Verification loop input) |
| **Industry Skill Demand** | Implemented (Structured baseline data) | Real-time market ingestion (P1) |
| **Skill Gap Classification** | Implemented (Deterministic rule-based) | Maintained (Roadmap input) |
| **Priority Scoring Engine** | Implemented (Deterministic formula) | Maintained (Roadmap ordering input) |
| **Evidence Audit Trail** | Implemented (Direct repo & file linkages) | Maintained (Milestone verification basis) |
| **Skill Dependency Graph (DAG)**| Not implemented | Planned (P4) |
| **Roadmap Generation** | Not implemented | Planned (P4) |
| **Curated Learning Resources** | Not implemented | Planned (P4) |
| **Project Challenge Specs** | Not implemented | Planned (P4) |
| **Weekly Workload Pacing** | Not implemented | Planned (P4) |
| **Milestone Progress Tracking**| Not implemented | Planned (P4) |
| **Dynamic Re-planning** | Not implemented | Planned (P4) |
| **GitHub Verification Loop** | Not implemented | Planned (P5) |
| **AI Milestone Explanation** | Not implemented | Planned (Local Qwen 3 8B) (P2/P4) |

---

## 13. Architectural Invariants

The Career Roadmap architecture enforces thirteen immutable principles:

1. **MVP Scope Boundary**: The v1.0.0 MVP identifies skill gaps and calculates priority scores; it does not generate, persist, or track roadmaps.
2. **Upstream Dependency**: Roadmap generation strictly consumes deterministic SkillForge intelligence.
3. **Single Priority Authority**: The roadmap engine consumes existing deterministic priority scores and never creates a competing priority formula.
4. **Dependency Graph is Post-MVP**: Skill prerequisite modeling belongs to Phase 4.
5. **Learning Resources are Post-MVP**: Curated educational materials belong to Phase 4.
6. **Project Challenges are Post-MVP**: Practical engineering challenge specifications belong to Phase 4.
7. **Verification Loop is Post-MVP**: Automated GitHub milestone verification belongs to Phase 5.
8. **Real-Time Adaptation Depends on P1**: Roadmap replanning driven by market shifts depends on the P1 real-time demand engine.
9. **RAG Retrieves Context**: RAG discovers resources and context; it does not compute demand or classify gaps.
10. **Grounded AI Generation**: All AI explanations and project suggestions must be grounded in verified SkillForge facts.
11. **Candidate Evidence Isolation**: Personalization and evidence remain strictly scoped to the active candidate.
12. **Observable Usage Over Mastery**: GitHub evidence demonstrates observable technical usage, not engineering mastery.
13. **Verification Reuse**: Milestone verification reuses the authoritative GitHub Intelligence Engine.
