# SkillForge AI — API Specification

## 1. API Overview

This document establishes the authoritative API specification for **SkillForge AI**, an evidence-based AI skill-gap analysis and personalized career roadmap platform.

The SkillForge AI backend is built with **FastAPI** (Python 3.12+), providing high-performance, asynchronous REST endpoints backed by **PostgreSQL 16** with the **pgvector** extension. The frontend is built on **Next.js** (App Router, TypeScript, Tailwind CSS) and interacts strictly with this API.

### Core Conventions
- **Protocol**: HTTP/1.1 and HTTP/2 over TLS in production; standard HTTP for local development.
- **Base URL**:
  - Development Root: `http://localhost:8000`
  - Development API v1: `http://localhost:8000/api/v1`
  - Production API: `https://api.skillforge.ai/api/v1`
- **Versioning Strategy**: URI-based path versioning under `/api/v1`. Unversioned root endpoints are strictly reserved for operational infrastructure diagnostics (`/health`, `/health/db`).
- **Data Exchange**: Requests and responses use `application/json; charset=utf-8`, except file upload endpoints which consume `multipart/form-data`.
- **Identifiers**: All resource identifiers are strictly UUIDv4 strings (e.g., `3fa85f64-5717-4562-b3fc-2c963f66afa6`).
- **Timestamps**: All timestamps are formatted in ISO 8601 extended format with UTC timezone offset (e.g., `2026-09-01T14:30:00.000Z`).
- **Authentication**: Stateless JSON Web Tokens (JWT) passed via the standard HTTP header:
  ```http
  Authorization: Bearer <access_token>
  ```

---

## 2. API Design Principles

1. **REST-Oriented Resources**: URIs represent concrete domain resources (e.g., `/resumes`, `/skills`, `/evidence`, `/roadmaps`), using standard HTTP verbs (`GET`, `POST`, `PATCH`, `DELETE`).
2. **Strict User Ownership**: All user-specific records are partitioned and queried strictly by the authenticated `user_id`. Cross-user data leakage is prevented at the database query layer.
3. **Pydantic Validation**: All incoming payloads are strongly typed and validated before reaching route handlers.
4. **Deterministic Business Logic**: Algorithmic scoring, dependency graphs, and gap classifications are computed deterministically on the backend.
5. **Separation of LLM & Numerical Data**: The LLM provides qualitative reasoning, natural-language explanation, and contextual extraction. Numerical industry demand metrics are mathematically derived from verified market data and stored in PostgreSQL; the LLM is prohibited from generating or modifying demand scores.
6. **Evidence-First Skill Evaluation**: Claims from resumes are treated as unverified (`CLAIMED`). Skills are only elevated to verified evidence tiers (`DEMONSTRATED` / `HIGH`) when backed by verifiable code artifacts from connected GitHub repositories.
7. **Idempotency**: `PUT` and `DELETE` requests are idempotent. Resource generation endpoints return deterministic representations or reuse active state where specified.
8. **Consistent Pagination**: Collection endpoints support standard limit/offset pagination parameters (`limit`, `offset`) and return structured pagination metadata.
9. **Descriptive Errors**: Failures return consistent error envelopes with structured error codes and actionable descriptions.

---

## 3. Authentication & User Context

Authentication is handled via OAuth2 Password Bearer flow issuing signed JWT access tokens. Passwords must be hashed using `bcrypt` or `argon2id`. The database field `password_hash` is strictly internal and never serialized in API responses.

### 3.1 Register User
```http
POST /api/v1/auth/register
Content-Type: application/json
```
#### Request Body
```json
{
  "email": "candidate@example.com",
  "password": "SecurePassword123!",
  "full_name": "Jane Doe",
  "target_role": "Backend Engineer",
  "target_location": "India",
  "weekly_hours_commitment": 10
}
```
#### Response `201 Created`
```json
{
  "data": {
    "user_id": "8a3e72c1-6789-4a12-b345-987654321abc",
    "email": "candidate@example.com",
    "full_name": "Jane Doe",
    "target_role": "Backend Engineer",
    "target_location": "India",
    "weekly_hours_commitment": 10,
    "created_at": "2026-09-01T14:30:00Z"
  }
}
```

### 3.2 Login (Acquire Token)
```http
POST /api/v1/auth/login
Content-Type: application/json
```
#### Request Body
```json
{
  "email": "candidate@example.com",
  "password": "SecurePassword123!"
}
```
#### Response `200 OK`
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 86400
  }
}
```

### 3.3 Get Current Authenticated User
```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```
#### Response `200 OK`
```json
{
  "data": {
    "user_id": "8a3e72c1-6789-4a12-b345-987654321abc",
    "email": "candidate@example.com",
    "full_name": "Jane Doe",
    "target_role": "Backend Engineer",
    "target_location": "India",
    "weekly_hours_commitment": 10,
    "created_at": "2026-09-01T14:30:00Z"
  }
}
```

---

## 4. User Profile

### 4.1 Get Profile
```http
GET /api/v1/users/me
Authorization: Bearer <access_token>
```
#### Response `200 OK`
```json
{
  "data": {
    "user_id": "8a3e72c1-6789-4a12-b345-987654321abc",
    "email": "candidate@example.com",
    "full_name": "Jane Doe",
    "target_role": "Backend Engineer",
    "target_location": "India",
    "weekly_hours_commitment": 10,
    "updated_at": "2026-09-01T14:30:00Z"
  }
}
```

### 4.2 Update Profile
```http
PATCH /api/v1/users/me
Authorization: Bearer <access_token>
Content-Type: application/json
```
#### Request Body
```json
{
  "full_name": "Jane Doe",
  "target_role": "Backend Engineer",
  "target_location": "India",
  "weekly_hours_commitment": 15
}
```
#### Response `200 OK`
```json
{
  "data": {
    "user_id": "8a3e72c1-6789-4a12-b345-987654321abc",
    "email": "candidate@example.com",
    "full_name": "Jane Doe",
    "target_role": "Backend Engineer",
    "target_location": "India",
    "weekly_hours_commitment": 15,
    "updated_at": "2026-09-01T14:35:00Z"
  }
}
```

---

## 5. Resume APIs

Candidate resumes are processed through a multi-stage pipeline:
```text
File Upload (PDF/DOCX)
      ↓ (Validation: Size, MIME, Magic Bytes)
File Storage by UUID & Metadata Record
      ↓ (Checkpoint 2: Text Extraction)
Raw Text Extraction & Section Segmentation
      ↓ (Checkpoint 3: Skill Extraction)
Entity Recognition & Taxonomy Normalization
      ↓ (Checkpoint 4: Persistence)
