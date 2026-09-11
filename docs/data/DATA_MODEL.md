# SkillForge AI — Database Schema & Data Models

This document defines the authoritative database schema and data models for **SkillForge AI**. It is organized into two primary divisions:

1. **v1.0.0 MVP Data Model (Frozen Baseline)**: The operational, deterministic schema implemented in PostgreSQL and SQLAlchemy on the frozen `v1.0.0-mvp` release.
2. **Post-MVP Planned Data Model**: High-level conceptual data models planned for post-MVP evolution on the `post-mvp-foundation` branch.

---

# Part 1: v1.0.0 MVP Data Model (Frozen Baseline)

## 1. Database Overview

SkillForge AI utilizes **PostgreSQL** with the **pgvector** extension as its unified relational datastore. The frozen v1.0.0 MVP schema consists of exactly 11 database tables managed via SQLAlchemy models (`backend/app/db/models.py`) and Alembic migrations (`backend/alembic/versions/` 0001 through 0011).

### Core Architecture Principle

> **"Store evidence and authoritative inputs.**
> **Derive intelligence deterministically.**
> **Keep AI-generated explanations separate from authoritative data."**

The Large Language Model (LLM) is strictly decoupled from the database system of record. The LLM is **never** the authoritative source of:
- Candidate skill possession
- Industry demand score
- Skill gap classification
- Priority score

---

## 2. Entity-Relationship Diagram (Frozen MVP)

```text
┌──────────────┐         ┌──────────────────────┐         ┌──────────────────────┐
│    users     │────┬───►│       resumes        │────┬───►│ user_claimed_skills  │
└──────┬───────┘    │    └──────────────────────┘    │    └──────────┬───────────┘
       │            │                                │               │
       │            └───►┌──────────────────────┐    │               │
       │                 │ github_repositories  │    │               │
       │                 └──────────┬───────────┘    │               │
       │                            │                │               │
       │                            ▼                │               │
       │                 ┌──────────────────────┐    │               │
       │                 │   project_evidence   │◄───┘               │
       │                 └──────────┬───────────┘                    │
       │                            │                                │
       │                            ▼                                │
       │                 ┌──────────────────────┐◄───────────────────┘
       │                 │        skills        │◄───┐
       │                 └──────────┬───────────┘    │
       │                            │                │
       │              ┌─────────────┼────────────────┤
       │              ▼             ▼                ▼
       │     ┌────────────────┐ ┌────────────────┐ ┌──────────────────┐
       │     │ skill_aliases  │ │ demonstrated_  │ │   skill_gaps     │
       │     │                │ │    skills      │ │                  │
       │     └────────────────┘ └────────────────┘ └─────────┬────────┘
       │                                                      │
       ▼                                                      │
┌──────────────┐         ┌──────────────────────┐             │
│  job_roles   │────────►│     skill_demand     │◄────────────┘
└──────────────┘         └──────────────────────┘
```

---

## 3. Table Specifications (Implemented MVP Tables)

### 3.1 `users`
Represents candidate user accounts and career target preferences.

- **Table Name**: `users`
- **Participation**: Root identity entity for candidate evidence scoping.
- **SQL Definition**:
  ```sql
  CREATE TABLE users (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      email VARCHAR(255) UNIQUE NOT NULL,
      full_name VARCHAR(128),
      target_role VARCHAR(128),
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
  );
  CREATE INDEX ix_users_email ON users(email);
  ```
- **Relationships**:
  - `resumes` (`Resume`): 1-to-many, cascades delete-orphan.
  - `claimed_skills` (`UserClaimedSkill`): 1-to-many, cascades delete-orphan.
  - `github_repositories` (`GitHubRepository`): 1-to-many, cascades delete-orphan.
  - `project_evidence` (`ProjectEvidence`): 1-to-many, cascades delete-orphan.
  - `demonstrated_skills` (`DemonstratedSkill`): 1-to-many, cascades delete-orphan.
  - `skill_gaps` (`SkillGap`): 1-to-many, cascades delete-orphan.

---

### 3.2 `skills`
The canonical repository of all normalized technologies and capabilities.

- **Table Name**: `skills`
- **Participation**: Central taxonomy nexus linking resume claims, code evidence, market demand, and gap analysis.
- **SQL Definition**:
  ```sql
  CREATE TABLE skills (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      name VARCHAR(128) UNIQUE NOT NULL,
      slug VARCHAR(128) UNIQUE NOT NULL,
      category VARCHAR(64),
      description TEXT,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
  );
  CREATE INDEX ix_skills_name ON skills(name);
  CREATE INDEX ix_skills_slug ON skills(slug);
  ```
- **Relationships**:
  - `aliases` (`SkillAlias`): 1-to-many, cascades delete-orphan.
  - `claimed_by_users` (`UserClaimedSkill`): 1-to-many, cascades delete-orphan.
  - `project_evidence` (`ProjectEvidence`): 1-to-many, cascades delete-orphan.
  - `demonstrated_by_users` (`DemonstratedSkill`): 1-to-many, cascades delete-orphan.
  - `industry_demands` (`IndustrySkillDemand`): 1-to-many, cascades delete-orphan.
  - `skill_gaps` (`SkillGap`): 1-to-many, cascades delete-orphan.

---

### 3.3 `skill_aliases`
Maps synonyms, abbreviations, casing variations, and historical acronyms to canonical skills.

- **Table Name**: `skill_aliases`
- **Participation**: Used during resume parsing and repository manifest scanning to normalize raw extracted mentions.
- **SQL Definition**:
  ```sql
  CREATE TABLE skill_aliases (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
      alias VARCHAR(128) NOT NULL,
      normalized_alias VARCHAR(128) NOT NULL,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
  );
  CREATE INDEX ix_skill_aliases_skill_id ON skill_aliases(skill_id);
  CREATE INDEX ix_skill_aliases_normalized_alias ON skill_aliases(normalized_alias);
  ```
