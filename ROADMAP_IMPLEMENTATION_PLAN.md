# SkillForge AI — Skill Roadmaps Implementation Plan

## 1. Architecture & Design Principles

The Skill Roadmaps feature is designed as an additive, non-breaking extension of the existing SkillForge AI MVP.
It bridges the gap between deterministic skill-gap identification and structured, actionable learning paths:

```text
Resume / GitHub Evidence
       │
       ▼
Skill Profile (Taxonomy Normalized)
       │
       ▼
Industry Market Demand (Canonical Benchmark)
       │
       ▼
Deterministic Skill Gap Classification (STRONG, PARTIAL, MISSING)
       │
       ▼
Gap Prioritization (HIGH, MEDIUM, LOW)
       │
       ▼
[NEW] Personalized Skill Roadmap (Curated Stages + Prerequisite DAG + Learning Resources + User Progress)
```

### Core Architecture Rules:
1. **Source of Truth Preservation**: No changes to `SkillGap`, `IndustrySkillDemand`, or `JobRole` business logic. Existing priority scores and levels computed by `skill_gap_service` are consumed directly.
2. **Deterministic & LLM-Free**: All ordering, prerequisite topological validation, priority matching, and progress transitions are strictly deterministic. No LLM calls are used for classification or ordering.
3. **Canonical Taxonomy Alignment**: Roadmap skills link directly to `skills.id` when canonical matches exist. Additional skills not yet in the baseline taxonomy have nullable `canonical_skill_id` without polluting the existing taxonomy.
4. **Market Data Boundary**: Canonical roles (Backend, Full Stack, Frontend, Cloud/DevOps, AI/ML) integrate with verified market demand and candidate skill gap records. Additional domains (Android, Data Engineer, Data Scientist, Cybersecurity, QA, iOS, UI/UX) operate on curated roadmaps with explicit `has_market_data = false`, preventing hallucinated demand statistics.
5. **Multi-Platform Neutrality**: Clean JSON APIs support Next.js and future Kotlin Android clients.
6. **Cross-User Data Isolation**: User roadmap progress (`NOT_STARTED`, `LEARNING`, `DONE`, `SKIPPED`) is persisted in PostgreSQL with strict foreign key constraints and user isolation via `X-User-Id` / `user_id`.

---

## 2. Database Schema Changes (Alembic Migration 0012)

Six new tables will be added in a single migration `0012_skill_roadmaps.py`:

```
┌──────────────────┐       1:N      ┌──────────────────┐       1:N      ┌──────────────────┐
│     roadmaps     │───────────────►│  roadmap_stages  │───────────────►│  roadmap_skills  │
└──────────────────┘                └──────────────────┘                └──────────────────┘
                                                                           │  ▲        │  ▲
                                                                  Prereq   │  │        │  │
                                                                   1:N     ▼  │        │  │
                                                               ┌──────────────────────┐│  │
                                                               │ roadmap_prerequisites││  │
                                                               └──────────────────────┘│  │
                                                                                       │  │
                                            1:N ┌────────────────────┐                 │  │ 1:N
                                                │ learning_resources │◄────────────────┘  │
                                                └────────────────────┘                    │
                                            1:N ┌───────────────────────┐                 │
                                                │ user_roadmap_progress │◄────────────────┘
                                                └───────────────────────┘
```

1. **`roadmaps`**:
   - `id`: UUID, Primary Key
   - `role_id`: UUID, Foreign Key (`job_roles.id`, nullable, ondelete='SET NULL')
   - `slug`: String(128), Unique, Indexed
   - `title`: String(128), Not Null
   - `domain`: String(128), Not Null, Indexed
   - `category`: String(64), Not Null
   - `description`: Text, Not Null
   - `version`: String(32), Default "v1.0"
   - `last_reviewed`: DateTime(timezone=True), Server Default now()
   - `has_market_data`: Boolean, Default False
   - `created_at`: DateTime(timezone=True), Server Default now()
   - `updated_at`: DateTime(timezone=True), Server Default now()

2. **`roadmap_stages`**:
   - `id`: UUID, Primary Key
   - `roadmap_id`: UUID, Foreign Key (`roadmaps.id`, ondelete='CASCADE'), Indexed
   - `name`: String(128), Not Null
   - `description`: Text, Nullable
   - `stage_order`: Integer, Not Null
   - `created_at`: DateTime(timezone=True), Server Default now()
   - Unique constraint: `(roadmap_id, stage_order)`

