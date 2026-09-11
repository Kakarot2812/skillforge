# SkillForge AI — API Specification

## 1. API Overview

This document establishes the authoritative API specification for **SkillForge AI** v1.0.0 MVP.

The backend is built with **FastAPI** (Python 3.12+), providing asynchronous REST endpoints backed by **PostgreSQL 16** with the **pgvector** extension. The frontend is built on **Next.js** (App Router, TypeScript, Tailwind CSS) and interacts with this API.

### Core Conventions
- **Protocol**: HTTP/1.1 and HTTP/2 over TLS in production; standard HTTP for local development.
- **Base URLs**:
  - Development Root: `http://localhost:8000`
  - Development API v1: `http://localhost:8000/api/v1`
  - Production API: `https://api.skillforge.ai/api/v1`
- **Versioning**: URI-based path versioning under `/api/v1`. Unversioned root endpoints are reserved for operational diagnostics (`/`, `/health`, `/health/db`).
- **Data Exchange**: Requests and responses use `application/json; charset=utf-8`, except file uploads which use `multipart/form-data`.
- **Identifiers**: All resource identifiers are RFC 4122 UUIDv4 strings (e.g., `3fa85f64-5717-4562-b3fc-2c963f66afa6`).
- **Timestamps**: All timestamps use ISO 8601 extended format with UTC offset (e.g., `2026-09-01T14:30:00.000Z`).
- **Data Boundaries**:
  - **Shared Catalogs**: Roles, skills, and industry demand data are shared across all users.
  - **Candidate Evidence**: Resumes, repositories, claimed skills, demonstrated skills, and skill gap analyses are strictly scoped to candidate identity.

---

## 2. API Design & Security Principles

1. **REST-Oriented Resources**: Predictable URIs representing domain entities (`/resumes`, `/skills`, `/github`, `/evidence`, `/roles`, `/demand`, `/intelligence`, `/gaps`).
2. **Deterministic Intelligence**: Skill gap classification (`STRONG`, `PARTIAL`, `MISSING`), priority calculation, and multi-repo evidence scoring are executed deterministically in code/SQL without LLM participation.
3. **Structured Industry Demand**: MVP demand metrics are database-derived statistics from structured market data. The LLM does not calculate, invent, or override demand scores.
4. **Evidence-Based Evaluation**: Skills are classified as `CLAIMED` via resume extraction and elevated to `DEMONSTRATED` only when backed by verifiable repository artifacts (manifests, workflows, Dockerfiles).
5. **Token Security**: GitHub Personal Access Tokens (PATs) are volatile in-memory credentials for upstream queries. PATs are never stored in the database, never logged, and never returned in API responses.
6. **IDOR & Scope Isolation**: Candidate-scoped endpoints validate candidate ownership and prevent cross-user data leakage.
7. **Pydantic Validation**: All request and response structures conform strictly to Pydantic schemas.

---

## 3. Standard Response & Error Formats

### 3.1 Standard Response Envelopes

#### Single Resource Envelope
```json
{
  "data": { ... }
}
```

#### Paginated Collection Envelope
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

### 3.2 Error Envelope Contract

All exceptions handled by the FastAPI application return a standardized JSON error envelope:

```json
{
  "detail": "Descriptive message or validation details",
  "error": {
    "code": "ERROR_CODE",
    "message": "Descriptive error explanation.",
    "details": {}
  }
}
```

### 3.3 HTTP Status Codes & Error Code Mapping

The backend error handler (`backend/app/main.py`) deterministically maps status codes to error codes:

| HTTP Status | Error Code | Trigger Scenarios in Implementation |
| :--- | :--- | :--- |
| `200 OK` | — | Successful resource retrieval, update, or calculation. |
| `201 Created` | — | Successful creation (resume upload). |
| `204 No Content` | — | Successful resource deletion with no response body. |
| `400 Bad Request` | `BAD_REQUEST` | Unsupported file extension, invalid PDF/DOCX magic bytes, invalid DOCX structure, empty upload, non-resume document rejected by semantic validation, invalid evidence level filter. |
| `401 Unauthorized` | `UNAUTHENTICATED` | Unauthenticated access when authentication is enforced. |
| `403 Forbidden` | `FORBIDDEN` | Cross-user access denied: mismatch between query `user_id` and `X-User-Id` header, or attempting to access another candidate's private resume. |
| `404 Not Found` | `NOT_FOUND` | Resource not found: nonexistent `resume_id`, `repo_id`, `role_id`, `skill_id`, `evidence_id`, or `user_id`. |
| `413 Payload Too Large` | `PAYLOAD_TOO_LARGE` | Uploaded resume file exceeds maximum size limit (5 MB). |
| `415 Unsupported Media Type` | `UNSUPPORTED_MEDIA_TYPE` | Uploaded file MIME type is not allowed. |
| `422 Unprocessable Entity` | `VALIDATION_ERROR` | Pydantic payload validation failure, blank/whitespace location, location > 64 chars, invalid gap status filter, invalid priority level filter, malformed UUID. |
| `429 Too Many Requests` | `RATE_LIMITED` | GitHub REST API upstream rate limit encountered. |
| `500 Internal Server Error` | `INTERNAL_SERVER_ERROR` | Unhandled backend exception. |
| `502 Bad Gateway` | `UPSTREAM_GATEWAY_ERROR` | Upstream GitHub API connection failure. |
| `503 Service Unavailable` | `SERVICE_UNAVAILABLE` | PostgreSQL or pgvector database connectivity failure during health checks. |
| `504 Gateway Timeout` | `GATEWAY_TIMEOUT` | Upstream GitHub API request timeout. |

---