- **Relationships**:
  - `skill` (`Skill`): Many-to-1 foreign key to `skills.id`.

---

### 3.4 `resumes`
Stores uploaded resume documents, extracted plain text, and parsed structural sections.

- **Table Name**: `resumes`
- **Participation**: Persists source candidate resume artifacts and raw extracted text.
- **SQL Definition**:
  ```sql
  CREATE TABLE resumes (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID REFERENCES users(id) ON DELETE CASCADE,
      file_name VARCHAR(255) NOT NULL,
      file_type VARCHAR(64) NOT NULL,
      file_size INTEGER NOT NULL,
      storage_path VARCHAR(512) NOT NULL,
      raw_text TEXT,
      parsed_data JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
  );
  CREATE INDEX ix_resumes_user_id ON resumes(user_id);
  ```
- **Notes on Fields**:
  - `user_id`: Nullable to allow anonymous onboarding and isolated test execution.
  - `parsed_data`: JSONB object holding detected sections, contact info, and parser metadata.
- **Relationships**:
  - `user` (`User`): Many-to-1 back-populates `resumes`.
  - `claimed_skills` (`UserClaimedSkill`): 1-to-many, cascades delete-orphan.

---

### 3.5 `user_claimed_skills`
Stores candidate self-asserted or resume-extracted skill claims.

- **Table Name**: `user_claimed_skills`
- **Participation**: Represents candidate claimed evidence before verification against code artifacts.
- **SQL Definition**:
  ```sql
  CREATE TABLE user_claimed_skills (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID REFERENCES users(id) ON DELETE CASCADE,
      skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
      resume_id UUID REFERENCES resumes(id) ON DELETE SET NULL,
      source VARCHAR(32) NOT NULL DEFAULT 'resume',
      raw_mention VARCHAR(128),
      confidence_score FLOAT NOT NULL DEFAULT 1.0,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      CONSTRAINT uq_user_claimed_skills_user_skill UNIQUE (user_id, skill_id)
  );
  CREATE INDEX ix_user_claimed_skills_user_id ON user_claimed_skills(user_id);
  CREATE INDEX ix_user_claimed_skills_skill_id ON user_claimed_skills(skill_id);
  CREATE INDEX ix_user_claimed_skills_resume_id ON user_claimed_skills(resume_id);
  ```
- **Relationships**:
  - `user` (`User`): Many-to-1 back-populates `claimed_skills`.
  - `skill` (`Skill`): Many-to-1 back-populates `claimed_by_users`.
  - `resume` (`Resume`): Many-to-1 back-populates `claimed_skills`.

---

### 3.6 `github_repositories`
Stores connected GitHub public repositories (excluding forks) and metadata.

- **Table Name**: `github_repositories`
- **Participation**: Source of repository metadata and file-tree manifests inspected for code evidence.
- **SQL Definition**:
  ```sql
  CREATE TABLE github_repositories (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID REFERENCES users(id) ON DELETE CASCADE,
      github_repository_id BIGINT,
      repo_name VARCHAR(128) NOT NULL,
      full_name VARCHAR(255),
      repo_url VARCHAR(512) NOT NULL,
      description TEXT,
      default_branch VARCHAR(64) DEFAULT 'main',
      visibility VARCHAR(32) DEFAULT 'public',
      primary_language VARCHAR(64),
      is_fork BOOLEAN NOT NULL DEFAULT FALSE,
      stars_count INTEGER NOT NULL DEFAULT 0,
      forks_count INTEGER NOT NULL DEFAULT 0,
      last_pushed_at TIMESTAMPTZ,
      repo_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      synced_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      CONSTRAINT uq_github_repos_user_repo_url UNIQUE (user_id, repo_url)
  );
  CREATE INDEX ix_github_repositories_user_id ON github_repositories(user_id);
  CREATE INDEX ix_github_repositories_github_repository_id ON github_repositories(github_repository_id);
  CREATE INDEX ix_github_repositories_repo_name ON github_repositories(repo_name);
  CREATE INDEX ix_github_repositories_full_name ON github_repositories(full_name);
  ```
- **Security Invariant**: Access tokens used for scanning are volatile in-memory only and are **never** stored in this table.
- **Relationships**:
  - `user` (`User`): Many-to-1 back-populates `github_repositories`.
  - `evidence_items` (`ProjectEvidence`): 1-to-many, cascades delete-orphan.

---

### 3.7 `project_evidence`
Audit-ready evidence records linking repository code artifacts to canonical skills.

- **Table Name**: `project_evidence`
- **Participation**: Source code evidence supporting demonstrated skill elevation.
- **SQL Definition**:
  ```sql
  CREATE TABLE project_evidence (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID REFERENCES users(id) ON DELETE CASCADE,
      repo_id UUID REFERENCES github_repositories(id) ON DELETE CASCADE,
      skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
      evidence_type VARCHAR(64) NOT NULL,
      file_path VARCHAR(255),
      artifact_name VARCHAR(128),
      evidence_description TEXT,
      matched_content TEXT,
      evidence_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
      confidence_score FLOAT NOT NULL,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      detected_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      CONSTRAINT uq_project_evidence_repo_skill_type_path UNIQUE (repo_id, skill_id, evidence_type, file_path)
  );
  CREATE INDEX ix_project_evidence_user_id ON project_evidence(user_id);
  CREATE INDEX ix_project_evidence_repo_id ON project_evidence(repo_id);
  CREATE INDEX ix_project_evidence_skill_id ON project_evidence(skill_id);
  CREATE INDEX ix_project_evidence_evidence_type ON project_evidence(evidence_type);
  ```
