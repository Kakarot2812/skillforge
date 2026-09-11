# SkillForge AI — Product Requirements Document

## 1. Product Overview

SkillForge AI is an evidence-based AI skill-gap and career roadmap platform.

The platform analyzes:

1. User resume
2. User GitHub repositories and projects
3. Target career role
4. Current industry skill demand

The system creates an evidence-based skill profile, identifies gaps between the user's demonstrated capabilities and current industry requirements, prioritizes those gaps, and generates a personalized learning roadmap containing resources and practical projects.

---

## 2. Problem

Students and early-career developers often do not know:

- Which skills are actually required for their target role
- Which skills they already possess
- Whether the skills listed on their resume are supported by actual project evidence
- Which missing skills should be learned first
- Which learning resources are appropriate for their current level
- Which projects can help demonstrate the missing skills

Generic career platforms provide static recommendations or generic learning paths.

SkillForge AI aims to make recommendations based on the user's actual evidence and changing industry demand.

---

## 3. Target Users

### Primary

- Computer science students
- College students
- Fresh graduates
- Early-career developers

### Secondary

- Career-switchers
- Placement preparation students
- Colleges and training institutions

---

## 4. Core User Journey

```text
Upload Resume
      ↓
Connect GitHub
      ↓
Select Target Role
      ↓
Analyze Skills
      ↓
Analyze Industry Demand
      ↓
Identify Skill Gaps
      ↓
Prioritize Gaps
      ↓
Generate Roadmap
      ↓
Recommend Resources
      ↓
Build Projects
      ↓
Verify Through GitHub
      ↓
Re-analyze Profile
```

---

## 5. Core Features

### 5.1 Resume Analysis

The system extracts:

- Technical skills
- Tools
- Frameworks
- Programming languages
- Projects
- Experience
- Education
- Certifications

The extracted information is normalized into the platform's skill taxonomy.

---

### 5.2 GitHub Analysis

The system analyzes user repositories to identify evidence of technical skills.

Possible evidence includes:

- Programming languages
- Frameworks
- Dependencies
- Project structure
- README information
- Configuration files
- Docker configuration
- CI/CD configuration
- Other publicly available repository metadata and files permitted through the GitHub API

The system distinguishes between:

**Claimed skill**

A skill mentioned in the resume.

**Demonstrated skill**

A skill for which the system finds project evidence.

---

### 5.3 Industry Demand Engine

The platform must not use a static list of trending technologies.

Industry demand is derived from structured market data.

The engine processes permitted job-market data and extracts:

- Skills
- Job roles
- Locations
- Industries
- Skill frequency
- Skill growth
- Historical demand

The engine produces role-specific demand signals.

Example:

```text
Backend Engineer

Java             72%
Spring Boot      64%
SQL              61%
Docker           51%
AWS              47%
Kubernetes       24%
```

Demand values must include data freshness.

---

### 5.4 Skill Gap Engine

The engine compares:

```text
User Skill Evidence
+
Target Role Requirements
+
Industry Demand
```

It identifies:

- Missing skills
- Weakly demonstrated skills
- High-priority skills
- Medium-priority skills
- Lower-priority skills

---

### 5.5 Priority Engine

Skill priority should consider multiple signals such as:

- Industry demand
- Recent demand growth
- Target-role relevance
- User skill gap
- Skill dependencies
- Estimated learning effort

The exact scoring formula will be documented separately.

---

### 5.6 Personalized Roadmap

The system converts prioritized skill gaps into a learning sequence.

Each roadmap item may contain:

- Skill
- Prerequisites
- Learning objective
- Learning resources
- Practical project
- Estimated effort
- Verification criteria

---

### 5.7 Resource Recommendation

Resources should be mapped to skills.

Possible resource categories:

- Official documentation
- Courses
- Tutorials
- Books
- Hands-on labs
- Projects
- Practice exercises

The system should prefer resources appropriate to the user's existing knowledge.

---

### 5.8 AI Assistant

The AI assistant can answer questions about:

- Skill gaps
- Roadmap
- Industry demand
- Recommended resources
- Projects
- Career readiness

The LLM should explain system-generated recommendations rather than independently inventing market-demand scores.

---

### 5.9 GitHub Skill Verification

After the user completes a project, the platform can analyze the updated GitHub repository and determine whether evidence exists for the target skill.

Example:

```text
Docker

Before:
Evidence: 0%

After:
Dockerfile detected
Docker Compose detected
Containerized application detected

Evidence: 84%
```

The user's skill profile can then be re-evaluated.

---

## 6. MVP Scope

### Included

- Resume upload
- Resume skill extraction
- GitHub connection
- Repository analysis
- Skill normalization
- Target-role selection
- Industry skill-demand dataset
- Demand calculation
- Skill-gap analysis
- Skill prioritization
- Personalized roadmap
- Resource recommendations
- Basic AI assistant
- Dashboard

### Deferred

- Full enterprise college platform
- Advanced recruiter features
- Automated job applications
- Complex psychometric testing
- Advanced labor-market forecasting
- Large-scale distributed infrastructure
- Neo4j
- Redis/Celery unless required
- Mobile application

---

## 7. Product Principles

### Evidence over claims

A resume claim should not automatically be treated as demonstrated expertise.

### Data over LLM opinion

Industry demand must be calculated from structured market data.

### Explainability

Every important recommendation should have an understandable reason.

### Dynamic demand

Industry demand must be refreshable rather than permanently hard-coded.

### Personalized learning

The roadmap should begin from the user's existing skills.

### Build to prove

Practical projects and GitHub evidence should contribute to skill verification.

---

## 8. Success Criteria

A successful MVP should demonstrate:

1. A user can upload a resume.
2. The system extracts technical skills.
3. A user can connect GitHub.
4. The system analyzes repositories.
5. Resume and GitHub evidence are combined.
6. A target role can be selected.
7. Current industry-demand data can be queried.
8. Skill gaps are calculated.
9. Gaps are prioritized.
10. A personalized roadmap is generated.
11. Relevant learning resources are recommended.
12. GitHub evidence can later be used to verify progress.

---

## 9. Core Differentiator

SkillForge AI is not intended to be a generic chatbot.

Its core intelligence comes from:

```text
Resume Evidence
+
GitHub Evidence
+
Industry Market Data
+
Skill Relationships
+
Personalized Recommendation Logic
```

The LLM is used primarily for extraction, contextual reasoning, explanations, and natural-language interaction.