Claimed Skills Persistence (user_claimed_skills)
```

### 5.1 Upload Resume
```http
POST /api/v1/resumes/upload
Content-Type: multipart/form-data
```
#### Form Data
- `file`: PDF or DOCX file (maximum size: 5 MB).
- *Note*: `user_id` is optional/nullable in Checkpoint 1 to support onboarding before authentication.

#### Response `201 Created`
```json
{
  "resume_id": "ff158ffc-ea91-4068-ad97-52e977abbda2",
  "filename": "jane_doe_resume.pdf",
  "file_type": "pdf",
  "file_size": 245760,
  "status": "uploaded",
  "message": "Resume uploaded successfully. Text extraction and skill analysis scheduled for Checkpoint 2.",
  "created_at": "2026-09-01T14:30:00Z"
}
```

### 5.2 List User Resumes
```http
GET /api/v1/resumes
Authorization: Bearer <access_token>
```
#### Response `200 OK`
```json
{
  "data": [
    {
      "resume_id": "ff158ffc-ea91-4068-ad97-52e977abbda2",
      "filename": "jane_doe_resume.pdf",
      "file_type": "pdf",
      "file_size": 245760,
      "created_at": "2026-09-01T14:30:00Z"
    }
  ],
  "meta": {
    "total": 1
  }
}
```

### 5.3 Get Resume Details
```http
GET /api/v1/resumes/{resume_id}
Authorization: Bearer <access_token>
```
#### Response `200 OK`
```json
{
  "data": {
    "resume_id": "ff158ffc-ea91-4068-ad97-52e977abbda2",
    "filename": "jane_doe_resume.pdf",
    "file_type": "pdf",
    "file_size": 245760,
    "has_raw_text": true,
    "parsed_data": {
      "sections_detected": ["skills", "experience", "education", "projects"],
      "extracted_skills_count": 8
    },
    "created_at": "2026-09-01T14:30:00Z"
  }
}
```

### 5.4 Delete Resume
```http
DELETE /api/v1/resumes/{resume_id}
Authorization: Bearer <access_token>
```
#### Response `204 No Content`

---

## 6. Claimed Skills

Skills extracted from uploaded resumes or explicitly self-declared by the candidate are persisted in `user_claimed_skills`.

### 6.1 List Claimed Skills
```http
GET /api/v1/skills/claimed
Authorization: Bearer <access_token>
```
#### Response `200 OK`
```json
{
  "data": [
    {
      "skill_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
      "skill_name": "Python",
      "canonical_slug": "python",
      "category": "Languages",
      "source": "resume",
      "raw_mention": "Python 3.10 / AsyncIO",
      "confidence_score": 0.95,
      "evidence_tier": "CLAIMED",
      "created_at": "2026-09-01T14:30:00Z"
    },
    {
      "skill_id": "2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e",
      "skill_name": "FastAPI",
      "canonical_slug": "fastapi",
      "category": "Frameworks",
      "source": "resume",
      "raw_mention": "FastAPI REST microservices",
      "confidence_score": 0.90,
      "evidence_tier": "CLAIMED",
      "created_at": "2026-09-01T14:30:00Z"
    }
  ],
  "meta": {
    "total": 2
  }
}
```

---

## 7. GitHub Integration

The GitHub engine accesses candidate repositories using the official GitHub REST API.

#### Security & Integrity Guarantees:
- **PAT Security**: Personal Access Tokens (PAT) are strictly volatile in-memory for HTTP `Authorization: Bearer` headers. PATs are **never** stored in the database, **never** placed in URL query parameters, **never** logged, and **never** returned in API responses or error payloads.
- **Error Mapping**: GitHub API failures map deterministically to standard internal errors:
  - 401 Unauthorized $\rightarrow$ `UNAUTHENTICATED`
  - 403 / 429 Rate Limited $\rightarrow$ `RATE_LIMITED`
  - 404 Not Found $\rightarrow$ `NOT_FOUND`
  - 422 Validation Error $\rightarrow$ `VALIDATION_ERROR`
  - 500 / 502 Upstream Failure $\rightarrow$ `UPSTREAM_GATEWAY_ERROR`
  - Timeout $\rightarrow$ `GATEWAY_TIMEOUT` (504)
- **Safety Limits**:
  - `MAX_TREE_ENTRIES = 1000` (prevents memory exhaustion on deep git trees)
  - `MAX_FILE_SIZE_BYTES = 512 KB` (safeguards against oversized manifest denial of service)
  - Repository code is **never executed** (no package installation, builds, or script execution).
  - Malicious paths containing traversal (`../`), null bytes, or absolute paths are strictly rejected.
- **Ownership Scoping**: All repository, evidence, and demonstrated-skill endpoints enforce `user_id` query scoping.
- **Stale Evidence Reconciliation**: Re-scans automatically delete removed evidence and recompute demonstrated skills. Skills with 0 remaining evidence records are automatically deleted from `demonstrated_skills`.

### 7.1 Connect GitHub Account
```http
POST /api/v1/github/connect
Authorization: Bearer <access_token>
Content-Type: application/json
```
#### Request Body
```json
{
  "github_username": "janedoe"
}
```
#### Response `200 OK`
```json
{
  "data": {
    "github_username": "janedoe",
    "connected": true,
    "discovered_repositories": 8
  }
}
```

### 7.2 List Discovered Repositories
```http
GET /api/v1/github/repositories
Authorization: Bearer <access_token>
```
#### Response `200 OK`
```json
{
  "data": [
    {
      "repo_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
      "repo_name": "task-management-api",
      "repo_url": "https://github.com/janedoe/task-management-api",
      "primary_language": "Python",
      "is_fork": false,
      "stars_count": 14,
      "last_pushed_at": "2026-08-20T10:15:00Z"
    }
  ],
  "meta": {
    "total": 1
  }
}
```

### 7.3 Get Repository Details
```http
GET /api/v1/github/repositories/{repo_id}
Authorization: Bearer <access_token>
```
#### Response `200 OK`
```json
{
  "data": {
    "repo_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
    "repo_name": "task-management-api",
    "repo_url": "https://github.com/janedoe/task-management-api",
    "primary_language": "Python",
    "is_fork": false,
    "stars_count": 14,
    "last_pushed_at": "2026-08-20T10:15:00Z",
    "repo_metadata": {
      "has_dockerfile": true,
      "has_ci_workflow": true,
      "detected_dependencies": ["fastapi", "sqlalchemy", "psycopg", "pytest"]
    }
  }
}
```

### 7.4 Analyze Repositories
```http
POST /api/v1/github/analyze
Authorization: Bearer <access_token>
Content-Type: application/json
```
#### Request Body
```json
{
  "selected_repo_ids": ["7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d"],
  "include_forks": false
}
```
#### Response `200 OK`
```json
{
  "data": {
    "repositories_analyzed": 1,
    "evidence_items_detected": 4,
    "demonstrated_skills": [
      {
        "skill_name": "FastAPI",
        "canonical_slug": "fastapi",
        "confidence_score": 0.85,
        "evidence_type": "dependency",
        "evidence_tier": "HIGH"
      },
      {
        "skill_name": "Docker",
        "canonical_slug": "docker",
        "confidence_score": 0.80,
        "evidence_type": "dockerfile",
        "evidence_tier": "HIGH"
      }
    ]
  }
}
```

---

## 8. Project Evidence

Auditable, concrete code artifacts extracted from repositories are persisted in `project_evidence`. Resume claims alone do NOT generate project evidence.

### 8.1 List Evidence Items
```http
GET /api/v1/evidence
Authorization: Bearer <access_token>
```
#### Response `200 OK`
```json
{
  "data": [
    {
      "evidence_id": "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
      "skill_name": "FastAPI",
      "canonical_slug": "fastapi",
      "repo_name": "task-management-api",
      "evidence_type": "dependency",
      "file_path": "backend/requirements.txt",
      "matched_content": "fastapi>=0.110.0",
      "confidence_score": 0.85,
      "detected_at": "2026-09-01T14:35:00Z"
    },
    {
      "evidence_id": "4d5e6f7a-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
      "skill_name": "Docker",
      "canonical_slug": "docker",
      "repo_name": "task-management-api",
      "evidence_type": "dockerfile",
      "file_path": "Dockerfile",
      "matched_content": "FROM python:3.12-slim\nWORKDIR /app",
      "confidence_score": 0.80,
      "detected_at": "2026-09-01T14:35:00Z"
    }
  ],
  "meta": {
    "total": 2
  }
}
```

### 8.2 Get Evidence Item by ID
```http
GET /api/v1/evidence/{evidence_id}
Authorization: Bearer <access_token>
```
#### Response `200 OK`
```json
{
  "data": {
    "evidence_id": "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
    "skill_name": "FastAPI",
    "canonical_slug": "fastapi",
    "repo_name": "task-management-api",
    "evidence_type": "dependency",
    "file_path": "backend/requirements.txt",
    "matched_content": "fastapi>=0.110.0",
    "confidence_score": 0.85,
    "detected_at": "2026-09-01T14:35:00Z"
  }
}
```

### 8.3 List Aggregated Demonstrated Skills
```http
GET /api/v1/skills/demonstrated?evidence_level=HIGH&limit=20&offset=0
Authorization: Bearer <access_token>
```
#### Query Parameters
- `limit` (optional, integer, default: 20, max: 100): Page limit.
- `offset` (optional, integer, default: 0): Records to skip.
- `repository_id` (optional, UUID): Filter skills with evidence in a specific repository.
- `skill_id` (optional, UUID): Filter by canonical skill ID.
- `evidence_level` (optional, string): Filter by tier (`HIGH`, `MEDIUM`, `LOW`).
- `user_id` (optional, UUID): Scoped user ID filter.

#### Deterministic Aggregation Formula
1. Group evidence by repository for the skill.
2. $\text{repo\_score}_i = \max_{e \in \text{evidence}(r_i, \text{skill})} (e.\text{confidence\_score})$. Repeated analysis or duplicate evidence within the same repository does NOT artificially inflate confidence.
3. Multi-repository bounded combination:
   $$\text{multi\_repo\_score} = 1.0 - \prod_{i=1}^{N} (1.0 - \text{repo\_score}_i)$$
4. Clamp: $0.0 \le \text{confidence\_score} \le 1.0$, rounded to 2 decimal places.
5. Deterministic Evidence Levels:
   - `HIGH`: $\text{confidence\_score} \ge 0.85$
   - `MEDIUM`: $0.70 \le \text{confidence\_score} < 0.85$
   - `LOW`: $\text{confidence\_score} < 0.70$
6. **Inviolable Rule**: LLMs are strictly forbidden from creating, inferring, or altering demonstrated skills or their confidence scores.

#### Response `200 OK`
```json
{
  "data": [
    {
      "skill_id": "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
      "skill_name": "FastAPI",
      "slug": "fastapi",
      "category": "Backend Framework",
      "confidence_score": 0.95,
      "evidence_level": "HIGH",
      "evidence_count": 2,
      "repository_count": 1,
      "last_verified_at": "2026-09-01T14:35:00Z",
      "repositories": [
        {
          "repository_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
          "repo_name": "task-management-api",
          "repo_url": "https://github.com/user/task-management-api",
          "max_confidence": 0.95,
          "evidence_count": 2
        }
      ],
      "evidence_types": ["dependency"]
    }
  ],
  "meta": {
    "total": 1,
    "limit": 20,
    "offset": 0
  }
}
```

### 8.4 Get Demonstrated Skill Detail with Audit Trail
```http
GET /api/v1/skills/demonstrated/{skill_id}
Authorization: Bearer <access_token>
```
#### Response `200 OK`
```json
{
  "data": {
    "skill_id": "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
    "skill_name": "FastAPI",
    "slug": "fastapi",
    "category": "Backend Framework",
    "description": "Modern, fast web framework for building APIs with Python.",
    "confidence_score": 0.95,
    "evidence_level": "HIGH",
    "evidence_count": 2,
    "repository_count": 1,
    "last_verified_at": "2026-09-01T14:35:00Z",
    "repositories": [
      {
        "repository_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
        "repo_name": "task-management-api",
        "repo_url": "https://github.com/user/task-management-api",
        "max_confidence": 0.95,
        "evidence_count": 2
      }
    ],
    "evidence_types": ["dependency"],
    "evidence": [
      {
        "evidence_id": "9b8a7f6e-5d4c-3b2a-1f0e-9d8c7b6a5e4d",
        "repository_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
        "repo_name": "task-management-api",
        "skill_id": "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
        "skill_name": "FastAPI",
        "canonical_slug": "fastapi",
        "evidence_type": "dependency",
        "artifact_path": "backend/requirements.txt",
        "file_path": "backend/requirements.txt",
        "artifact_name": "requirements.txt",
        "evidence_description": "FastAPI is declared as a Python dependency in backend/requirements.txt.",
        "matched_content": "fastapi==0.115.0",
        "confidence_score": 0.95,
        "evidence_metadata": {
          "package": "fastapi",
          "manifest": "requirements.txt"
        },
        "detected_at": "2026-09-01T14:35:00Z",
        "created_at": "2026-09-01T14:35:00Z"
      }
    ]
  }
}
```
#### Response `404 Not Found`
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Demonstrated skill with id '...' not found.",
    "details": null
  }
}
```

