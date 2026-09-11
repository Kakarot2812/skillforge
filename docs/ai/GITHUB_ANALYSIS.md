# SkillForge AI — GitHub Intelligence Engine

## 1. Purpose & Core Principles

The GitHub Intelligence Engine provides empirical, verifiable evidence of candidate engineering activity. Rather than taking resume assertions at face value or relying on superficial vanity metrics (such as star counts, follower numbers, or commit streaks), the engine inspects concrete repository artifacts to verify practical technical adoption.

### Core Principles

1. **Claimed vs. Demonstrated Evidence**:
   Resume data represents self-reported candidate assertions (**Claimed Skills**). GitHub repository inspection produces observable, auditable artifacts (**Demonstrated Skills**).
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
2. **Usage, Not Mastery**:
   > **"GitHub evidence demonstrates observable technical usage in repository artifacts; it does not establish complete proficiency or mastery."**
3. **Read-Only Inspection**:
   The engine interacts with the GitHub REST API strictly in a read-only capacity. Repository source code is never executed, built, or modified.
4. **Deterministic Analysis**:
   The v1.0.0 MVP analysis pipeline is 100% deterministic. Evidence discovery, canonical taxonomy matching, and multi-repository confidence scoring are computed by mathematical rules without generative AI or non-deterministic inference.

---

## 2. v1.0.0 MVP — Implemented GitHub Intelligence

The frozen v1.0.0 MVP implements an automated, read-only repository inspection and demonstrated skill aggregation engine.

### Implemented Processing Pipeline
```text
Candidate GitHub Account (@username)
        ↓
Account Verification & Discovery
(GitHub REST API GET /users/{username}/repos)
        ↓
Ownership & Eligibility Filtering
(Exclude forks, verify account ownership, handle empty repos)
        ↓
Repository Metadata Persistence
(PostgreSQL: github_repositories table)
        ↓
Repository Tree Inspection
(GitHub Git Tree API recursive scan, max 1,000 entries)
        ↓
Artifact Content Retrieval & Parsing
(Max 15 key manifests: requirements.txt, pyproject.toml, package.json,
 pom.xml, go.mod, Dockerfile, compose.yml, .github/workflows/*.yml)
        ↓
Canonical Skill Normalization
(Match against skills table & skill_aliases via normalized keys)
        ↓
Auditable Project Evidence Persistence
(PostgreSQL: project_evidence table)
        ↓
Multi-Repository Confidence Aggregation
(Bounded Noisy-OR formula across owned repositories)
        ↓
Demonstrated Skill Materialization
(PostgreSQL: demonstrated_skills table)
        ↓
Deterministic Skill Gap Engine Input
```

Authoritative demonstrated skills and evidence levels are produced entirely by this deterministic pipeline.

---

## 3. GitHub Connection & Repository Discovery

Candidates connect their GitHub accounts via `POST /api/v1/github/connect`.

### Connection & Discovery Protocol
- **Username Validation**: Sanitized using strict regex (`^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$`) to guard against path traversal and SSRF attacks.
- **Account Verification**: Calls `GET /users/{username}` on the GitHub API to confirm account existence before initiating repository queries.
- **Paginated Discovery**: Queries `GET /users/{username}/repos` with `type="owner"`, `sort="updated"`, and `per_page=100`, paginating up to 5 pages (maximum 500 candidate repositories).
- **Rate-Limit Handling**: Detects HTTP 403 / 429 rate-limit responses from GitHub and returns an HTTP 429 with an informative message.
- **Volatile Credential Handling**:
  - Candidates may optionally supply a Personal Access Token (`access_token`) to increase GitHub API rate limits.
  - Personal access tokens are strictly **request-scoped and volatile**. They are used only in the `Authorization: Bearer <token>` header during the immediate API call and are **never** stored in the database, logged to disk, or returned in API responses.
  - Public repositories are fully accessible without requiring authentication or OAuth authorization.

---

## 4. Repository Ownership & Isolation

To prevent cross-candidate evidence pollution and accidental namespace collisions, the platform enforces strict repository ownership verification.

### Ownership Verification Helper (`is_repo_owned_by_user`)
A repository summary entry is accepted as belonging to a candidate only if it satisfies case-insensitive verification across any of four structural attributes:
1. **Repository URL (`repo_url`)**: Matches `github.com/{username}/`, `github.com:{username}/`, or ends with `/{username}`.
2. **Full Repository Name (`full_name`)**: Starts with `{username}/` or contains `/{username}/`.
3. **Explicit Owner Attribute (`owner`)**: Matches the candidate's sanitized username.
4. **Owner-Prefixed Name (`repo_name`)**: Matches `{username}/...`.

