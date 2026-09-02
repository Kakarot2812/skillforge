# SkillForge AI — Engineering Foundation (Phase 1)

SkillForge AI is an evidence-based AI skill-gap analysis and career roadmap platform developed for the Smart India Hackathon (SIH).

This repository contains the complete Phase 1 engineering stack connecting:

```text
Browser
   ↓
Next.js Frontend (TypeScript + Tailwind CSS)
   ↓
FastAPI Backend (Python + SQLAlchemy + Alembic)
   ↓
PostgreSQL + pgvector (Relational Database + Vector Extension)
```

---

## 1. Prerequisites

- **Node.js**: v20+ (tested on Node v24.12.0)
- **Python**: 3.12+
- **Database**:
  - **Docker** with Docker Compose (preferred in containerized environments), **or**
  - **PostgreSQL 16/17** with `pgvector` installed locally via Homebrew (local development fallback).

---

## 2. Environment Configuration

### Root `.env.example`
Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Variables defined:

```env
# PostgreSQL with pgvector connection URL
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/skillforge

# Frontend API Base URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# Backend Settings
PROJECT_NAME="SkillForge AI API"
VERSION="0.1.0"
API_V1_STR="/api/v1"
CORS_ORIGINS=["http://localhost:3000"]
```

---

## 3. Database Startup

### Option A: Using Docker Compose (Standard)

Ensure Docker Desktop is running, then execute:

```bash
docker compose up -d
```

This provisions `pgvector/pgvector:pg16` on port `5432` with a persistent named volume `postgres_data`.

### Option B: Using Native Homebrew PostgreSQL (Local Mac Fallback)

If Docker is unavailable on your system:

```bash
# Start PostgreSQL service
brew services start postgresql@16

# Create database and enable pgvector
createdb skillforge 2>&1 || true
psql -d skillforge -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

## 4. Backend Setup & Startup

```bash
# Navigate to backend directory
cd backend

# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run initial Alembic database migrations
alembic upgrade head

# Start FastAPI development server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API documentation is accessible at:
- **Interactive Swagger UI**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- **ReDoc UI**: [http://localhost:8000/api/v1/redoc](http://localhost:8000/api/v1/redoc)

---

## 5. Frontend Setup & Startup

```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Start Next.js development server
npm run dev
```

The dashboard is accessible at:
- **Application URL**: [http://localhost:3000](http://localhost:3000)

---

## 6. API Health Endpoints

| Method | Endpoint | Description | Sample Output |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Application status | `{"status": "ok"}` |
| `GET` | `/health/db` | Database & pgvector status | `{"status": "ok", "database": "connected", "pgvector_installed": true}` |
| `GET` | `/api/v1/health` | Mounted v1 health check | `{"status": "ok"}` |
| `GET` | `/api/v1/health/db` | Mounted v1 database check | `{"status": "ok", "database": "connected", "pgvector_installed": true}` |

---

## 7. Testing Commands

### Backend Test Suite

```bash
cd backend
.venv/bin/pytest -v
```

Tests verify:
- Application startup and root endpoint
- `/health` and `/api/v1/health` responses
- Live database query execution and `pgvector` extension confirmation
- User and Skill database model CRUD operations

### Frontend Build & Typecheck

```bash
cd frontend
npm run build
```

Verifies strict TypeScript compilation and Next.js production bundling.

---

## 8. Phase Roadmap Reference

Follows the phase sequence defined in [`docs/MVP_PHASES.md`](docs/MVP_PHASES.md):

- **Phase 0**: Documentation & Architecture *(Complete)*
- **Phase 1**: Engineering Foundation *(Active)*
- **Phase 2**: Resume Intelligence *(Next)*
- **Phase 3**: GitHub Intelligence
- **Phase 4**: Industry Demand Engine
- **Phase 5**: Skill Gap + Priority Engine
- **Phase 6**: Roadmap + Resources
- **Phase 7**: RAG + AI Assistant
- **Phase 8**: GitHub Verification Loop
- **Phase 9**: Dashboard + UX Polish
- **Phase 10**: Testing + Deployment + SIH Demo