3. **`roadmap_skills`**:
   - `id`: UUID, Primary Key
   - `stage_id`: UUID, Foreign Key (`roadmap_stages.id`, ondelete='CASCADE'), Indexed
   - `roadmap_id`: UUID, Foreign Key (`roadmaps.id`, ondelete='CASCADE'), Indexed
   - `canonical_skill_id`: UUID, Foreign Key (`skills.id`, ondelete='SET NULL'), Nullable, Indexed
   - `name`: String(128), Not Null
   - `slug`: String(128), Not Null, Indexed
   - `description`: Text, Not Null
   - `difficulty`: String(32), Not Null (Check constraint: `BEGINNER`, `INTERMEDIATE`, `ADVANCED`)
   - `skill_order`: Integer, Not Null
   - `key_topics`: JSONB, Not Null, Default `[]`
   - `practice_project`: Text, Nullable
   - `role_relevance`: Text, Nullable ("WHY THIS MATTERS")
   - `created_at`: DateTime(timezone=True), Server Default now()
   - Unique constraint: `(stage_id, skill_order)`

4. **`roadmap_prerequisites`**:
   - `id`: UUID, Primary Key
   - `roadmap_skill_id`: UUID, Foreign Key (`roadmap_skills.id`, ondelete='CASCADE'), Indexed
   - `prerequisite_skill_id`: UUID, Foreign Key (`roadmap_skills.id`, ondelete='CASCADE'), Indexed
   - `created_at`: DateTime(timezone=True), Server Default now()
   - Unique constraint: `(roadmap_skill_id, prerequisite_skill_id)`

5. **`learning_resources`**:
   - `id`: UUID, Primary Key
   - `roadmap_skill_id`: UUID, Foreign Key (`roadmap_skills.id`, ondelete='CASCADE'), Indexed
   - `resource_type`: String(32), Not Null (Check constraint: `DOCUMENTATION`, `YOUTUBE`)
   - `title`: String(255), Not Null
   - `url`: String(512), Not Null
   - `description`: Text, Not Null
   - `created_at`: DateTime(timezone=True), Server Default now()

6. **`user_roadmap_progress`**:
   - `id`: UUID, Primary Key
   - `user_id`: UUID, Foreign Key (`users.id`, ondelete='CASCADE'), Indexed
   - `roadmap_skill_id`: UUID, Foreign Key (`roadmap_skills.id`, ondelete='CASCADE'), Indexed
   - `status`: String(32), Not Null, Default 'NOT_STARTED' (Check constraint: `NOT_STARTED`, `LEARNING`, `DONE`, `SKIPPED`)
   - `created_at`: DateTime(timezone=True), Server Default now()
   - `updated_at`: DateTime(timezone=True), Server Default now()
   - Unique constraint: `(user_id, roadmap_skill_id)`

---

## 3. Supported Roadmap Domains (12 Domains)

### Canonical MVP Roles (Integrated with Market Demand & Skill Gaps)
1. **Backend Engineer** (`backend-engineer`): Foundations (Python/DSA/Linux/Git) → Web APIs (REST/FastAPI/Auth) → Databases (SQL/Postgres/SQLAlchemy/Redis) → System Design (Caching/Queues/Microservices) → Deployment (Docker/CI-CD/Cloud) → Advanced (Observability/Security/Events).
2. **Full Stack Engineer** (`full-stack-engineer`): Core Web (HTML/CSS/JS) → Modern Frontend (React/TypeScript/Next.js/Tailwind) → Backend & APIs (Node.js/REST/FastAPI) → Data Storage (PostgreSQL/Redis) → DevOps & Production (Docker/CI-CD/Cloud).
3. **Frontend Engineer** (`frontend-engineer`): Web Foundations (HTML/CSS/JS) → Advanced UI & Typing (TypeScript/Tailwind/CSS Architecture) → Component Frameworks (React/State Management) → Full-Stack Frontend (Next.js/SSR/Performance) → Testing & Accessibility (Accessibility/Testing/Web Vitals).
4. **Cloud / DevOps Engineer** (`cloud-devops-engineer`): Core Systems (Linux/Git/Networking) → Containerization (Docker/Docker Compose) → Cloud Platforms (AWS Fundamentals/IAM) → CI/CD & Automation (GitHub Actions/Automation) → Orchestration & IaC (Kubernetes/Terraform) → Observability & Reliability.
5. **AI / ML Engineer** (`ai-ml-engineer`): Math & Programming (Python/NumPy/Pandas/Math) → Machine Learning Foundations (Scikit-Learn/Supervised & Unsupervised ML) → Deep Learning (PyTorch/Neural Networks) → Vector Search & Embeddings (pgvector/Embeddings/RAG) → Deployment & MLOps (FastAPI/Docker/Model Serving).

