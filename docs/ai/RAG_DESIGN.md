# SkillForge AI — RAG Architecture & AI Assistant Design

## 1. Purpose of RAG

Retrieval-Augmented Generation (RAG) is a planned post-MVP enhancement designed to provide semantic explanation, qualitative depth, and curated learning context for SkillForge AI.

### Core Architectural Principle

> **"RAG retrieves evidence. It does not calculate authoritative industry demand, skill gaps, or priority scores."**

```text
                 DETERMINISTIC TRUTH
                        │
                        ▼
        ┌──────────────────────────────┐
        │ SkillForge Verified Facts    │
        │                              │
        │ • Candidate evidence         │
        │ • Demonstrated skills        │
        │ • Industry demand            │
        │ • Growth signals             │
        │ • Skill gap classification   │
        │ • Priority scores            │
        └──────────────┬───────────────┘
                       │
                       ▼
                 RAG / RETRIEVAL
                       │
                       ▼
             Qwen 3 8B Local AI Layer
                       │
                       ▼
             Explanation / Guidance
```

In SkillForge AI, RAG is strictly an evidence retrieval and context-assembly mechanism. Authoritative quantitative metrics (demand scores, growth rates, gap statuses, and priority tiers) are computed deterministically by the platform's core mathematical engines. RAG supplies supporting documentation, learning resources, and project context so the local LLM can explain and reason over verified facts.

---

## 2. v1.0.0 MVP Boundary

> [!IMPORTANT]
> **RAG is NOT implemented in the v1.0.0 MVP.**
> The frozen v1.0.0 MVP operates entirely as a deterministic intelligence engine with zero runtime dependency on large language models, RAG pipelines, or vector stores.

The v1.0.0 MVP does **not** depend on:
- An LLM (local or cloud-hosted)
- A RAG retrieval pipeline
- Vector databases or semantic embedding models
- A RAG document store (e.g. `rag_documents` does not exist in the database)
- An AI conversational chatbot
- Semantic document retrieval
- An automated learning-resource recommendation engine

### Authoritative MVP Pipeline
```text
Resume Evidence (user_claimed_skills)
      +
GitHub Demonstrated Evidence (project_evidence & demonstrated_skills)
      +
Industry Skill Demand (skill_demand)
      ↓
Deterministic Skill Gap Engine
      ↓
Deterministic Priority Engine
      ↓
Evidence Audit Trail
```

The MVP system functions completely, robustly, and authoritatively without any AI or RAG components.

---

## 3. Planned Knowledge Architecture

In post-MVP phases, a curated knowledge base will be established to provide verified qualitative context for the AI assistant.

### Planned Knowledge Sources
Planned knowledge sources may include:
- **Official Technical Documentation**: Core reference architectures, API patterns, and framework guides.
- **Curated Learning Resources**: High-quality tutorials, reference courses, and documentation links mapped to canonical skills.
- **Project Challenge Specifications**: Practical engineering lab rubrics, starter templates, and milestone acceptance criteria.
- **Industry Context**: Technical whitepapers and engineering analyses explaining emerging technology adoption.

> [!NOTE]
> None of these corpora are ingested in the current MVP. All knowledge ingestion, curation, and indexing are planned post-MVP activities.

### Planned Document Metadata
Every ingested knowledge chunk will preserve strict provenance attributes:
- `canonical_skill_id`: Direct relational link to canonical taxonomy in the `skills` table
- `target_role_id`: Optional association with specific job roles
- `source_type`: Category of material (`official_doc`, `learning_resource`, `project_spec`, `industry_report`)
- `source_url`: Verifiable origin URL
- `version`: Software or framework version
- `difficulty_level`: Target expertise level (`beginner`, `intermediate`, `advanced`)
- `updated_at`: Ingestion or publication timestamp

### Chunking Strategy Note
Chunk sizes, token overlap parameters, embedding architectures, and indexing methods remain implementation decisions for the post-MVP RAG phase and will be determined through empirical validation.