- **Relationships**:
  - `user` (`User`): Many-to-1 back-populates `project_evidence`.
  - `repository` (`GitHubRepository`): Many-to-1 back-populates `evidence_items`.
  - `skill` (`Skill`): Many-to-1 back-populates `project_evidence`.

---

### 3.8 `demonstrated_skills`
Aggregated multi-repository code evidence level for each candidate skill.

- **Table Name**: `demonstrated_skills`
- **Participation**: Authoritative demonstrated evidence tier backing skill gap evaluations.
- **SQL Definition**:
  ```sql
  CREATE TABLE demonstrated_skills (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID REFERENCES users(id) ON DELETE CASCADE,
      skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
      confidence_score FLOAT NOT NULL,
      evidence_level VARCHAR(32) NOT NULL,
      evidence_count INTEGER NOT NULL DEFAULT 0,
      repository_count INTEGER NOT NULL DEFAULT 0,
      last_verified_at TIMESTAMPTZ,
      skill_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      CONSTRAINT uq_demonstrated_skills_user_skill UNIQUE (user_id, skill_id)
  );
  CREATE INDEX ix_demonstrated_skills_user_id ON demonstrated_skills(user_id);
  CREATE INDEX ix_demonstrated_skills_skill_id ON demonstrated_skills(skill_id);
  CREATE INDEX ix_demonstrated_skills_confidence_score ON demonstrated_skills(confidence_score);
  ```
- **Aggregation Formula**:
  - Within single repository: $\text{repo\_score} = \max(\text{evidence confidence})$.
  - Across multiple independent repositories: $\text{multi\_repo\_score} = 1.0 - \prod (1.0 - \text{repo\_score}_i)$.
  - Tiers: `HIGH` ($\ge 0.85$), `MEDIUM` ($0.70 \le score < 0.85$), `LOW` ($< 0.70$).
- **Relationships**:
  - `user` (`User`): Many-to-1 back-populates `demonstrated_skills`.
  - `skill` (`Skill`): Many-to-1 back-populates `demonstrated_by_users`.

---

### 3.9 `job_roles`
Canonical career progression tracks and target roles supported by the platform.

- **Table Name**: `job_roles`
- **Participation**: Industry track benchmark against which skill requirements and candidate gaps are calculated.
- **SQL Definition**:
  ```sql
  CREATE TABLE job_roles (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      title VARCHAR(128) UNIQUE NOT NULL,
      slug VARCHAR(128) UNIQUE NOT NULL,
      category VARCHAR(64) NOT NULL,
      description TEXT,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
  );
  CREATE INDEX ix_job_roles_title ON job_roles(title);
  CREATE INDEX ix_job_roles_slug ON job_roles(slug);
  CREATE INDEX ix_job_roles_category ON job_roles(category);
  ```
- **Relationships**:
  - `skill_demands` (`IndustrySkillDemand`): 1-to-many, cascades delete-orphan.
  - `skill_gaps` (`SkillGap`): 1-to-many, cascades delete-orphan.

---

### 3.10 `skill_demand`
Structured industry skill demand metrics. Note: Demand data is global, canonical market evidence and is **not** owned by any individual user.

- **Table Name**: `skill_demand`
- **Participation**: Provides empirical market baseline demand scores and growth rates for the skill gap and priority engines.
- **SQL Definition**:
  ```sql
  CREATE TABLE skill_demand (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      role_id UUID NOT NULL REFERENCES job_roles(id) ON DELETE CASCADE,
      skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
      location VARCHAR(64) NOT NULL DEFAULT 'India',
      sample_size INTEGER NOT NULL DEFAULT 10000,
      demand_score FLOAT NOT NULL,
      growth_rate FLOAT NOT NULL DEFAULT 0.0,
      data_updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      CONSTRAINT uq_skill_demand_role_skill_loc UNIQUE (role_id, skill_id, location),
      CONSTRAINT chk_demand_score_range CHECK (demand_score >= 0.0 AND demand_score <= 1.0),
      CONSTRAINT chk_sample_size_positive CHECK (sample_size > 0)
  );
  CREATE INDEX ix_skill_demand_role_id ON skill_demand(role_id);
  CREATE INDEX ix_skill_demand_skill_id ON skill_demand(skill_id);
  CREATE INDEX ix_skill_demand_location ON skill_demand(location);
  CREATE INDEX ix_skill_demand_demand_score ON skill_demand(demand_score);
  CREATE INDEX ix_skill_demand_growth_rate ON skill_demand(growth_rate);
  ```
- **Relationships**:
  - `role` (`JobRole`): Many-to-1 back-populates `skill_demands`.
  - `skill` (`Skill`): Many-to-1 back-populates `industry_demands`.

---

### 3.11 `skill_gaps`
Stores deterministic candidate skill gap results and priority scoring.

