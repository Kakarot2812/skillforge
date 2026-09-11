import io
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.database import SessionLocal
from app.db.models import JobRole, Resume, Skill, User

client = TestClient(app)


@pytest.fixture
def db_session():
    """Provides a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_pdf_bytes():
    """Generates a minimal valid PDF byte string with extractable text."""
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        b"4 0 obj << /Length 300 >> stream\n"
        b"BT\n"
        b"/F1 12 Tf\n"
        b"100 700 Td\n"
        b"(John Doe) Tj\n"
        b"0 -20 Td\n"
        b"(Email: john.doe@example.com | Phone: 555-0199) Tj\n"
        b"0 -30 Td\n"
        b"(EXPERIENCE) Tj\n"
        b"0 -20 Td\n"
        b"(Senior Software Engineer - Tech Corp - 2020 to Present) Tj\n"
        b"0 -20 Td\n"
        b"(Developed REST APIs using Python and FastAPI.) Tj\n"
        b"0 -30 Td\n"
        b"(SKILLS) Tj\n"
        b"0 -20 Td\n"
        b"(Python, FastAPI, Docker, PostgreSQL) Tj\n"
        b"0 -30 Td\n"
        b"(EDUCATION) Tj\n"
        b"0 -20 Td\n"
        b"(B.S. in Computer Science - State University - 2016-2020) Tj\n"
        b"ET\n"
        b"endstream\n"
        b"endobj\n"
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"xref\n"
        b"0 6\n"
        b"0000000000 65535 f \n"
        b"0000000010 00000 n \n"
        b"0000000060 00000 n \n"
        b"0000000117 00000 n \n"
        b"0000000224 00000 n \n"
        b"0000000577 00000 n \n"
        b"trailer << /Size 6 /Root 1 0 R >>\n"
        b"startxref\n"
        b"648\n"
        b"%%EOF\n"
    )
    return pdf_content


@pytest.fixture
def test_users(db_session: Session):
    """Creates two distinct legitimate users in the database."""
    user_a = User(
        id=uuid.uuid4(),
        email=f"candidate_a_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Candidate Alpha",
        target_role="Backend Engineer",
    )
    user_b = User(
        id=uuid.uuid4(),
        email=f"candidate_b_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Candidate Beta",
        target_role="Frontend Engineer",
    )
    db_session.add_all([user_a, user_b])
    db_session.commit()
    db_session.refresh(user_a)
    db_session.refresh(user_b)
    try:
        yield {"user_a": user_a, "user_b": user_b}
    finally:
        db_session.delete(user_a)
        db_session.delete(user_b)
        db_session.commit()


@pytest.fixture
def backend_role(db_session: Session):
    """Retrieves or ensures canonical backend role."""
    role = db_session.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    return role


# -----------------------------------------------------------------------------
# Test A: Same candidate: resume.user_id == X-User-Id -> roadmap generation succeeds
# -----------------------------------------------------------------------------
def test_same_candidate_roadmap_generation_succeeds(
    test_users, backend_role, sample_pdf_bytes, db_session: Session
):
    user_a = test_users["user_a"]

    # 1. Upload resume under user_a identity
    upload_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume_alpha.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        headers={"X-User-Id": str(user_a.id)},
    )
    assert upload_res.status_code == 201
    resume_data = upload_res.json()
    resume_id = resume_data["resume_id"]
    assert resume_data["user_id"] == str(user_a.id)

    try:
        # 2. Generate roadmap with matching candidate identity
        payload = {
            "role_id": str(backend_role.id),
            "location": "India",
            "resume_id": resume_id,
            "include_resume": True,
            "include_github": False,
        }
        gen_res = client.post(
            "/api/v1/roadmap/generate",
            json=payload,
            headers={"X-User-Id": str(user_a.id)},
        )
        assert gen_res.status_code == 200
        data = gen_res.json()["data"]
        assert data["role_id"] == str(backend_role.id)
        assert data["user_id"] == str(user_a.id)
        assert len(data["milestones"]) > 0

        # 3. Active roadmap fetch returns this roadmap
        active_res = client.get(
            f"/api/v1/roadmap/active?role_id={backend_role.id}",
            headers={"X-User-Id": str(user_a.id)},
        )
        assert active_res.status_code == 200
        assert active_res.json()["data"]["id"] == data["id"]
    finally:
        client.delete(f"/api/v1/resumes/{resume_id}", headers={"X-User-Id": str(user_a.id)})


# -----------------------------------------------------------------------------
# Test B: Different candidate: resume.user_id != X-User-Id -> backend returns 403
# -----------------------------------------------------------------------------
def test_different_candidate_roadmap_generation_fails_403(
    test_users, backend_role, sample_pdf_bytes, db_session: Session
):
    user_a = test_users["user_a"]
    user_b = test_users["user_b"]

    # Upload resume under user_a
    upload_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume_alpha.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        headers={"X-User-Id": str(user_a.id)},
    )
    assert upload_res.status_code == 201
    resume_id = upload_res.json()["resume_id"]

    try:
        # User B attempts to generate roadmap using User A's resume
        payload = {
            "role_id": str(backend_role.id),
            "location": "India",
            "resume_id": resume_id,
            "include_resume": True,
            "include_github": False,
        }
        res = client.post(
            "/api/v1/roadmap/generate",
            json=payload,
            headers={"X-User-Id": str(user_b.id)},
        )
        assert res.status_code == 403
        assert "Cross-user access denied" in res.json()["detail"]
    finally:
        client.delete(f"/api/v1/resumes/{resume_id}", headers={"X-User-Id": str(user_a.id)})


# -----------------------------------------------------------------------------
# Test C: Orphaned resume (user_id is NULL) -> candidate access denied (403)
# -----------------------------------------------------------------------------
def test_orphaned_resume_access_denied_for_candidate(
    test_users, backend_role, sample_pdf_bytes, db_session: Session
):
    user_a = test_users["user_a"]

    # Upload resume without X-User-Id -> orphaned resume (user_id=None)
    upload_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume_anon.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
    )
    assert upload_res.status_code == 201
    resume_id = upload_res.json()["resume_id"]
    assert upload_res.json()["user_id"] is None

    try:
        # Candidate User A attempts to generate roadmap with the orphaned resume -> 403 Forbidden
        payload = {
            "role_id": str(backend_role.id),
            "location": "India",
            "resume_id": resume_id,
            "include_resume": True,
            "include_github": False,
        }
        gen_res = client.post(
            "/api/v1/roadmap/generate",
            json=payload,
            headers={"X-User-Id": str(user_a.id)},
        )
        assert gen_res.status_code == 403
        assert "Cross-user access denied" in gen_res.json()["detail"]

        # Candidate User A attempts to get orphaned resume details -> 403 Forbidden
        get_res = client.get(
            f"/api/v1/resumes/{resume_id}",
            headers={"X-User-Id": str(user_a.id)},
        )
        assert get_res.status_code == 403
        assert "Cross-user access denied" in get_res.json()["detail"]
    finally:
        client.delete(f"/api/v1/resumes/{resume_id}")


# -----------------------------------------------------------------------------
# Test D: Candidate-scoped Resume List and Detail APIs
# -----------------------------------------------------------------------------
def test_candidate_scoped_resume_list_and_detail(
    test_users, sample_pdf_bytes, db_session: Session
):
    user_a = test_users["user_a"]
    user_b = test_users["user_b"]

    # Upload for User A
    res_a = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume_a.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        headers={"X-User-Id": str(user_a.id)},
    )
    id_a = res_a.json()["resume_id"]

    # Upload for User B
    res_b = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume_b.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        headers={"X-User-Id": str(user_b.id)},
    )
    id_b = res_b.json()["resume_id"]

    try:
        # User A lists resumes -> contains id_a, NOT id_b
        list_a = client.get("/api/v1/resumes", headers={"X-User-Id": str(user_a.id)})
        assert list_a.status_code == 200
        ids_a = {item["resume_id"] for item in list_a.json()["data"]}
        assert id_a in ids_a
        assert id_b not in ids_a

        # User B lists resumes -> contains id_b, NOT id_a
        list_b = client.get("/api/v1/resumes", headers={"X-User-Id": str(user_b.id)})
        assert list_b.status_code == 200
        ids_b = {item["resume_id"] for item in list_b.json()["data"]}
        assert id_b in ids_b
        assert id_a not in ids_b

        # Detail for User A accesses id_a -> 200 OK
        detail_a = client.get(f"/api/v1/resumes/{id_a}", headers={"X-User-Id": str(user_a.id)})
        assert detail_a.status_code == 200
        assert detail_a.json()["user_id"] == str(user_a.id)

        # User B attempts to access id_a -> 403 Forbidden
        detail_b_denied = client.get(f"/api/v1/resumes/{id_a}", headers={"X-User-Id": str(user_b.id)})
        assert detail_b_denied.status_code == 403
        assert "Cross-user access denied" in detail_b_denied.json()["detail"]
    finally:
        client.delete(f"/api/v1/resumes/{id_a}", headers={"X-User-Id": str(user_a.id)})
        client.delete(f"/api/v1/resumes/{id_b}", headers={"X-User-Id": str(user_b.id)})


# -----------------------------------------------------------------------------
# Test E: Identity conflict: conflicting query user_id vs X-User-Id header -> 403
# -----------------------------------------------------------------------------
def test_identity_conflict_query_vs_header_rejected_403(test_users):
    user_a = test_users["user_a"]
    user_b = test_users["user_b"]

    res = client.get(
        f"/api/v1/resumes?user_id={user_b.id}",
        headers={"X-User-Id": str(user_a.id)},
    )
    assert res.status_code == 403
    assert "Cross-user access denied" in res.json()["detail"]


# -----------------------------------------------------------------------------
# Test F: Upload with nonexistent candidate ID returns 404 (no fake users)
# -----------------------------------------------------------------------------
def test_upload_with_nonexistent_user_id_returns_404(sample_pdf_bytes):
    fake_user_id = str(uuid.uuid4())
    res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        headers={"X-User-Id": fake_user_id},
    )
    assert res.status_code == 404
    assert f"User with id '{fake_user_id}' not found." in res.json()["detail"]