## 4. Operational & Health APIs

### 4.1 Root Welcome
```http
GET /
```
Returns system operational metadata and documentation links.

#### Response `200 OK`
```json
{
  "name": "SkillForge AI Backend",
  "version": "1.0.0",
  "status": "operational",
  "docs": "/api/v1/docs"
}
```

### 4.2 Application Health Probe
```http
GET /health
GET /api/v1/health
```
Basic liveness probe verifying that the FastAPI application process is healthy.

#### Response `200 OK`
```json
{
  "status": "ok"
}
```

### 4.3 Database & pgvector Health Probe
```http
GET /health/db
GET /api/v1/health/db
```
Readiness probe verifying PostgreSQL database connectivity, server version, and the active status of the `pgvector` extension.

#### Response `200 OK`
```json
{
  "status": "ok",
  "database": "connected",
  "pgvector_installed": true,
  "database_version": "PostgreSQL 16.2 on x86_64-apple-darwin..."
}
```
#### Response `503 Service Unavailable`
```json
{
  "detail": "Database service unavailable or connection failed."
}
```

---

## 5. Resume Intelligence APIs

The Resume Intelligence service validates, securely stores, parses, segments, and normalizes candidate resumes.

### Implementation Specifications:
- **Supported File Formats**: Strictly `.pdf` and `.docx`.
- **Maximum File Size**: 5 MB (`5 * 1024 * 1024` bytes = 5,242,880 bytes).
- **Security & Integrity Checks**:
  - Filename sanitization via regex scrubbing to prevent directory traversal.
  - Magic byte inspection: `%PDF-` for PDFs; `\x50\x4b\x03\x04` for DOCX archives.
  - DOCX container verification: Validates OpenXML `[Content_Types].xml` and `word/` package structure.
  - Disk storage: Isolated UUID naming (`<uuid>.<ext>`) in upload storage directory.
- **Semantic Resume Validation Gate**: Verifies that the document is a genuine resume (requires minimum 50 words, rejects invoices, receipts, code snippets, and short notes). Failed validation cleans up the uploaded file and returns `400 Bad Request`.
- **Text & Section Extraction**: Segmented into Header, Education, Experience, Skills, Projects, and Contact Information using PyMuPDF and pdfplumber.
- **Skill Normalization**: Discovered terms are mapped to canonical skills via dictionary alias lookup and pgvector semantic matching.
- **Ownership & Cascade**: Resumes are stored in the `resumes` table. Deletion cascades to `user_claimed_skills` and unlinks disk files.

---

### 5.1 Upload and Parse Resume
```http
POST /api/v1/resumes/upload
Content-Type: multipart/form-data
```

#### Form Parameters
- `file` (UploadFile, required): PDF or DOCX file (max 5 MB).

#### Response `201 Created`
```json
{
  "resume_id": "ff158ffc-ea91-4068-ad97-52e977abbda2",
  "filename": "jane_doe_resume.pdf",
  "file_type": "pdf",
  "file_size": 245760,
  "status": "uploaded",
  "message": "Resume uploaded, parsed, and skills normalized successfully.",
  "extracted_sections": ["contact_info", "experience", "education", "skills", "projects"],
  "claimed_skills_count": 2,
  "claimed_skills": [
    {
      "skill_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
      "skill_name": "Python",
      "canonical_slug": "python",
      "category": "Programming Languages",
      "raw_mention": "Python 3.12 Core & AsyncIO",
      "confidence_score": 1.0
    },
    {
      "skill_id": "2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e",
      "skill_name": "FastAPI",
      "canonical_slug": "fastapi",
      "category": "Backend Framework",
      "raw_mention": "FastAPI microservices",
      "confidence_score": 0.9
    }
  ],
  "created_at": "2026-09-10T14:30:00Z"
}
```

#### Error Responses
- `400 Bad Request`: Empty file, missing filename, invalid magic bytes, invalid DOCX package, or non-resume semantic rejection.
- `413 Payload Too Large`: File exceeds 5 MB.
- `422 Unprocessable Entity`: Extraction or parsing failure.

---

### 5.2 List Resumes
```http
GET /api/v1/resumes?limit=20&offset=0
```

#### Query Parameters
- `limit` (integer, default: 20, min: 1, max: 100): Page size.
- `offset` (integer, default: 0, min: 0): Pagination offset.

#### Response `200 OK`
```json
{
  "data": [
    {
      "resume_id": "ff158ffc-ea91-4068-ad97-52e977abbda2",
      "filename": "jane_doe_resume.pdf",
      "file_type": "pdf",
      "file_size": 245760,
      "status": "uploaded",
      "detected_sections": ["contact_info", "experience", "education", "skills"],
      "claimed_skills_count": 2,
      "created_at": "2026-09-10T14:30:00Z"
    }
  ],
  "meta": {
    "total": 1,
    "limit": 20,
    "offset": 0
  }
}
```

---

### 5.3 Get Resume Details
```http
GET /api/v1/resumes/{resume_id}
```

#### Path Parameters
- `resume_id` (UUID, required): The UUID of the resume record.

#### Response `200 OK`
```json
{
  "resume_id": "ff158ffc-ea91-4068-ad97-52e977abbda2",
  "filename": "jane_doe_resume.pdf",
  "file_type": "pdf",
  "file_size": 245760,
  "has_raw_text": true,
  "raw_text": "Jane Doe\nBackend Software Engineer\nSkills: Python, FastAPI...",
  "detected_sections": ["contact_info", "experience", "education", "skills"],
  "contact_info": {
    "email": "jane@example.com",
    "phone": "+91 9876543210"
  },
  "claimed_skills_count": 2,
  "claimed_skills": [
    {
      "skill_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
      "skill_name": "Python",
      "canonical_slug": "python",
      "category": "Programming Languages",
      "raw_mention": "Python 3.12 Core & AsyncIO",
      "confidence_score": 1.0
    }
  ],
  "parsed_data": {
    "sections": { ... },
    "detected_sections": ["contact_info", "experience", "education", "skills"]
  },
  "created_at": "2026-09-10T14:30:00Z"
}
```

