# SkillForge AI — Skill Taxonomy & Normalization Engine

## 1. Purpose & Core Principles

The Skill Taxonomy serves as the **single source of canonical truth** across all SkillForge AI modules: resume parsing, GitHub repository inspection, industry market demand, and personalized roadmaps.

### Objectives

1. **Eliminate Duplication**: Consolidates variations, abbreviations, typos, and version tags into a single canonical skill entity.
2. **Deterministic Matching**: Prevents fragmentation where "Postgres", "PostgreSQL", and "psql" are treated as distinct skills.
3. **Structured Relationships**: Encodes hierarchical parent-child groupings and prerequisite graph dependencies.
4. **Semantic Fallback**: Employs vector embeddings to normalize unfamiliar or emerging industry terms.

---

## 2. Taxonomy Hierarchy & Categories

The taxonomy organizes technical skills into seven top-level domains:

```text
┌─────────────────────────────────────────────────────────────┐
│                    CANONICAL SKILL DOMAINS                  │
├──────────────────────────────┬──────────────────────────────┤
│ 1. Programming Languages     │ Python, TypeScript, Go, Java │
│ 2. Frontend Development      │ React, Next.js, Tailwind CSS │
│ 3. Backend & API Engineering │ FastAPI, Node.js, Spring Boot│
│ 4. Databases & Storage       │ PostgreSQL, MongoDB, Redis   │
│ 5. DevOps, Cloud & Infra     │ Docker, Kubernetes, AWS, CI  │
│ 6. AI, ML & Data Engineering │ PyTorch, Pandas, LangChain   │
│ 7. Systems & Architecture    │ Git, REST, System Design     │
└──────────────────────────────┴──────────────────────────────┘
```

---

## 3. Normalization Pipeline

```text
[Raw Input String] (e.g. "ReactJS", "k8s", "Amazon Web Services")
        │
        ▼
[String Preprocessing] (lowercase, trim whitespace, remove punctuation)
        │
        ▼
[Exact Match Lookup in skills & skill_aliases]
        ├──► Matched? ──► Return Canonical Skill ID & Slug
        │
        └──► No direct match?
                 │
                 ▼
        [Generate Dense Text Embedding (pgvector)]
                 │
                 ▼
        [Cosine Similarity Search on skills.embedding]
                 ├──► Similarity >= 0.88 ──► Map to Closest Canonical Skill
                 └──► Similarity < 0.88  ──► Flag for Review / Fallback
```

### Disambiguation Rules

- **Java vs. JavaScript**: Treated as strictly distinct skills with zero alias overlap.
- **Go / Golang**: Canonical name `Go` with aliases `golang` and `go-lang`. Context-aware tokenization prevents matching common English verbs.
- **C / C++ / C#**: Strict boundary matching ensuring `C++` (cpp) and `C#` (csharp) are segregated from plain `C`.
- **Frameworks vs. Languages**: `React` maps to *Frontend Frameworks*, but establishes a soft prerequisite relationship with `JavaScript` and `TypeScript`.

---

## 4. Skill Relationships & Graph Structure

Each skill entity maintains three relationship types:

1. **Parent Domain**: High-level categorization (e.g., `FastAPI` $\in$ *Backend Frameworks*).
2. **Prerequisites (Dependencies)**: Directed constraints governing learning sequence (e.g., `Docker` is a prerequisite for `Kubernetes`).
3. **Co-Occurrence Complements**: Skills commonly implemented alongside each other in production (e.g., `FastAPI` $\longleftrightarrow$ `PostgreSQL` $\longleftrightarrow$ `Docker`).

---

## 5. Canonical Seed Taxonomy

| Canonical Skill | Slug | Category | Common Aliases & Variations | Prerequisites |
| :--- | :--- | :--- | :--- | :--- |
| **Python** | `python` | Languages | `py`, `python3`, `cpython` | None |
| **TypeScript** | `typescript` | Languages | `ts`, `type-script` | JavaScript |
| **JavaScript** | `javascript` | Languages | `js`, `es6`, `ecmascript` | None |
| **Java** | `java` | Languages | `jdk`, `java8`, `java17`, `jvm` | None |
| **Go** | `go` | Languages | `golang`, `go-lang` | None |
| **SQL** | `sql` | Languages | `structured-query-language`, `ansi-sql` | None |
| **React** | `react` | Frontend | `reactjs`, `react.js`, `react-dom` | JavaScript |
| **Next.js** | `nextjs` | Frontend | `next.js`, `next13`, `next14`, `next` | React, TypeScript |
| **Tailwind CSS** | `tailwindcss` | Frontend | `tailwind`, `tailwind-css` | CSS |
| **FastAPI** | `fastapi` | Backend | `fast-api`, `fastapi-framework` | Python, REST APIs |
| **Node.js** | `nodejs` | Backend | `node`, `node.js` | JavaScript |
| **Spring Boot** | `spring-boot` | Backend | `springboot`, `spring-framework` | Java |
| **PostgreSQL** | `postgresql` | Databases | `postgres`, `psql`, `pg` | SQL |
| **MongoDB** | `mongodb` | Databases | `mongo`, `documentdb` | None |
| **Redis** | `redis` | Databases | `redis-cache`, `key-value-store` | None |
| **pgvector** | `pgvector` | Databases | `vector-extension`, `postgres-vector` | PostgreSQL |
| **Docker** | `docker` | DevOps & Cloud | `dockerfile`, `docker-compose`, `containers` | Linux Fundamentals |
| **Kubernetes** | `kubernetes` | DevOps & Cloud | `k8s`, `kube`, `kubectl` | Docker |
| **AWS** | `aws` | DevOps & Cloud | `amazon-web-services`, `aws-cloud` | Cloud Fundamentals |
| **GitHub Actions** | `github-actions` | DevOps & Cloud | `gh-actions`, `github-ci` | Git |
| **Git** | `git` | Systems | `git-scm`, `version-control` | None |
| **REST APIs** | `rest-apis` | Systems | `restful`, `rest-api`, `http-api` | HTTP Protocols |
| **Pytest** | `pytest` | Systems | `py-test`, `pytest-runner` | Python |
| **Docker Compose** | `docker-compose` | DevOps & Cloud | `compose`, `docker-compose-yml` | Docker |
| **PyTorch** | `pytorch` | AI & ML | `torch`, `torchvision` | Python |
| **Pandas** | `pandas` | AI & ML | `pandas-dataframe`, `pd` | Python |