### Additional Curated Domains (Clearly Identified Catalog, Market Data Disclaimed)
6. **Android Developer** (`android-developer`): Kotlin & OO/FP → Modern Android UI (Jetpack Compose) → Architecture & State (Android SDK, ViewModel, Navigation) → Data & Networking (Room, Coroutines, Retrofit/HTTP) → Quality & Deployment (Unit Testing, Gradle, Play Store).
7. **Data Engineer** (`data-engineer`): Programming & SQL (Python, SQL, Linux) → Data Modeling & Warehousing (PostgreSQL, Data Warehouses, OLAP) → Distributed Computing (PySpark, Apache Spark) → Pipeline Orchestration (Airflow, ETL/ELT) → Streaming & Serving (Kafka, Data Governance).
8. **Data Scientist** (`data-scientist`): Scientific Python & Math (Python, NumPy, Linear Algebra) → Data Analysis & Viz (Pandas, Matplotlib, Seaborn) → Classical ML (Scikit-Learn, Feature Engineering) → Advanced ML & Deep Learning (PyTorch, Model Evaluation) → Production Data Science (MLflow, Streamlit, API Delivery).
9. **Cybersecurity Engineer** (`cybersecurity-engineer`): Fundamentals (Networking, Protocols, Linux, Cryptography) → App & Web Security (OWASP Top 10, Auth/OAuth, Secure Coding) → Defense & SIEM (Log Analysis, Monitoring, Incident Response) → Cloud & Infra Security (Cloud IAM, Hardening, Compliance) → Offensive & Threat Analysis (Threat Modeling, Vulnerability Assessment).
10. **QA / Test Automation Engineer** (`qa-automation-engineer`): Quality Assurance Foundations (Testing Principles, Test Planning, Bug Lifecycle) → API Testing (Postman, REST API Validation) → End-to-End Web Automation (Playwright, Selenium, Test Runners) → CI/CD Integration (GitHub Actions Test Pipelines, Reporting) → Performance & Security Testing (Load Testing, Accessibility Audits).
11. **iOS Developer** (`ios-developer`): Swift Fundamentals (Swift Syntax, OOP & Protocol-Oriented) → Declarative UI (SwiftUI, Layouts, Navigation) → Architecture & Concurrency (Async/Await, MVVM, Architecture) → Data & Networking (URLSession, SwiftData/CoreData) → Polishing & App Store (XCTest, Instruments, App Store Guidelines).
12. **UI/UX Engineer / Product Designer** (`ui-ux-engineer`): User Experience Principles (Design Thinking, Information Architecture, Wireframing) → UI Prototyping (Figma, Design Systems, Typography & Color) → Design Systems & Tokens (Component Specs, Accessibility WCAG) → Frontend Implementation Bridge (HTML/CSS, Responsive Layouts, Micro-interactions) → Usability Testing & Iteration (User Testing, Heatmaps, Analytics).

All educational resources link to **authoritative, official documentation** (e.g. `docs.python.org`, `fastapi.tiangolo.com`, `react.dev`, `nextjs.org`, `developer.android.com`, `docs.docker.com`, `kubernetes.io`, `developer.apple.com`, etc.) and reputable YouTube channels (e.g., freeCodeCamp, Traversy Media, Fireship, Android Developers, Kevin Powell, Corey Schafer, etc.). No hallucinated links.

---

## 4. Backend API Endpoints

Mounted under `/api/v1/roadmaps` and `/api/v1/users/me/roadmap-progress`:

1. `GET /api/v1/roadmaps`:
   - Returns list of all roadmaps with metadata: `id`, `slug`, `title`, `domain`, `category`, `has_market_data`, `total_stages`, `total_skills`.
2. `GET /api/v1/roadmaps/{roadmap_id}`:
   - Returns full roadmap with stages, skills, prerequisites, and learning resources.
   - Query params: `user_id`, `ordering` ('curated' | 'recommended'), `x_user_id` header.
   - If canonical role: seamlessly fuses candidate `SkillGap` and `PrioritizedGap` data (status `STRONG`/`PARTIAL`/`MISSING`, priority `HIGH`/`MEDIUM`/`LOW`).
   - If `ordering=recommended`: sorts topologically respecting all prerequisites while bubbling HIGH and MEDIUM priority missing/partial skills to the earliest possible sequence.
3. `GET /api/v1/roadmaps/{roadmap_id}/skills/{skill_id}`:
   - Returns detailed skill metadata: description, difficulty, key topics, prerequisites, learning resources, practice project, role relevance ("Why this matters"), and current user progress.
