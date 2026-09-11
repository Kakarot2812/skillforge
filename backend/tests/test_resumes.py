import io
import os
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import SessionLocal
from app.db.models import Resume

client = TestClient(app)

from tests.test_resume_parser import generate_test_pdf_bytes, generate_test_docx_bytes

# Valid PDF and DOCX binary contents with genuine resume structure
VALID_PDF_BYTES = generate_test_pdf_bytes([
    "Candidate Resume",
    "Email: candidate@example.com | Phone: +1 555-0100",
    "Technical Skills",
    "Python, Docker, PostgreSQL, React",
    "Professional Experience",
    "Software Engineer at Acme Corp (2022 - 2024)",
    "Education",
    "B.S. in Computer Science",
])

VALID_DOCX_BYTES = generate_test_docx_bytes(
    header="Candidate Resume | candidate@example.com",
    skills="Python, Docker, PostgreSQL, React",
    experience="Software Engineer at Acme Corp",
    projects="SkillForge AI Platform",
    education="B.S. in Computer Science",
)


def test_upload_valid_pdf():
    """Verify that uploading a valid PDF succeeds and returns 201 with metadata."""
    files = {
        "file": ("candidate_resume.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")
    }
    response = client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 201
    data = response.json()

    assert "resume_id" in data
    assert uuid.UUID(data["resume_id"])  # must be valid UUID
    assert data["filename"] == "candidate_resume.pdf"
    assert data["file_type"] == "pdf"
    assert data["file_size"] == len(VALID_PDF_BYTES)
    assert data["status"] == "uploaded"

    # Verify database persistence
    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(Resume.id == uuid.UUID(data["resume_id"])).first()
        assert resume is not None
        assert resume.file_name == "candidate_resume.pdf"
        assert resume.file_type == "pdf"
        assert resume.file_size == len(VALID_PDF_BYTES)
        assert os.path.exists(resume.storage_path)

        # Cleanup test file
        if os.path.exists(resume.storage_path):
            os.remove(resume.storage_path)
        db.delete(resume)
        db.commit()
    finally:
        db.close()


def test_upload_valid_docx():
    """Verify that uploading a valid DOCX succeeds and returns 201."""
    files = {
        "file": (
            "candidate_resume.docx",
            io.BytesIO(VALID_DOCX_BYTES),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    response = client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 201
    data = response.json()

    assert data["filename"] == "candidate_resume.docx"
    assert data["file_type"] == "docx"
    assert data["file_size"] == len(VALID_DOCX_BYTES)

    # Clean up
    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(Resume.id == uuid.UUID(data["resume_id"])).first()
        if resume:
            if os.path.exists(resume.storage_path):
                os.remove(resume.storage_path)
            db.delete(resume)
            db.commit()
    finally:
        db.close()


def test_unique_resume_ids():
    """Verify that each upload produces a unique resume ID."""
    files1 = {"file": ("resume_1.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")}
    files2 = {"file": ("resume_2.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")}

    r1 = client.post("/api/v1/resumes/upload", files=files1)
    r2 = client.post("/api/v1/resumes/upload", files=files2)

    assert r1.status_code == 201
    assert r2.status_code == 201

    id1 = r1.json()["resume_id"]
    id2 = r2.json()["resume_id"]
    assert id1 != id2

    # Clean up
    db = SessionLocal()
    try:
        for res_id in [id1, id2]:
            resume = db.query(Resume).filter(Resume.id == uuid.UUID(res_id)).first()
            if resume:
                if os.path.exists(resume.storage_path):
                    os.remove(resume.storage_path)
                db.delete(resume)
        db.commit()
    finally:
        db.close()


def test_reject_unsupported_file_extension():
    """Verify that uploading files other than PDF or DOCX returns 400."""
    files = {"file": ("script.py", io.BytesIO(b"print('hello')"), "text/x-python")}
    response = client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]


def test_reject_oversized_file():
    """Verify that uploading a file larger than 5 MB returns 413."""
    # 5 MB + 1 KB
    large_payload = b"%PDF-" + b"0" * (5 * 1024 * 1024 + 1024)
    files = {"file": ("giant_resume.pdf", io.BytesIO(large_payload), "application/pdf")}
    response = client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 413
    assert "File exceeds maximum allowed size" in response.json()["detail"]


def test_reject_spoofed_pdf_magic_bytes():
    """Verify that an arbitrary text file renamed to .pdf fails content validation."""
    fake_pdf = b"Plain text file that is not really a PDF document at all"
    files = {"file": ("fake_resume.pdf", io.BytesIO(fake_pdf), "application/pdf")}
    response = client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 400
    assert "valid PDF signature" in response.json()["detail"]


def test_reject_empty_file():
    """Verify that uploading an empty (0-byte) file returns 400."""
    files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    response = client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_path_traversal_sanitization():
    """Verify that filenames containing directory traversal sequences are sanitized."""
    malicious_filename = "../../../../../etc/passwd.pdf"
    files = {"file": (malicious_filename, io.BytesIO(VALID_PDF_BYTES), "application/pdf")}
    response = client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 201
    data = response.json()

    assert ".." not in data["filename"]
    assert "/" not in data["filename"]

    # Verify storage path is within upload dir
    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(Resume.id == uuid.UUID(data["resume_id"])).first()
        assert resume is not None
        assert "passwd.pdf" in resume.file_name
        # The file on disk should be stored by UUID, not by the client's path
        assert str(resume.id) in resume.storage_path
        if os.path.exists(resume.storage_path):
            os.remove(resume.storage_path)
        db.delete(resume)
        db.commit()
    finally:
        db.close()
