# SkillForge AI — Resume Analysis Engine

## 1. Purpose & Core Principles

The Resume Analysis Engine serves as the candidate evidence extraction gateway in SkillForge AI. It ingests candidate resumes, validates their structural integrity, segments them into standard sections, extracts technical skill mentions, and normalizes them against the platform's canonical skill taxonomy.

### Core Principles

1. **Claimed vs. Demonstrated Evidence**:
   Skills extracted from a resume are classified strictly as **Claimed Skills** (`evidence_tier = "CLAIMED"`). They represent self-reported candidate assertions and do **not** constitute verified technical proficiency. Verified competency is established separately through empirical GitHub repository inspection (**Demonstrated Skills**).
   ```text
   Resume Upload
         ↓
   CLAIMED SKILLS

   GitHub Repositories
         ↓
   DEMONSTRATED SKILLS

   CLAIMED + DEMONSTRATED + MARKET DEMAND
                   ↓
           DETERMINISTIC GAP
   ```
2. **Deterministic Processing**: The v1.0.0 MVP extraction and normalization pipeline is 100% deterministic, relying on structured document parsing, regex section segmentation, and dictionary/alias cache lookups. No generative AI or non-deterministic models participate in the extraction or scoring of candidate skills.
3. **Canonical Normalization**: Raw skill strings are mapped directly to canonical skills in the database (`skills` table) via exact and normalized name/alias matching, preventing vocabulary fragmentation.
4. **Strict Document Validation**: The engine enforces a multi-layer validation gate that distinguishes between valid binary file containers and genuine resume documents, rejecting irrelevant or non-resume files before processing.

---

## 2. v1.0.0 MVP — Implemented Resume Intelligence

The frozen v1.0.0 MVP implements an end-to-end deterministic resume ingestion and skill-extraction pipeline.

### Implemented Processing Flow
```text
Uploaded Resume File (PDF / DOCX)
        ↓
File & Container Validation
(Extension, MIME, Max Size, Magic Bytes, DOCX Zip Structure)
        ↓
Binary Storage & UUID Assignment
(Saved to UPLOAD_DIR with UUID filename)
        ↓
Text Extraction & Unicode Normalization
(pypdf for PDF, python-docx for DOCX paragraphs & tables)
        ↓
Resume Semantic Validation Gate
(Word/character count thresholds, canonical section & profile keyword detection)
        ↓
Structural Section Segmentation & Profile Extraction
(Header, Summary, Skills, Experience, Projects, Education, Contact Info)
        ↓
Skill Mention Extraction
(Delimiter splitting, token edge cleaning, false positive filtering)
        ↓
Canonical Skill Normalization
(SkillTaxonomyCache resolution: canonical_exact, alias_exact, normalized, text_mention)
        ↓
Claimed Skill Evidence Persistence
(PostgreSQL: resumes and user_claimed_skills tables)
```

Authoritative career intelligence is computed entirely by this deterministic engine. No large language model or active RAG pipeline participates in this flow.

---

## 3. Resume Ingestion & Validation

The upload endpoint (`POST /api/v1/resumes/upload`) implements strict security, format, and content validation gates before any text parsing occurs.

### Ingestion Constraints & Checks

