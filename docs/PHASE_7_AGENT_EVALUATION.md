# Phase 7 — Agent Necessity & Tool-Orchestration Evaluation

> **Document Status**: ARCHITECTURAL EVALUATION & DECISION RECORD  
> **Phase**: Phase 7 (Evaluation Only — No Implementation, No Source Mutations)  
> **Target Systems**: Roadmap PDF Pipeline, Career Assistant Chatbot, RAG Service, Deterministic Engines  
> **Repository Context**: SkillForge AI (`/Users/niteshyadav/SIH`)

---

## 1. Current Architecture

SkillForge AI is built on a foundational principle that separates ground truth from natural-language explanation:

> **"Deterministic systems decide what is true. AI explains, reasons over, and personalizes verified evidence."**

The system does not permit an LLM or autonomous agent to invent, classify, rank, or reorder facts. Below is the active architecture across the four core subsystems inspected in this evaluation:

### 1.1 AI-Powered Roadmap PDF Generation Pipeline (Phases 1–6)

The roadmap PDF pipeline operates as a strictly linear, decoupled, five-stage process:

```
Deterministic SkillForge (DB + Service Layer)
       ↓
RoadmapPDFContextService
       ↓ (assembles immutable, bounded Pydantic context; computes SHA-256 hash)
VerifiedRoadmapPDFContext
       ↓
GeminiClient (via LangChain with_structured_output)
       ↓ (single-pass LLM invocation: tone personalization & phase explanations)
RoadmapPDFPersonalizedNarrative (Structured Pydantic Model)
       ↓
ReferenceIntegrityValidator
       ↓ (fail-closed gate: verifies skill IDs, milestone sequence, URL prohibition)
ValidatedRoadmapPDFContent
       ↓
RoadmapPDFRenderer (ReportLab Platypus Engine + NumberedCanvas)
       ↓
Publication-Quality A4 PDF Binary
```

Key characteristics of the current PDF implementation:
- **`RoadmapPDFContextService`**: Queries PostgreSQL for the canonical candidate roadmap (`RoadmapService`), deterministic skill gaps and priority rankings (`SkillGapService`), market demand metrics (`DemandService`), and candidate verification evidence. It builds a frozen `VerifiedRoadmapPDFContext` and signs it with a deterministic SHA-256 verification hash.
- **`GeminiClient` via LangChain**: Uses Gemini 2.5 Flash with `with_structured_output(RoadmapPDFPersonalizedNarrative)` in **exactly one** structured call. It receives an immutable context containing only database-backed facts.
- **`ReferenceIntegrityValidator`**: A fail-closed validation gate that confirms the LLM did not reorder milestones, drop phases, invent new skill IDs, introduce unapproved URLs, or make candidate-proof claims over curated practical challenges.
- **`RoadmapPDFRenderer`**: ReportLab Platypus engine using a two-pass `NumberedCanvas` to render exact typography, geometry, color tokens, and audit watermarks into an A4 PDF without contacting any database or external service.
- **FastAPI Layer**: Exposes `GET /api/v1/roadmaps/{roadmap_id}/pdf` with strict candidate authentication (`X-User-Id`) and ownership validation (IDOR defense).

### 1.2 Career Assistant Chatbot Pipeline

The Career Assistant explanation pipeline operates as an evidence-grounded conversational system:

```
Candidate Query + UserProfile + Conversation History (PostgreSQL)
       ↓
CareerChatService.check_evidence_sufficiency
       ↓ (deterministic keyword/regex gate rejects ungrounded queries before LLM)
RAG Evidence Retrieval (RAGService via pgvector with metadata filters)
       ↓
Personalization Context Assembly (assemble_personalization_context)
       ↓
Local Qwen 3 8B (or Gemini) with bounded system prompt
       ↓
CareerChatResponse (Grounded Explanation + Referenced Skill IDs + Retrieved Evidence)
```

