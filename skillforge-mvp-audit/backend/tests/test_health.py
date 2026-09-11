from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify root welcome endpoint returns 200 and operational metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "SkillForge AI API"
    assert data["status"] == "operational"


def test_health_endpoint():
    """Verify basic application health check returns status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_v1_health_endpoint():
    """Verify health endpoint mounted under /api/v1 prefix."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_health_endpoint():
    """Verify database health endpoint connects to PostgreSQL and confirms pgvector extension."""
    response = client.get("/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert data["pgvector_installed"] is True
    assert "database_version" in data


def test_api_v1_database_health_endpoint():
    """Verify database health endpoint mounted under /api/v1 prefix."""
    response = client.get("/api/v1/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert data["pgvector_installed"] is True
