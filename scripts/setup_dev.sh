#!/usr/bin/env bash
# SkillForge AI — Phase 1 Local Development Setup Script
set -e

echo "=== SkillForge AI: Setting up Phase 1 Local Environment ==="

# 1. Check PostgreSQL
echo "[1/4] Checking PostgreSQL and pgvector..."
if command -v psql &> /dev/null; then
    echo "PostgreSQL found in PATH."
    psql -d skillforge -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';" || {
        echo "Creating database and vector extension..."
        createdb skillforge 2>&1 || true
        psql -d skillforge -c "CREATE EXTENSION IF NOT EXISTS vector;"
    }
else
    echo "psql not in global PATH. Checking Homebrew installation..."
    /opt/homebrew/opt/postgresql@16/bin/psql -d skillforge -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';" || true
fi

# 2. Setup Python virtual environment
echo "[2/4] Setting up Python virtual environment..."
cd backend
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt

# 3. Run Alembic migrations
echo "[3/4] Running Alembic database migrations..."
alembic upgrade head

# 4. Install Frontend dependencies
echo "[4/4] Setting up Next.js frontend..."
cd ../frontend
npm install

echo "=== Setup Complete! ==="
echo "To run backend:  cd backend && source .venv/bin/activate && uvicorn app.main:app --port 8000"
echo "To run frontend: cd frontend && npm run dev"