| Validation Layer | Implemented Rule | Error Code / Behavior |
| :--- | :--- | :--- |
| **Allowed File Extensions** | Only `.pdf` and `.docx` are permitted. | `400 Bad Request` |
| **MIME Type Validation** | Validated against `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `application/msword`, and `application/octet-stream`. | `400 Bad Request` |
| **File Size Limit** | Enforced via `settings.MAX_UPLOAD_SIZE_BYTES` (streamed in 64 KB chunks). | `413 Request Entity Too Large` |
| **Empty File Detection** | Rejects 0-byte uploads. | `400 Bad Request` |
| **Magic Byte Inspection** | PDF must start with `%PDF-` (`0x25 0x50 0x44 0x46 0x2D`).<br>DOCX must start with PK zip signature `0x50 0x4B 0x03 0x04`. | `400 Bad Request` |
| **DOCX Package Structure** | Unpacks zip container in-memory to confirm presence of `[Content_Types].xml` or `word/` directory. | `400 Bad Request` |
| **Safe Storage & UUID** | File is assigned a `UUIDv4` identifier and saved as `<UUID>.<ext>` within `UPLOAD_DIR`. Directory traversal is prevented via resolved path checks. | `400 Bad Request` on path escape |
| **Upload Rollback** | If post-upload extraction or semantic validation fails, the written file is immediately unlinked (`unlink()`) from disk. | Zero orphaned files |

> [!IMPORTANT]
> The MVP does **not** implement Optical Character Recognition (OCR). Scanned image-only PDFs lacking an embedded text layer are explicitly rejected at the validation gate.

---

## 4. Text Extraction & Resume Parsing

Once the physical container is verified, text extraction is routed by file extension:

### 4.1 PDF Extraction (`pypdf`)
- Extracted using `pypdf.PdfReader`.
- Iterates across all pages, extracting raw text streams and joining pages with double line breaks (`\n\n`).
- Scanned or rasterized pages yield empty strings and are trapped by subsequent text validation.

### 4.2 DOCX Extraction (`python-docx`)
- Extracted using `docx.Document`.
- Ingests both narrative paragraphs (`doc.paragraphs`) and structured table layouts (`doc.tables`).
- Table rows are concatenated with vertical pipe separators (` | `), ensuring skills listed in multi-column tables remain parseable.

### 4.3 Text Normalization (`clean_extracted_text`)
Extracted text passes through deterministic normalization:
- Null bytes (`\x00`) are stripped.
- Common Unicode punctuation is converted to standard ASCII equivalents (e.g., curly quotes `\u2018`/`\u2019` $\rightarrow$ `'`, `\u201c`/`\u201d` $\rightarrow$ `"`, dashes `\u2013`/`\u2014` $\rightarrow$ `-`, non-breaking space `\u00a0` $\rightarrow$ ` `).
- Carriage returns (`\r\n`, `\r`) are normalized to standard line breaks (`\n`).
- Non-printable control characters are stripped while preserving tabs and standard newlines.
- Excess consecutive newlines (3+) are collapsed to 2.

### 4.4 Structural Section Segmentation (`parse_resume_sections`)
The cleaned text is segmented into logical blocks by evaluating lines against compiled regex patterns (`SECTION_HEADER_PATTERNS`):
- `skills`: Technical, core, key, or professional skills, proficiencies, competencies.
- `experience`: Work experience, professional history, employment, internships.
- `projects`: Technical, key, academic, or personal engineering projects.
- `education`: Academic background, degrees, qualifications, coursework.
- `summary`: Professional summary, career objective, profile, about me.
- `header`: Candidate identification and contact block preceding the first recognized heading.
- `other`: Residual content not assigned to a canonical section.

### 4.5 Resume Semantic Validation Gate (`validate_resume_document`)
Technical container validity is distinct from resume validity. A syntactically valid PDF containing an academic paper, recipe, or terms of service is rejected:

```text
Extracted Text Stream
        ↓
Extractable Text Check
(Must not be empty; scanned / image-only PDFs rejected)
        ↓
Volume Threshold Check
(Word count ≥ 4, Character count ≥ 20)
        ↓
Semantic Resume Signal Evaluation
        ├── Check 1: Contains ≥ 1 recognized canonical section
        │            (skills, experience, projects, education, summary)
        │                       OR
        └── Check 2: Contains contact info (email, phone, github, linkedin)
                     AND candidate profile keywords (e.g. curriculum vitae,
                     degree, b.tech, university, engineer, developer)
        ↓
Decision Gate
├── PASS: Proceed to skill extraction & persistence
└── FAIL: HTTP 422 Unprocessable Entity & Disk File Cleanup
```

**Validation Failure Responses (HTTP 422)**:
- **No Extractable Text**: `"Uploaded document contains no extractable text. Scanned or image-only documents are not supported."`
- **Insufficient Text**: `"Uploaded document contains insufficient text to be processed as a resume."`
- **Missing Resume Signals**: `"The uploaded document does not appear to be a resume. No recognized resume sections or candidate profile details were detected."`

---

## 5. Skill Extraction & Canonical Normalization

Skill extraction occurs without an LLM through a two-stage deterministic scanner followed by canonical taxonomy resolution.

### 5.1 Skill Mention Extraction (`skill_extractor.py`)
- **Dedicated Skills Section**: Splits content on standard delimiters (`,`, `|`, `\n`, `•`, `·`, `;`, `\t`, `/`). Strips category prefixes (e.g., `"Languages: Python, Go"` $\rightarrow$ `"Python"`, `"Go"`).
- **Secondary Sections (Projects & Experience)**: Scans for tool lists enclosed in parentheses or bullet labels (e.g., `"Implemented backend using (FastAPI, PostgreSQL)"`).
- **Token Edge Cleaning**: Strips markdown formatting (`*`, `#`, `-`), bullets, quotes, and brackets.
- **False-Positive Filtering**: Discards generic non-skill words (`team`, `project`, `experience`, `developer`, `leadership`, `management`, `using`, etc.) unless explicitly mapped in canonical taxonomy aliases.

