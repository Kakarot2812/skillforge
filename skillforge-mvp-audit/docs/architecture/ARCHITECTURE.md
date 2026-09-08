# SkillForge AI — System Architecture

## 1. Architecture Overview

SkillForge AI uses a modular architecture consisting of:

- Web frontend
- API backend
- Resume intelligence service
- GitHub intelligence service
- Industry demand engine
- Skill engine
- Recommendation engine
- Roadmap engine
- RAG layer
- LLM layer
- PostgreSQL database
- pgvector

---

## 2. High-Level Architecture

```text
                         USER
                           │
                           ▼
                ┌─────────────────────┐
                │ Next.js Frontend    │
                │ TypeScript          │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ FastAPI Backend     │
                └──────────┬──────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
 Resume Service      GitHub Service      Demand Engine
       │                   │                   │
       ▼                   ▼                   ▼
 Resume Parser        GitHub API         Market Data
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
                  ┌─────────────────┐
                  │ Skill Engine    │
                  └────────┬────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
       User Skill Profile          Skill Demand
             │                           │
             └─────────────┬─────────────┘
                           ▼
                  ┌─────────────────┐
                  │ Skill Gap       │
                  │ Engine          │
                  └────────┬────────┘
                           ▼
                  ┌─────────────────┐
                  │ Recommendation  │
                  │ Engine          │
                  └────────┬────────┘
                           ▼
                  ┌─────────────────┐
                  │ Roadmap Engine  │
                  └────────┬────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
       Resource System             Project System
              │                         │
              └────────────┬────────────┘
                           ▼
                      RAG + LLM
                           │
                           ▼
                    User Explanation
```

---

## 3. Frontend

Technology:

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui
- Recharts

Responsibilities:

- Authentication UI
- Resume upload
- GitHub connection
- Target-role selection
- Skill dashboard
- Industry-demand visualization
- Skill-gap visualization
- Roadmap
- Resources
- AI assistant

---

## 4. Backend

Technology:

- Python
- FastAPI

Responsibilities:

- Authentication
- API orchestration
- Resume processing
- GitHub integration
- Skill analysis
- Demand engine access
- Gap calculation
- Roadmap generation
- Resource retrieval
- AI interaction

---

## 5. Database

Primary database:

**PostgreSQL**

Vector extension:

**pgvector**

PostgreSQL stores:

- Users
- Resumes
- Projects
- Skills
- Jobs
- Skill demand
- Roadmaps
- Resources
- Progress
- Evidence

pgvector stores embeddings used for semantic retrieval and normalization.

---

## 6. AI Architecture

The system separates deterministic/data-driven intelligence from generative AI.

### Data-driven components

- Skill frequency
- Demand
- Growth
- Skill-gap calculation
- Priority scoring
- Evidence scoring

### LLM components

- Resume understanding
- Ambiguous skill extraction
- Natural-language explanations
- Roadmap wording
- AI assistant

### RAG components

- Industry context
- Learning resource retrieval
- Supporting documentation
- Contextual explanations

RAG must not be the primary mechanism for calculating industry demand.

---

## 7. Future Components

Potential future additions:

- Redis
- Celery
- Neo4j
- Advanced forecasting models

These are not mandatory for the initial MVP.