- **Table Name**: `skill_gaps`
- **Participation**: Persisted derived intelligence recording candidate evaluation against role demand.
- **SQL Definition**:
  ```sql
  CREATE TABLE skill_gaps (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID REFERENCES users(id) ON DELETE CASCADE,
      role_id UUID NOT NULL REFERENCES job_roles(id) ON DELETE CASCADE,
      skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
      location VARCHAR(64) NOT NULL DEFAULT 'India',
      status VARCHAR(32) NOT NULL,
      demand_score FLOAT NOT NULL,
      growth_rate FLOAT NOT NULL DEFAULT 0.0,
      claimed BOOLEAN NOT NULL DEFAULT FALSE,
      claim_confidence FLOAT NOT NULL DEFAULT 0.0,
      demonstrated BOOLEAN NOT NULL DEFAULT FALSE,
      demonstrated_score FLOAT NOT NULL DEFAULT 0.0,
      evidence_level VARCHAR(32),
      evidence_count INTEGER NOT NULL DEFAULT 0,
      priority_score FLOAT,
      priority_level VARCHAR(32),
      scoring_version VARCHAR(16) NOT NULL DEFAULT 'v1',
      computed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      gap_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      CONSTRAINT uq_skill_gaps_user_role_skill_loc UNIQUE (user_id, role_id, skill_id, location),
      CONSTRAINT chk_skill_gap_demand_score_range CHECK (demand_score >= 0.0 AND demand_score <= 1.0),
      CONSTRAINT chk_skill_gap_status CHECK (status IN ('STRONG', 'PARTIAL', 'MISSING'))
  );
  CREATE INDEX ix_skill_gaps_user_id ON skill_gaps(user_id);
  CREATE INDEX ix_skill_gaps_role_id ON skill_gaps(role_id);
  CREATE INDEX ix_skill_gaps_skill_id ON skill_gaps(skill_id);
  CREATE INDEX ix_skill_gaps_location ON skill_gaps(location);
  CREATE INDEX ix_skill_gaps_status ON skill_gaps(status);
  CREATE INDEX ix_skill_gaps_demand_score ON skill_gaps(demand_score);
  CREATE INDEX ix_skill_gaps_priority_score ON skill_gaps(priority_score);
  CREATE INDEX ix_skill_gaps_priority_level ON skill_gaps(priority_level);
  ```
- **Classification Invariant**: `status` is strictly constrained by database check constraint to `'STRONG'`, `'PARTIAL'`, or `'MISSING'`.
- **Relationships**:
  - `user` (`User`): Many-to-1 back-populates `skill_gaps`.
  - `role` (`JobRole`): Many-to-1 back-populates `skill_gaps`.
  - `skill` (`Skill`): Many-to-1 back-populates `skill_gaps`.

---

## 4. Evidence Audit Representation

> [!NOTE]
> **Evidence Audit is a Service-Level Structure, Not a Standalone Table.**

In SkillForge AI v1.0.0 MVP, the **Evidence Audit** is generated dynamically at request time by the `skill_gap_evidence_service` (`backend/app/services/skill_gap_evidence_service.py`). It synthesizes:
1. **Candidate Evidence**: Extracted resume claims from `user_claimed_skills` and `resumes`, plus verified code artifacts from `project_evidence` and `github_repositories`.
2. **Market Evidence**: Canonical role demand statistics from `skill_demand`.
3. **Deterministic Reasoning**: Rule-based text strings explaining why the skill received its specific gap status and priority score.

This avoids data duplication while ensuring 100% auditability traceable back to database foreign keys.

---

## 5. Source Data vs. Derived Data

The data model maintains a strict distinction between source inputs, market baselines, and derived calculations:

| Category | Entities / Data Elements | Persistence Layer | Mutability / Lifecycle |
| :--- | :--- | :--- | :--- |
| **Candidate Source Evidence** | Resumes (`resumes`), parsed sections, GitHub repos (`github_repositories`), code artifacts (`project_evidence`). | Persisted in PostgreSQL tables. | Updated on new uploads or GitHub repository re-scans. |
| **Market Evidence** | Role demand metrics (`skill_demand`), job roles (`job_roles`), canonical skills (`skills`). | Persisted in PostgreSQL tables. | Structured baseline in MVP; refreshable via pipeline in post-MVP. |
| **Derived Intelligence (Persisted)** | User claimed skills (`user_claimed_skills`), demonstrated skill scores (`demonstrated_skills`), skill gaps & priorities (`skill_gaps`). | Persisted in PostgreSQL tables with unique constraints. | Reconciled idempotently upon new candidate evidence or gap recalculation. |
| **Derived Intelligence (Request-Time)** | Evidence audit trails, cross-role comparisons, market demand signals, ranking views. | Computed dynamically at service time. | Generated on-the-fly from verified database records; never cached stale. |

---

## 6. Ownership & Data Isolation Model

SkillForge AI implements a multi-tier data scoping model:

### 6.1 Database Layer Isolation
- **Cascade Deletion**: When a candidate user is deleted from `users`, foreign keys configured with `ON DELETE CASCADE` automatically purge their resumes, claimed skills, connected repositories, project evidence, demonstrated skills, and skill gap records.
- **Unique Scoping Constraints**: Constraints such as `uq_user_claimed_skills_user_skill`, `uq_github_repos_user_repo_url`, and `uq_demonstrated_skills_user_skill` ensure that candidate data does not collide across accounts.

### 6.2 Service & API Layer Isolation
- **IDOR Protection**: Requests providing both `user_id` query parameters and `X-User-Id` headers verify that both values match; conflicting IDs return `403 Forbidden`.
- **Resume Isolation**: Accessing a resume belonging to another authenticated candidate returns `403 Forbidden`. Unauthenticated sessions cannot access resumes linked to authenticated users.
- **Repository Scoping**: Repository and evidence queries are filtered by candidate identity (`user_id` or GitHub `username`).
- **Global Public Catalogs**: Tables `skills`, `skill_aliases`, `job_roles`, and `skill_demand` have no `user_id` foreign key. They are global, immutable by candidates, and shared platform-wide.

---

## 7. Canonical Skill Model Nexus

The `skills` table serves as the authoritative spine across the entire intelligence engine:

```text
               ┌───────────────────────┐
               │ user_claimed_skills   │ (Resume Evidence)
               └───────────▲───────────┘
                           │ skill_id
                           │
┌──────────────────────┐   │   ┌───────────────────────┐
│   project_evidence   │───┼───►│        skills         │
└──────────────────────┘   │   └───────────▲───────────┘
               skill_id    │               │
                           │               │ skill_id
               ┌───────────▼───────────┐   │
               │  demonstrated_skills  │   │   ┌───────────────────────┐
               └───────────────────────┘   ├───►│     skill_demand      │ (Market Evidence)
                               skill_id    │   └───────────────────────┘
                                           │               │
                                           │ skill_id      │ skill_id
                               ┌───────────▼───────────┐   │
                               │      skill_gaps       │◄──┘
                               └───────────────────────┘
```

