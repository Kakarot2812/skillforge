# SkillForge AI — Database Schema & Data Models

## 1. Database Overview

SkillForge AI utilizes **PostgreSQL** with the **pgvector** extension as its unified datastore for relational entities, JSONB metadata, and vector embeddings.

### Core Data Layers

1. **User & Identity Layer**: Accounts, preferences, target career goals.
2. **Taxonomy & Graph Layer**: Canonical skills, aliases, and prerequisite DAG.
3. **Evidence Layer**: Resume extractions, GitHub repositories, and verifiable code artifacts.
4. **Market Intelligence Layer**: Job roles, structured demand statistics, and trend metrics.
5. **Roadmap & Content Layer**: Generated milestones, curated learning resources, and RAG knowledge chunks.

---

## 2. Entity-Relationship Diagram

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
       │     │ skill_aliases  │ │skill_dependenc.│ │learning_resources│
       │     └────────────────┘ └────────────────┘ └──────────────────┘
       ▼                                                     ▲
┌──────────────┐         ┌──────────────────────┐            │
│   roadmaps   │────────►│  roadmap_milestones  │────────────┘
└──────────────┘         └──────────────────────┘
       │
       ▼
┌──────────────┐         ┌──────────────────────┐
│  job_roles   │────────►│     skill_demand     │
└──────────────┘         └──────────────────────┘
```

---

## 3. Detailed Table Specifications

### 3.1 `users`
Represents candidate profiles and target career objectives.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(128),
    target_role VARCHAR(128),
    target_location VARCHAR(64) DEFAULT 'India',
    weekly_hours_commitment INT DEFAULT 10,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 `skills`
The canonical repository of all normalized technologies.

```sql
CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(128) UNIQUE NOT NULL,
    slug VARCHAR(128) UNIQUE NOT NULL,
    category VARCHAR(64) NOT NULL,
    description TEXT,
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_skills_embedding ON skills USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_skills_slug ON skills(slug);
```

### 3.3 `skill_aliases`
Maps alternative spellings, acronyms, and synonyms to canonical skills.

```sql
CREATE TABLE skill_aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    alias VARCHAR(128) NOT NULL,
    normalized_alias VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_skill_aliases_norm ON skill_aliases(normalized_alias);
```

### 3.4 `skill_dependencies`
Encodes the prerequisite Directed Acyclic Graph (DAG).

```sql
CREATE TABLE skill_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    prerequisite_skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    dependency_type VARCHAR(32) NOT NULL DEFAULT 'hard', -- 'hard' | 'soft'
    CONSTRAINT chk_no_self_dependency CHECK (skill_id != prerequisite_skill_id),
    UNIQUE (skill_id, prerequisite_skill_id)
);
```

### 3.5 `resumes`
Stores uploaded resume documents and structured parser outputs.

```sql
CREATE TABLE resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    raw_text TEXT,
    parsed_data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_resumes_user_id ON resumes(user_id);
```

### 3.6 `user_claimed_skills`
Skills extracted from resumes or self-declared by the candidate.

```sql
CREATE TABLE user_claimed_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    resume_id UUID REFERENCES resumes(id) ON DELETE SET NULL,
    source VARCHAR(32) NOT NULL DEFAULT 'resume',
    raw_mention VARCHAR(128),
    confidence_score FLOAT NOT NULL DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, skill_id)
);
```

### 3.7 `github_repositories`
Stores repositories connected and scanned for technical artifacts.

```sql
CREATE TABLE github_repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    repo_name VARCHAR(128) NOT NULL,
    repo_url VARCHAR(255) NOT NULL,
    primary_language VARCHAR(64),
    is_fork BOOLEAN DEFAULT FALSE,
    stars_count INT DEFAULT 0,
    last_pushed_at TIMESTAMPTZ,
    repo_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_github_repos_user ON github_repositories(user_id);
```

### 3.8 `project_evidence`
Audit-ready evidence linking codebase files to demonstrated skills.

```sql
CREATE TABLE project_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    repo_id UUID REFERENCES github_repositories(id) ON DELETE SET NULL,
    evidence_type VARCHAR(64) NOT NULL, -- 'dependency' | 'dockerfile' | 'ci_workflow' | 'code_volume'
    file_path VARCHAR(255),
    matched_content TEXT,
    confidence_score FLOAT NOT NULL, -- 0.0 to 1.0
    detected_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_project_evidence_user_skill ON project_evidence(user_id, skill_id);
