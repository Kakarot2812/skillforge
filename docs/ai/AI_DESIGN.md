# SkillForge AI — AI Architecture & Design Principles

## 1. Core AI Principles

SkillForge AI establishes a strict architectural boundary between deterministic mathematical computation and generative artificial intelligence.

```text
Structured Data
+
Deterministic Algorithms
        ↓
   FACT / SCORE
        ↓
    LLM + RAG
        ↓
   EXPLANATION
```

### Foundational Invariants

> **"The LLM never decides what is true. It only reasons over what SkillForge has already verified."**

> **"Deterministic systems decide what is true. AI explains, reasons over, and personalizes verified evidence."**

This boundary is an immutable architectural invariant enforced at the code, schema, and API levels—not merely an instruction in a system prompt.

---

# Part 1: v1.0.0 MVP — Deterministic Intelligence

## 2. v1.0.0 MVP — Deterministic Intelligence

The frozen v1.0.0 MVP operates as an end-to-end deterministic intelligence engine. Core career intelligence, evidence aggregation, demand analysis, skill gap classification, and priority calculations do **not** depend on a live LLM or active RAG pipeline.

### Implemented MVP Intelligence Flow
```text
Resume Evidence
+
GitHub Evidence
+
Industry Skill Demand
        ↓
Canonical Skill Model
        ↓
Deterministic Skill Gap Engine
        ↓
Deterministic Priority Engine
        ↓
Evidence Audit
        ↓
Candidate Career Insight
```

The deterministic intelligence layer is solely responsible for producing authoritative results. No LLM generates, calculates, or mutates these outputs.

---

## 3. Division of Authority

### What the Deterministic Layer Decides (Authoritative)
- **Canonical Skill Identity**: Normalized against the canonical taxonomy dictionary and aliases.
- **Resume-Derived Evidence**: Claimed skills and raw text mentions extracted via structured parsing.
- **GitHub Demonstrated Evidence**: Concrete code artifacts (dependencies, Dockerfiles, CI workflows) and multi-repo score aggregation via independent probability union.
- **Industry Demand Signals**: Structured baseline metrics (`demand_score`, `growth_rate`, `sample_size`).
- **Skill Gap Classification**: Categorization into `STRONG`, `PARTIAL`, or `MISSING`.
- **Priority Scoring & Level**: Weighted calculation based on demand, growth, and gap severity (`HIGH`, `MEDIUM`, `LOW`).
- **Evidence Audit**: Direct traceability linking conclusions to source database records.

### What the LLM Does NOT Decide (Prohibited)
- Whether a candidate possesses a skill.
- Whether a skill is classified as `STRONG`, `PARTIAL`, or `MISSING`.
- The authoritative market demand score.
- The authoritative market growth signal.
- The authoritative priority score.

---

## 4. Evidence Flow Architecture

All intelligence flows through a strict evidence pipeline:

```text
Resume
   ↓
Resume Evidence (user_claimed_skills)
   ↓
Candidate Evidence

GitHub
   ↓
Repository Evidence (project_evidence)
   ↓
Demonstrated Skills (demonstrated_skills)

Industry Demand
   ↓
Market Evidence (skill_demand)

Candidate Evidence
+
Market Evidence
   ↓
Deterministic Intelligence Engine
   ↓
Skill Gap + Priority + Evidence Audit
```

The generative AI layer sits strictly **after** this verified intelligence pipeline, consuming its structured outputs as read-only grounding context.

---

# Part 2: Post-MVP Planned AI Architecture

> [!NOTE]
> All components, models, RAG pipelines, and conversational interfaces in Part 2 are **POST-MVP / PLANNED** on the `post-mvp-foundation` branch. They are not implemented in the frozen `v1.0.0-mvp` release.

---

## 5. Post-MVP — Qwen + RAG Architecture

In post-MVP evolution, SkillForge integrates a local open-weight large language model (**Qwen 3 8B**) coupled with a Retrieval-Augmented Generation (RAG) pipeline to provide natural-language reasoning, career coaching, and personalized learning guidance.

### Planned Post-MVP AI Flow
```text
Verified SkillForge Results
        +
Candidate Evidence
        +
Market Evidence
        ↓
Retrieval / RAG
        ↓
Qwen 3 8B (Local LLM)
        ↓
Structured AI Response
        ↓
Verification Gate
        ↓
User
```

Qwen 3 8B runs locally to ensure complete candidate data privacy, low latency, and zero data leakage to third-party APIs.

---

## 6. The Role of RAG (Retrieval vs. Calculation)

RAG functions strictly as an **evidence retrieval and contextual assembly mechanism**.

### What RAG Does NOT Do
- RAG does **not** calculate industry demand.
- RAG does **not** decide skill ownership.
- RAG does **not** classify skill gaps.
- RAG does **not** calculate priority scores.