- **Cross-Reference**: For the complete list of canonical technology domains, categories, and alias mappings, consult the companion document [SKILL_TAXONOMY.md](file:///Users/niteshyadav/SIH/docs/data/SKILL_TAXONOMY.md).

---

## 8. Industry Demand Data Representation

In the frozen v1.0.0 MVP:
- `skill_demand` stores **structured baseline data** across canonical roles and geographic locations (e.g., location `"India"`).
- Demand scores (`demand_score`) are normalized floats between `0.0` and `1.0`.
- Growth rates (`growth_rate`) reflect annual market trajectories (e.g., `+0.08` for +8% YoY).
- Sample sizes (`sample_size`) record job posting volumes supporting the statistic.
- Database check constraints (`chk_demand_score_range`, `chk_sample_size_positive`) mathematically enforce data bounds.
- **Real-time market ingestion is NOT part of the frozen MVP.**

---

# Part 2: Post-MVP Planned Data Model

> [!NOTE]
> All concepts, entities, and relationships in Part 2 are **PLANNED FOR POST-MVP EVOLUTION** on the `post-mvp-foundation` branch. They are not implemented in the frozen `v1.0.0-mvp` schema.

The post-MVP roadmap introduces new capabilities that will eventually require dedicated data models:

### P1 — Real-Time Industry Demand Concepts

#### Checkpoint P1-C Implemented Table: `market_jobs`
Stores normalized, deduplicated external job postings ingested from market data providers (Adzuna).

- **Table Name**: `market_jobs`
- **Participation**: Staging and provenance repository for raw/normalized market job postings before role classification or skill extraction.
- **SQL Definition**:
  ```sql
  CREATE TABLE market_jobs (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      source VARCHAR(64) NOT NULL,
      external_job_id VARCHAR(255) NOT NULL,
      title VARCHAR(512) NOT NULL,
      description TEXT,
      company_name VARCHAR(255),
      location VARCHAR(255),
      category VARCHAR(128),
      contract_type VARCHAR(64),
      contract_time VARCHAR(64),
      created_at TIMESTAMPTZ,
      redirect_url VARCHAR(1024),
      raw_data JSONB NOT NULL DEFAULT '{}'::jsonb,
      ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      CONSTRAINT uq_market_jobs_source_external_job_id UNIQUE (source, external_job_id)
  );
  CREATE INDEX ix_market_jobs_source ON market_jobs(source);
  CREATE INDEX ix_market_jobs_ingested_at ON market_jobs(ingested_at);
  CREATE INDEX ix_market_jobs_created_at ON market_jobs(created_at);
  ```
- **Natural Identity & Uniqueness**: `(source, external_job_id)` is the unique constraint preventing cross-run and cross-query duplication.
- **Idempotent Upsert**: PostgreSQL native `ON CONFLICT (source, external_job_id) DO UPDATE` with `COALESCE` ensuring non-destructive updates without overwriting existing data with empty values.
- **Provenance & Lineage**: `raw_data` retains the complete provider payload (e.g. Adzuna JSON) for auditable extraction lineage without storing API secrets.
- **Timestamps**: `created_at` records upstream provider posting time; `ingested_at` records local intake timestamp; `updated_at` records record modification timestamp.
- **Scope Boundary**: Strictly isolated from the MVP `skill_demand` table; skill extraction and demand recalculation happen in subsequent post-MVP checkpoints.

#### Checkpoint P1-D Implemented Table: `market_job_skills`
Stores canonical skill evidence extracted deterministically from persisted market job text.

- **Table Name**: `market_job_skills`
- **Participation**: Relational evidence bridge associating raw market jobs (`market_jobs`) with canonical taxonomy skills (`skills`).
- **SQL Definition**:
  ```sql
  CREATE TABLE market_job_skills (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      market_job_id UUID NOT NULL REFERENCES market_jobs(id) ON DELETE CASCADE,
      skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
      matched_alias VARCHAR(128) NOT NULL,
      source_field VARCHAR(32) NOT NULL,
      evidence_text TEXT,
      extraction_method VARCHAR(64) NOT NULL DEFAULT 'deterministic_taxonomy_match',
      confidence_score FLOAT NOT NULL DEFAULT 1.0,
      extracted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      CONSTRAINT uq_market_job_skills_job_skill UNIQUE (market_job_id, skill_id)
  );
  CREATE INDEX ix_market_job_skills_market_job_id ON market_job_skills(market_job_id);
  CREATE INDEX ix_market_job_skills_skill_id ON market_job_skills(skill_id);
  ```
- **Natural Identity & Uniqueness**: `(market_job_id, skill_id)` ensures one market job receives at most one relationship per canonical skill.
- **Idempotent Persistence & Reconciliation**: PostgreSQL-native `ON CONFLICT (market_job_id, skill_id) DO UPDATE` updates matched metadata if changes occur. If job text changes, stale skills no longer detected are purged deterministically.
- **Provenance**: `matched_alias` records the exact taxonomy phrase/alias matched; `source_field` records whether extracted from `'title'` or `'description'`; `evidence_text` records the verbatim text context snippet.
- **Foreign Keys**: Cascades deletion if a parent `market_job` or `skill` is removed.
- **Scope Boundary**: Strictly isolated from MVP `skill_demand` records; demand metric aggregation and growth calculations are deferred to Checkpoint P1-E.

#### Checkpoint P1-E Implemented Table: `market_skill_demand`
Stores live computed market-demand snapshots aggregated deterministically from persisted market jobs and extracted skills.

- **Table Name**: `market_skill_demand`
- **Participation**: Live market-demand layer computed empirically from active `market_jobs` and `market_job_skills` records.
- **SQL Definition**:
  ```sql
  CREATE TABLE market_skill_demand (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
      source VARCHAR(64) NOT NULL DEFAULT 'adzuna',
      job_count INTEGER NOT NULL DEFAULT 0,
      sample_size INTEGER NOT NULL,
      demand_share FLOAT NOT NULL,
      demand_score FLOAT NOT NULL,
      computed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      CONSTRAINT uq_market_skill_demand_source_skill UNIQUE (source, skill_id),
      CONSTRAINT chk_market_skill_demand_score_range CHECK (demand_score >= 0.0 AND demand_score <= 1.0),
      CONSTRAINT chk_market_skill_demand_share_range CHECK (demand_share >= 0.0 AND demand_share <= 1.0),
      CONSTRAINT chk_market_skill_demand_job_count_non_negative CHECK (job_count >= 0),
      CONSTRAINT chk_market_skill_demand_sample_size_non_negative CHECK (sample_size >= 0)
  );
  CREATE INDEX ix_market_skill_demand_skill_id ON market_skill_demand(skill_id);
  CREATE INDEX ix_market_skill_demand_source ON market_skill_demand(source);
  CREATE INDEX ix_market_skill_demand_demand_score ON market_skill_demand(demand_score);
  ```
- **Aggregation Inputs**: `market_jobs` JOIN `market_job_skills` on `market_jobs.id = market_job_skills.market_job_id`.
- **Unique-Job Counting Rule**: Uses SQL `COUNT(DISTINCT market_job_id)` per canonical skill; repeated mentions within a single job never inflate `job_count`.
- **Demand Metric Formulas**:
  $$\text{demand\_share} = \frac{\text{job\_count}}{\text{sample\_size}}$$
  $$\text{demand\_score} = \text{round}(\text{demand\_share}, 4)$$
  Both are bounded in $[0.0, 1.0]$ and guarded against division by zero.
- **Natural Key & Recomputation**: `(source, skill_id)` uniquely identifies a skill demand record within a provider snapshot. Recomputation replaces/upserts snapshot records idempotently.
- **Reconciliation**: Skills no longer demanded in the current snapshot are automatically purged (`reconcile=True`).
- **Scope Boundary**: Strictly isolated from the 49-record MVP `skill_demand` table; historical growth rate calculation and 24-hour automated refresh are implemented in Checkpoint P1-F.

#### Checkpoint P1-F Implemented Tables: `market_skill_demand_snapshots` & `market_skill_demand_growth`
Provides the immutable historical snapshot layer and current materialized growth engine on top of P1-E demand aggregation.

##### 1. Table: `market_skill_demand_snapshots`
Stores immutable, point-in-time snapshots of computed market skill demand metrics.

- **Table Name**: `market_skill_demand_snapshots`
- **Participation**: Historical snapshot layer capturing point-in-time market demand metrics.
- **SQL Definition**:
  ```sql
  CREATE TABLE market_skill_demand_snapshots (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
      source VARCHAR(64) NOT NULL DEFAULT 'adzuna',
      job_count INTEGER NOT NULL,
      sample_size INTEGER NOT NULL,
      demand_share FLOAT NOT NULL,
      demand_score FLOAT NOT NULL,
      snapshot_at TIMESTAMPTZ NOT NULL,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      CONSTRAINT uq_market_skill_demand_snapshots_source_skill_time UNIQUE (source, skill_id, snapshot_at),
      CONSTRAINT chk_market_skill_demand_snapshots_score_range CHECK (demand_score >= 0.0 AND demand_score <= 1.0),
      CONSTRAINT chk_market_skill_demand_snapshots_share_range CHECK (demand_share >= 0.0 AND demand_share <= 1.0),
      CONSTRAINT chk_market_skill_demand_snapshots_job_count_non_negative CHECK (job_count >= 0),
      CONSTRAINT chk_market_skill_demand_snapshots_sample_size_non_negative CHECK (sample_size >= 0)
  );
  CREATE INDEX ix_market_skill_demand_snapshots_skill_id ON market_skill_demand_snapshots(skill_id);
  CREATE INDEX ix_market_skill_demand_snapshots_source ON market_skill_demand_snapshots(source);
  CREATE INDEX ix_market_skill_demand_snapshots_snapshot_at ON market_skill_demand_snapshots(snapshot_at);
  CREATE INDEX ix_market_skill_demand_snapshots_source_time ON market_skill_demand_snapshots(source, snapshot_at);
  ```
- **Natural Identity**: `(source, skill_id, snapshot_at)` uniquely identifies a historical demand snapshot row.
- **Immutability & Idempotency**: Snapshots are strictly immutable. Submitting an identical snapshot at the same timestamp is idempotent (`inserted=0, unchanged=N`); conflicting data submissions for an existing timestamp are rejected (`MarketDemandSnapshotConflictError`).
- **Source Isolation**: Preserves provider provenance via `source` (e.g. `'adzuna'`).
- **Foreign Keys**: `skill_id` references canonical `skills(id)` with cascade deletion.

##### 2. Table: `market_skill_demand_growth`
Stores the current materialized growth rate and trend classification between comparable historical snapshots.

- **Table Name**: `market_skill_demand_growth`
- **Participation**: Current materialized growth intelligence comparing the latest snapshot to the immediately preceding snapshot.
- **SQL Definition**:
  ```sql
  CREATE TABLE market_skill_demand_growth (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
      source VARCHAR(64) NOT NULL DEFAULT 'adzuna',
      previous_snapshot_id UUID REFERENCES market_skill_demand_snapshots(id) ON DELETE SET NULL,
      current_snapshot_id UUID NOT NULL REFERENCES market_skill_demand_snapshots(id) ON DELETE CASCADE,
      previous_demand_score FLOAT NOT NULL,
      current_demand_score FLOAT NOT NULL,
      growth_rate FLOAT NOT NULL,
      growth_class VARCHAR(16) NOT NULL,
      computed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      CONSTRAINT uq_market_skill_demand_growth_source_skill UNIQUE (source, skill_id)
  );
  CREATE INDEX ix_market_skill_demand_growth_skill_id ON market_skill_demand_growth(skill_id);
  CREATE INDEX ix_market_skill_demand_growth_source ON market_skill_demand_growth(source);
  CREATE INDEX ix_market_skill_demand_growth_growth_class ON market_skill_demand_growth(growth_class);
  ```
- **Natural Key & Materialization**: `(source, skill_id)` uniquely identifies the current growth state for a canonical skill within a data source. The growth table updates as newer snapshots arrive.
- **Auditability**: References `previous_snapshot_id` and `current_snapshot_id` to ensure growth calculations are fully reproducible and auditable.
- **Deterministic Classification**: `growth_class` is classified strictly by `growth_rate`:
  - `growth_rate > 0.05` $\rightarrow$ `'RISING'`
  - `-0.05 <= growth_rate <= 0.05` $\rightarrow$ `'STABLE'`
  - `growth_rate < -0.05` $\rightarrow$ `'DECLINING'`
- **Strict Scope Boundary**: Completely isolated from the frozen MVP `skill_demand` table (strictly 49 rows), `job_roles`, candidate `skill_gaps`, and candidate readiness priorities.

#### Checkpoint P3 Implemented Tables: `rag_documents` & `rag_chunks`
Provides the evidence retrieval layer storing approved evidence documents, deterministic chunks, and pgvector embeddings.

##### 1. Table: `rag_documents`
Stores explicitly approved, bounded evidence documents for RAG retrieval.

- **Table Name**: `rag_documents`
- **Participation**: Authoritative storage of approved evidence documents (market summaries, deterministic analysis explanations, bounded code snippets, approved learning resources).
- **SQL Definition**:
  ```sql
  CREATE TABLE rag_documents (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      source_type VARCHAR(32) NOT NULL,
      source_reference VARCHAR(512) NOT NULL,
      title VARCHAR(255) NOT NULL,
      content TEXT NOT NULL,
      document_metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
  );
  CREATE INDEX ix_rag_documents_source_type ON rag_documents(source_type);
  CREATE INDEX ix_rag_documents_source_reference ON rag_documents(source_reference);
  ```
- **Relationships**:
  - `chunks` (`RAGChunk`): 1-to-many, cascades delete-orphan.
- **Ingestion Boundary**: Strictly restricted to approved evidence. Arbitrary raw resume PDFs/DOCX, entire GitHub repositories, raw database dumps, and secrets are prohibited.

##### 2. Table: `rag_chunks`
Stores deterministically chunked text segments with pgvector embeddings for similarity retrieval.

- **Table Name**: `rag_chunks`
- **Participation**: Vector search target linking chunks to parent documents, provenance, and canonical skills.
- **SQL Definition**:
  ```sql
  CREATE TABLE rag_chunks (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      document_id UUID NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
      chunk_index INTEGER NOT NULL,
      content TEXT NOT NULL,
      embedding VECTOR(384) NOT NULL,
      skill_id UUID REFERENCES skills(id) ON DELETE SET NULL,
      source_type VARCHAR(32) NOT NULL,
      source_reference VARCHAR(512) NOT NULL,
      chunk_metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      CONSTRAINT uq_rag_chunks_document_chunk_index UNIQUE (document_id, chunk_index),
      CONSTRAINT chk_rag_chunks_chunk_index_non_negative CHECK (chunk_index >= 0)
  );
  CREATE INDEX ix_rag_chunks_document_id ON rag_chunks(document_id);
  CREATE INDEX ix_rag_chunks_skill_id ON rag_chunks(skill_id);
  CREATE INDEX ix_rag_chunks_source_type ON rag_chunks(source_type);
  CREATE INDEX ix_rag_chunks_source_reference ON rag_chunks(source_reference);
  ```
- **Dimension Consistency**: Vector dimension is strictly 384, consistent with `sentence-transformers/all-MiniLM-L6-v2` and `settings.EMBEDDING_DIMENSION`.
- **Search Semantics**: Exact cosine distance (`<=>`), stable secondary tie-breaking ordering (`distance ASC, id ASC`), and authoritative metadata filtering.

#### Checkpoint P4 Implemented Tables: Personalized Roadmap & Curated Resources
Implements deterministic career roadmaps, explicit skill dependencies, approved resource catalogs, and practical project specifications (Migration: `0017_roadmap_and_resources`).

##### 1. Table: `skill_dependencies`
Represents directed prerequisite edges in the canonical skill graph ($u \to v$ means $u$ should be learned before $v$).

- **Table Name**: `skill_dependencies`
- **Participation**: Authoritative Directed Acyclic Graph (DAG) constraints used by the deterministic roadmap sequencing engine.
- **SQL Definition**:
  ```sql
  CREATE TABLE skill_dependencies (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
      prerequisite_skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
      dependency_type VARCHAR(32) NOT NULL DEFAULT 'HARD',
      description TEXT,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      CONSTRAINT uq_skill_dependencies_skill_prereq UNIQUE (skill_id, prerequisite_skill_id),
      CONSTRAINT chk_skill_dependencies_no_self_loop CHECK (skill_id != prerequisite_skill_id),
      CONSTRAINT chk_skill_dependencies_type CHECK (dependency_type IN ('HARD', 'RECOMMENDED'))
  );
  CREATE INDEX ix_skill_dependencies_skill_id ON skill_dependencies(skill_id);
  CREATE INDEX ix_skill_dependencies_prereq_id ON skill_dependencies(prerequisite_skill_id);
  ```
- **Semantics**:
  - `HARD`: Mandatory prerequisite. Blocks downstream skills in topological sorting unless candidate already possesses `STRONG` demonstrated evidence.
  - `RECOMMENDED`: Helpful complementary skill. Preserved in metadata and rationale; does NOT block scheduling.

##### 2. Table: `approved_resources`
Stores explicitly approved, curated learning resources for canonical skills.

- **Table Name**: `approved_resources`
- **Participation**: Sole authority for learning materials. Arbitrary web scraping and hallucinated LLM URLs are strictly prohibited.
- **SQL Definition**:
  ```sql
  CREATE TABLE approved_resources (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
      title VARCHAR(255) NOT NULL,
      url VARCHAR(1024) NOT NULL,
      resource_type VARCHAR(64) NOT NULL,
      provider VARCHAR(128) NOT NULL,
      difficulty VARCHAR(32) NOT NULL,
      estimated_minutes INTEGER,
      is_approved BOOLEAN DEFAULT true NOT NULL,
      approval_source VARCHAR(64) DEFAULT 'CURATED_SEED' NOT NULL,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
  );
  CREATE INDEX ix_approved_resources_skill_id ON approved_resources(skill_id);
  CREATE INDEX ix_approved_resources_resource_type ON approved_resources(resource_type);
  ```

##### 3. Table: `approved_projects`
Stores curated practical projects mapped to canonical skills and career roles.

- **Table Name**: `approved_projects`
- **Participation**: Hands-on project challenges providing deliverable manifests and verification criteria for P5 GitHub verification.
- **SQL Definition**:
  ```sql
  CREATE TABLE approved_projects (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
      role_id UUID REFERENCES job_roles(id) ON DELETE SET NULL,
      title VARCHAR(255) NOT NULL,
      description TEXT NOT NULL,
      difficulty VARCHAR(32) NOT NULL,
      deliverables JSONB DEFAULT '[]'::jsonb NOT NULL,
      verification_criteria JSONB DEFAULT '[]'::jsonb NOT NULL,
      estimated_hours INTEGER,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
  );
  CREATE INDEX ix_approved_projects_skill_id ON approved_projects(skill_id);
  CREATE INDEX ix_approved_projects_role_id ON approved_projects(role_id);
  ```

##### 4. Table: `candidate_roadmaps`
Persisted learning trajectories for authenticated candidates.

- **Table Name**: `candidate_roadmaps`
- **Participation**: Audit trail and lifecycle container for candidate roadmaps. Requires non-null authenticated `user_id` to prevent IDOR vulnerabilities. (Anonymous roadmaps are generated strictly in-memory).
- **SQL Definition**:
  ```sql
  CREATE TABLE candidate_roadmaps (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      role_id UUID NOT NULL REFERENCES job_roles(id) ON DELETE CASCADE,
      target_role_title VARCHAR(128) NOT NULL,
      location VARCHAR(64) DEFAULT 'India' NOT NULL,
      status VARCHAR(32) DEFAULT 'ACTIVE' NOT NULL,
      roadmap_version VARCHAR(16) DEFAULT 'v1' NOT NULL,
      summary_metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      CONSTRAINT chk_candidate_roadmaps_status CHECK (status IN ('ACTIVE', 'COMPLETED', 'ARCHIVED'))
  );
  CREATE INDEX ix_candidate_roadmaps_user_id ON candidate_roadmaps(user_id);
  CREATE INDEX ix_candidate_roadmaps_role_id ON candidate_roadmaps(role_id);
  CREATE INDEX ix_candidate_roadmaps_user_role ON candidate_roadmaps(user_id, role_id);
  ```

##### 5. Table: `roadmap_milestones`
Ordered milestones within a candidate roadmap.

- **Table Name**: `roadmap_milestones`
- **Participation**: Sequenced learning steps enforcing strictly deterministic ordering and status lifecycle.
- **SQL Definition**:
  ```sql
  CREATE TABLE roadmap_milestones (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      roadmap_id UUID NOT NULL REFERENCES candidate_roadmaps(id) ON DELETE CASCADE,
      skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
      order_index INTEGER NOT NULL,
      status VARCHAR(32) DEFAULT 'NOT_STARTED' NOT NULL,
      gap_status VARCHAR(32) NOT NULL,
      priority_score FLOAT,
      priority_level VARCHAR(32),
      reason TEXT NOT NULL,
      project_id UUID REFERENCES approved_projects(id) ON DELETE SET NULL,
      milestone_metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
      CONSTRAINT uq_roadmap_milestones_order UNIQUE (roadmap_id, order_index),
      CONSTRAINT uq_roadmap_milestones_skill UNIQUE (roadmap_id, skill_id),
      CONSTRAINT chk_roadmap_milestones_status CHECK (status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'VERIFIED')),
      CONSTRAINT chk_roadmap_milestones_order_positive CHECK (order_index >= 1)
  );
  CREATE INDEX ix_roadmap_milestones_roadmap_id ON roadmap_milestones(roadmap_id);
  CREATE INDEX ix_roadmap_milestones_skill_id ON roadmap_milestones(skill_id);
  ```
- **Lifecycle Semantics**: P4 strictly initializes milestones to `NOT_STARTED`. `VERIFIED` status is strictly reserved for P5 GitHub verification.
- **Transitive Prerequisite Scoring**: Transitive-only prerequisites maintain `priority_score = NULL` and `priority_level = NULL` (no fabricated priority facts).

### P5 — GitHub Skill Verification Loop Concepts
- **Verification Event**: Audit records logging candidate milestone verification attempts.
- **Repository Re-Scan**: Incremental code artifact diffing triggering deterministic skill gap recalculation.
- **Skill Progression History**: Historical time-series tracking candidate skill advancement over time.