#### Error Responses
- `404 Not Found`: Resume ID does not exist.

---

### 5.4 Delete Resume
```http
DELETE /api/v1/resumes/{resume_id}
```

Safely deletes the resume file from disk, deletes the database record, and cascades the deletion to associated claimed skills.

#### Response `204 No Content`
*(Empty response body)*

#### Error Responses
- `404 Not Found`: Resume ID does not exist (or has already been deleted).

---

## 6. Skills Intelligence APIs

Provides endpoints to query candidate claimed skills and multi-repository demonstrated skills.

### 6.1 List Claimed Skills
```http
GET /api/v1/skills/claimed?resume_id=ff158ffc-ea91-4068-ad97-52e977abbda2&limit=20&offset=0
```

#### Query Parameters
- `resume_id` (UUID, optional): Filter skills by specific resume ID scope.
- `limit` (integer, default: 20, min: 1, max: 100): Page limit.
- `offset` (integer, default: 0, min: 0): Page offset.

#### Response `200 OK`
```json
{
  "data": [
    {
      "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "skill_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
      "skill_name": "Python",
      "canonical_slug": "python",
      "category": "Programming Languages",
      "source": "resume",
      "raw_mention": "Python 3.12 Core & AsyncIO",
      "confidence_score": 1.0,
      "evidence_tier": "CLAIMED",
      "resume_id": "ff158ffc-ea91-4068-ad97-52e977abbda2",
      "created_at": "2026-09-10T14:30:00Z"
    }
  ],
  "meta": {
    "total": 1,
    "limit": 20,
    "offset": 0
  }
}
```

---

### 6.2 List Aggregated Demonstrated Skills
```http
GET /api/v1/skills/demonstrated?evidence_level=HIGH&limit=20&offset=0
```

Retrieves demonstrated skills aggregated across all connected GitHub repositories.

#### Query Parameters
- `evidence_level` (string, optional): Filter by tier (`HIGH`, `MEDIUM`, `LOW`). Invalid values return `400 Bad Request`.
- `repository_id` (UUID, optional): Filter by supporting repository.
- `skill_id` (UUID, optional): Filter by canonical skill ID.
- `user_id` (UUID, optional): Filter by user ID.
- `username` (string, optional): Filter by GitHub account username/owner.
- `limit` (integer, default: 20, min: 1, max: 100): Page limit.
- `offset` (integer, default: 0, min: 0): Page offset.

#### Multi-Repository Aggregation Rules
1. Within a single repository: $\text{repo\_score} = \max(\text{evidence confidence})$.
2. Across multiple independent repositories: $\text{multi\_repo\_score} = 1.0 - \prod (1.0 - \text{repo\_score}_i)$, clamped to $[0.0, 1.0]$.
3. Evidence Level Tiers:
   - `HIGH`: $\text{confidence\_score} \ge 0.85$
   - `MEDIUM`: $0.70 \le \text{confidence\_score} < 0.85$
   - `LOW`: $\text{confidence\_score} < 0.70$