---

## 4. Planned Retrieval Pipeline

The planned post-MVP retrieval engine will assemble contextual grounding packets to inform the local reasoning layer:

```text
User Query
    +
Candidate Context (Target Role, User Level)
    +
Verified Skill & Market Facts (Database Records)
    ↓
Metadata / Scope Filtering (Role, Skill ID)
    ↓
Semantic Retrieval (pgvector cosine similarity)
    +
Keyword Retrieval where useful (PostgreSQL tsvector)
    ↓
Evidence Ranking & Selection (Top-K Passages)
    ↓
Local Qwen 3 8B Model
    ↓
Structured, Evidence-Grounded Response
```

### PostgreSQL / pgvector Infrastructure
The SkillForge platform utilizes PostgreSQL for its relational database layer. For semantic vector retrieval, `pgvector` represents the natural planned architectural direction for embedding storage. However, RAG-specific vector tables, HNSW indices, and vector search endpoints belong strictly to post-MVP development.

---

## 5. Verified Facts vs Retrieved Context

SkillForge maintains an architectural separation between two distinct data streams:

| Dimension | A. Verified Structured Facts | B. Retrieved Context |
| :--- | :--- | :--- |
| **Origin** | Deterministic SkillForge core engines & SQL database | Future RAG knowledge repository |
| **Authority** | **Authoritative & Immutable** | Qualitative & Contextual |
| **Examples** | • Candidate demonstrated score ($0.95$)<br>• Skill gap status (`STRONG`, `PARTIAL`, `MISSING`)<br>• Authoritative demand score ($0.80$)<br>• YoY market growth rate ($+0.12$)<br>• Priority level (`HIGH`)<br>• Verified repository code artifacts<br>• Verified resume claims | • Official Docker containerization guides<br>• Recommended FastAPI tutorials<br>• Architectural best practices<br>• Milestone project acceptance rubrics<br>• Industry adoption context |
| **LLM Permitted Use** | Must use exact values; **never** alter or guess | Synthesizes to explain and contextualize verified facts |

### Numerical Truth Invariant
- **Industry Demand** is calculated exclusively by the deterministic Industry Demand Engine.
- **Skill Gaps** are classified exclusively by the deterministic Skill Gap Engine.
- **Priority Scores** are calculated exclusively by the deterministic Priority Engine.
- **RAG must NOT recalculate, modify, or estimate these values.**
- **The LLM must NOT invent or extrapolate alternative metrics.**

If the database establishes that `demand_score = 0.80`, `growth_rate = 0.12`, and `priority_level = "HIGH"`, the AI layer must reference those exact verified values.

### RAG Does Not Update Industry Demand
RAG is an evidence-retrieval mechanism, not an ingestion pipeline. Industry demand freshness is provided by the planned P1 Real-Time Market Demand pipeline:

```text
Job Market Sources
      ↓
Ingestion & Deduplication
      ↓
Skill Extraction & Normalization
      ↓
Deterministic Demand Calculation
      ↓
PostgreSQL (skill_demand table)
      ↓
SkillForge APIs / RAG Grounding Context
```

---

## 6. Grounding & Anti-Hallucination Constraints

The platform enforces immutable architectural rules to prevent model hallucinations:

> **"The LLM never decides what is true. It only reasons over what SkillForge has already verified."**

> **"Deterministic systems decide what is true. AI explains, reasons over, and personalizes verified evidence."**

### Hallucination Boundaries
The assistant is strictly forbidden from fabricating:
1. **Repository Evidence**: It must never claim a candidate demonstrated code unless a matching `project_evidence` record exists.
2. **Resume Claims**: It must never assert that a candidate claimed a skill unless verified in `user_claimed_skills`.
3. **Market Metrics**: It must never invent demand percentages, trend figures, or salary numbers.
4. **Skill Classifications**: It must never contradict deterministic gap statuses (`STRONG`, `PARTIAL`, `MISSING`).
5. **Priority Rankings**: It must never reorder priorities contrary to the deterministic priority score.