```

### 3.9 `job_roles`
Target industry career tracks.

```sql
CREATE TABLE job_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(128) UNIQUE NOT NULL,
    slug VARCHAR(128) UNIQUE NOT NULL,
    category VARCHAR(64) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

### 3.10 `skill_demand`
Aggregated empirical market demand metrics. Note: Industry demand is global, canonical data not owned by any user. LLMs are strictly prohibited from generating, modifying, or inferring demand scores.

```sql
CREATE TABLE skill_demand (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES job_roles(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    location VARCHAR(64) NOT NULL DEFAULT 'India',
    sample_size INT NOT NULL DEFAULT 10000 CHECK (sample_size > 0),
    demand_score FLOAT NOT NULL CHECK (demand_score >= 0.0 AND demand_score <= 1.0),
    growth_rate FLOAT NOT NULL DEFAULT 0.0,  -- YoY trend (e.g. 0.08 = +8%)
    data_updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (role_id, skill_id, location)
);

CREATE INDEX idx_skill_demand_role_id ON skill_demand(role_id);
CREATE INDEX idx_skill_demand_skill_id ON skill_demand(skill_id);
CREATE INDEX idx_skill_demand_demand_score ON skill_demand(demand_score);
CREATE INDEX idx_skill_demand_role_skill ON skill_demand(role_id, skill_id);
```

### 3.11 `skill_gaps`
Deterministic candidate skill gap calculations combining resume claims, GitHub demonstrated evidence, and canonical industry demand.

```sql
CREATE TABLE skill_gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES job_roles(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    location VARCHAR(64) NOT NULL DEFAULT 'India',
    status VARCHAR(32) NOT NULL CHECK (status IN ('STRONG', 'PARTIAL', 'MISSING')),
    demand_score FLOAT NOT NULL CHECK (demand_score >= 0.0 AND demand_score <= 1.0),
    growth_rate FLOAT NOT NULL DEFAULT 0.0,
    claimed BOOLEAN NOT NULL DEFAULT FALSE,
    claim_confidence FLOAT NOT NULL DEFAULT 0.0,
    demonstrated BOOLEAN NOT NULL DEFAULT FALSE,
    demonstrated_score FLOAT NOT NULL DEFAULT 0.0,
    evidence_level VARCHAR(32),
    evidence_count INT NOT NULL DEFAULT 0,
    priority_score FLOAT,
    priority_level VARCHAR(32),
    scoring_version VARCHAR(16) NOT NULL DEFAULT 'v1',
    computed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    gap_metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, role_id, skill_id, location)
);

CREATE INDEX idx_skill_gaps_user_id ON skill_gaps(user_id);
CREATE INDEX idx_skill_gaps_role_id ON skill_gaps(role_id);
CREATE INDEX idx_skill_gaps_skill_id ON skill_gaps(skill_id);
CREATE INDEX idx_skill_gaps_status ON skill_gaps(status);
CREATE INDEX idx_skill_gaps_demand_score ON skill_gaps(demand_score);
CREATE INDEX idx_skill_gaps_priority_score ON skill_gaps(priority_score);
CREATE INDEX idx_skill_gaps_priority_level ON skill_gaps(priority_level);
CREATE INDEX idx_skill_gaps_user_role ON skill_gaps(user_id, role_id);
CREATE UNIQUE INDEX uq_skill_gaps_null_user ON skill_gaps(role_id, skill_id, location) WHERE user_id IS NULL;
```

### 3.12 `roadmaps` & `roadmap_milestones`
Sequential personalized curriculum and tracking.

```sql
CREATE TABLE roadmaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES job_roles(id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE roadmap_milestones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    sequence_order INT NOT NULL,
    title VARCHAR(128) NOT NULL,
    description TEXT,
    target_skills JSONB NOT NULL,
    estimated_hours INT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'NOT_STARTED',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

### 3.12 `learning_resources` & `rag_documents`
Vetted educational content and vector knowledge base.

```sql
CREATE TABLE learning_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    url VARCHAR(512) NOT NULL,
    resource_type VARCHAR(64) NOT NULL,
    difficulty VARCHAR(32) NOT NULL,
    rating FLOAT DEFAULT 4.5,
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rag_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id UUID REFERENCES skills(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    corpus_type VARCHAR(64) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rag_docs_embedding ON rag_documents USING hnsw (embedding vector_cosine_ops);
```