### Authoritative Pipeline
```text
Market / Data Sources
        ↓
Data Ingestion & Normalization
        ↓
Deterministic Demand Engine
        ↓
Verified Market Data (PostgreSQL)
        ↓
Indexed / Retrievable Knowledge
        ↓
RAG Retrieval
        ↓
LLM Explanation
```

> **"RAG retrieves evidence.
> The deterministic demand engine determines the authoritative market signal."**

---

## 7. Evidence-Grounded Career Chatbot (P3)

The planned career chatbot provides natural-language interaction over verified candidate and market data.

### Example Interaction
**Candidate Question**: *"Why is Docker a high priority for me?"*

### Response Processing Pipeline
```text
Candidate Evidence (Zero Docker repo artifacts)
+
GitHub Evidence (No container manifests found)
+
Industry Demand (80% demand for Backend Engineer)
+
Growth Signal (+12% YoY growth rate)
+
Deterministic Priority Result (HIGH priority score: 0.71)
        ↓
RAG Retrieval (Audit trail + canonical role benchmarks)
        ↓
Qwen 3 8B
        ↓
Contextual Explanation:
"Docker is prioritized as HIGH because your target role (Backend Engineer)
exhibits 80% market demand with +12% annual growth, and no containerization
evidence was detected in your connected repositories."
```

The chatbot explains an existing, mathematically verified result rather than generating a subjective opinion.

---

## 8. AI Safety and Verification Boundary

To ensure complete reliability and prevent hallucination, the AI layer enforces strict verification rules:

1. **Non-Authoritative Output**: LLM responses are treated as untrusted interpretations until verified against database records.
2. **Candidate Fact Grounding**: All candidate assertions must originate directly from verified `user_claimed_skills` or `project_evidence`.
3. **Market Fact Grounding**: All market assertions must originate from verified `skill_demand` data.
4. **Classification Invariance**: Explanations must exactly reflect the deterministic gap classification (`STRONG`, `PARTIAL`, or `MISSING`).
5. **Priority Invariance**: Priority explanations must align with the calculated `priority_score` and tier.
6. **Explicit Abstention**: If required evidence is missing or ambiguous, the AI system must abstain with an explicit status code such as `INSUFFICIENT_EVIDENCE` rather than fabricating facts.
7. **No Override**: The LLM is technically barred from mutating system-of-record tables.

---

## 9. Future Verification Pipeline

Before an AI-generated explanation is returned to the user, an automated verification pipeline cross-validates the response:

```text
Deterministic Engine
        ↓
Verified Facts
        ↓
RAG Retrieval
        ↓
Qwen 3 8B
        ↓
Verification Gate
        ├── Validate factual claims against retrieved evidence
        ├── Validate candidate claims against candidate evidence
        ├── Validate market claims against market evidence
        ├── Validate classification against deterministic classification
        └── Validate priority explanation against deterministic score
        ↓
Verified Response Delivered to User
```

---

## 10. Conceptual Structured AI Response Schema

Future AI endpoints will return structured JSON envelopes to allow client-side validation and rendering:

```json
{
  "answer": "Docker is classified as a HIGH priority gap because it is required by 80% of Backend Engineer roles (+12% YoY) and lacks demonstrated code artifacts in your repositories.",
  "evidence": [
    {
      "source": "skill_demand",
      "metric": "demand_score",
      "value": 0.80
    },
    {
      "source": "project_evidence",
      "metric": "evidence_count",
      "value": 0
    }
  ],
  "sources": [
    "PostgreSQL:skill_demand",
    "PostgreSQL:project_evidence"
  ],
  "confidence": "HIGH",
  "status": "VERIFIED"
}
```

*(Note: This schema illustrates future design concepts and is not an active MVP API contract).*

---

## 11. AI Development Principles

1. **Evidence Before Generation**: Ground every prompt in verified database facts.
2. **Deterministic Core Before LLM**: Compute all numbers, ranks, and categories mathematically first.
3. **Retrieval Before Generation**: Retrieve relevant audit context before invoking the model.
4. **Verification After Generation**: Check generated statements against source facts.
5. **Abstain When Evidence is Insufficient**: Never guess or extrapolate beyond verified data.
6. **Zero Silent Overrides**: Never allow the LLM to alter authoritative system conclusions.
7. **Modular Decoupling**: Keep the system fully operational even if the AI explanation layer is offline.

---

## 12. Relation to Post-MVP Roadmap

The AI design aligns directly with the five-phase post-MVP roadmap:

```text
P1: Real-Time Industry Demand
        ↓ (Produces fresher, verified market evidence)
P2: Local Qwen 3 8B AI Layer
        ↓ (Provides local, privacy-preserving reasoning)
P3: Evidence-Grounded Career Chatbot
        ↓ (Enables natural-language interaction over verified facts)
P4: Personalized Roadmap + Resources
        ↓ (Generates actionable learning milestones matched to gaps)
P5: GitHub Verification Loop
          (Closes the loop from learning back to verified evidence)
```

