# SkillForge AI — User Flow & Journey

## 1. Overview

SkillForge AI guides students and early-career software engineers from their current skill profile to verifiable career readiness.

The platform continuously loops between three states:
1. **Assessment**: Evidence extraction from resumes and GitHub repositories.
2. **Targeting & Gap Analysis**: Alignment with data-driven industry demand for a selected role.
3. **Action & Verification**: Execution of a personalized roadmap followed by GitHub-based re-verification.

---

## 2. High-Level Flow Diagram

```text
┌─────────────────────────┐
│     1. User Entry       │
│  Landing / Auth / Role  │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│    2. Data Ingestion    │
│  Resume + GitHub Auth   │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   3. Skill Extraction   │
│ Claimed vs Demonstrated │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ 4. Demand & Gap Engine  │
│  Role Demand vs Profile │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  5. Dynamic Roadmap     │
│ Milestones + Resources  │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   6. Project Building   │
│ Practical Implementation│
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  7. GitHub Verification │
│ Re-scan & Evidence Lift │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  8. Re-evaluation Loop  │
│ Updated Skills & Status │
└─────────────────────────┘
```

---

## 3. Step-by-Step User Journey

### Step 1: Onboarding & Target Role Selection

1. The user lands on SkillForge AI and authenticates (or continues as guest during MVP evaluation).
2. The user selects a target career role (e.g., *Backend Engineer*, *Full Stack Engineer*, *AI/ML Engineer*, *Cloud/DevOps Engineer*).
3. The system displays current baseline industry signals for that role to provide immediate context.

### Step 2: Resume Ingestion & Claimed Skill Extraction

1. The user uploads a resume in PDF or DOCX format.
2. The backend parses document structure, extracting:
   - Technical skills mentioned
   - Project descriptions
   - Professional experience & internships
   - Educational background & certifications
3. The user reviews extracted skills in an interactive confirmation modal:
   - Skills are tagged as **Claimed Skills**.
   - User can confirm, dismiss false positives, or add unmentioned skills.

### Step 3: GitHub Connection & Repository Ingestion

1. The user connects their GitHub account via OAuth or public username.
2. The system fetches the user's public repositories.
3. The user selects which repositories represent original technical work (excluding forks or clones if desired).
4. The GitHub Intelligence service inspects:
   - Primary languages and byte counts
   - Dependency manifests (`package.json`, `requirements.txt`, `pom.xml`, `go.mod`, etc.)
   - DevOps assets (`Dockerfile`, CI/CD workflow YAML files)
   - Commit history and repository structure
5. Extracted skills are tagged as **Demonstrated Skills** with supporting evidence references.

### Step 4: Evidence Synthesis & Unified Profile

1. The system merges Claimed and Demonstrated data into an **Evidence Matrix**:
   - **Claimed + Demonstrated**: High confidence, verified practical skill.
   - **Claimed Only**: Stated on resume, but lacks public project evidence.
   - **Demonstrated Only**: Present in codebase, but omitted from resume.
2. An interactive dashboard displays:
   - Skill coverage radar chart
   - Evidence confidence breakdown per skill
   - Identified strengths and foundational gaps

### Step 5: Industry Demand & Gap Analysis

1. The system queries the Industry Demand Engine for the selected target role.
2. Real-time market demand metrics are applied:
   - Skill frequency (% of active job listings requiring the skill)
   - Demand trajectory (growing, stable, or declining)
   - Role criticality (core requirement vs. peripheral tool)
3. The Skill Gap Engine computes the prioritized gap:
   $$\text{Gap Priority} = f(\text{Market Demand}, \text{Trend}, \text{Evidence Deficit}, \text{Prerequisites})$$
4. The user sees a clear breakdown:
   - **Critical Gaps**: High market demand, zero demonstrated evidence.
   - **Growth Gaps**: Moderate demand, emerging industry trend.
   - **Verified Match**: Demonstrated skills meeting market requirements.

### Step 6: Personalized Roadmap Generation

1. The Roadmap Engine performs topological sorting over the skill dependency graph.
2. A phased, milestone-based learning plan is generated:
   - Respects prerequisites (e.g., Docker is scheduled before Kubernetes).
   - Skips skills already demonstrated with high confidence.
   - Adapts to user-selected weekly time availability (e.g., 5, 10, or 20 hours/week).
3. Each milestone includes:
   - Clear learning objectives
   - Curated high-yield documentation, tutorials, and courses
   - A practical project challenge designed to produce verifiable GitHub evidence

### Step 7: Project Implementation & Resource Consumption

1. The user accesses milestone resources via the dashboard.
2. The AI Career Assistant is available to answer conceptual questions, explain architectural patterns, and clarify project requirements.
3. The user builds the practical project locally and pushes code to their GitHub repository.

### Step 8: GitHub Verification Loop

1. The user clicks **Verify Milestone** and provides the target repository URL.
2. The GitHub Verification service scans the new commits:
   - Validates presence of target technologies in manifests.
   - Checks structural implementation criteria (e.g., valid Dockerfile, test suites, API routes).
3. If criteria are met:
   - The skill status upgrades from *Claimed/Missing* to *Demonstrated*.
   - Evidence confidence score updates in real time.
   - Milestone marks as **Verified**, unlocking subsequent roadmap phases.
4. If criteria are not met:
   - Constructive actionable feedback is provided identifying missing components.

---

## 4. Edge Cases & Handling

| Scenario | System Behavior |
| :--- | :--- |
| **No Resume Provided** | User enters GitHub handle directly; system infers claimed profile from READMEs and bio. |
| **No GitHub Provided** | System generates roadmap based on resume claims, marking all skills as unverified. |
| **Private Repositories** | User can provide read-only token or run a local verification script. |
| **Forked Repositories** | System filters out forks by default to prevent crediting third-party code. |
| **Niche / Custom Target Role** | Semantic fallback maps custom role to closest canonical industry role. |
| **Corrupted / Image-Only Resume** | System prompts for text-based PDF/DOCX or manual skill input. |

---

## 5. User States Lifecycle

```text
GUEST / NEW
    ↓ (Upload Resume & GitHub)
PROFILED
    ↓ (Select Target Role)
ANALYZED
    ↓ (Generate Learning Plan)
ROADMAP_ACTIVE
    ↓ (Submit Project for Verification)
VERIFYING
    ↓ (Criteria Passed)
ADVANCED / VERIFIED
```