#### Response `200 OK`
```json
{
  "data": [
    {
      "skill_id": "2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e",
      "skill_name": "FastAPI",
      "slug": "fastapi",
      "category": "Backend Framework",
      "confidence_score": 0.95,
      "evidence_level": "HIGH",
      "evidence_count": 2,
      "repository_count": 1,
      "last_verified_at": "2026-09-10T14:35:00Z",
      "repositories": [
        {
          "repository_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
          "repo_name": "task-management-api",
          "repo_url": "https://github.com/janedoe/task-management-api",
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

---

### 6.3 Get Demonstrated Skill Detail with Audit Trail
```http
GET /api/v1/skills/demonstrated/{skill_id}
```

Retrieves the demonstrated skill record alongside all underlying auditable `project_evidence` items. If no evidence records remain, stale records are automatically cleaned up and `404 Not Found` is returned.

#### Path Parameters
- `skill_id` (UUID, required): Canonical skill UUID.

#### Query Parameters
- `user_id` (UUID, optional): User ownership scope.

#### Response `200 OK`
```json
{
  "data": {
    "skill_id": "2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e",
    "skill_name": "FastAPI",
    "slug": "fastapi",
    "category": "Backend Framework",
    "description": "Modern, fast web framework for building APIs with Python.",
    "confidence_score": 0.95,
    "evidence_level": "HIGH",
    "evidence_count": 1,
    "repository_count": 1,
    "last_verified_at": "2026-09-10T14:35:00Z",
    "repositories": [
      {
        "repository_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
        "repo_name": "task-management-api",
        "repo_url": "https://github.com/janedoe/task-management-api",
        "max_confidence": 0.95,
        "evidence_count": 1
      }
    ],
    "evidence_types": ["dependency"],
    "evidence": [
      {
        "evidence_id": "9b8a7f6e-5d4c-3b2a-1f0e-9d8c7b6a5e4d",
        "repository_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
        "repo_name": "task-management-api",
        "skill_id": "2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e",
        "skill_name": "FastAPI",
        "canonical_slug": "fastapi",
        "evidence_type": "dependency",
        "artifact_path": "backend/requirements.txt",
        "file_path": "backend/requirements.txt",
        "artifact_name": "requirements.txt",
        "evidence_description": "FastAPI declared in requirements.txt",
        "matched_content": "fastapi>=0.115.0",
        "confidence_score": 0.95,
        "evidence_metadata": {},
        "detected_at": "2026-09-10T14:35:00Z",
        "created_at": "2026-09-10T14:35:00Z"
      }
    ]
  }
}
```

---

## 7. GitHub Intelligence APIs

### 7.1 Connect GitHub Account
```http
POST /api/v1/github/connect
Content-Type: application/json
```

Connects to GitHub, discovers public repositories, filters out forks, and stores repository metadata.

#### Request Body
```json
{
  "github_username": "janedoe",
  "access_token": "ghp_optionalVolatileTokenForRateLimits"
}
```

#### Response `200 OK`
```json
{
  "data": {
    "github_username": "janedoe",
    "connected": true,
    "discovered_repositories": 4,
    "connected_at": "2026-09-10T14:35:00Z",
    "repositories": [
      {
        "repo_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
        "github_repository_id": 12345678,
        "repo_name": "task-management-api",
        "full_name": "janedoe/task-management-api",
        "repo_url": "https://github.com/janedoe/task-management-api",
        "description": "Async task management REST API",
        "default_branch": "main",
        "visibility": "public",
        "primary_language": "Python",
        "is_fork": false,
        "stars_count": 12,
        "forks_count": 2,
        "last_pushed_at": "2026-09-08T10:00:00Z",
        "synced_at": "2026-09-10T14:35:00Z"
      }
    ]
  }
}
```

#### Error Responses
- `400 Bad Request`: Invalid username format.
- `404 Not Found`: GitHub user does not exist on GitHub.
- `429 Too Many Requests`: GitHub API rate limit reached.

---

### 7.2 List Discovered Repositories
```http
GET /api/v1/github/repositories?limit=20&offset=0
```

#### Query Parameters
- `limit` (integer, default: 20, min: 1, max: 100): Items per page.
- `offset` (integer, default: 0, min: 0): Records to skip.
- `user_id` (UUID, optional): Scoped user ID filter.
- `username` (string, optional): Restrict strictly to repositories owned by that GitHub account handle.

#### Response `200 OK`
Returns paginated list of non-forked discovered repositories (`GitHubRepositoryListResponse`).

---

### 7.3 Get Repository Details
```http
GET /api/v1/github/repositories/{repo_id}
```

Reads stored metadata from PostgreSQL without issuing redundant GitHub API requests.

#### Response `200 OK`
```json
{
  "data": {
    "repo_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
    "github_repository_id": 12345678,
    "repo_name": "task-management-api",
    "full_name": "janedoe/task-management-api",
    "repo_url": "https://github.com/janedoe/task-management-api",
    "description": "Async task management REST API",
    "default_branch": "main",
    "visibility": "public",
    "primary_language": "Python",
    "is_fork": false,
    "stars_count": 12,
    "forks_count": 2,
    "last_pushed_at": "2026-09-08T10:00:00Z",
    "repo_metadata": {
      "has_dockerfile": true,
      "has_ci_workflow": true
    },
    "created_at": "2026-09-10T14:35:00Z",
    "synced_at": "2026-09-10T14:35:00Z"
  }
}
```

---

### 7.4 Analyze Repositories for Evidence
```http
POST /api/v1/github/analyze
Content-Type: application/json
```

Recursively scans file trees for dependency manifests (`requirements.txt`, `package.json`, `pom.xml`, `go.mod`), infrastructure files (`Dockerfile`, `docker-compose.yml`), and CI/CD configurations (`.github/workflows/*.yml`). Recomputes demonstrated skills idempotently.

#### Request Body
```json
{
  "repository_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
  "selected_repo_ids": null,
  "include_forks": false
}
```

#### Response `200 OK`
```json
{
  "data": {
    "repository_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
    "repository_name": "task-management-api",
    "analyzed": true,
    "repositories_analyzed": 1,
    "evidence_count": 2,
    "evidence_items_detected": 2,
    "demonstrated_skills": [
      {
        "skill_id": "2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e",
        "skill_name": "FastAPI",
        "name": "FastAPI",
        "canonical_slug": "fastapi",
        "confidence_score": 0.95,
        "evidence_type": "dependency",
        "evidence_tier": "HIGH"
      }
    ]
  }
}
```

---

## 8. Project Evidence APIs

Auditable, concrete code artifacts extracted from repositories are stored in `project_evidence`.

### 8.1 List Verified Project Evidence Items
```http
GET /api/v1/evidence?repository_id=7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d&limit=20&offset=0
```

#### Query Parameters
- `limit` (integer, default: 20, min: 1, max: 100)
- `offset` (integer, default: 0, min: 0)
- `repository_id` / `repo_id` (UUID, optional): Filter by repository.
- `skill_id` (UUID, optional): Filter by skill.
- `evidence_type` (string, optional): Filter by evidence type (e.g. `dependency`, `dockerfile`, `ci_workflow`).
- `user_id` (UUID, optional): Filter by user ID.

#### Response `200 OK`
```json
{
  "data": [
    {
      "evidence_id": "9b8a7f6e-5d4c-3b2a-1f0e-9d8c7b6a5e4d",
      "repository_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
      "repo_name": "task-management-api",
      "skill_id": "2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e",
      "skill_name": "FastAPI",
      "canonical_slug": "fastapi",
      "evidence_type": "dependency",
      "artifact_path": "backend/requirements.txt",
      "file_path": "backend/requirements.txt",
      "artifact_name": "requirements.txt",
      "evidence_description": "FastAPI declared in requirements.txt",
      "matched_content": "fastapi>=0.115.0",
      "confidence_score": 0.95,
      "evidence_metadata": {},
      "detected_at": "2026-09-10T14:35:00Z",
      "created_at": "2026-09-10T14:35:00Z"
    }
  ],
  "meta": {
    "total": 1,
    "limit": 20,
    "offset": 0
  }
}
```

---

### 8.2 Get Project Evidence Item Detail
```http
GET /api/v1/evidence/{evidence_id}
```

#### Response `200 OK`
Returns single `ProjectEvidenceDetailResponse`.

#### Error Responses
- `404 Not Found`: Evidence item not found.

---

## 9. Canonical Job Roles APIs

### 9.1 List Canonical Job Roles
```http
GET /api/v1/roles?category=Engineering&limit=20&offset=0
```

#### Query Parameters
- `category` (string, optional): Role category filter.
- `limit` (integer, default: 20, min: 1, max: 100)
- `offset` (integer, default: 0, min: 0)

#### Response `200 OK`
```json
{
  "data": [
    {
      "role_id": "9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c",
      "title": "Backend Engineer",
      "slug": "backend-engineer",
      "category": "Engineering",
      "description": "Designs, implements, and maintains server-side systems."
    }
  ],
  "meta": {
    "total": 1,
    "limit": 20,
    "offset": 0
  }
}
```

---

### 9.2 Get Canonical Job Role by ID
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
    "description": "Designs, implements, and maintains server-side systems."
  }
}
```

---

## 10. Industry Skill Demand APIs

> [!IMPORTANT]
> MVP demand data is **structured baseline data** stored in PostgreSQL table `skill_demand`. Real-time market data ingestion is a planned post-MVP capability. The LLM is strictly prohibited from altering or generating demand metrics.

### 10.1 Audit Demand Data Quality & Integrity
```http
GET /api/v1/demand/audit/quality
```

Executes SQL integrity audits: checks for orphaned roles, orphaned demand records, out-of-bounds scores (`0.0 <= demand_score <= 1.0`), non-positive sample sizes, and duplicate records.

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
    "audit_timestamp": "2026-09-10T14:40:00Z"
  }
}
```

---

### 10.2 List Industry Skill Demand
```http
GET /api/v1/demand?role_id=9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c&location=India&limit=20&offset=0
```

#### Query Parameters
- `role_id` (UUID, optional): Canonical job role filter.
- `skill_id` (UUID, optional): Canonical skill filter.
- `location` (string, default: `"India"`): Geographic scope.
- `limit` (integer, default: 20, min: 1, max: 100)
- `offset` (integer, default: 0, min: 0)

#### Response `200 OK`
```json
{
  "data": [
    {
      "skill_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
      "skill_name": "Python",
      "canonical_slug": "python",
      "category": "Programming Languages",
      "role_id": "9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c",
      "role_title": "Backend Engineer",
      "location": "India",
      "sample_size": 14200,
      "demand_score": 0.78,
      "growth_rate": 0.08,
      "data_updated_at": "2026-09-01"
    }
  ],
  "meta": {
    "total": 1,
    "limit": 20,
    "offset": 0,
    "role_id": "9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c",
    "location": "India",
    "data_freshness": "2026-09-01"
  }
}
```

---

### 10.3 Get Role Demand Profile Breakdown
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
      "description": "Designs, implements, and maintains server-side systems."
    },
    "skills": [
      {
        "skill_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
        "skill_name": "Python",
        "canonical_slug": "python",
        "category": "Programming Languages",
        "demand_score": 0.78,
        "growth_rate": 0.08,
        "sample_size": 14200,
        "location": "India",
        "data_updated_at": "2026-09-01"
      }
    ]
  },
  "meta": {
    "total": 1,
    "location": "India",
    "data_freshness": "2026-09-01",
    "total_demanded_skills": 1,
    "average_demand_score": 0.78,
    "highest_demand_score": 0.78,
    "lowest_demand_score": 0.78,
    "average_growth_rate": 0.08,
    "top_skill": "Python"
  }
}
```

---

## 11. Demand Intelligence APIs

Advanced analytical endpoints for skill rankings, multi-role comparisons, market signals, and growth trends.

### 11.1 Skill Demand Ranking
```http
GET /api/v1/intelligence/skills/ranking?location=India&limit=50&offset=0
```
Calculates weighted demand across the market: `SUM(demand_score * sample_size) / SUM(sample_size)`.

### 11.2 Skill Demand Profile Across Job Roles
```http
GET /api/v1/intelligence/skills/{skill_id}/roles?location=India
```
Returns cross-role demand profile for a specific skill.

### 11.3 Compare Canonical Job Roles
```http
POST /api/v1/intelligence/roles/compare
Content-Type: application/json
```
Compares 2 to 5 canonical job roles deterministically. Identifies shared skills, role-specific specializations, and demand score differentials.

#### Request Body
```json
{
  "role_ids": [
    "9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c",
    "0a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d"
  ],
  "location": "India"
}
```

### 11.4 Role Market Signals
```http
GET /api/v1/intelligence/roles/{role_id}/signals?location=India
```
Returns rising, stable, and declining skill counts, top 5 demanded skills, and top 5 fastest growing skills.

### 11.5 Demand Growth Trends
```http
GET /api/v1/intelligence/trends?location=India&limit=20&offset=0
```
Lists demand records enriched with growth trajectory classifications (`RISING`, `STABLE`, `DECLINING`), ordered by growth rate descending.

---

## 12. Skill Gap & Priority APIs

The Skill Gap Engine compares candidate evidence against structured role demand requirements using deterministic formulas.

### Supported Candidate Evidence States:
1. **Resume Only**: Extracted claimed skills; demonstrated evidence is empty.
2. **GitHub Only**: Inspected repositories; claimed evidence is empty.
3. **Resume + GitHub**: Unified synthesis cross-validating claims against code artifacts.

### Deterministic Gap Classifications:
- `STRONG`: Candidate evidence satisfies or exceeds benchmark requirements.
- `PARTIAL`: Moderate evidence or claimed skill lacking sufficient demonstrated depth.
- `MISSING`: Target-role skill with neither claimed nor demonstrated evidence.

*(Note: No alternative classification names are used; LLMs do not perform classification).*

### Priority Scoring Formula (`scoring_version: "v1"`):
$$\text{growth\_signal} = \text{clamp}\left(\frac{\text{growth\_rate} + 1.0}{2.0}, 0.0, 1.0\right)$$
$$\text{priority\_score} = \text{gap\_severity\_weight} \cdot (0.70 \cdot \text{demand\_score} + 0.30 \cdot \text{growth\_signal})$$

Where:
- $\text{gap\_severity\_weight}$: `MISSING` = $1.0$, `PARTIAL` = $0.5$, `STRONG` = $0.0$
- Priority Tiers:
  - `HIGH`: $\text{priority\_score} \ge 0.67$
  - `MEDIUM`: $0.34 \le \text{priority\_score} < 0.67$
  - `LOW`: $\text{priority\_score} < 0.34$

---

### 12.1 Get Skill Gaps for Target Role
```http
GET /api/v1/gaps/{role_id}?location=India&status=MISSING
X-User-Id: <optional_uuid>
```

#### Query Parameters
- `location` (string, default: `"India"`): 1–64 characters, non-blank.
- `status` (string, optional): Filter by gap status (`STRONG`, `PARTIAL`, `MISSING`).
- `limit` (integer, optional): 1–100.
- `offset` (integer, default: 0): Offset $\ge 0$.
- `user_id` (UUID, optional): Scoped user ID.
- `resume_id` (UUID, optional): Specific resume ID scope.
- `username` (string, optional): GitHub account scope.
- `include_resume` (boolean, default: `true`): Include resume claims.
- `include_github` (boolean, default: `true`): Include GitHub demonstrated evidence.

#### Headers
- `X-User-Id` (string, optional): Authenticated candidate UUID for IDOR protection.

#### Response `200 OK`
```json
{
  "data": {
    "role": {
      "role_id": "9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c",
      "title": "Backend Engineer",
      "slug": "backend-engineer",
      "category": "Engineering",
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
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "skill_id": "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
        "skill_name": "Docker",
        "canonical_slug": "docker",
        "category": "DevOps",
        "status": "MISSING",
        "demand_score": 0.80,
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
      }
    ]
  },
  "meta": {
    "user_id": "8f7e6d5c-4b3a-2f1e-0d9c-8b7a6f5e4d3c",
    "location": "India",
    "calculated_at": "2026-09-10T14:45:00Z",
    "data_freshness": "2026-09-01",
    "scoring_version": "v1"
  }
}
```

---

### 12.2 Get Prioritized Actionable Gaps for Role
```http
GET /api/v1/gaps/{role_id}/priorities?location=India&priority_level=HIGH&status=MISSING
X-User-Id: <optional_uuid>
```

Retrieves candidate's actionable gaps (`MISSING` and `PARTIAL` only). `STRONG` skills are excluded.

#### Query Parameters
- `priority_level` (string, optional): `HIGH`, `MEDIUM`, `LOW`.
- `status` (string, optional): `MISSING`, `PARTIAL`. (Requesting `STRONG` returns `422 Unprocessable Entity`).
- Other parameters match Section 12.1.

#### Response `200 OK`
```json
{
  "data": {
    "role": {
      "role_id": "9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c",
      "title": "Backend Engineer",
      "slug": "backend-engineer",
      "category": "Engineering",
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
    "calculated_at": "2026-09-10T14:45:00Z",
    "data_freshness": "2026-09-01",
    "scoring_version": "v1"
  }
}
```

---

### 12.3 Execute Skill Gap Analysis
```http
POST /api/v1/gaps/analyze
Content-Type: application/json
X-User-Id: <optional_uuid>
```

Computes and idempotently persists skill gap results in PostgreSQL.

#### Request Body
```json
{
  "target_role_id": "9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c",
  "location": "India",
  "user_id": "8f7e6d5c-4b3a-2f1e-0d9c-8b7a6f5e4d3c",
  "resume_id": null,
  "include_resume": true,
  "include_github": true,
  "username": "janedoe"
}
```

#### Response `200 OK`
Returns `SkillGapResponse` object matching Section 12.1.

---

## 13. Evidence Audit API

### 13.1 Retrieve Audit Evidence Chain for Skill Gap
```http
GET /api/v1/gaps/{role_id}/skills/{skill_id}/evidence?location=India
X-User-Id: <optional_uuid>
```

Retrieves the complete, auditable evidence chain for a specific skill gap, detailing the relationship between resume evidence, GitHub artifacts, market signals, and rule-based explanations.

#### Response `200 OK`
```json
{
  "data": {
    "skill_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "skill_name": "Python",
    "canonical_slug": "python",
    "category": "Programming Languages",
    "status": "STRONG",
    "priority_score": null,
    "priority_level": null,
    "candidate_evidence": {
      "has_evidence": true,
      "resume_claims": [
        {
          "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
          "raw_mention": "Python 3.12 Core & AsyncIO",
          "confidence_score": 1.0,
          "source": "resume",
          "resume_id": "ff158ffc-ea91-4068-ad97-52e977abbda2",
          "resume_file_name": "jane_doe_resume.pdf",
          "created_at": "2026-09-10T14:30:00Z"
        }
      ],
      "github_demonstrated": {
        "confidence_score": 0.95,
        "evidence_level": "HIGH",
        "evidence_count": 1,
        "repository_count": 1,
        "last_verified_at": "2026-09-10T14:35:00Z"
      },
      "github_artifacts": [
        {
          "id": "9b8a7f6e-5d4c-3b2a-1f0e-9d8c7b6a5e4d",
          "repo_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
          "repo_name": "task-management-api",
          "repo_full_name": "janedoe/task-management-api",
          "repo_url": "https://github.com/janedoe/task-management-api",
          "evidence_type": "dependency",
          "file_path": "backend/requirements.txt",
          "artifact_name": "requirements.txt",
          "matched_content": "fastapi>=0.115.0",
          "confidence_score": 0.95,
          "detected_at": "2026-09-10T14:35:00Z"
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
      "sample_size": 14200,
      "data_updated_at": "2026-09-01"
    },
    "reasoning": {
      "classification_reason": "Strong because verified GitHub code artifacts demonstrate this skill at HIGH confidence (95%) across 1 repository(ies) with 1 evidence artifact(s).",
      "priority_reason": "Skill is already sufficiently demonstrated (STRONG). It is not considered an actionable gap.",
      "scoring_version": "v1"
    }
  },
  "meta": {
    "user_id": "8f7e6d5c-4b3a-2f1e-0d9c-8b7a6f5e4d3c",
    "location": "India",
    "calculated_at": "2026-09-10T14:50:00Z",
    "data_freshness": "2026-09-01",
    "scoring_version": "v1"
  }
}
```

---

## 14. Ownership, Scoping & Security Contract

### 14.1 Candidate Data Isolation
All candidate-specific resources implement strict ownership scoping:
- **IDOR Protection**: When both `user_id` query parameter and `X-User-Id` header are present, they must match. Conflicting IDs trigger `403 Forbidden`.
- **User Existence**: If a `user_id` is supplied, the database checks that the user exists. Nonexistent IDs trigger `404 Not Found`.
- **Resume Ownership**: If a `resume_id` is supplied:
  - The resume must exist (`404 Not Found`).
  - If the candidate is authenticated (`user_id` is present), the resume must belong to that candidate (`403 Forbidden`).
  - If the session is unauthenticated (`user_id` is None), attempting to access a resume owned by an authenticated user returns `403 Forbidden`.
- **Cross-User Leakage**: Claimed skills and demonstrated skills are queried strictly filtered by `user_id` or `resume_id`.

### 14.2 Shared Catalog Integrity
Canonical entities (`skills`, `job_roles`, `skill_demand`) are global public read-only catalogs. They cannot be modified by candidate API requests.

---

## 15. Implemented MVP Endpoints

The following table lists the active endpoints implemented in the SkillForge AI v1.0.0 MVP:

| HTTP Method | Route | Purpose | Implementation Status |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Root operational welcome & docs link | **IMPLEMENTED** |
| `GET` | `/health` | Service health liveness probe | **IMPLEMENTED** |
| `GET` | `/health/db` | PostgreSQL & pgvector connectivity probe | **IMPLEMENTED** |
| `GET` | `/api/v1/health` | Mounted v1 service health probe | **IMPLEMENTED** |
| `GET` | `/api/v1/health/db` | Mounted v1 database & pgvector probe | **IMPLEMENTED** |
| `POST` | `/api/v1/resumes/upload` | Upload, validate, parse resume & normalize claimed skills | **IMPLEMENTED** |
| `GET` | `/api/v1/resumes` | List candidate resumes with pagination | **IMPLEMENTED** |
| `GET` | `/api/v1/resumes/{resume_id}` | Get resume parsed sections and claimed skills | **IMPLEMENTED** |
| `DELETE` | `/api/v1/resumes/{resume_id}` | Delete resume file and cascade delete claimed skills | **IMPLEMENTED** |
| `GET` | `/api/v1/skills/claimed` | List candidate claimed skills from resumes | **IMPLEMENTED** |
| `GET` | `/api/v1/skills/demonstrated` | List multi-repo aggregated demonstrated skills | **IMPLEMENTED** |
| `GET` | `/api/v1/skills/demonstrated/{skill_id}` | Get demonstrated skill with auditable evidence trail | **IMPLEMENTED** |
| `POST` | `/api/v1/github/connect` | Discover public repositories (excluding forks) | **IMPLEMENTED** |
| `GET` | `/api/v1/github/repositories` | List discovered non-forked repositories | **IMPLEMENTED** |
| `GET` | `/api/v1/github/repositories/{repo_id}` | Get stored repository metadata | **IMPLEMENTED** |
| `POST` | `/api/v1/github/analyze` | Scan code manifests and recompute demonstrated skills | **IMPLEMENTED** |
| `GET` | `/api/v1/evidence` | List verified project evidence items | **IMPLEMENTED** |
| `GET` | `/api/v1/evidence/{evidence_id}` | Get project evidence item detail by ID | **IMPLEMENTED** |
| `GET` | `/api/v1/roles` | List canonical job roles | **IMPLEMENTED** |
| `GET` | `/api/v1/roles/{role_id}` | Get canonical job role by ID | **IMPLEMENTED** |
| `GET` | `/api/v1/demand/audit/quality` | Audit industry demand data quality and SQL integrity | **IMPLEMENTED** |
| `GET` | `/api/v1/demand` | List structured industry skill demand statistics | **IMPLEMENTED** |
| `GET` | `/api/v1/demand/{role_id}` | Get complete role demand profile breakdown | **IMPLEMENTED** |
| `GET` | `/api/v1/intelligence/skills/ranking` | Rank skills across market or specific role | **IMPLEMENTED** |
| `GET` | `/api/v1/intelligence/skills/{skill_id}/roles` | Profile of a skill across all canonical roles | **IMPLEMENTED** |
| `POST` | `/api/v1/intelligence/roles/compare` | Multi-role skill comparison and overlap analysis | **IMPLEMENTED** |
| `GET` | `/api/v1/intelligence/roles/{role_id}/signals` | Market signals and growth trajectories | **IMPLEMENTED** |
| `GET` | `/api/v1/intelligence/trends` | Classified market growth trends (RISING, STABLE, DECLINING) | **IMPLEMENTED** |
| `GET` | `/api/v1/gaps/{role_id}` | Retrieve deterministic skill gap analysis for role | **IMPLEMENTED** |
| `GET` | `/api/v1/gaps/{role_id}/priorities` | Retrieve prioritized actionable gaps (MISSING & PARTIAL) | **IMPLEMENTED** |
| `POST` | `/api/v1/gaps/analyze` | Execute deterministic skill gap analysis idempotently | **IMPLEMENTED** |
| `GET` | `/api/v1/gaps/{role_id}/skills/{skill_id}/evidence` | Retrieve audit evidence chain for specific skill gap | **IMPLEMENTED** |

---

## 16. Post-MVP Planned APIs

> [!NOTE]
> The endpoints and capabilities in this section are **PLANNED FOR POST-MVP EVOLUTION** on the `post-mvp-foundation` branch. They are not implemented in the frozen `v1.0.0-mvp` release. This section documents high-level conceptual directions only; exact paths, schemas, and provider integrations have not yet been selected.

### P1 — Real-Time Industry Demand Pipeline
- **Market Data Ingestion**: Endpoints to ingest licensed and permitted job postings.
- **Market Demand Refresh & Recalculation**: Automated endpoints to trigger deterministic statistical demand recalculation and update PostgreSQL demand tables.
- **Demand Evidence & Source Retrieval**: Endpoints exposing data lineage, sample sizes, and freshness metrics for refreshed market observations.

### P2 & P3 — Local Qwen 3 8B AI Layer & Evidence-Grounded Career Chatbot
- **Evidence-Grounded Explanations**: Endpoints providing natural-language reasoning over verified SkillForge candidate and market evidence.
- **Interactive Career Assistant**: Conversational endpoints for candidate Q&A grounded strictly in deterministic audit records and verified market signals.

### P4 — Personalized Roadmap & Learning Resources
- **Personalized Roadmap Generation**: Sequenced learning path generation based on prerequisite DAG topological sorting.
- **Vetted Learning Resources & Projects**: Curated resource matching and hands-on project challenge recommendations tailored to candidate skill gaps.

### P5 — GitHub Skill Verification Loop (Implemented)

The following closed-loop verification endpoints are implemented under `/api/v1/roadmap`:

#### 1. Verify Roadmap Milestone
- **Method**: `POST`
- **Path**: `/api/v1/roadmap/{roadmap_id}/milestones/{milestone_id}/verify`
- **Headers**:
  - `X-User-Id`: Candidate UUID (Required)
  - `Authorization`: `Bearer <github_pat>` (Optional; required for private candidate repositories)
- **Request Body**:
  ```json
  {
    "repository_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "commit_sha": "optional-snapshot-sha"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "id": "uuid",
    "milestone_id": "uuid",
    "roadmap_id": "uuid",
    "repository_id": "uuid",
    "commit_sha": "40-char-sha",
    "status": "VERIFIED",
    "composite_confidence": 0.92,
    "deliverable_score": 1.0,
    "criteria_score": 0.88,
    "skill_confidence": 0.85,
    "verified_at": "2026-09-11T12:00:00Z",
    "details": {
      "deliverables": [...],
      "criteria": [...]
    },
    "demonstrated_skills_recalculated": true,
    "roadmap_unlocked": true
  }
  ```
- **Status Codes**:
  - `200 OK`: Verification completed (`VERIFIED`, `PARTIAL`, `UNVERIFIED`, or persisted `FAILED` audit record).
  - `400 Bad Request`: Forked repository, query/body credential leakage, or milestone not associated with project deliverables.
  - `401 Unauthorized`: Missing `X-User-Id`.
  - `403 Forbidden`: Candidate does not own roadmap, repository, or connected GitHub handle mismatch.
  - `404 Not Found`: Roadmap, milestone, or repository not found.

#### 2. Get Milestone Verification History
- **Method**: `GET`
- **Path**: `/api/v1/roadmap/{roadmap_id}/milestones/{milestone_id}/verification`
- **Headers**:
  - `X-User-Id`: Candidate UUID (Required)
- **Query Parameters**:
  - `limit`: Integer (Default: 10)
- **Response**: `200 OK`
  ```json
  {
    "milestone_id": "uuid",
    "verifications": [...],
    "total": 1
  }
  ```

#### 3. Batch Verify Roadmap Milestones
- **Method**: `POST`
- **Path**: `/api/v1/roadmap/{roadmap_id}/verify`
- **Headers**:
  - `X-User-Id`: Candidate UUID (Required)
  - `Authorization`: `Bearer <github_pat>` (Optional)
- **Request Body**:
  ```json
  {
    "repository_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "milestone_ids": ["uuid-1", "uuid-2"],
    "commit_sha": "optional-snapshot-sha"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "roadmap_id": "uuid",
    "verifications": [...],
    "total_evaluated": 2,
    "total_verified": 1
  }
  ```