```text
Candidate Account: "Kakarot2812"

Matching Examples:
  ✓ https://github.com/Kakarot2812/skillforge  (repo_url match)
  ✓ Kakarot2812/ecommerce-api                 (full_name match)

Rejected Non-Matching Examples:
  ✗ https://github.com/Kakarot2812-other/repo  (substring collision prevented)
  ✗ octocat/skillforge                        (unowned repository)
  ✗ "skillforge" without owner context        (unqualified name rejected)
```

Evidence aggregation and gap calculations strictly query repositories matching the candidate's ownership scope, guaranteeing that code artifacts from one candidate never leak into another candidate's evaluation.

---

## 5. Repository Eligibility

Before tree traversal and artifact extraction, repositories undergo eligibility filtering:

1. **Fork Exclusion**:
   - Repositories marked as forks (`repo.is_fork == True`) are filtered out during discovery (`filter_and_normalize`) and excluded by default from analysis.
   - This ensures demonstrated evidence reflects original engineering work rather than upstream contributions.
2. **Empty Repository Handling**:
   - The GitHub Git Tree API returns an HTTP 409 Conflict status for empty repositories (repositories with no commits or default branch).
   - The analyzer traps HTTP 409 and safely returns an empty tree, preventing crashes or failed batch syncs.
3. **Read-Only Scope Safeguards**:
   - File paths are validated with `is_safe_repo_path` to reject path traversal (`..`), null bytes (`\0`), and absolute path escapes before issuing content requests.

*(Note: Automated clone/template detection is not implemented in the v1.0.0 MVP and is planned for post-MVP evolution).*

---

## 6. Repository Artifact Analysis

The analyzer inspects project trees via `GET /repos/{full_name}/git/trees/{branch}?recursive=1` and selectively retrieves target files without cloning repository source code.

### Inspection Limits & Safeguards
- **Tree Scan Limit**: Evaluates up to `MAX_TREE_ENTRIES = 1,000` entries per repository.
- **File Size Limit**: Individual file content downloads are capped at `MAX_FILE_SIZE_BYTES = 512 KB`.
- **Manifest Retrieval Cap**: Limits inspection to a maximum of 15 key manifests per repository to avoid exhausting API rate limits.

### Implemented Artifact Detectors

| Category | Target File / Pattern | Extraction Logic | Base Confidence |
| :--- | :--- | :--- | :---: |
| **Python Dependencies** | `requirements.txt`<br>`requirements-*.txt` | Strips version specifiers and environment markers; extracts package names. | $0.95$ |
| **Python Project Config** | `pyproject.toml` | Parses PEP 621 `project.dependencies` and Poetry `tool.poetry.dependencies` via `tomllib`. | $0.95$ |
| **JavaScript / TypeScript** | `package.json` | Parses JSON dependencies across `dependencies`, `devDependencies`, and `peerDependencies`. | $0.95$ |
| **Java / Maven** | `pom.xml` | Strips XML namespaces and extracts `<dependency><artifactId>` tags using `xml.etree.ElementTree`. | $0.95$ |
| **Go Modules** | `go.mod` | Parses `require` directives and module paths for package identities. | $0.95$ |
| **Docker Containerization** | `Dockerfile`<br>`*.dockerfile` | Confirms valid containerization by verifying presence of `FROM` instructions. | $0.90$ |
| **Docker Compose** | `docker-compose.yml`<br>`compose.yml` | Parses service definitions via regex to identify configured container images. | $0.88$ |
| **CI/CD Workflows** | `.github/workflows/*.yml`<br>`.github/workflows/*.yaml` | Verifies automated GitHub Actions pipeline configuration and triggers. | $0.85$ |
| **Primary Language** | Repository GitHub metadata | Uses GitHub's detected primary language as repository-level structural baseline evidence. | $0.70$ |

---

## 7. Demonstrated Skill Evidence

When an artifact detector extracts a candidate token, the token is resolved against the canonical taxonomy before being persisted:

### Normalization & Filtering
- Candidate tokens are normalized using alphanumeric stripping (`normalize_string_key`).
- Matches are evaluated against canonical skill names, canonical slugs, and registered skill aliases (`skill_aliases`).
- Discovered packages or utilities that do not map to an entry in the canonical skill taxonomy are safely discarded.