Each phase builds systematically upon the verified foundation established in preceding phases.

---

## 13. Implementation Baseline Matrix

| Capability | v1.0.0 MVP (Frozen Baseline) | Post-MVP (Planned Evolution) |
| :--- | :--- | :--- |
| **Resume Evidence Extraction** | Implemented (Regex, PyMuPDF, Taxonomy Cache) | Extend (LLM ambiguous resolution) |
| **GitHub Evidence Extraction** | Implemented (Manifest & CI inspection) | Extend (Deeper AST inspection) |
| **Industry Skill Demand** | Implemented (Structured baseline data) | Real-time market data ingestion (P1) |
| **Skill Gap Classification** | Implemented (Deterministic rule-based) | AI explanation & contextual reasoning (P2) |
| **Priority Scoring** | Implemented (Deterministic formula) | AI explanation & contextual reasoning (P2) |
| **RAG Retrieval Engine** | Not implemented | Planned (pgvector semantic retrieval) |
| **Local Qwen 3 8B LLM** | Not implemented | P2-A client foundation, P2-B verified context contract, and P2-C evidence-grounded chatbot implemented; RAG deferred to P3 |
| **Career Chatbot** | Not implemented | Checkpoint P2-C evidence-grounded explanation service implemented (`/api/v1/ai/chat`); interactive dialogue / memory deferred to P3 |
| **Personalized Roadmap** | Not implemented | Planned (DAG prerequisite sequencing) (P4) |
| **GitHub Verification Loop**| Not implemented | Planned (Continuous milestone verification) (P5) |

---

## 14. Checkpoint P2-A Status: Local Qwen 3 8B / Ollama Foundation

Checkpoint P2-A establishes the isolated backend communication foundation for the locally running Qwen 3 8B model via Ollama.

### Core Architectural Invariants
- **Local Model Runtime**: Ollama operates entirely locally on the host machine (`OLLAMA_BASE_URL=http://localhost:11434`, default model `OLLAMA_MODEL=qwen3:8b`).
- **Zero Cloud Model Dependency**: No external AI APIs, cloud tokens, or API keys are required or supported.
- **Strict Non-Authoritative Role**: In strict compliance with *"The LLM never decides what is true"*, Qwen is technically and architecturally prohibited from deciding:
  - Skill possession or evidence validity
  - `STRONG`, `PARTIAL`, or `MISSING` skill gap status
  - Market `demand_score`, `growth_rate`, or `growth_class`
  - Candidate readiness score or `priority_score`
  - Database truth
- **Decoupled Application Startup**: FastAPI starts and operates completely independently of Ollama availability. If the local Ollama daemon is offline or stopped, all deterministic SkillForge functionality (resumes, GitHub evidence, market demand, skill gaps, priorities) remains 100% operational.
- **Stateless Infrastructure Layer**: Checkpoint P2-A introduces zero database models, migrations, or database writes.
- **Future AI Layers**: Later checkpoints (P2-B through P2-E) will pass verified deterministic facts from PostgreSQL into structured prompt contexts for natural-language explanation and reasoning.

---

## 15. Checkpoint P2-B Status: Verified Context Contract

Checkpoint P2-B establishes the formal, isolated **Verified Context Contract** between deterministic SkillForge intelligence and generative AI layers (`qwen3:8b`).

### Architectural Pipeline
```text
DETERMINISTIC SYSTEM (PostgreSQL / Evidence Engines)
            │
            ▼
     VERIFIED FACTS (Skills, Evidence, Market, Priorities)
            │
            ▼
P2-B VERIFIED CONTEXT CONTRACT (Pydantic v2 `frozen=True`)
            │
            ▼ (Deterministic Validation Gate)
     QWEN 3 8B (Explanation & Reasoning Layer)
            │
            ▼
AIGeneratedExplanation (status="EXPLANATORY")
```

### Core Invariants Enforced in Code
1. **Separation of Facts vs. Generated Text**:
   - `VerifiedContext` represents read-only, verified truth derived exclusively from deterministic SkillForge subsystems.
   - `AIGeneratedExplanation` represents explanatory output generated by the LLM. It is explicitly typed with `status="EXPLANATORY"`.
   - **No Reverse Path**: Generated text is strictly barred from mutating, updating, or entering `VerifiedContext`.
2. **Deterministic Source Provenance**:
   - Every verified fact carries explicit origin provenance typed via `FactProvenance` enum (`RESUME`, `GITHUB`, `MARKET`, `DETERMINISTIC_ANALYSIS`).
   - Free-form untyped provenance strings are rejected.