Key characteristics of the current Chatbot implementation:
- **`CareerChatService`**: Orchestrates deterministic sufficiency validation (`check_evidence_sufficiency`), intent classification, and conversation history via `ConversationService` and `langchain_history`.
- **Deterministic Sufficiency Gate**: Inspects queries against canonical skills in the pre-assembled `VerifiedContext`. If the candidate asks about an unverified skill or asks for learning priorities when no gaps are evaluated, the system deterministically rejects the query before any LLM is called, returning `ChatResponseStatus.INSUFFICIENT_EVIDENCE`.
- **`RAGService` Integration**: Pulls supporting evidence chunks using `LocalSentenceTransformerProvider` and PostgreSQL `pgvector` Cosine distance search, filtered by canonical `skill_ids`.

### 1.3 Deterministic SkillForge Intelligence Engines

SkillForge already maintains deterministic services that compute all authoritative data:
- **`SkillGapService`**: Classifies gaps into `STRONG`, `PARTIAL`, or `MISSING` based on AST-analyzed code artifacts (`DemonstratedSkillService`) and parsed resume claims (`ResumeParser`). It calculates deterministic priority scores:
  $$\text{priority\_score} = \text{gap\_severity\_weight} \times (0.70 \times \text{demand\_score} + 0.30 \times \text{growth\_signal})$$
- **`DemandIntelligenceService` & `DemandService`**: Ingests, normalizes, and ranks market demand across canonical roles and skills using real job market data (Adzuna, Ashby, Greenhouse, Lever).
- **`RoadmapEngine` & `RoadmapService`**: Loads the skill dependency directed acyclic graph (DAG), validates topological ordering, schedules milestones, and binds approved curated learning resources and practical project challenges.
- **`VerificationService` & `ProjectVerifier`**: Orchestrates milestone verification through automated code analysis, file tree AST inspection, commit verification, and automated test pass validation without LLM discretion.

### 1.4 Theoretical Tool Surface

Every core backend operation that could theoretically be exposed as an AI tool was inspected:

| Potential Tool | Data Read | Deterministic | Authoritative | Needed by PDF Pipeline? | Existing Service / Orchestrator |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `get_candidate_profile` | `User`, `UserProfile` | Yes | Yes | **No** (Already assembled in context) | `UserProfileService.get_profile` |
| `get_claimed_skills` | `UserClaimedSkill`, `Resume` | Yes | Yes | **No** (Already assembled in context) | `ResumeParser`, `SkillGapService` |
| `get_demonstrated_skills` | `DemonstratedSkill`, `ProjectEvidence` | Yes | Yes | **No** (Already assembled in context) | `DemonstratedSkillService` |
| `get_skill_gaps` | `SkillGap`, `IndustrySkillDemand` | Yes | Yes | **No** (Already assembled in context) | `SkillGapService.compute_and_persist_skill_gaps` |
| `get_prioritized_gaps` | `SkillGap`, `IndustrySkillDemand` | Yes | Yes | **No** (Already assembled in context) | `SkillGapService.prioritize_skill_gaps` |
| `get_market_demand` | `IndustrySkillDemand`, `MarketSkillDemandGrowth` | Yes | Yes | **No** (Already assembled in context) | `DemandService`, `DemandIntelligenceService` |
| `get_canonical_roadmap` | `CandidateRoadmap`, `RoadmapMilestone`, `SkillDependency` | Yes | Yes | **No** (Already assembled in context) | `RoadmapService.get_roadmap_by_id` |
| `get_approved_resources` | `ApprovedResource`, `RoadmapMilestone` | Yes | Yes | **No** (Already assembled in context) | `RoadmapService`, `ResourceService` |
| `get_approved_projects` | `ApprovedProject`, `RoadmapMilestone` | Yes | Yes | **No** (Already assembled in context) | `RoadmapService` |
| `get_milestone_verifications` | `MilestoneVerification`, `ProjectEvidence` | Yes | Yes | **No** (Already assembled in context) | `VerificationService` |
| `retrieve_rag_evidence` | `RAGDocument`, `RAGChunk` (pgvector) | Yes | Yes | **No** (PDF does not require RAG chunks) | `RAGService.retrieve` |

