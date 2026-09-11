# SkillForge AI — Career Roadmap Engine

## 1. Purpose & Core Philosophy

The Roadmap Engine transforms prioritized skill gaps into an actionable, structured, and personalized learning trajectory.

### Core Principles

1. **Prerequisite-First Sequencing**: High-demand skills are never scheduled before their foundational prerequisites are satisfied.
2. **Zero Redundancy**: Skills already proven via verified GitHub evidence are omitted or condensed into accelerated review checkpoints.
3. **Paced for Reality**: Milestones adapt dynamically to the user's declared weekly availability ($5$, $10$, or $20\text{ hours/week}$).
4. **Action-Oriented Milestones**: Every milestone culminates in a practical project challenge designed for automated GitHub verification.

---

## 2. Skill Dependency Graph (DAG)

Technical proficiencies are modeled as a Directed Acyclic Graph (DAG) stored in the `skill_dependencies` table:

```text
            ┌───────────────┐
            │    Python     │
            └───────┬───────┘
                    │
            ┌───────▼───────┐
            │    FastAPI    │
            └───────┬───────┘
                    │
    ┌───────────────┼───────────────┐
    ▼                               ▼
┌───────────────┐           ┌───────────────┐
│  PostgreSQL   │           │    Docker     │
└───────┬───────┘           └───────┬───────┘
        │                           │
        └───────────────┬───────────┘
                        ▼
            ┌───────────────────────┐
            │ Kubernetes Orchestr.  │
            └───────────────────────┘
```

- **Nodes**: Canonical skills from `skills`.
- **Edges**: Directed prerequisite relationships (`skill_id` depends on `prerequisite_skill_id`).
- **Dependency Types**:
  - `Hard`: Mandatory prerequisite; downstream skill cannot be learned without it.
  - `Soft`: Recommended complementary skill; improves comprehension but does not strictly block sequencing.

---

## 3. Sequencing Algorithm

The sequencing engine uses a modified Topological Sort incorporating priority weighting:

```text
[Input: Prioritized Skill Gaps {S}]
               │
               ▼
[Filter Out Demonstrated Skills (Evidence >= 0.70)]
               │
               ▼
[Extract Subgraph of Required Skills & Missing Prerequisites]
               │
               ▼
[Topological Sort with Priority-Weighted In-Degree Resolution]
               │
               ▼
[Partition into Workload-Balanced Milestones]
               │
               ▼
[Attach Curated Resources & Project Challenges]
```

### In-Degree & Priority Resolution
When multiple candidate skills have zero unresolved prerequisites (in-degree $= 0$ in the active subgraph), the tie is broken by the **Priority Score** $P(s)$:

$$P(s) = \alpha \cdot \text{DemandScore}(s) + \beta \cdot \text{GrowthRate}(s) + \gamma \cdot \text{Deficit}(s)$$

This guarantees that among immediately learnable technologies, the highest-leverage industry skills appear earliest in the sequence.

---

## 4. Milestone Architecture

Milestones structure learning into sequential phases:

```text
┌─────────────────────────────────────────────────────────────┐
│ Milestone 1: Core API Engineering (Est. 2 Weeks @ 10h/week) │
├─────────────────────────────────────────────────────────────┤
│ Target Skills: FastAPI, Pydantic, REST Architecture          │
├─────────────────────────────────────────────────────────────┤
│ Curated Learning Resources:                                 │
│ • Official FastAPI Tutorial (Doc)                          │
│ • Building Resilient Microservices (Course Module)          │
├─────────────────────────────────────────────────────────────┤
│ Practical Project Challenge:                                │
│ "Build a multi-resource REST API with JWT authentication"   │
├─────────────────────────────────────────────────────────────┤
│ GitHub Verification Criteria:                               │
│ • requirements.txt contains 'fastapi' & 'pydantic'          │
│ • At least 4 API route endpoints defined                    │
│ • Automated test suite using pytest passing in repo         │
└─────────────────────────────────────────────────────────────┘
```

### Milestone Lifecycle

```text
NOT_STARTED ──► IN_PROGRESS ──► PROJECT_SUBMITTED ──► VERIFIED
                                         │ (Criteria missing)
                                         └──► REVISION_REQUESTED
```

---

## 5. Dynamic Re-planning & Feedback Loop

The roadmap is an adaptive plan rather than a static document:

1. **Milestone Verification**: When the user completes the project and pushes to GitHub, the verification service scans the commits.
2. **Evidence Elevation**: The validated skill moves to *Demonstrated* in the user's skill profile.
3. **Graph Recalculation**: Downstream dependent milestones are unlocked.
4. **Market Shift Updates**: If industry demand for a secondary skill surges significantly over time, subsequent unstarted milestones adjust their priority ordering automatically.

---

## 6. Data Representation

```json
{
  "roadmap_id": "8f3b145e-990a-4bf7-96a1-6a2c340dfa12",
  "target_role": "Backend Engineer",
  "total_estimated_weeks": 8,
  "weekly_hours_commitment": 10,
  "current_status": "ACTIVE",
  "milestones": [
    {
      "sequence_order": 1,
      "title": "Containerization & Development Environments",
      "target_skills": ["Docker", "Docker Compose"],
      "estimated_hours": 15,
      "status": "IN_PROGRESS",
      "learning_resources": [
        {
          "title": "Docker Official Getting Started Guide",
          "resource_type": "documentation",
          "url": "https://docs.docker.com/get-started/",
          "estimated_minutes": 120
        }
      ],
      "project_challenge": {
        "title": "Containerize a Full-Stack Web Application",
        "description": "Create a multi-stage Dockerfile and docker-compose.yml orchestrating API and database services.",
        "verification_rubric": {
          "required_files": ["Dockerfile", "docker-compose.yml"],
          "prohibited_patterns": ["ADD .", "latest"],
          "expected_services": ["web", "db"]
        }
      }
    }
  ]
}
```