### Evidence Record Model (`project_evidence`)
Normalized matches are persisted idempotently in the `project_evidence` table with direct provenance:
- `id` (UUIDv4)
- `user_id` (Candidate UUID, nullable)
- `repo_id` (ForeignKey to `github_repositories.id`)
- `skill_id` (ForeignKey to `skills.id`)
- `evidence_type` (`"dependency"`, `"dockerfile"`, `"ci_workflow"`, `"repository_structure"`)
- `file_path` (Relative file path within repository, e.g. `backend/requirements.txt`)
- `artifact_name` (Target artifact, e.g. `requirements.txt`, `Dockerfile`)
- `matched_content` (Snippet of matched line or instruction)
- `confidence_score` (Deterministic artifact weight: $0.70$ to $0.95$)
- `detected_at` (Timestamp)

Stale evidence records for a repository that are no longer detected upon re-analysis are automatically pruned during database reconciliation.

---

## 8. Confidence & Aggregation

SkillForge AI does not use subjective weights or speculative linear formulas. Demonstrated skill confidence is aggregated through a deterministic two-tier model:

### Tier 1: Single-Repository Evidence Maximum
Within an individual repository, a skill may appear across multiple manifests (e.g. `package.json`, `Dockerfile`, and a workflow). To prevent redundant scans or multiple manifest mentions in the same repository from artificially inflating confidence, the repository score is the **maximum** confidence among its evidence items:

$$\text{repo\_score}(r, s) = \max_{e \in \text{evidence}(r, s)} (\text{confidence}(e))$$

### Tier 2: Multi-Repository Bounded Noisy-OR Aggregation
When a candidate demonstrates a skill across multiple independent repositories ($r_1, r_2, \dots, r_n$), the platform aggregates the independent evidence using a **bounded noisy-OR** formula:

$$S(s) = 1 - \prod_{i=1}^{n} \bigl(1 - \text{repo\_score}(r_i, s)\bigr)$$

The result is clamped to $[0.0, 1.0]$ and rounded to two decimal places.

### Why Noisy-OR?
- **Diminishing Returns**: Two independent repositories demonstrating Docker ($0.90$ each) produce:
  $$1 - (1 - 0.90)(1 - 0.90) = 1 - (0.10 \times 0.10) = 0.99$$
- **Prevents Linear Runaway**: Adding repositories asymptotically approaches $1.0$ without exceeding bounds.
- **Cross-Repo Reinforcement**: Demonstrating a skill across multiple separate projects provides stronger statistical proof of capability than demonstrating it in a single project.

### Evidence Level Tiers

| Evidence Level | Aggregated Confidence Score | Interpretation |
| :--- | :---: | :--- |
| **HIGH** | $\ge 0.85$ | Robust, multi-repo or high-confidence primary evidence. Satisfies the GitHub demonstration requirement for `STRONG` skill gap status. |
| **MEDIUM** | $0.70 \le \text{score} < 0.85$ | Observable baseline evidence (e.g. single structural language match). Satisfies partial evidence requirements. |
| **LOW** | $< 0.70$ | Marginal or low-confidence evidence. |

> [!IMPORTANT]
> Demonstrated-skill confidence reflects **empirical evidence strength**, not candidate mastery or engineering seniority.

---

## 9. Evidence Persistence & Audit

Demonstrated skills are materialized in the `demonstrated_skills` table and link directly to the underlying `project_evidence` rows.

### Evidence Audit Trail Integration
Every demonstrated skill can be audited via `GET /api/v1/gaps/{role_id}/evidence/{skill_id}`:
- **Repository Provenance**: Repository name, full name (`owner/repo`), and clickable GitHub URL.
- **Artifact Provenance**: Specific file path, artifact type, and matched code/manifest content.
- **Temporal Verification**: Precise timestamp when the artifact was verified (`detected_at` / `last_verified_at`).

### Conceptual Audit Representation

```json
{
  "skill_name": "FastAPI",
  "confidence_score": 0.95,
  "evidence_level": "HIGH",
  "evidence_count": 2,
  "repository_count": 2,
  "artifacts": [
    {
      "repo_name": "skillforge",
      "file_path": "backend/requirements.txt",
      "artifact_name": "requirements.txt",
      "evidence_type": "dependency",
      "matched_content": "fastapi>=0.110.0",
      "confidence_score": 0.95
    },
    {
      "repo_name": "microservices-demo",
      "file_path": "services/auth/pyproject.toml",
      "artifact_name": "pyproject.toml",
      "evidence_type": "dependency",
      "matched_content": "fastapi = \"^0.110.0\"",
      "confidence_score": 0.95
    }
  ]
}
```
*(Conceptual example illustrating audit linkages — not a rigid API contract).*