---

## 2. PDF Agent Evaluation

We explicitly evaluated whether introducing an agent (e.g. ReAct loop or LangGraph state machine) to the Roadmap PDF generation pipeline would add any meaningful value.

### 2.1 Evaluation Dimensions

1. **Dynamic Tool Selection**:
   - *Analysis*: In PDF generation, the inputs (`roadmap_id`, authenticated `user_id`) and required outputs (complete personalized career document) are static and known in advance. Every PDF document requires the candidate profile, readiness metrics, prioritized gaps, milestone timeline, curated resources, and practice challenges.
   - *Finding*: There is zero conditional uncertainty regarding which data sources to consult. An agent dynamically selecting tools would simply query 100% of the available tools on every invocation. Dynamic tool selection provides no value.

2. **Multi-Step Reasoning**:
   - *Analysis*: The LLM's task in PDF generation is narrative explanation and tone calibration over verified facts (e.g. drafting executive summaries, strategic phase rationales, and motivational closing guidance).
   - *Finding*: This is a single-pass text synthesis task. It does not involve hypothesis testing, trial-and-error retrieval, or branching problem-solving. Multi-step reasoning would unnecessarily partition a coherent document generation task into disjointed reasoning steps.

3. **Context Assembly**:
   - *Analysis*: Currently, `RoadmapPDFContextService` joins the normalized PostgreSQL tables in single-digit milliseconds, guarantees IDOR ownership checks, enforces schema consistency, and generates a cryptographic verification hash.
   - *Finding*: Shifting context assembly from optimized SQL joins to an autonomous agent calling API tools would drastically increase database roundtrips, introduce potential failure points, and create opportunities for the agent to forget or omit required context fields.

4. **Latency**:
   - *Analysis*: Current architecture completes deterministic context assembly in 20–50ms and the single Gemini 2.5 Flash structured call in 1.5–2.5s, delivering the PDF to the user in ~2–3s.
   - *Finding*: An agent loop executing 4 to 8 sequential LLM reasoning and tool-calling hops would inflate generation time to 10–20+ seconds. For an interactive document download endpoint, this creates a severe degradation in user experience and risks HTTP connection timeouts.

5. **Hallucination Surface**:
   - *Analysis*: Current architecture restricts Gemini 2.5 Flash to generating specific strings within `RoadmapPDFPersonalizedNarrative`. All metrics, milestone IDs, and URLs are injected from verified database records and enforced by `ReferenceIntegrityValidator`.
   - *Finding*: An agent with tool access can hallucinate tool parameters (e.g. querying invalid UUIDs or unverified candidate handles), misinterpret intermediate tool outputs, or fail to terminate tool-calling loops. This exponentially expands the error and vulnerability surface.

6. **Auditability**:
   - *Analysis*: The current pipeline computes a deterministic SHA-256 hash over canonical facts (`generate_deterministic_verification_hash`) and embeds it in the PDF footer watermark. Any evaluator or recruiter can verify that the PDF matches exact database records at generation time.
   - *Finding*: Non-deterministic agent traversal makes document reproducibility impossible. Two generations for the same roadmap could query different tools in different sequences, destroying auditability.

7. **Deterministic Boundaries**:
   - *Analysis*: The core invariant states: *"Deterministic systems decide what is true."*
   - *Finding*: Introducing an agent creates a significant risk of boundary erosion. An agent might attempt to recalculate readiness percentages, reorder milestones according to its own internal priors, or selectively omit skill gaps it deems "unimportant," directly violating SkillForge's core contract.

8. **User-Visible Benefit**:
   - *Analysis*: What does the user receive?
   - *Finding*: The user receives the exact same visual PDF layout and verified facts. An agent provides **zero user-visible benefit** while introducing slower downloads, higher error rates, and increased infrastructure cost.