---

## 9. Job Roles

Target industry tracks stored in `job_roles`.

### 9.1 List Job Roles
```http
GET /api/v1/roles?category=Engineering
```
#### Query Parameters
- `category` (optional, string): Filter by role category (e.g., `Engineering`, `Data`).
- `limit` (optional, default: 20): Maximum records.
- `offset` (optional, default: 0): Records to skip.

#### Response `200 OK`
```json
{
  "data": [
    {
      "role_id": "9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c",
      "title": "Backend Engineer",
      "slug": "backend-engineer",
      "category": "Engineering",
      "description": "Designs, implements, and maintains scalable server-side systems, databases, and APIs."
    },
    {
      "role_id": "0a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d",
      "title": "Full Stack Engineer",
      "slug": "full-stack-engineer",
      "category": "Engineering",
      "description": "Builds complete web applications covering frontend user interfaces and backend services."
    }
  ],
  "meta": {
    "total": 2
  }
}
```

### 9.2 Get Role by ID
```http
GET /api/v1/roles/{role_id}
```
#### Response `200 OK`
```json
{
  "data": {
    "role_id": "9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c",
    "title": "Backend Engineer",
    "slug": "backend-engineer",
    "category": "Engineering",
    "description": "Designs, implements, and maintains scalable server-side systems, databases, and APIs."
  }
}
```

---

## 10. Industry Skill Demand

> [!IMPORTANT]
> **Data Integrity Constraint**: `demand_score` is a database-derived statistical metric calculated from structured, permitted job-market data. The API exposes stored values directly from PostgreSQL table `skill_demand`. The LLM MUST NOT calculate, rewrite, estimate, or override `demand_score`.

### 10.1 List Industry Demand
```http
GET /api/v1/demand?role_id=9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c&location=India&limit=10
```
#### Query Parameters
- `role_id` (optional, UUID): Filter by target job role.
- `location` (optional, string, default: `India`): Market geographic scope.
- `limit` (optional, integer, default: 20): Maximum skills to return.
- `offset` (optional, integer, default: 0): Records to skip.

#### Response `200 OK`
```json
{
  "data": [
    {
      "skill_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
      "skill_name": "Python",
      "canonical_slug": "python",
      "role_title": "Backend Engineer",
      "location": "India",
      "sample_size": 14200,
      "demand_score": 0.68,
      "growth_rate": 0.08,
      "data_updated_at": "2026-09-01"
    },
    {
      "skill_id": "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
      "skill_name": "Docker",
      "canonical_slug": "docker",
      "role_title": "Backend Engineer",
      "location": "India",
      "sample_size": 14200,
      "demand_score": 0.51,
      "growth_rate": 0.12,
      "data_updated_at": "2026-09-01"
    }
  ],
  "meta": {
    "role_id": "9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c",
    "location": "India",
    "total": 2,
    "data_freshness": "2026-09-01"
  }
}
```

### 10.2 Get Role Demand Breakdown
```http
GET /api/v1/demand/{role_id}?location=India
```
#### Response `200 OK`
```json
{
  "data": {
    "role": {
      "role_id": "9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c",
      "title": "Backend Engineer",
      "slug": "backend-engineer",
      "category": "Engineering",
      "description": "Designs, implements, and maintains scalable server-side systems, databases, and APIs."
    },
    "skills": [
      {
        "skill_id": "64c288bb-5278-4506-a96f-f7e7a5004928",
        "skill_name": "Git",
        "canonical_slug": "git",
        "category": "Systems",
        "demand_score": 0.78,
        "growth_rate": 0.02,
        "sample_size": 14200,
        "location": "India",
        "data_updated_at": "2026-09-01"
      }
    ]
  },
  "meta": {
    "total": 13,
    "location": "India",
    "data_freshness": "2026-09-01",
    "total_demanded_skills": 13,
    "average_demand_score": 0.58,
    "highest_demand_score": 0.78,
    "lowest_demand_score": 0.35,
    "average_growth_rate": 0.08,
    "top_skill": "Git"
  }
}
```

### 10.3 Audit Demand Data Quality & Integrity
```http
GET /api/v1/demand/audit/quality
```
Audits the integrity of the industry demand data foundation via SQL aggregations:
- Confirms zero orphaned demand records
- Confirms zero out-of-bounds demand scores (`0.0 <= demand_score <= 1.0`)
- Confirms positive sample sizes (`sample_size > 0`)
- Confirms zero duplicate records (`UNIQUE (role_id, skill_id, location)`)
- Confirms 100% role coverage

#### Response `200 OK`
```json
{
  "data": {
    "status": "VALID",
    "total_roles": 5,
    "total_demand_records": 49,
    "roles_with_demand": 5,
    "orphaned_roles": 0,
    "orphaned_demand_records": 0,
    "out_of_bounds_scores": 0,
    "non_positive_sample_sizes": 0,
    "duplicate_records": 0,
    "data_freshness": "2026-09-01",
    "audit_timestamp": "2026-09-01T16:20:00Z"
  }
}
```

### 10.4 Skill Demand Ranking
```http
GET /api/v1/intelligence/skills/ranking?location=India&limit=50
```
Calculates weighted demand across the market:
`SUM(demand_score * sample_size) / SUM(sample_size)`.

### 10.5 Skill Across Roles
```http
GET /api/v1/intelligence/skills/{skill_id}/roles?location=India
```
Returns demand profile of a single skill across all canonical roles.

### 10.6 Role Comparison
```http
POST /api/v1/intelligence/roles/compare
Content-Type: application/json

{
  "role_ids": ["UUID_1", "UUID_2"],
  "location": "India"
}
```
Compares 2 to 5 canonical job roles deterministically. Identifies shared skills, role-specific specializations, and demand score differentials.