### Explicit Abstention (`INSUFFICIENT_EVIDENCE`)
If a user query asks for evidence or recommendations where database facts or retrieved context are missing or ambiguous, the AI layer must not guess. It must return an explicit abstention:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "message": "SkillForge does not have verified evidence or knowledge documents to answer this inquiry without speculation."
}
```

Abstaining is always architecturally preferable to generating plausible but unverified statements.

### Post-MVP Verification Layer
Before an AI response is returned to a user, a verification gate will cross-validate the generated output against grounding data:
```text
Deterministic Facts + Retrieved Knowledge
        ↓
Local Qwen 3 8B Generation
        ↓
Response Verification Gate
├── Verify factual metrics match deterministic database values
├── Verify candidate claims match candidate evidence
├── Verify gap status matches deterministic classification
└── Verify cited sources match retrieved knowledge chunks
        ↓
Verified Response Delivered to Candidate
```

---

## 7. Planned AI Assistant

The conversational assistant is scheduled as Phase 3 (**P3**) of the post-MVP roadmap.

### Roadmap Sequence
```text
P1: Real-Time Industry Demand
        ↓ (Generates continuous verified market evidence)
P2: Local Qwen 3 8B AI Layer
        ↓ (Deploys private, local open-weight inference engine)
P3: Evidence-Grounded Career Chatbot
        ↓ (Integrates RAG retrieval over verified facts and documents)
P4: Personalized Roadmap + Resources
        ↓ (Generates actionable learning milestones matched to gaps)
P5: GitHub Verification Loop
          (Closes the loop from learning back to verified code artifacts)
