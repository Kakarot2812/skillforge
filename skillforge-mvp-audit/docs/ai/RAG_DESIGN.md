# SkillForge AI — RAG Architecture & AI Assistant Design

## 1. Role of RAG in SkillForge AI

Retrieval-Augmented Generation (RAG) grounds the SkillForge AI Career Assistant in verified educational materials, project specifications, and contextual industry documentation.

### Core Architectural Constraint

> [!IMPORTANT]
> **RAG must NOT be the source of truth for numerical industry-demand scores.**
> All quantitative metrics (demand percentages, trend velocities, skill gap scores) are computed deterministically by the Industry Demand Engine and SQL database. RAG provides semantic explanation, qualitative depth, and resource discovery to support these numbers.

```text
┌──────────────────────────────────────────────┐
│             NUMERICAL TRUTH                  │
│    Industry Demand Engine (SQL / Tables)     │
│        • Demand %  • Trend %  • Gap %        │
└──────────────────────┬───────────────────────┘
                       │ (Grounding Facts)
                       ▼
┌──────────────────────────────────────────────┐
│           QUALITATIVE CONTEXT (RAG)          │
│    PostgreSQL pgvector (Knowledge Chunks)    │
│        • Official Docs  • Project Briefs     │
│        • Learning Guides • Industry Reports  │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│            LLM REASONING & OUTPUT            │
│   Explainable Recommendations & Guidance     │
└──────────────────────────────────────────────┘
```

---

## 2. Knowledge Base Corpora & Chunking

The RAG index ingests four curated corpora:

| Corpus | Content Description | Metadata Tags |
| :--- | :--- | :--- |
| **Official Documentation** | Curated summaries of core frameworks, architectural patterns, and reference APIs. | `skill_id`, `doc_type: "official_guide"`, `version` |
| **Learning Resources** | Course outlines, tutorial chapters, book recommendations, and video transcripts. | `skill_id`, `difficulty: "beginner" \| "intermediate" \| "advanced"`, `est_minutes` |
| **Project Challenge Briefs** | Detailed functional specs, architectural diagrams, acceptance rubrics, and starter code hints. | `skill_id`, `role_id`, `project_type: "hands_on_lab"` |
| **Industry Context Reports** | Whitepapers, engineering blogs, and market commentary explaining *why* technologies are emerging. | `role_id`, `topic`, `published_date` |

### Chunking Strategy

- **Chunk Size**: $350 - 500$ tokens per chunk.
- **Chunk Overlap**: $50$ tokens to preserve syntactic and semantic boundary context.
- **Metadata Association**: Every vector embedding is coupled with a relational foreign key pointing directly to the canonical skill in the `skills` table.

---

## 3. Storage & Retrieval Pipeline

### 3.1 Vector Database Schema

Embeddings are stored in PostgreSQL using the `pgvector` extension:

```sql
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

CREATE INDEX idx_rag_documents_embedding 
ON rag_documents USING hnsw (embedding vector_cosine_ops);

CREATE INDEX idx_rag_documents_skill_id 
ON rag_documents (skill_id);
```

### 3.2 Hybrid Retrieval Pipeline

To ensure precision and speed, the retrieval engine follows a two-stage hybrid process:

```text
[User Query + Active Context]
             │
             ├──► 1. Metadata Filtering (Active Skill IDs, Target Role, User Level)
             │
             ├──► 2. Semantic Dense Retrieval (pgvector cosine similarity)
             │
             └──► 3. Keyword Sparse Matching (PostgreSQL tsvector full-text search)
             │
             ▼
     [Reciprocal Rank Fusion (RRF)]
             │
             ▼
    [Top-K Grounding Chunks]
```

1. **Structured Context Filter**: Restricts candidate chunks to the user's active roadmap milestone or target role skills.
2. **Dense Vector Search**: Computes cosine distance against `rag_documents.embedding`.
3. **Keyword Ranking**: Matches exact technical terms (e.g., function names, CLI flags, package versions).
4. **Rank Fusion**: Selects the top $K=5$ most relevant and authoritative context passages.

---

## 4. Grounding Constraints & Prompt Engineering

System prompts enforce strict hallucination barriers:

```text
You are the SkillForge AI Career Copilot. Your role is to explain recommendations,
assist with project challenges, and provide technical guidance.

CRITICAL RULES:
1. Grounding: Rely strictly on the provided SQL Data Facts and Retrieved Context.
2. Demand Metrics: Never invent, guess, or modify industry demand numbers or percentages.
   Always refer to the exact values provided in the Context:
   - Target Role: {target_role}
   - Skill Demand: {demand_percentage}%
   - Trend: {growth_trend}
3. Actionable Guidance: When explaining a skill gap, direct the user toward the assigned
   practical project challenge and curated learning resources.
4. Code Examples: Ensure all code snippets follow modern industry standards and include
   type hints and error handling.
```

---

## 5. Interaction Scenarios

### Scenario A: Explaining a Skill Gap Recommendation
- **User Query**: *"Why is Docker ranked as my highest priority gap for Backend Engineer?"*
- **System Action**: 
  - Pulls exact demand facts from database: `Demand: 64%`, `Trend: +14%`, `User Evidence: 0%`.
  - Retrieves official Docker backend architecture primer from `rag_documents`.
- **Response**: Explains that 64% of backend listings require containerization, noting that while the user has strong Python and database skills, zero container manifests were found in their GitHub repositories. Outlines the milestone challenge to containerize their existing API.

### Scenario B: Clarifying a Project Challenge
- **User Query**: *"What are the exact acceptance criteria for my FastAPI milestone project?"*
- **System Action**:
  - Retrieves the milestone rubric from `rag_documents` filtered by `milestone_id`.
- **Response**: Outlines the required endpoints, Dockerfile multi-stage build structure, and Pytest coverage threshold necessary to pass the automated GitHub verification check.