### 10.7 Role Market Signals
```http
GET /api/v1/intelligence/roles/{role_id}/signals?location=India
```
Returns market-demand signals including counts of rising, stable, and declining skills, top 5 demanded skills, and top 5 fastest growing skills.

### 10.8 Demand Trends
```http
GET /api/v1/intelligence/trends?location=India&limit=20
```
Lists demand records enriched with growth trajectory classifications (`RISING`, `STABLE`, `DECLINING`), ordered by growth rate descending.

---

## 11. Skill Gap Analysis

Combines claimed skills, verified project evidence, target role requirements, and mathematical industry demand metrics.

### Evidence Classification Tiers
- `HIGH`: Claimed in resume AND demonstrated by repository code artifacts.
- `MEDIUM`: Demonstrated by repository code artifacts without explicit resume claim.
- `LOW`: Claimed in resume only; zero repository code artifacts detected.
- `MISSING`: Required by target role but neither claimed nor demonstrated.

### Priority Score Formula
The engine prioritizes skill gaps using a deterministic formula with configurable weights:
$$\text{Priority} = w_{\text{demand}} \cdot \text{DemandScore} + w_{\text{growth}} \cdot \text{GrowthRate} + w_{\text{gap}} \cdot (1 - \text{EvidenceScore}) + \text{PrerequisiteBonus}$$

Where:
- $w_{\text{demand}} = 0.40$ (market baseline demand weight)
- $w_{\text{growth}} = 0.20$ (market trend trajectory weight)
- $w_{\text{gap}} = 0.30$ (candidate proficiency deficit weight)
- $\text{PrerequisiteBonus} = 0.10$ (applied if all prerequisites in DAG are satisfied)

### 11.1 Retrieve Skill Gaps for Role
```http
GET /api/v1/gaps/{role_id}?location=India&status=MISSING&limit=50&offset=0
X-User-Id: <optional_user_id>
```
Computes and returns the candidate's deterministic skill gap analysis against a canonical target role.
Combines:
- Industry demand requirements for the target role (`skill_demand`)
- Candidate resume claims (`user_claimed_skills`)
- Candidate GitHub demonstrated evidence (`demonstrated_skills`)
Classifies each skill into `STRONG`, `PARTIAL`, or `MISSING`.

#### Query Parameters:
- `location` (string, optional, default: `"India"`, 1–64 chars): Market geographic scope. Blank or whitespace returns `422`.
- `status` (string, optional): Filter by gap status (`STRONG`, `PARTIAL`, `MISSING`). Invalid value returns `422`.
- `limit` (integer, optional, 1–100): Maximum records to return. Invalid bounds return `422`.
- `offset` (integer, optional, default: 0, $\ge 0$): Pagination offset. Negative values return `422`.
- `user_id` (UUID, optional): Scoped candidate ID. If mismatched with `X-User-Id`, returns `403 Forbidden`. If non-existent, returns `404 Not Found`.

#### Response `200 OK`
```json
{
  "data": {
    "role": {
      "role_id": "9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c",
      "title": "Backend Engineer",
      "slug": "backend-engineer",
      "category": "Backend",
      "description": "Designs, implements, and maintains server-side systems."
    },
    "location": "India",
    "summary": {
      "total_required_skills": 13,
      "strong_count": 2,
      "partial_count": 3,
      "missing_count": 8
    },
    "skills": [
      {
        "id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
        "skill_id": "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
        "skill_name": "Docker",
        "canonical_slug": "docker",
        "category": "DevOps",
        "status": "MISSING",
        "demand_score": 0.51,
        "growth_rate": 0.12,
        "claimed": false,
        "claim_confidence": 0.0,
        "demonstrated": false,
        "demonstrated_score": 0.0,
        "evidence_level": null,
        "evidence_count": 0,
        "priority_score": 0.71,
        "priority_level": "HIGH",
        "scoring_version": "v1"
      },
      {
        "id": "2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e",
        "skill_id": "2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e",
        "skill_name": "Python",
        "canonical_slug": "python",
        "category": "Programming",
        "status": "STRONG",
        "demand_score": 0.78,
        "growth_rate": 0.08,
        "claimed": true,
        "claim_confidence": 1.0,
        "demonstrated": true,
        "demonstrated_score": 0.95,
        "evidence_level": "HIGH",
        "evidence_count": 2
      }
    ]
  },
  "meta": {
    "user_id": "8f7e6d5c-4b3a-2f1e-0d9c-8b7a6f5e4d3c",
    "location": "India",
    "calculated_at": "2026-09-02T09:15:00Z",
    "data_freshness": "2026-09-01",
    "scoring_version": "v1"
  }
}
```

### 11.2 Execute Gap Analysis
```http
POST /api/v1/gaps/analyze
Content-Type: application/json
X-User-Id: <optional_user_id>

{
  "target_role_id": "9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c",
  "location": "India",
  "user_id": "8f7e6d5c-4b3a-2f1e-0d9c-8b7a6f5e4d3c"
}
```
Idempotently analyzes and reconciles candidate skill gaps.
- **Idempotency**: Repeated calls do not duplicate rows or alter scores.
- **Stale Cleanup**: Purges obsolete skill requirements if role requirements change.
- **Security**: Validates location (non-blank). Returns `403 Forbidden` if `user_id` conflicts with `X-User-Id`. Returns `404 Not Found` if user does not exist.

#### Response `200 OK`
Returns the deterministic skill gap analysis object (`SkillGapResponse`).

### 11.3 Retrieve Prioritized Actionable Gaps for Role
```http
GET /api/v1/gaps/{role_id}/priorities?location=India&priority_level=HIGH&status=MISSING&limit=50&offset=0
X-User-Id: <optional_user_id>
```
Retrieves candidate's deterministically prioritized actionable skill gaps (`MISSING` and `PARTIAL` only). `STRONG` skills are excluded.

#### Query Parameters:
- `location` (string, optional, default: `"India"`, 1–64 chars): Market geographic scope.
- `priority_level` (string, optional): Filter by priority tier (`HIGH`, `MEDIUM`, `LOW`). Invalid value returns `422`.
- `status` (string, optional): Filter by actionable gap severity (`MISSING`, `PARTIAL`). Invalid value (such as `STRONG`) returns `422`.
- `limit` (integer, optional, 1–100): Maximum records to return.
- `offset` (integer, optional, default: 0, $\ge 0$): Pagination offset.
- `user_id` (UUID, optional): Scoped candidate ID. IDOR protected via `X-User-Id`.

#### Priority Model (`scoring_version: "v1"`):
$$\text{growth\_signal} = \text{clamp}\left(\frac{\text{growth\_rate} + 1.0}{2.0}, 0.0, 1.0\right)$$
$$\text{priority\_score} = \text{gap\_severity\_weight} \cdot (0.70 \cdot \text{demand\_score} + 0.30 \cdot \text{growth\_signal})$$
Where:
- $\text{gap\_severity\_weight}$: `MISSING` = $1.0$, `PARTIAL` = $0.5$, `STRONG` = $0.0$
- Priority Tiers:
  - `HIGH`: $\text{priority\_score} \ge 0.67$
  - `MEDIUM`: $0.34 \le \text{priority\_score} < 0.67$
  - `LOW`: $\text{priority\_score} < 0.34$

#### Deterministic Ordering:
1. `priority_score DESC`
2. `MISSING before PARTIAL`
3. `demand_score DESC`
4. `growth_rate DESC`
5. `skill.name ASC`
6. `skill.id ASC`

#### Response `200 OK`
```json
{
  "data": {
    "role": {
      "role_id": "9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c",
      "title": "Backend Engineer",
      "slug": "backend-engineer",
      "category": "Backend",
      "description": "Designs, implements, and maintains server-side systems."
    },
    "location": "India",
    "summary": {
      "total_actionable_gaps": 7,
      "high_priority_count": 3,
      "medium_priority_count": 3,
      "low_priority_count": 1,
      "missing_count": 6,
      "partial_count": 1
    },
    "gaps": [
      {
        "skill_id": "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
        "skill_name": "Docker",
        "canonical_slug": "docker",
        "category": "DevOps",
        "status": "MISSING",
        "priority_score": 0.71,
        "priority_level": "HIGH",
        "demand_score": 0.80,
        "growth_rate": 0.12,
        "claimed": false,
        "claim_confidence": 0.0,
        "demonstrated": false,
        "demonstrated_score": 0.0,
        "evidence_level": null,
        "evidence_count": 0,
        "location": "India",
        "explanation": "HIGH priority: Skill is missing from your profile with high market demand (80%) and rapidly growing (+12% YoY)."
      }
    ]
  },
  "meta": {
    "user_id": "8f7e6d5c-4b3a-2f1e-0d9c-8b7a6f5e4d3c",
    "location": "India",
    "calculated_at": "2026-09-02T10:00:00Z",
    "data_freshness": "2026-09-01",
    "scoring_version": "v1"
  }
}
```

