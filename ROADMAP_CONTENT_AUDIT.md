# SkillForge AI — Complete Roadmap Content Audit

This document presents an exhaustive audit of all 12 roadmap domains currently implemented in SkillForge AI.
Each domain is evaluated for foundational completeness, modern technology relevance, architectural soundness, testing, security, deployment, and practical learning progression.

---

## 1. Android Development (`android-developer`)

- **Domain**: Android Development
- **Current Coverage**:
  - Total Stages: 3
  - Total Skills: 6
  - Stage 1 — Kotlin Programming Fundamentals (Kotlin, Android Studio & SDK)
  - Stage 2 — Declarative UI with Jetpack Compose (Jetpack Compose)
  - Stage 3 — Architecture, Networking & Persistence (Kotlin Coroutines & Flow, Retrofit & REST Networking, Room Database)
- **Missing Skills**:
  - *Foundations*: Decomposition of Kotlin into language foundations (null safety, collections, generics, OOP/FP) vs. Android Studio/SDK tooling.
  - *UI & Design*: Jetpack Compose is treated as a single monolith. Missing: Compose Fundamentals & State, Recomposition, Modifiers, Material 3 Design System, Themes, Typography, Animations, Adaptive Layouts.
  - *Architecture & State*: ViewModel, UI State modeling, StateFlow / SharedFlow, Repository pattern, Clean Architecture, Unidirectional Data Flow (UDF).
  - *Dependency Injection*: Dagger and Hilt are completely absent. Modern enterprise Android development mandates Hilt for `@Inject`, modules, components, scopes, and test fakes.
  - *Navigation*: Navigation Compose, type-safe routes, backstack management, deep links, argument passing.
  - *Local Data*: DataStore (Jetpack's modern replacement for SharedPreferences), Room migrations, caching strategies, offline-first architecture.
  - *Background Tasks*: WorkManager, foreground services, notifications.
  - *Testing*: Unit testing (JUnit, MockK, Turbine), ViewModel testing, Coroutine testing (`StandardTestDispatcher`), Compose UI testing (`createComposeRule`), integration tests.
  - *Security*: Android Keystore, EncryptedSharedPreferences, Network Security Config, certificate pinning, biometric prompt, API key safety.
  - *Build & Deployment*: Gradle build variants, ProGuard/R8 shrinking, release signing, Google Play Store publishing guidelines, CI/CD with GitHub Actions.
  - *Performance & Profiling*: Macrobenchmark, Android Studio Profiler (CPU/Memory/Network), leak detection.
- **Outdated/Questionable Skills**:
  - Merging Android Studio and SDK into a single generic entry without lifecycle, manifests, and Gradle fundamentals.
  - Lumping all Compose concepts (layouts, state, animations, theming) into one single skill card.
- **Proposed Additions**:
  1. *Kotlin Programming Fundamentals* (Variables, null safety, OOP, lambdas, collections)
  2. *Android SDK & Studio Fundamentals* (Project structure, AndroidManifest, Activities, lifecycle, Intents, resources)
  3. *Kotlin Coroutines & Structured Concurrency* (Dispatchers, suspend functions, Flow, StateFlow, SharedFlow)
  4. *Jetpack Compose Fundamentals & State* (Composables, state hoisting, recomposition, modifiers, remember, derivedStateOf)
  5. *Material 3 & Design Systems* (Dynamic color, typography, themes, dark mode, animations, adaptive window sizes)
  6. *Navigation Compose* (NavHost, type-safe arguments, nested graphs, deep linking)
  7. *Android Architecture & ViewModel* (MVVM, UI State, Repository pattern, Clean Architecture, UDF)
  8. *Dependency Injection with Hilt* (Dagger/Hilt, `@AndroidEntryPoint`, `@Inject`, Hilt modules, ViewModel injection, testing with Hilt)
  9. *Networking with Retrofit & OkHttp* (REST APIs, Moshi/Kotlinx Serialization, OkHttp interceptors, error handling)
  10. *Local Persistence with Room & DataStore* (Entities, DAOs, relations, migrations, Preferences/Proto DataStore, offline-first)
  11. *Background Processing with WorkManager* (Periodic work, constraints, expedited jobs, notifications)
  12. *Android Testing & Quality Assurance* (JUnit 5, MockK, Turbine, Compose UI tests, ViewModel tests)
  13. *Android Security & Storage Hardening* (Android Keystore, EncryptedSharedPreferences, Network Security Config)
  14. *Gradle Build Optimization & Play Store Release* (Build variants, ProGuard/R8, app signing, AAB, Play Store publishing)
- **Ordering Changes**:
  - Sequence: Kotlin Fundamentals → Android SDK & Studio → Coroutines & Flow → Compose Fundamentals → Material 3 → Navigation Compose → Architecture & ViewModel → Dependency Injection (Hilt) → Retrofit & OkHttp → Room & DataStore → WorkManager → Testing → Security → Gradle & Release.
- **Rationale**:
  Android cannot be taught as 6 surface-level cards. A professional Android developer must be proficient in declarative UI (Compose + Material 3), reactive architecture (ViewModel + StateFlow + UDF), robust DI (Hilt), offline-first data (Room + DataStore + Retrofit), and test-driven development.

---

## 2. Backend Engineering (`backend-engineer`)

- **Domain**: Backend Engineering
- **Current Coverage**:
  - Total Stages: 5
  - Total Skills: 12
  - Stage 1 — Foundations: Python, Git, Linux Fundamentals
  - Stage 2 — Backend & API Engineering: REST APIs, FastAPI, Pytest
  - Stage 3 — Databases & Persistence: SQL, PostgreSQL, Redis
  - Stage 4 — System Design & Distributed Architecture: System Design Fundamentals
  - Stage 5 — Containerization & DevOps: Docker, AWS
- **Missing Skills**:
  - *Authentication & Authorization*: OAuth2, JWT, password hashing (Argon2/bcrypt), RBAC, session management.
  - *Asynchronous Queues & Message Brokers*: Celery, Redis Streams / RabbitMQ, background workers, event-driven patterns.
  - *Database Migrations & Advanced ORM*: SQLAlchemy 2.0, Alembic, connection pooling, indexing strategies, handling N+1 queries.
  - *API Security & Defense*: Rate limiting, CORS, CSRF, SQL injection defense, OWASP API Top 10, secrets management.
  - *Observability & Telemetry*: Structured logging, Prometheus metrics, Grafana dashboards, OpenTelemetry distributed tracing.
  - *CI/CD Automation*: GitHub Actions automated testing and deployment pipelines.
- **Outdated/Questionable Skills**:
  - Jumping straight from single-instance Docker/AWS to System Design without covering message queues, authentication, or observability.
- **Proposed Additions**:
  1. *Authentication & Authorization (JWT, OAuth2, RBAC)*
  2. *Database Migrations & ORM with SQLAlchemy & Alembic*
  3. *Asynchronous Task Queues & Message Brokers (Celery & Redis)*
  4. *API Security & OWASP Top 10*
  5. *Backend Observability & Monitoring (Prometheus, Grafana, Structured Logging)*
  6. *CI/CD Pipelines with GitHub Actions*
- **Ordering Changes**:
  - Foundations (Python, Git, Linux) → APIs (REST, FastAPI) → Persistence (SQL, Postgres, SQLAlchemy/Alembic) → Auth & Security (JWT, OAuth2, API Security) → Caching & Queues (Redis, Celery) → Testing (Pytest) → Containers & CI/CD (Docker, GitHub Actions) → Architecture & Cloud (System Design, AWS, Observability).
- **Rationale**:
  Production backends require secure authentication, background job offloading, schema migrations, and active observability. Adding these provides a real-world enterprise backend curriculum.

---

## 3. Frontend Engineering (`frontend-engineer`)

- **Domain**: Frontend Engineering
- **Current Coverage**:
  - Total Stages: 2
  - Total Skills: 7
  - Stage 1 — Core Web Technologies: HTML, CSS, JavaScript
  - Stage 2 — Component Frameworks & UI Architecture: TypeScript, Tailwind CSS, React, Next.js
- **Missing Skills**:
  - *State Management & Data Fetching*: React Context, Zustand / Redux Toolkit, and TanStack Query (React Query) for server-state caching.
  - *Web Accessibility (a11y)*: WCAG 2.1 AA, semantic HTML, ARIA landmarks, keyboard navigation, screen reader testing.
  - *Frontend Testing*: Vitest / Jest unit testing, React Testing Library (RTL) component testing, Playwright / Cypress for end-to-end testing.
  - *Web Performance & Core Web Vitals*: LCP, INP, CLS optimization, code-splitting, lazy loading, bundle analysis.
  - *Modern Build Tooling & Asset Pipelines*: Vite, package management (npm/pnpm), ES modules.
- **Outdated/Questionable Skills**:
  - Two stages are too shallow for a dedicated Frontend Engineer track. Component architecture and Full-Stack React (Next.js) are compressed.
- **Proposed Additions**:
  1. *State Management & Server State (Zustand & TanStack Query)*
  2. *Web Accessibility & WCAG Standards (ARIA, Keyboard Navigation, Contrast)*
  3. *Frontend Testing & Quality Assurance (Vitest, React Testing Library, Playwright)*
  4. *Web Performance & Core Web Vitals (LCP, INP, CLS, Code Splitting)*
  5. *Modern Build Tooling with Vite*
- **Ordering Changes**:
  - Foundations (HTML, CSS, JavaScript) → Tooling & Typing (TypeScript, Vite) → UI & Styling (Tailwind CSS, Accessibility) → React & State Management (React, Zustand & TanStack Query) → Full-Stack Frameworks (Next.js) → Testing & Performance (Frontend Testing, Core Web Vitals).
- **Rationale**:
  Modern frontend engineering demands deep knowledge of accessibility, performance metrics, robust state management, and multi-tier testing.

---

## 4. Full Stack Engineering (`full-stack-engineer`)

- **Domain**: Full Stack Engineering
- **Current Coverage**:
  - Total Stages: 3
  - Total Skills: 9
  - Stage 1 — Web Foundations: HTML, CSS, JavaScript
  - Stage 2 — Modern Frontend & Typing: TypeScript, React, Next.js
  - Stage 3 — Full-Stack Backend & Storage: Node.js, PostgreSQL, Docker
- **Missing Skills**:
  - *Full-Stack Styling & Design Systems*: Tailwind CSS is missing from Full Stack.
  - *Full-Stack Authentication*: NextAuth / Auth.js, JWT, session cookies, OAuth integrations.
  - *Client-Server Communication & API Design*: RESTful APIs, Server Actions, TanStack Query for cache invalidation.
  - *Caching & In-Memory Data*: Redis for caching, rate limiting, and session stores.
  - *Continuous Integration & Cloud Deployment*: GitHub Actions CI/CD and production deployment (Vercel, AWS, or Docker hosts).
- **Outdated/Questionable Skills**:
  - Jumps from Next.js straight to Node.js and PostgreSQL without covering end-to-end authentication, caching, or full-stack API integration.
- **Proposed Additions**:
  1. *Tailwind CSS & Responsive UI*
  2. *REST APIs & Server-Client Communication*
  3. *Full-Stack Authentication & Security (NextAuth / Auth.js & JWT)*
  4. *In-Memory Caching with Redis*
  5. *CI/CD & Cloud Deployment (GitHub Actions & Cloud Hosting)*
- **Ordering Changes**:
  - Web Foundations (HTML, CSS, JavaScript) → Modern Frontend (TypeScript, Tailwind CSS, React) → Full-Stack Core (Next.js, REST APIs) → Backend & Persistence (Node.js, PostgreSQL, Redis) → Auth & DevOps (Full-Stack Auth, Docker, GitHub Actions CI/CD).
- **Rationale**:
  Full stack developers must seamlessly connect the client and server layers with secure auth, synchronized state, and automated deployment.

---

## 5. Cloud / DevOps Engineer (`cloud-devops-engineer`)

- **Domain**: Cloud & Infrastructure
- **Current Coverage**:
  - Total Stages: 3
  - Total Skills: 6
  - Stage 1 — Infrastructure Foundations: Linux Systems, Git
  - Stage 2 — Containers & CI/CD: Docker, GitHub Actions
  - Stage 3 — Cloud Platforms & Container Orchestration: AWS, Kubernetes
- **Missing Skills**:
  - *Infrastructure as Code (IaC)*: Terraform / OpenTofu (HCL, state management, modules, plan/apply workflows).
  - *Cloud Networking & Security*: VPC, public/private subnets, Security Groups, IAM least privilege, NAT Gateways, Route 53, TLS/SSL.
  - *Observability, Logging & Alerting*: Prometheus, Grafana, Loki/Fluentd, Alertmanager, SLOs/SLIs.
  - *GitOps & Deployment Automation*: Helm charts, ArgoCD, blue-green / canary release strategies.
  - *Configuration Management & Automation*: Ansible / Cloud-init.
- **Outdated/Questionable Skills**:
  - Only 6 skills for a domain as expansive as Cloud/DevOps. Missing Terraform and Cloud Networking makes it incomplete for any mid-level role.
- **Proposed Additions**:
  1. *Infrastructure as Code with Terraform (HCL, State, Modules)*
  2. *Cloud Networking & IAM Security Architecture (VPC, Subnets, IAM, Security Groups)*
  3. *Cloud Observability & Monitoring (Prometheus, Grafana, Centralized Logging)*
  4. *GitOps & Continuous Delivery (Helm, ArgoCD, Kubernetes Deployments)*
- **Ordering Changes**:
  - Systems & VCS (Linux, Git) → Containers & Automation (Docker, GitHub Actions) → Cloud & Networking (AWS, Cloud Networking & IAM) → IaC & Orchestration (Terraform, Kubernetes) → GitOps & Observability (GitOps/Helm, Observability/Monitoring).
- **Rationale**:
  DevOps cannot function without automated infrastructure provisioning (Terraform) and reliable observability.

---

## 6. AI / ML Engineer (`ai-ml-engineer`)

- **Domain**: Artificial Intelligence & Machine Learning
- **Current Coverage**:
  - Total Stages: 3
  - Total Skills: 5
  - Stage 1 — Mathematical Foundations & Scientific Python: Python, Pandas
  - Stage 2 — Deep Learning & Neural Networks: PyTorch
  - Stage 3 — Vector Databases & RAG Architectures: pgvector, FastAPI
- **Missing Skills**:
  - *NumPy & Numerical Linear Algebra*: Array operations, broadcasting, matrix multiplication, vectorization.
  - *Classical Machine Learning*: Scikit-Learn (Supervised/Unsupervised learning, regression, classification, random forests, clustering).
  - *Model Validation & Metrics*: Cross-validation, bias-variance tradeoff, ROC-AUC, precision/recall, F1-score.
  - *Natural Language Processing & Transformers*: Hugging Face Transformers, tokenization, embeddings, self-attention mechanisms.
  - *MLOps & Model Deployment*: MLflow, model registries, containerized inference with Docker, model serving architectures.
- **Outdated/Questionable Skills**:
  - Skipping directly from Pandas to PyTorch without NumPy, classical ML (Scikit-Learn), or evaluation fundamentals.
- **Proposed Additions**:
  1. *NumPy & Numerical Computing (Arrays, Broadcasting, Vectorization)*
  2. *Classical Machine Learning with Scikit-Learn (Algorithms, Feature Engineering)*
  3. *Model Evaluation, Validation & Metrics (Cross-validation, ROC-AUC, Tuning)*
  4. *LLM Engineering & Hugging Face Transformers (Embeddings, Tokenization, RAG)*
  5. *MLOps & Model Serving (MLflow, Model Registry, Docker Model Deployment)*
- **Ordering Changes**:
  - Foundations (Python, NumPy, Pandas) → Classical ML (Scikit-Learn, Model Evaluation) → Deep Learning (PyTorch) → Generative AI (Hugging Face / LLMs, pgvector) → Production & MLOps (FastAPI, MLOps & Model Serving).
- **Rationale**:
  AI/ML engineers must master fundamental data modeling and classical algorithms before deploying deep neural networks and generative AI solutions.

---

## 7. Data Engineering (`data-engineer`)

- **Domain**: Data Engineering
- **Current Coverage**:
  - Total Stages: 3
  - Total Skills: 5
  - Stage 1 — SQL & Relational Modeling: SQL, Data Modeling
  - Stage 2 — Data Pipelines & Distributed Computing: Python, Apache Spark (PySpark)
  - Stage 3 — Pipeline Orchestration & Cloud Warehouses: Apache Airflow
- **Missing Skills**:
  - *Cloud Data Warehousing*: Snowflake / Google BigQuery / Amazon Redshift (OLAP, columnar storage, partitioning, clustering).
  - *Analytics Engineering & Transformation*: dbt (Data Build Tool), SQL transformations, data lineage, documentation.
  - *Real-Time Streaming & Event Ingestion*: Apache Kafka / Redpanda (producers, consumers, topics, partitions).
  - *Data Lakehouse & Formats*: Parquet, Delta Lake / Apache Iceberg, ACID transactions on object storage.
  - *Data Quality & Observability*: Great Expectations / Soda, schema validation, data pipeline testing.
- **Outdated/Questionable Skills**:
  - 5 skills does not reflect a production data engineering stack; lacks modern lakehouse formats, streaming, and analytics engineering.
- **Proposed Additions**:
  1. *Cloud Data Warehousing (Snowflake, BigQuery, Columnar Storage, Partitioning)*
  2. *Analytics Engineering with dbt (Transformations, Lineage, Testing)*
  3. *Streaming & Event Ingestion with Apache Kafka (Pub/Sub, Partitions, Consumer Groups)*
  4. *Data Lakehouse Architecture & Storage Formats (Delta Lake, Parquet, Iceberg)*
  5. *Data Quality & Pipeline Reliability (Great Expectations, Automated Validation)*
- **Ordering Changes**:
  - Foundations (Python, SQL, Data Modeling) → Data Warehousing & Transformation (Cloud Data Warehouses, dbt) → Distributed & Lakehouse Computing (Apache Spark, Lakehouse / Delta Lake) → Orchestration & Streaming (Apache Airflow, Apache Kafka) → Data Quality & Reliability.
- **Rationale**:
  The modern data stack centers on dbt, cloud warehouses, streaming ingestion with Kafka, and lakehouse formats.

---

## 8. Data Science (`data-scientist`)

- **Domain**: Data Science
- **Current Coverage**:
  - Total Stages: 2
  - Total Skills: 4
  - Stage 1 — Statistics, Probability & Python: Python, Statistics & Probability
  - Stage 2 — Data Exploration & Machine Learning: Pandas, Scikit-Learn
- **Missing Skills**:
  - *NumPy & Numerical Computing*: Core tensor/matrix operations.
  - *Data Visualization & Storytelling*: Matplotlib, Seaborn, Plotly, dashboarding with Streamlit.
  - *SQL for Data Analysis*: Advanced queries, window functions, CTEs, cohort analysis.
  - *Feature Engineering & Data Preprocessing*: Imputation, categorical encoding, scaling, PCA, feature selection.
  - *A/B Testing & Causal Inference*: Hypothesis testing, statistical power, p-values, experiment design.
  - *Deep Learning Foundations*: PyTorch basics for computer vision and tabular/text modeling.
  - *Model Tracking & Experimentation*: MLflow / Weights & Biases.
- **Outdated/Questionable Skills**:
  - Only 4 skills across 2 stages is far too brief for data science. Lacks visualization, SQL analysis, and experimentation.
- **Proposed Additions**:
  1. *NumPy & Scientific Computing*
  2. *Data Visualization & Storytelling (Matplotlib, Seaborn, Streamlit)*
  3. *SQL for Data Analysis & Cohort Metrics (Window Functions, CTEs)*
  4. *Feature Engineering & Data Preprocessing (Encoding, Scaling, PCA)*
  5. *A/B Testing, Experiment Design & Causal Inference*
  6. *Deep Learning Foundations with PyTorch*
- **Ordering Changes**:
  - Foundations (Python, Statistics & Probability, NumPy) → Exploratory Analysis (Pandas, Data Visualization, SQL for Data Analysis) → Machine Learning & Features (Feature Engineering, Scikit-Learn) → Advanced Science (A/B Testing, Deep Learning with PyTorch).
- **Rationale**:
  Data scientists must extract data using SQL, visualize exploratory distributions, engineer features, rigorously run A/B tests, and train predictive models.

---

## 9. Cybersecurity Engineer (`cybersecurity-engineer`)

- **Domain**: Cybersecurity
- **Current Coverage**:
  - Total Stages: 2
  - Total Skills: 3
  - Stage 1 — Networking & Security Foundations: Network Security & Protocols, Linux Security & Hardening
  - Stage 2 — Web Application Security & OWASP: OWASP Top 10
- **Missing Skills**:
  - *Cryptography Fundamentals*: Symmetric/asymmetric encryption, AES, RSA, SHA-256, PKI, digital signatures, TLS handshakes.
  - *Identity & Access Management (IAM) & Zero Trust*: OAuth2, OIDC, SAML, Multi-Factor Authentication (MFA), least privilege.
  - *Vulnerability Assessment & Penetration Testing*: Nmap, Burp Suite, vulnerability scanners, CVSS scoring, remediation.
  - *SIEM, Log Analysis & Incident Response*: Splunk / ELK, incident response lifecycle (NIST/SANS), threat detection, SOC triage.
  - *Cloud & Container Security*: Cloud security posture, IAM misconfigurations, container image scanning (Trivy), runtime defenses.
  - *Secure Software Development (SSDLC)*: Threat modeling (STRIDE), SAST/DAST tools, dependency auditing.
- **Outdated/Questionable Skills**:
  - Only 3 skills total. Lacks cryptography, IAM, SIEM, penetration testing, and cloud security.
- **Proposed Additions**:
  1. *Cryptography & Public Key Infrastructure (PKI, AES, RSA, Hashing, TLS)*
  2. *Identity & Access Management & Zero Trust (OAuth2, OIDC, MFA, Least Privilege)*
  3. *Vulnerability Scanning & Penetration Testing (Nmap, Burp Suite, CVSS)*
  4. *SIEM, Log Analysis & Incident Response (Threat Detection, Incident Triage, SOC)*
  5. *Cloud Infrastructure & Container Security (Cloud IAM, Image Scanning, Hardening)*
- **Ordering Changes**:
  - Security Foundations (Network Security, Linux Hardening, Cryptography) → Application & Identity Defense (OWASP Top 10, IAM & Zero Trust) → Security Operations & Threat Hunting (Vulnerability Assessment, SIEM & Incident Response) → Cloud & Modern Defenses (Cloud & Container Security).
- **Rationale**:
  Cybersecurity requires defense-in-depth across networks, cryptography, web apps, identity systems, and cloud infrastructure.

---

## 10. QA / Test Automation Engineer (`qa-automation-engineer`)

- **Domain**: Quality Assurance & Test Automation
- **Current Coverage**:
  - Total Stages: 2
  - Total Skills: 3
  - Stage 1 — Quality Assurance Foundations: Testing Fundamentals & Test Strategy
  - Stage 2 — API Testing & End-to-End Browser Automation: API Testing (Postman & REST), Playwright Automation
- **Missing Skills**:
  - *Test Automation Architecture & Design Patterns*: Page Object Model (POM), data-driven testing, clean fixture architecture.
  - *Automated Unit & Integration Testing*: Pytest / Jest test runners, mocking external dependencies, parameterized suites.
  - *CI/CD Continuous Test Automation*: GitHub Actions automated test workflows, running headless browsers, artifact & video capture, flaky test mitigation.
  - *Performance & Load Testing*: k6 / Locust, load profiles, stress testing, latency percentile analysis.
  - *Accessibility & Cross-Browser Audits*: Axe-core automated accessibility audits, cross-browser regression testing.
- **Outdated/Questionable Skills**:
  - Only 3 skills total. Ignores CI integration, test framework design patterns, and load testing.
- **Proposed Additions**:
  1. *Test Automation Architecture & Page Object Model (POM, Fixtures, Reusability)*
  2. *Automated Unit & Integration Testing (Pytest, Mocking, Test Runners)*
  3. *Continuous Testing in CI/CD (GitHub Actions, Headless Automation, Reporting)*
  4. *Performance & Load Testing with k6 (Stress Testing, Concurrency, Latency)*
  5. *Automated Accessibility & Cross-Browser Testing (Axe-core, WCAG Automation)*
- **Ordering Changes**:
  - QA Strategy & Core (Testing Fundamentals, Automated Unit & Integration Testing) → Functional Automation (API Testing, Playwright Automation, Test Automation Architecture/POM) → Performance & Accessibility (Performance Testing with k6, Automated Accessibility) → CI/CD Integration (Continuous Testing in CI/CD).
- **Rationale**:
  Test automation engineers must design scalable test frameworks (POM), automate API and browser journeys, test system limits with k6, and integrate tests into CI/CD pipelines.

---

## 11. iOS Developer (`ios-developer`)

- **Domain**: Mobile Development (iOS)
- **Current Coverage**:
  - Total Stages: 2
  - Total Skills: 3
  - Stage 1 — Swift Programming Fundamentals: Swift
  - Stage 2 — Declarative UI with SwiftUI: SwiftUI, URLSession & Modern Swift Concurrency
- **Missing Skills**:
  - *iOS App Architecture & MVVM*: Model-View-ViewModel, `@Observable` / ObservableObject, State & Binding, Unidirectional Data Flow.
  - *Local Persistence & Storage*: SwiftData / CoreData, UserDefaults, Keychain Services for secure storage.
  - *Navigation & NavigationStack*: NavigationStack, sheets, modal presentations, deep linking.
  - *Testing & Quality Assurance*: XCTest framework, unit testing ViewModels, async testing, UI testing with XCUITest.
  - *Xcode Build, Provisioning & App Store Release*: Xcode project structure, provisioning profiles, certificates, TestFlight, App Store Connect publishing.
- **Outdated/Questionable Skills**:
  - Only 3 skills total. Lacks MVVM architecture, persistence (SwiftData), unit testing, and App Store publishing.
- **Proposed Additions**:
  1. *iOS App Architecture & State with MVVM (`@Observable`, State, Binding, UDF)*
  2. *Local Persistence with SwiftData & Keychain (SwiftData, SQLite, Secure Keychain)*
  3. *iOS Unit & UI Testing with XCTest (ViewModel Testing, Mocking, XCUITest)*
  4. *Xcode Build System, Provisioning & App Store Release (Profiles, TestFlight, Publishing)*
- **Ordering Changes**:
  - Foundations (Swift, SwiftUI) → Architecture & Networking (URLSession & Swift Concurrency, iOS Architecture & MVVM) → Persistence & Testing (SwiftData & Keychain, XCTest & UI Testing) → Tooling & Release (Xcode, TestFlight & App Store Release).
- **Rationale**:
  A complete iOS developer roadmap must cover declarative UI (SwiftUI), modern concurrency (async/await), state management (MVVM), secure storage (SwiftData/Keychain), testing (XCTest), and release pipelines.

---

## 12. UI/UX Engineer / Product Designer (`ui-ux-engineer`)

- **Domain**: Design & Frontend Engineering
- **Current Coverage**:
  - Total Stages: 2
  - Total Skills: 3
  - Stage 1 — UX Principles & User Research: UX Research & Design Thinking
  - Stage 2 — High-Fidelity Prototyping & Design Systems: Figma & High-Fidelity Prototyping, Web Accessibility (WCAG)
- **Missing Skills**:
  - *Information Architecture & Wireframing*: Site maps, user flows, journey maps, low-fidelity wireframing, card sorting.
  - *Design Systems & Design Tokens*: Component tokens, typography and color scales, auto-layout, component variants, Tokens Studio.
  - *Interaction Design & Micro-Animations*: Prototyping interactive transitions, easing curves, stateful component prototypes.
  - *Usability Testing & Metric-Driven Iteration*: Moderated/unmoderated user testing protocols, heatmaps, System Usability Scale (SUS), analytics.
  - *Developer Handoff & Frontend Bridge*: Inspecting design specs, responsive breakpoint architecture, flexbox/grid layout translation, design token export.
- **Outdated/Questionable Skills**:
  - 3 skills cannot represent a professional UI/UX roadmap; lacks information architecture, interaction design, usability testing, and developer handoff.
- **Proposed Additions**:
  1. *Information Architecture & User Flows (Site Maps, Wireframing, User Journeys)*
  2. *Design Systems & Component Architecture (Design Tokens, Auto-Layout, Variants)*
  3. *Interaction Design & Micro-Animations (Transitions, Easing, Interactive States)*
  4. *Usability Testing & Quantitative UX Metrics (User Testing, Heatmaps, SUS)*
  5. *Developer Handoff & Responsive Layout Translation (CSS Specs, Breakpoints, Tokens)*
- **Ordering Changes**:
  - Research & IA (UX Research, Information Architecture) → Visual Design & Systems (Figma Prototyping, Design Systems, Accessibility) → Interaction & Validation (Interaction Design, Usability Testing) → Production Bridge (Developer Handoff & Layout Translation).
- **Rationale**:
  Product designers and UI/UX engineers must bridge discovery, information architecture, systematic component design, usability testing, and seamless handoff to engineering.

---

## Summary of Audit Metrics

| Domain | Current Skills | Target Skills | Status After Upgrade |
|---|:---:|:---:|---|
| **Android Development** | 6 | 14 | **Complete Enterprise Track** |
| **Backend Engineering** | 12 | 16 | **Complete Enterprise Track** |
| **Frontend Engineering** | 7 | 12 | **Complete Enterprise Track** |
| **Full Stack Engineering** | 9 | 14 | **Complete Enterprise Track** |
| **Cloud / DevOps Engineer** | 6 | 10 | **Complete Enterprise Track** |
| **AI / ML Engineer** | 5 | 10 | **Complete Enterprise Track** |
| **Data Engineering** | 5 | 10 | **Complete Enterprise Track** |
| **Data Scientist** | 4 | 10 | **Complete Enterprise Track** |
| **Cybersecurity Engineer** | 3 | 8 | **Complete Enterprise Track** |
| **QA / Test Automation** | 3 | 8 | **Complete Enterprise Track** |
| **iOS Developer** | 3 | 7 | **Complete Enterprise Track** |
| **UI/UX Engineer** | 3 | 8 | **Complete Enterprise Track** |

Every single roadmap skill will be equipped with:
1. Canonical or curated metadata aligned with zero-breakage taxonomy constraints.
2. Verified, official documentation link.
3. High-quality, reputable YouTube course or tutorial link.
4. Exactly three progressive practice problems (Foundation, Integration, Mastery) with declared concepts tested, rigorous requirements, expected outcomes, and helpful hints.