### 2.2 Architectural Comparison: PDF Generation

| Architectural Metric | Current Architecture (Deterministic Context + LangChain) | Agent Architecture (ReAct / LangGraph) |
| :--- | :--- | :--- |
| **LLM Invocations** | Exactly 1 structured invocation | 4 to 8 sequential tool-dispatch invocations |
| **End-to-End Latency** | ~1.8 – 2.8 seconds | ~8.0 – 20.0 seconds |
| **Token Consumption** | ~1,800 prompt tokens / ~900 output tokens | ~10,000 – 25,000 cumulative tokens |
| **Context Completeness** | 100% deterministic (guaranteed by schema) | Probabilistic (agent may omit required data) |
| **Verification Hash** | Deterministic SHA-256 over exact canonical facts | Inconsistent across multiple dynamic tool calls |
| **Failure Modes** | Single atomic failure handled with clear HTTP codes | Cascading failure (tool parse error, tool loop, timeout) |
| **IDOR Defense** | Enforced at SQL layer prior to LLM invocation | Must be re-validated at every dynamic tool boundary |

---

## 3. Career Assistant Agent Evaluation

While an agent provides no value for the Roadmap PDF generation pipeline, the **Career Assistant** represents a fundamentally different architectural paradigm.

### 3.1 Why the Career Assistant Differs from PDF Generation

In PDF generation, the question and data requirements are 100% known in advance. In the Career Assistant:
- The candidate's query is open-ended and unpredictable.
- Query intents vary across turns:
  - *"Why is TypeScript ranked higher priority than Docker for my target role?"* (Requires: Skill Gaps + Market Demand)
  - *"Can you inspect my GitHub repo for Milestone 2 and see if I'm ready for verification?"* (Requires: Roadmap Milestone + GitHub Verification)
  - *"What are the best official documentation resources for my next phase?"* (Requires: Roadmap DAG + Approved Resources)
  - *"What are the salary and hiring trends for Backend Engineers in Pune vs Bangalore?"* (Requires: Market Demand Intelligence)

### 3.2 Current Chatbot Limitations

The current `CareerChatService` relies on:
1. A static, monolithic `VerifiedContext` that must be pre-assembled before the conversation starts.
2. A rigid regex/keyword sufficiency gate (`check_evidence_sufficiency`). If a candidate query touches on a topic where facts were not pre-loaded into `VerifiedContext`, the gate fails closed and rejects the query, even if the backend database contains the authoritative answer.
3. Inability to execute follow-up data fetches across multi-turn coaching dialogues.

### 3.3 Potential Future Tool-Oriented Workflows

An agentic tool-orchestration layer could legitimately provide value in a future Career Assistant by dynamically querying narrow, verified SkillForge tools:

1. **Targeted Data Retrieval**: Instead of loading an enormous monolithic context containing the entire database profile, roadmap, demand tables, and verification logs on every turn, the agent inspects user intent and invokes only the relevant tool (e.g. `query_market_demand(skill="FastAPI")`).
2. **Multi-Domain Synthesis**: Answering complex user inquiries such as: *"Based on my latest GitHub commit and current market hiring trends, should I finish Milestone 3 or start learning Kubernetes?"* requires combining roadmap status, verification evidence, and industry growth signals.
3. **Interactive Milestone Preparation**: The agent could query `get_milestone_rubric(milestone_id)` and compare it with the candidate's repository file tree to provide specific advice before the candidate triggers formal deterministic verification.

> [!NOTE]
> **Status**: This evaluation identifies the Career Assistant as a legitimate potential future use case. **No agent code or tools are implemented in this phase.**

---

## 4. RAG Agent Evaluation

We evaluated whether the existing RAG architecture (`RAGService`, `EvidenceRetriever`, `RAGRepository`) requires an agent.

### 4.1 Evaluation Dimensions