### 11.4 Retrieve Gap Evidence Chain for Skill
```http
GET /api/v1/gaps/{role_id}/skills/{skill_id}/evidence?location=India
X-User-Id: <optional_user_id>
```
Retrieves the complete deterministic evidence chain and audit trail for a specific skill gap:
- **Candidate Evidence**: Extracted resume claims (`user_claimed_skills`, `resumes`) and verified GitHub code artifacts (`demonstrated_skills`, `project_evidence`, `github_repositories`).
- **Market Evidence**: Canonical industry demand statistics (`skill_demand`) for the target role and location.
- **Deterministic Reasoning**: Rule-based grounded explanations for status classification and priority tier without LLM inference.

#### Response `200 OK`
```json
{
  "data": {
    "skill_id": "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
    "skill_name": "Python",
    "canonical_slug": "python",
    "category": "Programming",
    "status": "STRONG",
    "priority_score": null,
    "priority_level": null,
    "candidate_evidence": {
      "has_evidence": true,
      "resume_claims": [
        {
          "id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
          "raw_mention": "Python 3.12 Core & Asyncio",
          "confidence_score": 1.0,
          "source": "resume",
          "resume_id": "8f7e6d5c-4b3a-2f1e-0d9c-8b7a6f5e4d3c",
          "resume_file_name": "resume_2026.pdf",
          "created_at": "2026-09-02T09:00:00Z"
        }
      ],
      "github_demonstrated": {
        "confidence_score": 0.92,
        "evidence_level": "HIGH",
        "evidence_count": 1,
        "repository_count": 1,
        "last_verified_at": "2026-09-02T09:10:00Z"
      },
      "github_artifacts": [
        {
          "id": "2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e",
          "repo_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
          "repo_name": "live-async-api",
          "repo_full_name": "user/live-async-api",
          "repo_url": "https://github.com/user/live-async-api",
          "evidence_type": "MANIFEST_DEPENDENCY",
          "file_path": "requirements.txt",
          "artifact_name": "uvicorn",
          "matched_content": "uvicorn>=0.28.0",
          "confidence_score": 0.92,
          "detected_at": "2026-09-02T09:10:00Z"
        }
      ]
    },
    "market_evidence": {
      "role_id": "9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c",
      "role_title": "Backend Engineer",
      "role_slug": "backend-engineer",
      "location": "India",
      "demand_score": 0.78,
      "growth_rate": 0.08,
      "sample_size": 10000,
      "data_updated_at": "2026-09-01T00:00:00Z"
    },
    "reasoning": {
      "classification_reason": "Strong because verified GitHub code artifacts demonstrate this skill at HIGH confidence (92%) across 1 repository(ies) with 1 evidence artifact(s).",
      "priority_reason": "Skill is already sufficiently demonstrated (STRONG). It is not considered an actionable gap.",
      "scoring_version": "v1"
    }
  },
  "meta": {
    "user_id": "8f7e6d5c-4b3a-2f1e-0d9c-8b7a6f5e4d3c",
    "location": "India",
    "calculated_at": "2026-09-02T10:15:00Z",
    "data_freshness": "2026-09-01",
    "scoring_version": "v1"
  }
}
```

### 11.5 Active Gaps State
```http
GET /api/v1/gaps
```
#### Response `200 OK`
Returns the latest computed gap analysis state for the authenticated user.

---

## 12. Roadmap APIs

The Roadmap Engine sequences prioritized skill gaps into structured learning milestones:
```text
Ranked Skill Gaps
      ↓
Prerequisite DAG Inspection (skill_dependencies)
      ↓
Topological Sort with Priority Tie-Breaking
      ↓
Milestone Clustering & Workload Partitioning
      ↓
Curated Resource Association (learning_resources)
      ↓
Hands-On Project Assignment & GitHub Rubric
      ↓
Persisted Roadmap & Milestones (roadmaps, roadmap_milestones)
```

The LLM is strictly prohibited from altering topological prerequisite orderings.

### 12.1 Generate Personalized Roadmap
```http
POST /api/v1/roadmaps/generate
Authorization: Bearer <access_token>
Content-Type: application/json
```
#### Request Body
```json
{
  "role_id": "9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c",
  "weekly_hours_commitment": 10
}
```
#### Response `201 Created`
```json
{
  "data": {
    "roadmap_id": "5e6f7a8b-9c0d-1e2f-3a4b-5c6d7e8f9a0b",
    "role_title": "Backend Engineer",
    "status": "ACTIVE",
    "total_milestones": 3,
    "estimated_weeks": 6,
    "milestones": [
      {
        "milestone_id": "6f7a8b9c-0d1e-2f3a-4b5c-6d7e8f9a0b1c",
        "sequence_order": 1,
        "title": "Containerization & Microservices Infrastructure",
        "description": "Master Docker containerization, multi-container Docker Compose architectures, and image optimization.",
        "target_skills": ["Docker", "Docker Compose"],
        "estimated_hours": 15,
        "status": "IN_PROGRESS"
      },
      {
        "milestone_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
        "sequence_order": 2,
        "title": "Cloud Native Orchestration",
        "description": "Deploy resilient microservices to Kubernetes clusters with ingress controllers and persistent volumes.",
        "target_skills": ["Kubernetes"],
        "estimated_hours": 20,
        "status": "NOT_STARTED"
      }
    ],
    "created_at": "2026-09-01T14:45:00Z"
  }
}
```

### 12.2 List User Roadmaps
```http
GET /api/v1/roadmaps
Authorization: Bearer <access_token>
```
#### Response `200 OK`
```json
{
  "data": [
    {
      "roadmap_id": "5e6f7a8b-9c0d-1e2f-3a4b-5c6d7e8f9a0b",
      "role_title": "Backend Engineer",
      "status": "ACTIVE",
      "total_milestones": 3,
      "created_at": "2026-09-01T14:45:00Z"
    }
  ],
  "meta": { "total": 1 }
}
```

### 12.3 Get Roadmap Details
```http
GET /api/v1/roadmaps/{roadmap_id}
Authorization: Bearer <access_token>
```
#### Response `200 OK`
Returns the complete roadmap object with milestones.

### 12.4 Get Roadmap Milestones
```http
GET /api/v1/roadmaps/{roadmap_id}/milestones
Authorization: Bearer <access_token>
```
#### Response `200 OK`
Returns the ordered array of milestones for `{roadmap_id}`.

### 12.5 Update Milestone Status
```http
PATCH /api/v1/roadmaps/{roadmap_id}/milestones/{milestone_id}
Authorization: Bearer <access_token>
Content-Type: application/json
```
#### Request Body
```json
{
  "status": "IN_PROGRESS"
}
```
#### Allowed Statuses
`NOT_STARTED`, `IN_PROGRESS`, `SUBMITTED`, `VERIFIED`.

#### Response `200 OK`
```json
{
  "data": {
    "milestone_id": "6f7a8b9c-0d1e-2f3a-4b5c-6d7e8f9a0b1c",
    "status": "IN_PROGRESS",
    "updated_at": "2026-09-01T14:50:00Z"
  }
}
```

---

## 13. Learning Resources

Educational resources mapped to canonical skills stored in `learning_resources`.

### 13.1 List Learning Resources
```http
GET /api/v1/resources?skill_id=3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f&difficulty=beginner
```
#### Query Parameters
- `skill_id` (optional, UUID): Filter by canonical skill.
- `difficulty` (optional, string): `beginner`, `intermediate`, `advanced`.
- `resource_type` (optional, string): `documentation`, `course`, `tutorial`, `book`.
- `limit` (optional, integer, default: 20): Maximum records.
- `offset` (optional, integer, default: 0): Records to skip.

#### Response `200 OK`
```json
{
  "data": [
    {
      "resource_id": "8b9c0d1e-2f3a-4b5c-6d7e-8f9a0b1c2d3e",
      "skill_name": "Docker",
      "title": "Official Docker Getting Started Guide",
      "url": "https://docs.docker.com/get-started/",
      "resource_type": "documentation",
      "difficulty": "beginner",
      "rating": 4.8
    }
  ],
  "meta": { "total": 1 }
}
```

