# SkillForge AI — GitHub Intelligence Engine

## 1. Purpose & Principles

The GitHub Intelligence Engine provides **empirical validation** for skills claimed by a candidate.

Instead of accepting resume claims at face value or relying on superficial vanity metrics (such as GitHub stars or commit streaks), the engine inspects repository artifacts to confirm practical engineering usage.

### Core Principles

1. **Evidence Over Assertion**: A skill is only marked *Demonstrated* when supported by concrete code, configuration, or dependency manifests.
2. **Read-Only Inspection**: The system accesses public repositories strictly using read-only API scopes.
3. **Artifact-Driven Verification**: Evidence is derived from verifiable project assets: dependencies, build files, container manifests, and CI workflows.
4. **Fork and Clone Isolation**: Repositories marked as forks or identified as cloned boilerplate templates are excluded from evidence accumulation.

---

## 2. Inspection Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Public REST API                   │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
               ▼                               ▼
       Repository Discovery             File Tree Traversal
       (Filter forks / empty)           (Recursive tree scan)
               │                               │
               └───────────────┬───────────────┘
                               ▼
               ┌───────────────────────────────┐
               │    Target Artifact Parsers    │
               ├───────────────────────────────┤
               │ • Dependency Manifests        │
               │ • Infrastructure & Containers │
               │ • CI/CD & Testing Assets      │
               │ • Language Volume Breakdown   │
               └───────────────┬───────────────┘
                               ▼
               ┌───────────────────────────────┐
               │   Evidence Heuristic Engine   │
               └───────────────┬───────────────┘
                               ▼
               ┌───────────────────────────────┐
               │ Demonstrated Skill Confidence │
               └───────────────────────────────┘
```

---

## 3. Inspection Dimensions & Artifacts

### 3.1 Dependency Manifests

The engine inspects project dependency definitions to identify exact framework and library adoption:

| Ecosystem | Target Manifest Files | Extracted Technologies |
| :--- | :--- | :--- |
| **Node.js / TS** | `package.json`, `pnpm-lock.yaml`, `yarn.lock` | React, Next.js, Express, Tailwind, Prisma, NestJS, Jest |
| **Python** | `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py` | FastAPI, Django, Flask, SQLAlchemy, PyTorch, Pandas, Pytest |
| **Java / Kotlin** | `pom.xml`, `build.gradle`, `build.gradle.kts` | Spring Boot, Hibernate, JUnit, Quarkus |
| **Go** | `go.mod` | Gin, Fiber, GORM, Chi |
| **Rust** | `Cargo.toml` | Actix, Axum, Tokio, Serde |
| **C# / .NET** | `*.csproj`, `packages.config` | ASP.NET Core, Entity Framework |

### 3.2 Infrastructure & DevOps Assets

Production-grade engineering evidence is detected by scanning configuration files:

- **Docker**: Presence of `Dockerfile` and `docker-compose.yml` confirms containerization capability.
- **CI/CD**: Workflows located in `.github/workflows/*.yml` or `.gitlab-ci.yml` confirm automation and pipeline proficiency.
- **Kubernetes / Cloud**: Manifests in `k8s/`, `helm/`, or Terraform files (`*.tf`) verify infrastructure-as-code competency.

### 3.3 Engineering Best Practices

- **Automated Tests**: Directories such as `tests/`, `__tests__/`, `spec/`, or files matching `*test*.py`, `*.spec.ts`, `*_test.go`.
- **API Documentation**: OpenAPI/Swagger definitions (`swagger.json`, `openapi.yaml`) or comprehensive `README.md` documents.

---

## 4. Evidence Scoring Model

For each canonical skill $s$, the engine computes an **Evidence Score** $E(s) \in [0.0, 1.0]$:

$$E(s) = w_{\text{manifest}} \cdot S_{\text{manifest}} + w_{\text{code}} \cdot S_{\text{code}} + w_{\text{infra}} \cdot S_{\text{infra}} + w_{\text{recency}} \cdot S_{\text{recency}}$$

### Component Breakdown

| Signal | Weight | Evaluation Criteria |
| :--- | :---: | :--- |
| $S_{\text{manifest}}$ | $0.40$ | Direct presence in package/dependency files ($1.0$ for direct dependency, $0.5$ for dev/transitive). |
| $S_{\text{code}}$ | $0.25$ | Volume of language/files associated with the technology in original repositories. |
| $S_{\text{infra}}$ | $0.20$ | Supporting deployment/config files (e.g., Dockerfile, CI pipeline invoking tests). |
| $S_{\text{recency}}$ | $0.15$ | Recency of commits touching the technology (decay applied for activity $>18$ months old). |

### Confidence Tiers

- **High Evidence ($E(s) \ge 0.70$)**: Strong, verifiable project implementation. Skill considered fully *Demonstrated*.
- **Moderate Evidence ($0.40 \le E(s) < 0.70$)**: Direct dependency found or basic project evidence. Recommended for minor refresh or capstone verification.
- **Low / Unverified ($E(s) < 0.40$)**: Superficial mention, outdated commit, or claimed only on resume. Treated as a gap requiring project evidence.

---

## 5. Output Schema

```json
{
  "github_username": "octocat",
  "analyzed_repositories_count": 8,
  "last_analyzed_at": "2026-09-01T12:00:00Z",
  "demonstrated_skills": [
    {
      "skill_name": "FastAPI",
      "canonical_slug": "fastapi",
      "confidence_score": 0.85,
      "evidence_tier": "HIGH",
      "evidence_trail": [
        {
          "repo_name": "ecommerce-api",
          "repo_url": "https://github.com/octocat/ecommerce-api",
          "artifact_type": "dependency_manifest",
          "file_path": "requirements.txt",
          "matched_entry": "fastapi==0.110.0"
        },
        {
          "repo_name": "ecommerce-api",
          "artifact_type": "infrastructure",
          "file_path": "Dockerfile",
          "matched_entry": "CMD [\"uvicorn\", \"app.main:app\"]"
        }
      ]
    },
    {
      "skill_name": "Docker",
      "canonical_slug": "docker",
      "confidence_score": 0.75,
      "evidence_tier": "HIGH",
      "evidence_trail": [
        {
          "repo_name": "ecommerce-api",
          "artifact_type": "infrastructure",
          "file_path": "docker-compose.yml",
          "matched_entry": "services.web.build"
        }
      ]
    }
  ]
}
```