```

RAG and the AI Assistant build directly upon the market data foundation (P1) and local model infrastructure (P2).

### Local Qwen 3 8B Inference
The planned reasoning model is **Qwen 3 8B**, running locally on the user's host machine or dedicated platform infrastructure. Local inference ensures:
- Complete candidate privacy: sensitive resume details and repository code are never sent to third-party APIs.
- Zero external API token cost.
- Low-latency local context assembly.

---

## 8. Example Future Interaction

*(The following scenarios illustrate planned post-MVP capabilities. They are not implemented in v1.0.0).*

### Future Scenario A: Explaining a Skill Priority

**User Query**: *"Why is Docker ranked as a HIGH priority gap for me?"*

**Future System Execution**:
1. **Retrieve Verified Facts**: Fetches the candidate's gap record for `Docker` under role `Backend Engineer`:
   - `status`: `MISSING`
   - `demonstrated_score`: `0.0` (zero container artifacts detected across connected repositories)
   - `demand_score`: `0.80` (80% of regional backend roles require Docker)
   - `growth_rate`: `+0.12` (+12% YoY industry growth)
   - `priority_level`: `HIGH`
2. **Retrieve Context**: RAG retrieves a primer on why containerization is a baseline standard for distributed backend systems.
3. **Assemble Prompt**: Supplies verified facts and retrieved context to local Qwen 3 8B.
4. **Generate & Verify**: Qwen produces an explanation; verification confirms all numbers match the database.
5. **Final Output**:
   > *"Docker is classified as a HIGH priority gap because your target role (Backend Engineer) exhibits 80% market demand with +12% annual growth, while zero containerization evidence was detected in your connected repositories. Adding a Dockerfile and docker-compose setup to your projects will establish demonstrated evidence."*

### Future Scenario B: Personalized Learning Guidance

**User Query**: *"What should I learn to improve my Docker evidence?"*

**Future System Execution**:
1. **Inspect Gap & Demonstrated Evidence**: Notes candidate has strong Python/FastAPI code but lacks container configuration.
2. **Retrieve Curated Learning Resources**: RAG pulls verified project guides for containerizing FastAPI applications.
3. **Generate Actionable Guidance**: Proposes a practical milestone: create a multi-stage Dockerfile for their existing backend project.
4. **Grounding Verification**: Ensures all recommended libraries and patterns are aligned with canonical resources.

---

## 9. Post-MVP Evolution

The RAG architecture supports the five-phase post-MVP roadmap:

- **Phase 1 (P1) — Real-Time Industry Demand**: Establishes continuous job market ingestion, providing fresh, statistically sound demand metrics for grounding.
- **Phase 2 (P2) — Local Qwen 3 8B AI Layer**: Establishes local model inference, prompt templates, and structured JSON output parsing.
- **Phase 3 (P3) — Evidence-Grounded Career Chatbot**: Implements pgvector semantic retrieval, document chunking, and the evidence-grounded dialogue interface.
- **Phase 4 (P4) — Personalized Roadmap + Resources**: Uses RAG to map curated tutorials, documentation chapters, and project lab challenges to candidate gap priorities.
- **Phase 5 (P5) — GitHub Verification Loop**: Re-analyzes candidate repositories after project completion, updating demonstrated evidence and verifying gap closure.

---

## 10. AI Safety Invariants

The SkillForge AI architecture enforces ten fundamental invariants:

1. **MVP Independence**: The v1.0.0 MVP is fully operational and authoritative without RAG or LLM dependencies.
2. **Non-Authoritative Generation**: RAG and LLMs never calculate or override numerical demand metrics.
3. **Deterministic Gap Authority**: Skill gap classifications (`STRONG`, `PARTIAL`, `MISSING`) are determined solely by deterministic logic.
4. **Deterministic Priority Authority**: Priority scores and tiers are calculated solely by mathematical formulas.
5. **Strict Grounding**: Every candidate assertion must originate from verified database records (`user_claimed_skills`, `project_evidence`).
6. **Provenance Tracking**: All retrieved knowledge chunks must maintain verifiable source URLs and metadata.
7. **Explicit Abstention**: When evidence or context is insufficient, the system must abstain with `INSUFFICIENT_EVIDENCE` rather than speculate.
8. **Candidate Isolation**: Candidate evidence must remain strictly scoped to the active candidate and account.
9. **Decoupled Market Ingestion**: Real-time market demand freshness is generated by the ingestion pipeline, not by RAG retrieval.
10. **Explainability Role**: AI functions strictly as an explanation, reasoning, and personalization layer over verified facts.

---

## 11. MVP vs Post-MVP Capability Matrix

| Capability | v1.0.0 MVP (Frozen Baseline) | Post-MVP (Planned Evolution) |
| :--- | :--- | :--- |
| **Deterministic Demand Engine** | Implemented (Structured baseline data) | Real-time market ingestion (P1) |
| **Skill Gap Classification** | Implemented (Deterministic rule-based) | Maintained (Grounds AI layer) |
| **Priority Engine** | Implemented (Deterministic formula) | Maintained (Grounds AI layer) |
| **Evidence Audit Trail** | Implemented (Direct repo, file & claim links)| Maintained (Grounds AI layer) |
| **RAG Retrieval Engine** | Not implemented | Planned (pgvector semantic retrieval) (P3) |
| **Vector Embedding Storage**| Not implemented (No `rag_documents` table) | Planned (PostgreSQL `pgvector`) (P3) |
| **Curated Knowledge Corpora**| Not implemented | Planned (Docs, tutorials, rubrics) (P3) |
| **Local Qwen 3 8B LLM** | Not implemented | Planned (Local open-weight reasoning) (P2) |
| **Career Chatbot** | Not implemented | Planned (Evidence-grounded dialogue) (P3) |
| **Personalized Roadmap** | Not implemented | Planned (DAG milestone sequencing) (P4) |
| **GitHub Verification Loop**| Not implemented | Planned (Continuous gap closure) (P5) |