### 13.2 Get Resource Details
```http
GET /api/v1/resources/{resource_id}
```
#### Response `200 OK`
Returns the single learning resource entity matching `{resource_id}`.

---

## 14. Resource Recommendation

Selects curated learning materials using deterministic filters and semantic vector similarity in PostgreSQL `pgvector`. RAG is forbidden from fabricating resource URLs or metadata.

### 14.1 Get Recommendations for Milestone
```http
POST /api/v1/resources/recommend
Authorization: Bearer <access_token>
Content-Type: application/json
```
#### Request Body
```json
{
  "milestone_id": "6f7a8b9c-0d1e-2f3a-4b5c-6d7e8f9a0b1c",
  "limit": 3
}
```
#### Selection Pipeline
1. Identifies `target_skills` in the milestone.
2. Inspects candidate's current evidence level (skips basic content if prior evidence exists).
3. Matches resources in `learning_resources` by canonical `skill_id`.
4. Ranks candidates by `rating` and cosine similarity against milestone requirements.

#### Response `200 OK`
```json
{
  "data": {
    "milestone_id": "6f7a8b9c-0d1e-2f3a-4b5c-6d7e8f9a0b1c",
    "recommendations": [
      {
        "resource_id": "8b9c0d1e-2f3a-4b5c-6d7e-8f9a0b1c2d3e",
        "title": "Official Docker Getting Started Guide",
        "url": "https://docs.docker.com/get-started/",
        "resource_type": "documentation",
        "difficulty": "beginner",
        "skill_name": "Docker",
        "relevance_score": 0.94
      }
    ]
  }
}
```

---

## 15. AI Assistant

The Contextual AI Assistant provides grounded guidance, explains prerequisite rationale, and clarifies project rubrics.

### Retrieval & Grounding Pipeline
```text
User Prompt + Authenticated User Context
                 ↓
Query Embedding Generation (pgvector)
                 ↓
Cosine Similarity Retrieval from rag_documents
                 ↓
Deterministic Grounding Facts Injected:
  • Target Role & Market Demand % from skill_demand
  • Verified User Skills & Gaps from project_evidence
  • Active Roadmap Milestone Status
                 ↓
LLM Prompt Assembly & Structured Generation
                 ↓
Grounded Response Returned
```

The LLM cannot modify system-of-record data, nor can it invent numerical demand figures. Responses are returned as structured JSON payloads.

### 15.1 Assistant Chat
```http
POST /api/v1/assistant/chat
Authorization: Bearer <access_token>
Content-Type: application/json
```
#### Request Body
```json
{
  "message": "Why is Docker scheduled before Kubernetes in my roadmap?",
  "active_milestone_id": "6f7a8b9c-0d1e-2f3a-4b5c-6d7e8f9a0b1c"
}
```
#### Response `200 OK`
```json
{
  "data": {
    "reply": "Docker is sequenced before Kubernetes because container runtime fundamentals are a hard architectural prerequisite for cluster orchestration in our taxonomy. In the Indian market for Backend Engineers, Docker exhibits 51% demand with +12% annual growth. Mastering container build files, networking, and multi-container Docker Compose provides the practical artifacts required before deploying distributed Kubernetes pods.",
    "grounded_facts": {
      "target_role": "Backend Engineer",
      "market_demand": "51%",
      "growth_rate": "+12%",
      "dependency_relationship": "Docker is a hard prerequisite for Kubernetes in canonical taxonomy"
    },
    "referenced_sources": [
      {
        "title": "SkillForge Taxonomy Prerequisite Graph",
        "corpus_type": "taxonomy"
      }
    ]
  }
}
```

---

## 16. GitHub Project Verification

Automated verification loop evaluating hands-on candidate repositories against the milestone rubric. Merely creating an empty repository does not pass verification.

### 16.1 Verify Completed Milestone
```http
POST /api/v1/verify/project
Authorization: Bearer <access_token>
Content-Type: application/json
```
#### Request Body
```json
{
  "milestone_id": "6f7a8b9c-0d1e-2f3a-4b5c-6d7e8f9a0b1c",
  "repository_url": "https://github.com/janedoe/task-management-api"
}
```
#### Evaluation Pipeline
```text
POST /verify/project
       ↓
GitHub API Repository Tree Scan
       ↓
Inspect Manifests, Dockerfile, Workflows, Source
       ↓
Rubric Evaluation against Milestone Target Skills
       ↓
Outcome Decision:
  ├── PASS (Score >= 0.70):
  │     • Insert rows into project_evidence
  │     • Update roadmap_milestones status to 'VERIFIED'
  │     • Elevate skill evidence tiers to 'DEMONSTRATED' / 'HIGH'
  │     • Recompute active skill gaps
  └── FAIL (Score < 0.70):
        • Return detailed missing criteria checklist
        • Status remains 'IN_PROGRESS'
```

#### Response `200 OK (Verification Passed)`
```json
{
  "data": {
    "milestone_id": "6f7a8b9c-0d1e-2f3a-4b5c-6d7e8f9a0b1c",
    "verification_status": "VERIFIED",
    "score": 0.85,
    "evaluated_criteria": [
      { "criterion": "Dockerfile present and syntactically valid", "passed": true },
      { "criterion": "docker-compose.yml multi-service configuration", "passed": true },
      { "criterion": "Service health check defined", "passed": true }
    ],
    "elevated_skills": ["Docker", "Docker Compose"],
    "next_milestone_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d"
  }
}
```

#### Response `200 OK (Verification Failed)`
```json
{
  "data": {
    "milestone_id": "6f7a8b9c-0d1e-2f3a-4b5c-6d7e8f9a0b1c",
    "verification_status": "REJECTED",
    "score": 0.40,
    "evaluated_criteria": [
      { "criterion": "Dockerfile present and syntactically valid", "passed": true },
      { "criterion": "docker-compose.yml multi-service configuration", "passed": false },
      { "criterion": "Service health check defined", "passed": false }
    ],
    "missing_evidence": [
      "No docker-compose.yml file detected in repository root.",
      "Dockerfile is missing HEALTHCHECK directive or service check."
    ],
    "actionable_checklist": [
      "Add a valid docker-compose.yml coordinating your web service and database.",
      "Include a HEALTHCHECK CMD curl in your Dockerfile."
    ]
  }
}
```

---

## 17. Dashboard API

Consolidated dashboard endpoint designed for the Next.js frontend to eliminate redundant roundtrips and avoid duplicating business logic client-side.

### 17.1 Get Dashboard State
```http
GET /api/v1/dashboard
Authorization: Bearer <access_token>
```
#### Response `200 OK`
```json
{
  "data": {
    "user": {
      "user_id": "8a3e72c1-6789-4a12-b345-987654321abc",
      "full_name": "Jane Doe",
      "target_role": "Backend Engineer",
      "weekly_hours_commitment": 10
    },
    "skills_summary": {
      "claimed_count": 8,
      "demonstrated_count": 4,
      "verified_count": 2
    },
    "top_skill_gaps": [
      {
        "skill_name": "Docker",
        "priority_rank": 1,
        "demand_score": 0.51,
        "evidence_tier": "MISSING"
      },
      {
        "skill_name": "Kubernetes",
        "priority_rank": 2,
        "demand_score": 0.38,
        "evidence_tier": "MISSING"
      }
    ],
    "active_roadmap": {
      "roadmap_id": "5e6f7a8b-9c0d-1e2f-3a4b-5c6d7e8f9a0b",
      "status": "ACTIVE",
      "current_milestone": {
        "milestone_id": "6f7a8b9c-0d1e-2f3a-4b5c-6d7e8f9a0b1c",
        "sequence_order": 1,
        "title": "Containerization & Microservices Infrastructure",
        "status": "IN_PROGRESS"
      },
      "completed_milestones_count": 0,
      "total_milestones_count": 3
    }
  }
}
```

---

## 18. Common Response Format

All API responses conform to standard JSON envelopes.

### 18.1 Single Resource Envelope
```json
{
  "data": { ... }
}
```

### 18.2 Collection Envelope with Pagination Metadata
```json
{
  "data": [ ... ],
  "meta": {
    "total": 42,
    "limit": 20,
    "offset": 0
  }
}
```