### Role in the Deterministic Skill Gap Engine
The GitHub Intelligence Engine supplies evidence; it does **not** determine skill gap statuses or priorities:
- **`STRONG`**: Candidate possesses verified GitHub code artifacts at `HIGH` confidence ($\ge 0.85$).
- **`PARTIAL`**: Candidate claimed the skill on their resume or possesses GitHub evidence below the strong threshold ($< 0.85$).
- **`MISSING`**: Candidate possesses neither a resume claim nor verified GitHub evidence.

Final gap classifications and priority rankings are computed solely by the deterministic skill gap engine.

---

## 10. Post-MVP Planned Evolution

The following capabilities are **PLANNED** for post-MVP phases on the `post-mvp-foundation` branch:

1. **Deeper Source Code & AST Analysis (P2 / P5)**: Inspecting function calls, library imports, and architectural patterns within `.py`, `.ts`, and `.go` source files rather than manifests alone.
2. **Continuous GitHub Verification Loop (P5)**: Re-analyzing connected repositories as candidates complete learning milestones to automatically verify gap closure.
3. **Broader Ecosystem Manifests**: Ingesting Rust (`Cargo.toml`), C# (`*.csproj`), Gradle (`build.gradle`), and Swift Package Manager manifests.
4. **Semantic Repository Matching**: Using pgvector embeddings to match repository descriptions and README content to canonical skills.
5. **Cloned Boilerplate & Template Detection**: Comparing repository commit graphs or AST structures against known boilerplate repositories to detect cloned template code.
6. **Temporal & Recency Analysis**: Factoring commit recency and author contributions into confidence weighting.
7. **Private Repository Support**: Optional GitHub App integration for authorized private repository analysis with complete candidate privacy preservation.

---

## 11. AI Boundary & Invariants

To prevent hallucination and maintain authoritative data integrity, the platform enforces these strict invariants:

> **"The MVP GitHub Intelligence Engine is deterministic and evidence-driven."**

> **"The future AI layer may explain repository evidence, but it must not fabricate repository artifacts or override authoritative evidence."**

> **"The LLM must not independently declare a skill demonstrated without corresponding SkillForge evidence."**

> **"Demonstrated evidence is not equivalent to mastery."**

### Architectural Invariants
- The LLM is technically prohibited from writing to `github_repositories`, `project_evidence`, or `demonstrated_skills`.
- If an explanation refers to repository evidence, all cited file paths, lines, and repository names must originate from verified database records.
- If no repository evidence exists for a skill, the AI layer must explicitly report that no code demonstration was found.

---

## 12. MVP vs Post-MVP Capability Matrix

| Capability | v1.0.0 MVP (Frozen Baseline) | Post-MVP (Planned Evolution) |
| :--- | :--- | :--- |
| **GitHub Account Discovery** | Implemented (Public REST API, paginated) | Extend (GitHub App / Webhooks) |
| **Repository Ownership Validation** | Implemented (`is_repo_owned_by_user` 4-tier check)| Extend (Multi-account linking) |
| **Fork Exclusion** | Implemented (`is_fork == False` filtering) | Extend (Selective fork contribution parsing) |
| **Empty Repository Handling** | Implemented (Traps HTTP 409 Conflict) | Maintain |
| **Read-Only Artifact Inspection**| Implemented (Git Trees & Contents API) | Extend (AST source code inspection) |
| **Dependency Manifest Ingestion** | Implemented (Python, JS/TS, Java/Maven, Go) | Extend (Rust, C#, Gradle, Swift) |
| **Container & CI Artifacts** | Implemented (Dockerfile, Compose, GitHub Actions) | Extend (GitLab CI, CircleCI, K8s manifests) |
| **Canonical Normalization** | Implemented (Deterministic taxonomy & alias cache)| Planned (pgvector semantic embeddings) |
| **Multi-Repo Score Aggregation** | Implemented (Bounded Noisy-OR formula) | Extend (Author contribution weighting) |
| **Evidence Level Tiers** | Implemented (HIGH $\ge 0.85$, MEDIUM, LOW) | Maintain |
| **Evidence Audit Trail** | Implemented (Direct repo, file, and snippet link) | Extend (Interactive code diff viewer) |
| **LLM Repository Analysis** | Not implemented | Planned (Local Qwen 3 8B reasoning) (P2) |
| **Milestone Verification Loop** | Not implemented | Planned (Continuous gap closure) (P5) |
