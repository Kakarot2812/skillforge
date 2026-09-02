# Industry Demand Engine

## 1. Purpose

The Industry Demand Engine determines which technical skills are currently relevant to specific career roles and how demand is changing over time.

The system must avoid hard-coded lists of "trending skills."

---

## 2. Input

The engine can consume permitted and appropriately licensed market data containing information such as:

- Job title
- Job description
- Required skills
- Location
- Industry
- Date
- Experience level

Additional market reports may provide contextual signals but should not replace structured job-market data.

---

## 3. Processing Pipeline

```text
Raw Job Data
     ↓
Data Cleaning
     ↓
Deduplication
     ↓
Job Classification
     ↓
Skill Extraction
     ↓
Skill Normalization
     ↓
Skill Mapping
     ↓
Historical Aggregation
     ↓
Demand Calculation
     ↓
Trend Calculation
     ↓
Demand API
```

---

## 4. Skill Extraction

Skills may be extracted using a hybrid approach:

1. Skill dictionary/rules
2. NLP
3. Embeddings
4. LLM for ambiguous cases

The LLM should not be the sole source of truth.

---

## 5. Skill Normalization

Different expressions representing the same skill should map to a canonical skill.

Example:

```text
Amazon Web Services
AWS
AWS Cloud
Amazon AWS

        ↓

AWS
```

Another example:

```text
K8s
Kubernetes
Kubernetes orchestration

        ↓

Kubernetes
```

Embeddings can assist semantic matching.

---

## 6. Demand Metrics

For each skill, the engine should maintain:

- Number of relevant jobs
- Percentage of relevant jobs
- Recent demand
- Historical demand
- Growth rate
- Role relevance
- Location relevance

---

## 7. Trend Detection

The system should track demand over time.

Example:

```text
Month     Docker Demand

January      31%
February     33%
March        36%
April        39%
May          43%
```

This allows the system to identify:

- High demand
- Stable demand
- Growing demand
- Declining demand

---

## 8. Role-Specific Demand

Demand should always be evaluated in context.

Example:

```text
Backend Engineer
        ↓
Relevant Jobs
        ↓
Skill Demand
```

The platform should not claim that a skill is universally valuable merely because it appears frequently in unrelated job categories.

---

## 9. Location

The engine should eventually support location-specific analysis.

Potential locations:

- India
- Delhi NCR
- Bengaluru
- Hyderabad
- Mumbai
- Pune

Location filtering will be implemented after the core MVP demand pipeline is working.

---

## 10. Data Freshness

Every demand result must contain a freshness indicator.

Example:

```text
Market data:
Updated: 1 September 2026
```

The system must never imply that historical data is real-time.

---

## 11. RAG Relationship

RAG does not determine the numerical demand score.

Instead:

```text
Structured Market Data
        ↓
Demand Engine
        ↓
Demand Score
```

RAG can provide contextual explanations:

```text
Demand Score
      +
Industry Reports
      ↓
LLM Explanation
```

---

## 12. Output

Example:

```json
{
  "role": "Backend Engineer",
  "location": "India",
  "data_updated": "2026-09-01",
  "skills": [
    {
      "skill": "Docker",
      "demand": 0.51,
      "trend": 0.12
    },
    {
      "skill": "AWS",
      "demand": 0.47,
      "trend": 0.09
    }
  ]
}
```

The exact schema may evolve during implementation.