### 18.3 HTTP Status Codes Used
| Status Code | Meaning | Standard Usage |
| :--- | :--- | :--- |
| `200 OK` | Success | Successful resource retrieval, update, or calculation. |
| `201 Created` | Resource Created | Successful entity creation (register, upload, generate). |
| `204 No Content` | Success (No Body) | Successful resource deletion. |
| `400 Bad Request` | Client Error | Invalid format, malformed input, magic-byte mismatch. |
| `401 Unauthorized` | Authentication Failure | Missing, invalid, or expired JWT bearer token. |
| `403 Forbidden` | Access Denied | Accessing a resource owned by another user. |
| `404 Not Found` | Resource Absent | Requested resource does not exist in datastore. |
| `409 Conflict` | State Conflict | Duplicate unique field (e.g. duplicate email). |
| `413 Payload Too Large` | File Too Large | File upload exceeds maximum threshold (5 MB). |
| `422 Unprocessable Entity` | Schema Error | Pydantic payload validation failure. |
| `500 Internal Server Error` | Server Error | Unhandled backend exception. |

---

## 19. Error Response Format

Errors return consistent payloads with standard error codes:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested roadmap milestone does not exist.",
    "details": {
      "resource_type": "milestone",
      "resource_id": "6f7a8b9c-0d1e-2f3a-4b5c-6d7e8f9a0b1c"
    }
  }
}
```

### Standard Error Codes
| Error Code | HTTP Status | Description |
| :--- | :--- | :--- |
| `VALIDATION_ERROR` | 422 / 400 | Request parameter or payload failed Pydantic validation. |
| `UNSUPPORTED_MEDIA_TYPE` | 400 | File is not an accepted PDF or DOCX binary. |
| `FILE_TOO_LARGE` | 413 | File exceeds 5 MB size limit. |
| `AUTHENTICATION_REQUIRED` | 401 | Missing or invalid Authorization header. |
| `FORBIDDEN_ACCESS` | 403 | User does not own the requested resource. |
| `RESOURCE_NOT_FOUND` | 404 | Entity not found in database. |
| `DUPLICATE_RESOURCE` | 409 | Resource violates unique constraint. |
| `INTERNAL_SERVER_ERROR` | 500 | Unhandled exception (sanitized in production). |

*Security Rule*: Stack traces, internal file paths, database connection strings, and tokens are NEVER exposed in error responses.

---

## 20. Validation Rules

| Field / Parameter | Type | Validation Constraints |
| :--- | :--- | :--- |
| `id` / `*_id` | UUID | Valid RFC 4122 UUIDv4 string. |
| `email` | String | Valid email address; max 255 characters; normalized lowercase. |
| `password` | String | Minimum 8 characters; at least 1 number and 1 special character. |
| `file` (Resume) | Binary | Strictly `.pdf` or `.docx`; max 5 MB ($5 \times 1024 \times 1024$ bytes); valid magic bytes (`%PDF-` or `PK\x03\x04`). |
| `confidence_score` | Float | $0.0 \le \text{confidence\_score} \le 1.0$. |
| `demand_score` | Float | $0.0 \le \text{demand\_score} \le 1.0$. |
| `growth_rate` | Float | Real number representing YoY growth (e.g. $-0.50 \le \text{growth\_rate} \le +2.00$). |
| `weekly_hours` | Integer | $5 \le \text{weekly\_hours\_commitment} \le 40$. |
| `repository_url` | String | Valid HTTP/HTTPS GitHub URL (`https://github.com/:owner/:repo`). |

---

## 21. Authorization & Ownership

All user-specific endpoints enforce strict ownership:
- Queries execute scoped database operations: `SELECT ... WHERE user_id = current_user.id`.
- Accessing another user's resume, repository, roadmap, evidence, or assistant history returns `404 Not Found` or `403 Forbidden`.
- Global public read-only catalogs (`skills`, `job_roles`, `skill_demand`, `learning_resources`) are readable by all authenticated or guest users.

---

## 22. API-to-Database Mapping

| Endpoint | HTTP Method | Primary Database Tables |
| :--- | :--- | :--- |
| `/auth/register`, `/auth/login`, `/auth/me` | POST, GET | `users` |
| `/users/me` | GET, PATCH | `users` |
| `/resumes/upload`, `/resumes`, `/resumes/{id}` | POST, GET, DELETE | `resumes`, `users` |
| `/skills/claimed` | GET | `user_claimed_skills`, `skills` |
| `/github/connect`, `/github/repositories` | POST, GET | `github_repositories`, `users` |
| `/github/analyze` | POST | `github_repositories`, `project_evidence`, `skills` |
| `/evidence`, `/evidence/{id}` | GET | `project_evidence`, `skills`, `github_repositories` |
| `/roles`, `/roles/{id}` | GET | `job_roles` |
| `/demand`, `/demand/{role_id}` | GET | `skill_demand`, `job_roles`, `skills` |
| `/gaps/analyze`, `/gaps` | POST, GET | `user_claimed_skills`, `project_evidence`, `skill_demand`, `skill_dependencies` |
| `/roadmaps/generate`, `/roadmaps` | POST, GET | `roadmaps`, `roadmap_milestones`, `skill_dependencies`, `skills` |
| `/roadmaps/{id}/milestones/{m_id}` | PATCH | `roadmap_milestones` |
| `/resources`, `/resources/{id}` | GET | `learning_resources`, `skills` |
| `/resources/recommend` | POST | `learning_resources`, `roadmap_milestones`, `skills` |
| `/assistant/chat` | POST | `rag_documents`, `skill_demand`, `project_evidence`, `roadmaps` |
| `/verify/project` | POST | `roadmap_milestones`, `project_evidence`, `github_repositories`, `skills` |
| `/dashboard` | GET | `users`, `user_claimed_skills`, `project_evidence`, `roadmaps`, `roadmap_milestones` |

---

## 23. API Security

1. **Authentication & Password Security**: Passwords hashed using bcrypt/argon2 with salting. Access tokens use HMAC-SHA256 with an ephemeral secret key loaded from environment variables.
2. **Path Traversal & Safe File Storage**: Client filenames are sanitized with `os.path.basename` and regex scrubbing. Disk storage exclusively uses `<uuid>.<ext>` inside `backend/uploads/resumes/` (isolated from source code and ignored by git).
3. **MIME & Magic Byte Verification**: Uploads are verified by file extension AND magic byte header inspections (`%PDF-` and `PK\x03\x04`). Spoofed extensions are rejected with HTTP 400.
4. **Token Protection**: GitHub Personal Access Tokens (PATs) are never saved in plaintext and never serialized in API responses.
5. **SSRF Protection**: Repository verification validates that URLs resolve strictly to `github.com` domains before HTTP queries are issued.
6. **Prompt Injection Hardening**: Resumes, commit logs, and repository files are treated as untrusted user input and enclosed within XML/Markdown delimiter boundaries in LLM prompts.

---

## 24. LLM Boundary

| Allowed LLM Capabilities | Strictly Prohibited Actions |
| :--- | :--- |
| Extracting entities (skills, experience) from unstructured resume text. | Inventing or generating numerical industry-demand percentages. |
| Resolving ambiguous skill mentions to canonical taxonomy slugs. | Modifying or overriding database `demand_score` values. |
| Providing conversational explanations for roadmap milestones. | Declaring a skill verified without concrete repository evidence. |
| Generating milestone descriptions and project challenge briefs. | Bypassing or reordering prerequisite DAG relationships. |
| Explaining rubric failures and actionable improvement steps. | Fabricating learning resource URLs or metadata. |

---

## 25. API Sequence Examples

### Example A — Resume Ingestion
```text
Client -> POST /api/v1/resumes/upload (binary PDF)
          FastAPI verifies magic bytes (%PDF-) and size (< 5 MB)
          FastAPI writes uploads/resumes/<uuid>.pdf and records row in 'resumes'
       <- 201 Created (resume_id)
```

### Example B — GitHub Repository Analysis
```text
Client -> POST /api/v1/github/connect (username: 'janedoe')
       <- 200 OK (discovered_repositories: 4)
Client -> POST /api/v1/github/analyze (repo_ids: ['...'])
          Backend scans package manifests (requirements.txt, Dockerfile)
          Backend creates audit records in 'project_evidence'
       <- 200 OK (demonstrated_skills: ['FastAPI', 'Docker'])
```

### Example C — Skill Gap & Priority Calculation
```text
Client -> POST /api/v1/gaps/analyze (target_role_id: '...')
          Backend loads claimed skills (resume) + demonstrated skills (evidence)
          Backend retrieves empirical demand_score from 'skill_demand'
          Backend calculates Priority Score using deterministic formula
       <- 200 OK (prioritized_gaps: [ { skill: 'Docker', priority_rank: 1, evidence: 'MISSING' } ])
```