3. **Deep Immutability & Input Protection**:
   - All context models enforce Pydantic v2 `frozen=True` and `extra="forbid"`.
   - Context collections (`skills`, `evidence`, `market`, `priorities`) are typed as immutable tuples (`Tuple[..., ...]`), preventing programmatic modification, attribute mutation, and item append/reassignment after construction.
4. **Allowed Fact Types Only**:
   - Core context permits only strictly typed facts: `VerifiedCandidateContext`, `VerifiedSkillFact`, `VerifiedEvidenceFact`, `VerifiedMarketFact`, and `VerifiedPriorityFact`.
   - Unrestricted dicts (e.g. `facts: dict[str, Any]`) and arbitrary untyped payloads are strictly forbidden (`extra="forbid"`).
5. **No Raw Candidate Dumps**:
   - Whole resumes, raw document dumps, and entire GitHub repository file trees are barred from the context. Evidence is restricted to verified, bounded snippets (`snippet` length <= 2,000 characters).
6. **Deterministic Validation Gate**:
   - `validate_verified_context()` executes purely deterministically before any AI call.
   - Rejects empty contexts, invalid scores outside `[0.0, 1.0]`, invalid enums, unbounded collections, empty identifiers, and cross-fact inconsistencies.
7. **Stateless In-Memory Contract**:
   - Introduces zero database writes, zero SQLAlchemy queries, and zero Alembic migrations.
   - No automatic persistence of prompts or AI outputs.
8. **Deferred Capabilities**:
   - Checkpoint P2-B does **not** implement P2-C explanation logic, RAG retrieval/vector databases, chatbot dialogue, conversational memory, or roadmap generation.

---

## 16. Checkpoint P2-C Status: Evidence-Grounded Career Chatbot

Checkpoint P2-C establishes the first **Evidence-Grounded Career Chatbot** service and API endpoint (`POST /api/v1/ai/chat`) on top of the verified context contract (P2-B) and local Qwen 3 8B inference (P2-A).

### Architectural Pipeline
```text
Existing Deterministic Intelligence (PostgreSQL / Evidence Engines)
                      │
                      ▼
               VerifiedContext (P2-B)
                      │
                      ▼
           CareerChatService (P2-C)
                      │
                      ├── [Deterministic Validation Gate: validate_verified_context]
                      │
                      ├── [Deterministic Evidence Sufficiency Gate]
                      │          │
                      │          ├── Insufficient ──► CareerChatResponse(status="INSUFFICIENT_EVIDENCE") [No LLM Call]
                      │          │
                      │          └── Sufficient
                      │                   │
                      │                   ▼
                      ├── [Deterministic Prompt Serialization: serialize_verified_context]
                      │                   │
                      │                   ▼
                      └── [QwenClient.chat invocation]
                                          │
                                          ▼
                         CareerChatResponse (status="EXPLANATORY")
```

### Core Invariants Enforced in Code
1. **Evidence-Grounded Role**:
   - The chatbot explains, reasons over, and personalizes existing verified facts from `VerifiedContext`.
   - It is strictly barred from asserting new authoritative facts (`verified_skill`, `skill_classification`, `demand_score`, `priority_score`).
2. **Deterministic Evidence Sufficiency Gate**:
   - The service deterministically verifies whether the context contains the necessary facts before invoking Qwen.
   - If a question asks about candidate weakness in a skill that has market data but no candidate evidence, the service returns `status="INSUFFICIENT_EVIDENCE"` without calling Qwen (Rule 5: Market facts alone never imply candidate skill possession or weakness).
   - If a query asks about an unknown skill not present in the context, it returns `status="INSUFFICIENT_EVIDENCE"` immediately without calling Qwen.
3. **No General-Purpose Chatbot / Zero Persistence**:
   - The service is strictly stateless: 0 conversation history, 0 chat sessions, 0 persistent memory.
   - Each request receives a fresh, independent prompt containing only the verified context and user query.
4. **Zero Untyped Dictionaries**:
   - Replaces untyped dictionaries with strongly typed models: `CareerChatRequest`, `CareerChatResponse`, `ChatResponseStatus`, `ChatUsageStats`.
5. **Distinct Failure Classification**:
   - Clearly distinguishes between `INSUFFICIENT_EVIDENCE` (deterministic fact absence), `CareerChatServiceUnavailableError` (503: Ollama offline), `CareerChatTimeoutError` (504: generation timeout), and `CareerChatGenerationError` (502: API error). Infrastructure errors are never masked as lack of evidence.
6. **Stateless API Endpoint**:
   - `POST /api/v1/ai/chat` consumes an already-constructed and validated `VerifiedContext`.
   - Never constructs `VerifiedContext` from raw resume text, GitHub repositories, job postings, or arbitrary client JSON.
7. **Deferred Capabilities**:
   - Checkpoint P2-C does not implement RAG retrieval, pgvector embeddings, conversational history, autonomous tool calling, or roadmap generation.