4. `GET /api/v1/users/me/roadmap-progress`:
   - Returns user's roadmap progress map (`roadmap_skill_id` -> `status`, `updated_at`).
5. `PUT /api/v1/users/me/roadmap-progress/{skill_id}`:
   - Updates user's progress for a roadmap skill (`status`: `NOT_STARTED`, `LEARNING`, `DONE`, `SKIPPED`).
   - Enforces user ownership and cross-user isolation.

---

## 5. Frontend Architecture

### New Components (`frontend/src/components/roadmap/`):
1. `SkillRoadmap.tsx`: Main container managing domain selection, viewing mode ('Recommended' vs 'Full Roadmap'), summary metrics, and detail panel state.
2. `RoadmapRoleSelector.tsx`: Horizontal selector for the 12 roadmap domains, distinguishing canonical roles (with verified market badge) from curated catalog tracks.
3. `RoadmapProgress.tsx`: High-level metrics bar (completed skills, in-progress skills, total skills, completion percentage, readiness tier).
4. `RoadmapStage.tsx`: Accordion/card container rendering a roadmap stage, its description, stage-level progress bar, and list of skill cards.
5. `RoadmapSkillCard.tsx`: Interactive skill card/button rendering:
   - Skill name, difficulty badge
   - User state badge (`NOT_STARTED`, `LEARNING`, `DONE`, `SKIPPED`)
   - If canonical role: SkillGap badge (`STRONG` ✓, `PARTIAL` →, `MISSING` ✕) and Priority indicator (`🔥 High Priority`, `Medium`, etc.)
   - Click triggers opening `SkillDetailPanel`.
6. `SkillDetailPanel.tsx`: Right-side slide-over drawer showing:
   - Skill title, domain, stage, difficulty
   - Concise 2-4 line description
   - Key topics bullet points
   - Prerequisites list with status indicators
   - Learning Resources with safe "Open" external action:
     - Official Documentation (Title, description, URL)
     - Reputable YouTube Video/Course (Title, description, URL)
   - Optional Practice Project / Exercise
   - "Why This Matters" (Role relevance)
   - User state toggle buttons: `[Not Started] [Learning] [Done] [Skip]` with immediate visual feedback and persistent backend sync.

### Navigation Integration:
- In `frontend/src/app/page.tsx`:
  - Add navigation tabs in top header or tab bar: `[Home] [Analyze] [Roadmap] [Dashboard]`.
  - Selecting "Roadmap" seamlessly displays the `SkillRoadmap` module with deep link/tab persistence.

### API Client (`frontend/src/lib/api.ts`):
- Add TypeScript interfaces: `RoadmapSummary`, `RoadmapDetail`, `RoadmapStageItem`, `RoadmapSkillItem`, `LearningResourceItem`, `RoadmapProgressUpdate`.
- Add client methods: `fetchRoadmaps`, `fetchRoadmapDetail`, `fetchRoadmapSkill`, `fetchUserRoadmapProgress`, `updateRoadmapSkillProgress`.

---

## 6. Verification & Testing Strategy

### Automated Tests (`backend/tests/test_roadmaps.py`):
1. `test_list_roadmaps`: Verifies 12 domains are returned, canonical roles have `has_market_data=True` and others `False`.
2. `test_get_roadmap_detail`: Verifies stages, skills, resources, and prerequisites structure.
3. `test_invalid_roadmap_id`: Verifies 404 for nonexistent UUID and 422 for malformed UUID.
4. `test_prerequisite_graph_integrity`: Verifies no circular prerequisites exist in any of the 12 domains.
5. `test_recommended_ordering_topological_sort`: Verifies that recommended ordering NEVER violates prerequisite order (e.g. Linux precedes Docker, Python precedes FastAPI).
6. `test_recommended_ordering_prioritizes_high_gaps`: Verifies high priority gaps appear earlier in recommended order than low priority skills when prerequisites allow.
7. `test_user_progress_lifecycle`: Tests transition between `NOT_STARTED`, `LEARNING`, `DONE`, `SKIPPED`.
8. `test_invalid_progress_status`: Rejects illegal status strings with 422.
9. `test_cross_user_isolation`: Verifies that User A's progress updates never affect User B.
10. `test_canonical_skill_taxonomy_consistency`: Verifies that canonical skills referenced in roadmaps correspond to existing `skills` records.
11. `test_existing_gap_tests_pass`: Ensures all 20 existing test suites continue to pass without regression.

### Frontend Validation:
- Run `npm run build` to guarantee zero TypeScript or Turbopack compilation errors.