### Example D — Personalized Roadmap Generation
```text
Client -> POST /api/v1/roadmaps/generate (role_id: '...', weekly_hours: 10)
          Backend extracts required subgraph from 'skill_dependencies'
          Topological sort orders prerequisites before advanced skills
          Partitions skills into sequential milestones with curated resources
       <- 201 Created (roadmap_id, milestones: [ { order: 1, title: 'Docker Basics' } ])
```

### Example E — Hands-On Project Verification
```text
Client -> POST /api/v1/verify/project (milestone_id: '...', repo_url: '...')
          Backend scans candidate repo tree for Dockerfile and compose file
          Passes criteria -> creates project_evidence, marks milestone 'VERIFIED'
       <- 200 OK (verification_status: 'VERIFIED', next_milestone_id: '...')
```

---

## 26. OpenAPI Compatibility

This API specification maps directly to FastAPI and Pydantic schemas. 
When the FastAPI application runs, the interactive documentation is automatically accessible at:
- **Swagger UI**: `/api/v1/docs`
- **ReDoc**: `/api/v1/redoc`
- **OpenAPI JSON**: `/api/v1/openapi.json`

---

## 27. Implementation Status

The implementation status is based on inspection of the actual repository code:

| Endpoint | Purpose | MVP Phase | Implementation Status |
| :--- | :--- | :--- | :--- |
| `GET /` | Operational API metadata | Phase 1 | **IMPLEMENTED** |
| `GET /health` | Application status probe | Phase 1 | **IMPLEMENTED** |
| `GET /health/db` | PostgreSQL & pgvector check | Phase 1 | **IMPLEMENTED** |
| `GET /api/v1/health` | Mounted v1 application probe | Phase 1 | **IMPLEMENTED** |
| `GET /api/v1/health/db` | Mounted v1 database probe | Phase 1 | **IMPLEMENTED** |
| `POST /api/v1/resumes/upload` | Resume document upload, section extraction & skill normalization | Phase 2 (CP 1–4) | **IMPLEMENTED** |
| `GET /api/v1/resumes` | List user resumes with pagination | Phase 2 (CP 4) | **IMPLEMENTED** |
| `GET /api/v1/resumes/{id}` | Get resume parsed metadata, sections & claimed skills | Phase 2 (CP 2, 4) | **IMPLEMENTED** |
| `DELETE /api/v1/resumes/{id}` | Delete resume document and cascade claimed skills | Phase 2 (CP 4) | **IMPLEMENTED** |
| `POST /api/v1/auth/register` | User registration | Phase 1 / 2 | PLANNED |
| `POST /api/v1/auth/login` | JWT authentication login | Phase 1 / 2 | PLANNED |
| `GET /api/v1/auth/me` | Current user identity | Phase 1 / 2 | PLANNED |
| `GET /api/v1/users/me` | User profile retrieval | Phase 1 / 2 | PLANNED |
| `PATCH /api/v1/users/me` | Update target role and preferences | Phase 1 / 2 | PLANNED |
| `GET /api/v1/skills/claimed` | List resume-claimed skills | Phase 2 (CP 3, 4) | **IMPLEMENTED** |
| `GET /api/v1/skills/demonstrated` | List aggregated demonstrated skills | Phase 3 (CP 1–4) | **IMPLEMENTED** |
| `GET /api/v1/skills/demonstrated/{id}` | Get demonstrated skill with audit trail | Phase 3 (CP 1–4) | **IMPLEMENTED** |
| `POST /api/v1/github/connect` | Discover user GitHub repositories | Phase 3 (CP 1–4) | **IMPLEMENTED** |
| `GET /api/v1/github/repositories` | List discovered repositories | Phase 3 (CP 1–4) | **IMPLEMENTED** |
| `GET /api/v1/github/repositories/{id}` | Inspect repository metadata | Phase 3 (CP 1–4) | **IMPLEMENTED** |
| `POST /api/v1/github/analyze` | Scan code manifests for evidence | Phase 3 (CP 1–4) | **IMPLEMENTED** |
| `GET /api/v1/evidence` | Audit list of verified project evidence | Phase 3 (CP 1–4) | **IMPLEMENTED** |
| `GET /api/v1/evidence/{id}` | Audit detailed project evidence by ID | Phase 3 (CP 1–4) | **IMPLEMENTED** |
| `GET /api/v1/roles` | List canonical job roles | Phase 4 (CP 1, 2) | **IMPLEMENTED** |
| `GET /api/v1/roles/{role_id}` | Get canonical job role by ID | Phase 4 (CP 1, 2) | **IMPLEMENTED** |
| `GET /api/v1/demand` | Query empirical skill demand statistics | Phase 4 (CP 1, 2) | **IMPLEMENTED** |
| `GET /api/v1/demand/{role_id}` | Get complete role demand profile breakdown | Phase 4 (CP 1, 2) | **IMPLEMENTED** |
| `GET /api/v1/demand/audit/quality` | Audit demand data quality and integrity | Phase 4 (CP 2) | **IMPLEMENTED** |
| `GET /api/v1/intelligence/skills/ranking` | Rank skills across market or specific role | Phase 4 (CP 3) | **IMPLEMENTED** |
| `GET /api/v1/intelligence/skills/{id}/roles` | Demand profile of a skill across roles | Phase 4 (CP 3) | **IMPLEMENTED** |
| `POST /api/v1/intelligence/roles/compare` | Multi-role skill comparison and overlap | Phase 4 (CP 3) | **IMPLEMENTED** |
| `GET /api/v1/intelligence/roles/{id}/signals` | Market signals and growth trajectories | Phase 4 (CP 3) | **IMPLEMENTED** |
| `GET /api/v1/intelligence/trends` | Classified market growth trajectories | Phase 4 (CP 3) | **IMPLEMENTED** |
| `GET /api/v1/gaps/{role_id}` | Retrieve deterministic skill gaps for role | Phase 5 (CP 1, 4) | **IMPLEMENTED** |
| `POST /api/v1/gaps/analyze` | Execute deterministic skill gap analysis | Phase 5 (CP 1, 4) | **IMPLEMENTED** |
| `GET /api/v1/gaps/{role_id}/priorities` | Retrieve prioritized actionable gaps | Phase 5 (CP 2, 4) | **IMPLEMENTED** |
| `GET /api/v1/gaps/{role_id}/skills/{skill_id}/evidence` | Retrieve audit evidence chain for skill gap | Phase 5 (CP 3, 4) | **IMPLEMENTED** |
| `GET /api/v1/gaps` | Get active gap state | Phase 5 | PLANNED |
| `POST /api/v1/roadmaps/generate` | Generate topologically sorted roadmap | Phase 6 | PLANNED |
| `GET /api/v1/roadmaps` | List user roadmaps | Phase 6 | PLANNED |
| `GET /api/v1/roadmaps/{id}` | Get active roadmap details | Phase 6 | PLANNED |
| `PATCH /api/v1/roadmaps/{id}/milestones/{m_id}` | Update milestone state | Phase 6 | PLANNED |
| `GET /api/v1/resources` | Query curated learning resources | Phase 6 | PLANNED |
| `POST /api/v1/resources/recommend` | Semantic resource recommendation | Phase 6 / 7 | PLANNED |
| `POST /api/v1/assistant/chat` | Grounded RAG career assistant | Phase 7 | PLANNED |
| `POST /api/v1/verify/project` | GitHub milestone verification loop | Phase 8 | PLANNED |
| `GET /api/v1/dashboard` | Consolidated Next.js dashboard state | Phase 9 | PLANNED |

---

## 28. Rules for Maintaining API_SPEC.md

1. **API_SPEC.md is the authoritative contract**: Client and server implementations must remain consistent with this specification.
2. **Database synchronization**: Schema alterations in `DATA_MODEL.md` or Alembic migrations require immediate API specification review.
3. **Documentation before completion**: New endpoints must be fully documented in `API_SPEC.md` before being marked complete.
4. **Controlled Versioning**: Breaking changes require explicit RFC review and version incrementing under `/api/v2`.
5. **Deterministic Demand Principle**: Numerical industry-demand values remain strictly database- and statistics-owned.
6. **LLM Boundary Inviolability**: LLM and RAG layers cannot overwrite or bypass deterministic scoring, graph sequencing, or database evidence.
7. **Scoped Authorization**: Every user-owned resource must explicitly document and enforce `WHERE user_id = current_user.id`.
8. **Valid Examples**: All request and response payloads in this document must conform to valid JSON and accurate Pydantic types.
9. **Accurate Implementation Tracking**: Section 27 must accurately reflect active repository code, avoiding premature claims of completion.
10. **Evidence Primacy**: The API must never treat a self-asserted resume claim as verified repository evidence.