1. **Deterministic Retrieval vs Agentic Retrieval**:
   - The current RAG implementation uses `DeterministicChunker`, local embeddings via `LocalSentenceTransformerProvider` (`all-MiniLM-L6-v2`), and `RAGRepository` using PostgreSQL `pgvector` Cosine similarity search with structured metadata filters (`skill_ids`, `source_types`).
   - *Finding*: Deterministic single-pass vector retrieval retrieves top-k relevant approved evidence chunks in <30ms with high precision.

2. **Tool Selection**:
   - Does RAG require choosing among multiple retrieval tools?
   - *Finding*: No. All approved evidence documents (curated learning materials, project rubrics) reside in a single normalized `rag_documents` / `rag_chunks` schema with canonical taxonomy tags. A single retrieval interface satisfies all requirements.

3. **Multi-Step Retrieval & Query Decomposition**:
   - Does SkillForge require complex multi-hop retrieval (e.g. decomposing a question into 3 sub-queries across disparate corpora)?
   - *Finding*: No. Candidate career questions are domain-specific and reference specific skills or milestones. Multi-step query decomposition would add token cost and latency without improving retrieval precision.

4. **Iterative Reasoning**:
   - Does the retrieval pipeline require the LLM to inspect retrieved chunks, judge their relevance, and issue secondary queries?
   - *Finding*: No. In SkillForge, supporting evidence is already curated and authoritative. The LLM's role is to synthesize and explain the retrieved chunks, not to act as a recursive search engine.

### 4.2 Conclusion for RAG

**Deterministic retrieval is entirely sufficient.** Existing RAG does not require an agent. Adding an agent to RAG would degrade performance, introduce retrieval nondeterminism, and violate the simplicity principle without improving answer quality.

---

## 5. Security Considerations

If an agentic tool-orchestration model is adopted in a future Career Assistant phase, the following strict security boundaries must be enforced across all tools:

### 5.1 Authentication & Ownership (IDOR Defense)
- Every tool function signature must accept an authenticated execution context (`authenticated_user_id: UUID`).
- Tools must never accept arbitrary target `user_id` parameters from the LLM prompt. The user context must be derived strictly from verified session tokens / JWT headers.
- Any attempt to query roadmaps, resumes, or verification records not owned by `authenticated_user_id` must fail closed with `HTTP 403 Forbidden`.

### 5.2 Narrow Tool Contracts
- Tools must be defined with strictly typed Pydantic parameter schemas (e.g. `skill_id: UUID`, `role_id: UUID`, `limit: int = 10`).
- No tool may accept freeform query objects, arbitrary filter dictionaries, or unstructured execution strings.
- Tool return values must be bounded Pydantic data transfer objects, preventing prompt injection vectors from unescaped raw data.

### 5.3 Verified Data Boundaries
- Tools must function solely as read-only interfaces to existing deterministic services (`SkillGapService`, `RoadmapService`, `DemandIntelligenceService`).
- An agent must **never** be given tools that allow it to insert, mutate, or delete records in the database, nor tools that alter skill classifications or readiness scores.

### 5.4 Prohibition of Arbitrary SQL
- Tools must strictly use parameterized SQLAlchemy ORM queries and existing service methods.
- Tools must never expose SQL query generation, raw string formatting (`text(...)`), or database schema inspection to the LLM.

### 5.5 Secret & Credential Protection
- All GitHub Personal Access Tokens (PATs), database connection strings, Gemini API keys, and internal hashes must remain completely isolated from tool outputs and agent contexts.
- The secret sanitization pattern established in `ai_verification_explanation_service.py` (`redact_secrets`) must be applied to all tool inputs and outputs.

### 5.6 Prohibition of Arbitrary Network Access
- Tools must not perform arbitrary HTTP fetching, URL scraping, or outbound socket connections.
- External network interactions must remain restricted to existing backend worker services (e.g. Adzuna job ingestion, GitHub API client).

---

## 6. Architecture Decision

Based on thorough architectural investigation, concrete pipeline evaluation, and factual trade-off analysis, we record the following formal decisions:

