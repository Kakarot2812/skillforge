# SkillForge AI — Resume Analysis Engine

## 1. Purpose & Core Principles

The Resume Analysis Engine serves as the initial skill extraction gateway in SkillForge AI.

It parses unconstrained, multi-format candidate resumes to identify claimed technical skills, educational background, work history, and engineering projects.

### Core Principles

1. **Claimed vs. Demonstrated**: Skills extracted from a resume are classified strictly as **Claimed Skills**. They represent self-assertions that require empirical verification through GitHub project inspection.
2. **Context-Aware Extraction**: Differentiates between skills actively used in key projects versus technologies merely listed in keyword blocks.
3. **Canonical Normalization**: All extracted terms are mapped directly to the platform's canonical skill taxonomy.
4. **Resilience to Formatting**: Ingests standard PDF and DOCX formats without requiring ATS-specific formatting templates.

---

## 2. Ingestion & Parsing Architecture

```text
┌───────────────────────────────┐
│     Uploaded Resume File      │
│         (PDF / DOCX)          │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│  Layout & Text Extraction     │
│   (PyMuPDF / pdfplumber)      │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│   Structural Segmentation     │
│ (Header, Experience, Projects,│
│     Skills, Education)        │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│    Entity Extraction Layer    │
│  - Dictionary & Regex Matcher │
│  - LLM Contextual Extraction  │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│     Taxonomy Normalizer       │
│  - Exact Alias Matching       │
│  - pgvector Semantic Distance │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│     Claimed Skill Matrix      │
│  (Persisted in PostgreSQL)    │
└───────────────────────────────┘
```

---

## 3. Processing Pipeline

### 3.1 Document Ingestion & Text Extraction
- Reads binary streams from `POST /api/v1/resumes/upload`.
- Uses layout-aware text extraction to preserve paragraph structures, dates, bullet points, and headings.
- Strips non-printable characters and normalizes whitespace.

### 3.2 Structural Section Segmentation
The raw text is segmented into logical resume sections using heuristic heading detection and regex patterns:
- **Contact & Header**: Name, email, GitHub handle, LinkedIn URL.
- **Skills Section**: Dedicated technology, tools, and language lists.
- **Experience / Internships**: Chronological job titles, organizations, dates, and narrative bullet points.
- **Projects**: Self-directed and academic projects, project titles, tech stacks, and GitHub links.
- **Education & Certifications**: Degrees, institutions, graduation dates, and certifications.

### 3.3 Skill Extraction Strategy
Extraction uses a two-tier hybrid model:
1. **Direct Dictionary & Pattern Matching**: Scans against canonical skills and aliases from `skill_aliases`.
2. **LLM Contextual Extraction**: Identifies technologies mentioned within narrative project bullets where exact phrasing varies (e.g., *"designed an asynchronous event processing worker using Redis queues"* $\rightarrow$ `Redis`, `Asynchronous Architecture`).

### 3.4 Taxonomy Normalization & Alias Mapping
- Normalized aliases map terms to canonical entities (e.g., *"Amazon Web Services"* $\rightarrow$ `AWS`).
- Ambiguous or novel skills generate dense vector embeddings that query `skills.embedding` in PostgreSQL using `pgvector`.
- Matches with cosine similarity $\ge 0.88$ map to existing taxonomy entries; remaining entries are stored for taxonomy review.

---

## 4. Claimed Skill Scoring & Confidence

Extracted skills receive an initial confidence score based on context:

| Context of Mention | Confidence Weight | Explanation |
| :--- | :---: | :--- |
| **Project Implementation** | $0.90$ | Skill explicitly tied to a concrete project with technical deliverables. |
| **Work Experience / Role** | $0.85$ | Skill listed in professional or internship responsibilities. |
| **Dedicated Skills Block** | $0.60$ | Skill listed only in a standalone keyword list. |
| **Certification / Course** | $0.70$ | Skill associated with an accredited course or certification. |

---

## 5. Output Schema

```json
{
  "resume_id": "c71a3994-e815-4fa8-bcf6-7d1bb39da81e",
  "candidate_name": "Jane Doe",
  "github_handle_detected": "janedoe",
  "sections_detected": ["skills", "experience", "projects", "education"],
  "claimed_skills": [
    {
      "canonical_skill": "Python",
      "canonical_slug": "python",
      "category": "Programming Languages",
      "confidence": 0.95,
      "context_source": "projects",
      "snippet": "Developed REST API backend using Python and FastAPI for order tracking."
    },
    {
      "canonical_skill": "FastAPI",
      "canonical_slug": "fastapi",
      "category": "Backend Frameworks",
      "confidence": 0.90,
      "context_source": "projects",
      "snippet": "Engineered asynchronous endpoints with FastAPI and SQLAlchemy."
    },
    {
      "canonical_skill": "Docker",
      "canonical_slug": "docker",
      "category": "DevOps & Cloud",
      "confidence": 0.60,
      "context_source": "skills_block",
      "snippet": "Tools: Git, Docker, VS Code, Postman"
    }
  ]
}
```