### 5.2 Canonical Normalization (`skill_normalizer.py`)
Extracted tokens are matched against the in-memory `SkillTaxonomyCache` loaded from the `skills` and `skill_aliases` database tables:

```text
Raw Candidate Token
        ↓
1. Exact Canonical Match (case-insensitive name match)
   → Confidence: 0.95 (match_type: "canonical_exact")
        ↓
2. Exact Alias Match (case-insensitive alias match)
   → Confidence: 0.90 (match_type: "alias_exact")
        ↓
3. Normalized Canonical Match (alphanumeric key match, e.g. "ReactJS" → "reactjs")
   → Confidence: 0.88 (match_type: "canonical_normalized")
        ↓
4. Normalized Alias Match (alphanumeric key match, e.g. "react.js" → "reactjs")
   → Confidence: 0.85 (match_type: "alias_normalized")
        ↓
5. Full-Text Boundary Scan (regex \b{skill.name}\b for skills > 2 chars)
   → Confidence: 0.80 (match_type: "text_mention")
```

### Confidence Semantics
> [!NOTE]
> The confidence score ($0.80$ to $0.95$) reflects **taxonomy normalization certainty** (the match quality between raw text and canonical skill identity). It does **not** represent candidate proficiency or skill mastery.

Deduplication ensures that if a skill is identified multiple times across sections or match tiers, only the single entry with the highest confidence score is retained.

---

## 6. Claimed Skill Evidence

Normalized matches are transformed into persisted candidate evidence:

- **Entity Model**: Each identified skill is persisted in the `user_claimed_skills` table.
- **Traceability**: Each record links the canonical skill ID (`skill_id`), owning candidate (`user_id`), origin resume (`resume_id`), source tag (`source = "resume"`), the original extracted string (`raw_mention`), and the resolution confidence (`confidence_score`).
- **Idempotency & Re-parsing**:
  - If a skill is already claimed by the user for that resume, the existing record is updated if the new parse yields a higher confidence score.
  - When re-parsing an existing resume, claimed skill records no longer present in the updated document text are automatically pruned.
- **Parsed Data Synchronization**: A lightweight summary list is serialized directly into `resume.parsed_data["claimed_skills"]` and `resume.parsed_data["claimed_skills_count"]` for fast retrieval without table joins.

---

## 7. Candidate/Profile Extraction

During text segmentation, candidate contact identifiers and document structural metadata are extracted and stored within `resume.parsed_data`:

### Contact Details (`extract_contact_info`)
- **Email**: Extracted via RFC-compliant email regex (`EMAIL_REGEX`).
- **Phone**: Extracted via domestic and international phone pattern matching (`PHONE_REGEX`).
- **GitHub Handle**: Extracted from GitHub profile URLs (`github.com/([A-Za-z0-9_-]+)`).
- **LinkedIn URL**: Extracted from LinkedIn profile URLs (`linkedin.com/in/([A-Za-z0-9_%-]+)`).

### Document Metadata
- Character count (`char_count`), word count (`word_count`), line count (`line_count`).
- Detected section roster (`detected_sections`).
- Original filename and upload MIME type.

Candidate name and employment dates are preserved in the segmented section texts (`sections["header"]`, `sections["experience"]`) but are not parsed into granular relational entities in the MVP.

---

## 8. Resume Ownership & Isolation

To maintain candidate privacy and evidence integrity:

1. **Candidate Scoping**: Every resume record maintains an optional foreign key `user_id` referencing `users.id` with `ON DELETE CASCADE`.
2. **Deterministic Evidence Isolation**:
   - Skill gap calculations (`POST /api/v1/gaps/calculate`) and claimed skill queries (`GET /api/v1/skills/claimed`) accept an explicit `resume_id` parameter.
   - When `resume_id` is supplied, candidate evidence is strictly scoped to that single resume, preventing claims from older historical resumes or separate candidates from leaking into the analysis.
   - When omitted, deterministic fallback selects the latest uploaded resume for the candidate.
3. **Safe Deletion Cascade**: Deleting a resume via `DELETE /api/v1/resumes/{resume_id}` removes the physical binary file from disk (`unlink()`), deletes the `resumes` record, and automatically deletes all associated `user_claimed_skills` records via SQLAlchemy cascade.

---

## 9. MVP Output / Persistence

The engine stores all output in PostgreSQL using two primary models:

### `resumes` Table
- `id` (UUIDv4 primary key)
- `user_id` (UUID nullable foreign key)
- `file_name` (Sanitized original filename)
- `file_type` (`"pdf"` or `"docx"`)
- `file_size` (Byte count)
- `storage_path` (Absolute disk path)
- `raw_text` (Normalized full text)
- `parsed_data` (JSONB container holding sections, contact info, and claimed skills summary)
- `created_at` (Timestamp)

### `user_claimed_skills` Table
- `id` (UUIDv4 primary key)
- `user_id` (UUID nullable foreign key)
- `skill_id` (UUID foreign key to `skills.id`)
- `resume_id` (UUID foreign key to `resumes.id`)
- `source` (`"resume"`)
- `raw_mention` (Original text token)
- `confidence_score` (Float between 0.80 and 0.95)
- `created_at` (Timestamp)

*(For exhaustive schema definitions and constraints, refer to [DATA_MODEL.md](file:///Users/niteshyadav/SIH/docs/data/DATA_MODEL.md)).*

---

## 10. Post-MVP Planned Evolution

The following capabilities are **PLANNED** for post-MVP phases on the `post-mvp-foundation` branch:

1. **LLM Contextual Extraction (P2)**: Using local open-weight Qwen 3 8B to extract implicit technologies mentioned in narrative project bullets where keywords do not match canonical aliases.
2. **pgvector Semantic Normalization**: Generating dense embeddings for unrecognized candidate tokens and querying `skills.embedding` using cosine similarity ($\ge 0.88$) to resolve novel technical terms.
3. **Deep Profile & NER Extraction**: Structured entity recognition for candidate names, university degrees, GPAs, and employment date ranges.
4. **Contextual Evidence Weighting**: Distinguishing whether a skill was used as a primary architectural framework versus a peripheral library based on narrative depth.
5. **Scanned PDF Ingestion**: OCR pipeline for extracting text from scanned image-only PDF documents.
6. **Multilingual Resume Parsing**: Ingestion and normalization of resumes written in non-English languages.

---

## 11. AI Boundary

To prevent hallucinations and preserve system integrity, the platform enforces these architectural boundaries:

> **"The Resume Analysis Engine extracts and structures candidate-provided evidence. It does not determine authoritative skill proficiency."**

> **"The deterministic intelligence layer combines candidate evidence with market demand to determine skill gaps and priorities."**

> **"The future AI layer may explain and personalize verified results, but must not silently override the authoritative evidence or deterministic intelligence."**

### Architectural Rules
- Resume claims indicate that a candidate **asserts** familiarity with a technology; only GitHub code artifacts establish **demonstrated** capability.
- The resume engine does not assign skill gap classifications (`STRONG`, `PARTIAL`, `MISSING`) or calculate priority scores. Those classifications are computed solely by the deterministic skill gap engine.
- Generative AI models must treat `user_claimed_skills` as read-only grounding context and are strictly prohibited from creating or modifying claimed skill records.

---

## 12. MVP vs Post-MVP Capability Matrix

| Capability | v1.0.0 MVP (Frozen Baseline) | Post-MVP (Planned Evolution) |
| :--- | :--- | :--- |
| **PDF Upload & Ingestion** | Implemented (`pypdf` text stream extraction) | Extend (Layout preservation) |
| **DOCX Upload & Ingestion** | Implemented (`python-docx` paragraphs & tables) | Extend (Header/footer extraction) |
| **File Security Validation** | Implemented (Magic bytes, MIME, size, zip packaging) | Extend (Virus scanning) |
| **Semantic Document Gate** | Implemented (Heuristic section, contact, keyword gate) | Improve (ML document classification) |
| **Scanned Document OCR** | Not implemented (Rejected with HTTP 422) | Planned (Tesseract / local vision OCR) |
| **Section Segmentation** | Implemented (Regex heading detection) | Improve (Layout-aware segmentation) |
| **Skill Mention Extraction** | Implemented (Delimiter splitting, token cleaning) | Extend (LLM contextual extraction) (P2) |
| **Taxonomy Normalization** | Implemented (`SkillTaxonomyCache` 5 tiers) | Planned (pgvector semantic embeddings) |
| **Claimed Skill Persistence**| Implemented (`user_claimed_skills` table) | Extend (Contextual weight scoring) |
| **Contact Info Extraction** | Implemented (Regex for email, phone, GitHub, LinkedIn)| Extend (Granular name/location NER) |
| **Evidence Scoping & Isolation**| Implemented (`resume_id` scoping & cascade delete) | Extend (Multi-resume delta tracking) |
