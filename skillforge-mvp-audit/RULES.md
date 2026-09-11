# SkillForge AI — Development Rules

## 1. Architecture

Do not introduce a new technology without documenting why it is necessary.

Prefer the simplest solution that satisfies the requirement.

---

## 2. AI

The LLM must not be treated as the source of truth for numerical industry-demand calculations.

Use structured data and deterministic/statistical methods wherever possible.

---

## 3. Data

Every market-demand dataset must record:

- Source
- Collection date
- Processing date
- Geographic scope
- Role scope
- License/usage constraints where applicable

---

## 4. Evidence

Resume claims and demonstrated GitHub evidence must remain distinguishable.

Never automatically treat a resume claim as proof of expertise.

---

## 5. APIs

Frontend must communicate with backend through documented APIs.

Do not place business logic directly inside frontend components.

---

## 6. Database

Database schema changes must be documented.

Avoid unnecessary duplication.

---

## 7. Secrets

Never commit:

- API keys
- GitHub tokens
- Database passwords
- `.env` files containing secrets

Use `.env.example` for required variables.

---

## 8. Testing

Every major service should have tests.

Critical logic requiring tests:

- Skill normalization
- Demand calculation
- Skill-gap calculation
- Priority scoring
- Resource ranking

---

## 9. Git

Use small, meaningful commits.

Recommended format:

```text
feat: add resume upload
feat: add github repository analysis
feat: implement demand engine
fix: normalize aws skill aliases
docs: update architecture
test: add skill gap tests
```

---

## 10. Documentation

If implementation changes architecture or behavior, update the corresponding documentation.

Documentation and implementation must remain synchronized.

---

## 11. MVP Discipline

Do not add features merely because they sound impressive.

Every feature must answer:

> Does this improve the core user journey?

The core journey is:

```text
Resume
→ GitHub
→ Skill Profile
→ Industry Demand
→ Skill Gap
→ Roadmap
→ Resources
→ Verification
```