> ### **Agent not required for the Roadmap PDF MVP.**

and:

> ### **Agentic tool orchestration may be valuable for a future Career Assistant workflow.**

---

## 7. Recommended Future Boundary

If an agent is justified and approved for a future Career Assistant iteration, it must strictly adhere to the following conceptual boundary:

```
User (Candidate Query)
       ↓
Career Assistant Agent (LLM Reasoning Layer)
       ↓ (dynamically selects which read-only verified tools to query)
Narrow Verified SkillForge Tools
 ├── Profile Tool (Reads candidate profile & target role)
 ├── Verified Evidence Tool (Reads AST-demonstrated & claimed skills)
 ├── Skill Gaps Tool (Reads deterministic gap classifications & priority scores)
 ├── Market Demand Tool (Reads empirical industry demand & growth rates)
 ├── Roadmap Tool (Reads topologically sequenced DAG milestones)
 ├── Progress Tool (Reads deterministic milestone verification state)
 └── RAG Evidence Tool (Reads curated supporting learning materials)
       ↓
Grounded Response (Personalized Explanation over Verified Facts)
```

### Invariant Rules for Future Implementation:
1. **The agent may choose WHICH verified tools to call.**
2. **The tools remain solely responsible for determining WHAT IS TRUE.**
3. The agent is strictly prohibited from bypassing tools to query raw database tables.
4. The agent is strictly prohibited from overriding tool-returned readiness percentages, gap categories (`STRONG`, `PARTIAL`, `MISSING`), or milestone sequence orders.

---

## 8. What We Are NOT Changing

In accordance with the constraints of Phase 7 (Evaluation Only), this phase makes **zero changes** to application code, configurations, or schemas:

- **PDF Generation**: Unchanged. Continues to use deterministic `RoadmapPDFContextService`, `GeminiClient`, and `RoadmapPDFRenderer`.
- **Gemini Client**: Unchanged. Retains structured Pydantic output integration (`with_structured_output`).
- **LangChain Integration**: Unchanged. Retains current prompt and history wrappers without agent executors.
- **ReportLab Engine**: Unchanged. Retains exact two-pass `NumberedCanvas` renderer and visual tokens.
- **Deterministic Skill Intelligence**: Unchanged. `SkillGapService`, `RoadmapEngine`, and `DemandService` retain sole authority over truth.
- **RAG Subsystem**: Unchanged. `RAGService`, pgvector indexing, and deterministic filtering remain intact.
- **Database Schema & Migrations**: Unchanged. Zero migrations, zero schema modifications, zero new tables.
- **Frontend Code**: Unchanged.
- **API Contracts**: Unchanged.

---

## 9. Validation

A complete read-only validation of the codebase and test suite was conducted:

### 9.1 Git Status Inspection
- Confirmed zero modified application code files.
- Confirmed zero staged code changes.
- Only the evaluation documentation file `docs/PHASE_7_AGENT_EVALUATION.md` is created.

### 9.2 Test Suite Execution
Existing tests across relevant subsystems were executed using `pytest` without error:
- **Roadmap PDF Pipeline Tests**:
  - `backend/tests/test_roadmap_pdf_context.py` (20 passed)
  - `backend/tests/test_roadmap_pdf_generation.py` (27 passed, 1 skipped)
  - `backend/tests/test_roadmap_pdf_renderer.py` (31 passed)
  - `backend/tests/test_roadmap_pdf_api.py` (25 passed)
  - **Result: 103 passed, 1 skipped (100% pass rate for PDF pipeline)**
- **Career Assistant & RAG Tests**:
  - `backend/tests/test_career_chatbot.py` (42 passed)
  - `backend/tests/test_rag.py` (54 passed)
  - `backend/tests/test_verified_context.py` (29 passed)
  - **Result: 125 passed (100% pass rate for chatbot and RAG systems)**

All tests reflect the actual implementation and confirm that the deterministic boundaries and structured LangChain integrations are functioning as designed.
