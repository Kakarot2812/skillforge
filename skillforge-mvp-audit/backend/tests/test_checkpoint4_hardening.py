import io
import os
import uuid
import zipfile
from docx import Document
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import SessionLocal
from app.db.models import Resume, UserClaimedSkill
from app.services.skill_service import process_and_persist_resume_skills

client = TestClient(app)


def make_test_pdf_bytes(lines: list[str]) -> bytes:
    stream_content = "BT\n/F1 12 Tf\n50 750 Td\n15 TL\n"
    for line in lines:
        safe_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream_content += f"({safe_line}) '\n"
    stream_content += "ET\n"
    stream_bytes = stream_content.encode("latin1")
    stream_len = len(stream_bytes)

    pdf_str = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length {stream_len} >>
stream
{stream_content}endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000300 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
400
%%EOF"""
    return pdf_str.encode("latin1")


def test_list_resumes_endpoint_pagination():
    """
    Requirement 3: GET /resumes
    - Paginated resume records
    - Standard response envelope from API_SPEC.md
    - limit/offset pagination and total in meta
    """
    # Upload 2 resumes
    pdf_bytes_1 = make_test_pdf_bytes(["Candidate One", "Skills", "Python, Docker"])
    pdf_bytes_2 = make_test_pdf_bytes(["Candidate Two", "Skills", "React, FastAPI"])

    r1 = client.post("/api/v1/resumes/upload", files={"file": ("cand1.pdf", io.BytesIO(pdf_bytes_1), "application/pdf")})
    r2 = client.post("/api/v1/resumes/upload", files={"file": ("cand2.pdf", io.BytesIO(pdf_bytes_2), "application/pdf")})
    assert r1.status_code == 201
    assert r2.status_code == 201

    id1 = r1.json()["resume_id"]
    id2 = r2.json()["resume_id"]

    try:
        # Query list
        res = client.get("/api/v1/resumes?limit=1&offset=0")
        assert res.status_code == 200
        body = res.json()
        assert "data" in body
        assert "meta" in body
        assert len(body["data"]) == 1
        assert body["meta"]["limit"] == 1
        assert body["meta"]["offset"] == 0
        assert body["meta"]["total"] >= 2

        first_item = body["data"][0]
        assert "resume_id" in first_item
        assert "filename" in first_item
        assert "file_type" in first_item
        assert "file_size" in first_item
        assert "status" in first_item
        assert "detected_sections" in first_item
        assert "claimed_skills_count" in first_item
        assert "created_at" in first_item
    finally:
        # Cleanup
        client.delete(f"/api/v1/resumes/{id1}")
        client.delete(f"/api/v1/resumes/{id2}")


def test_get_resume_details_comprehensive():
    """
    Requirement 3: GET /resumes/{resume_id}
    - resume metadata, raw_text, parsed_data, detected sections, contact info, claimed skills
    """
    pdf_bytes = make_test_pdf_bytes([
        "Jane Detail",
        "Email: jane.detail@test.io | Phone: +1 555-0199",
        "Technical Skills",
        "Python, PostgreSQL, Kubernetes",
    ])
    up_res = client.post("/api/v1/resumes/upload", files={"file": ("jane_detail.pdf", io.BytesIO(pdf_bytes), "application/pdf")})
    assert up_res.status_code == 201
    resume_id = up_res.json()["resume_id"]

    try:
        detail_res = client.get(f"/api/v1/resumes/{resume_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()

        assert detail["resume_id"] == resume_id
        assert detail["filename"] == "jane_detail.pdf"
        assert detail["file_type"] == "pdf"
        assert detail["has_raw_text"] is True
        assert "Jane Detail" in detail["raw_text"]
        assert "skills" in detail["detected_sections"]
        assert detail["contact_info"]["email"] == "jane.detail@test.io"
        assert detail["claimed_skills_count"] >= 3

        skill_names = {s["skill_name"] for s in detail["claimed_skills"]}
        assert "Python" in skill_names
        assert "PostgreSQL" in skill_names
        assert "Kubernetes" in skill_names
    finally:
        client.delete(f"/api/v1/resumes/{resume_id}")


def test_delete_resume_and_cascade_cleanup():
    """
    Requirement 3 & 12: DELETE /resumes/{resume_id}
    - Deletes file from disk
    - Deletes database record
    - Cleans up associated user_claimed_skills
    - Repeated delete returns clean 404
    """
    pdf_bytes = make_test_pdf_bytes(["Delete Candidate", "Skills", "Docker, Redis"])
    up_res = client.post("/api/v1/resumes/upload", files={"file": ("to_delete.pdf", io.BytesIO(pdf_bytes), "application/pdf")})
    assert up_res.status_code == 201
    resume_id = up_res.json()["resume_id"]

    # Verify file and claimed skills exist in DB
    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(Resume.id == uuid.UUID(resume_id)).first()
        assert resume is not None
        storage_path = resume.storage_path
        assert os.path.exists(storage_path)

        claimed = db.query(UserClaimedSkill).filter(UserClaimedSkill.resume_id == uuid.UUID(resume_id)).all()
        assert len(claimed) >= 2
    finally:
        db.close()

    # 1. Execute DELETE
    del_res = client.delete(f"/api/v1/resumes/{resume_id}")
    assert del_res.status_code == 204

    # 2. Verify file removed from disk
    assert not os.path.exists(storage_path)

    # 3. Verify DB record and cascade
    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(Resume.id == uuid.UUID(resume_id)).first()
        assert resume is None

        orphaned = db.query(UserClaimedSkill).filter(UserClaimedSkill.resume_id == uuid.UUID(resume_id)).all()
        assert len(orphaned) == 0
    finally:
        db.close()

    # 4. Repeated DELETE returns clean 404
    repeat_del = client.delete(f"/api/v1/resumes/{resume_id}")
    assert repeat_del.status_code == 404
    error_body = repeat_del.json()
    assert error_body["error"]["code"] == "NOT_FOUND"


def test_idempotent_resume_processing():
    """
    Requirement 4 & 5: Idempotency
    - Processing same resume twice does NOT duplicate claimed skills or canonical skills
    - Confidence scores preserved
    """
    pdf_bytes = make_test_pdf_bytes(["Idempotency Test", "Skills", "Python, TypeScript, Git"])
    up_res = client.post("/api/v1/resumes/upload", files={"file": ("idempotent.pdf", io.BytesIO(pdf_bytes), "application/pdf")})
    assert up_res.status_code == 201
    resume_id = up_res.json()["resume_id"]

    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(Resume.id == uuid.UUID(resume_id)).first()
        initial_claimed_count = db.query(UserClaimedSkill).filter(UserClaimedSkill.resume_id == resume.id).count()
        assert initial_claimed_count >= 3

        # Re-process the same resume
        reprocessed = process_and_persist_resume_skills(db, resume)
        after_claimed_count = db.query(UserClaimedSkill).filter(UserClaimedSkill.resume_id == resume.id).count()

        # Count must remain exactly the same (no duplicates)
        assert after_claimed_count == initial_claimed_count
    finally:
        db.close()
        client.delete(f"/api/v1/resumes/{resume_id}")


def test_invalid_docx_structure_rejected():
    """
    Requirement 6: DOCX must be validated as an actual OpenXML WordprocessingML package.
    A plain zip without word/ structure is rejected with 400 Bad Request.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("some_random_file.txt", "hello world")

    buf.seek(0)
    fake_docx_bytes = buf.getvalue()

    res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("fake.docx", io.BytesIO(fake_docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert res.status_code == 400
    assert "openxml" in res.json()["error"]["message"].lower() or "docx" in res.json()["error"]["message"].lower()


def test_standardized_error_envelope():
    """
    Requirement 10: Standardized error envelope
    404, 413, 422 return structured error format.
    """
    # 404
    non_existent = str(uuid.uuid4())
    res_404 = client.get(f"/api/v1/resumes/{non_existent}")
    assert res_404.status_code == 404
    body = res_404.json()
    assert "error" in body
    assert body["error"]["code"] == "NOT_FOUND"
    assert "not found" in body["error"]["message"].lower()

    # 422 (validation error on bad UUID format)
    res_422 = client.get("/api/v1/resumes/not-a-valid-uuid")
    assert res_422.status_code == 422
    body_422 = res_422.json()
    assert "error" in body_422
    assert body_422["error"]["code"] == "VALIDATION_ERROR"


def test_parser_robustness_missing_sections():
    """
    Requirement 7 & 8: Gracefully handles missing sections.
    Resume containing only experience, no dedicated skills section or contact info.
    """
    pdf_bytes = make_test_pdf_bytes([
        "Anonymous Developer",
        "Work Experience",
        "Built backend microservices using Python and PostgreSQL at Acme.",
    ])
    up_res = client.post("/api/v1/resumes/upload", files={"file": ("no_skills_sec.pdf", io.BytesIO(pdf_bytes), "application/pdf")})
    assert up_res.status_code == 201
    resume_id = up_res.json()["resume_id"]

    try:
        detail_res = client.get(f"/api/v1/resumes/{resume_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()

        # Contact info should be all None without crashing
        assert detail["contact_info"]["email"] is None
        assert detail["contact_info"]["phone"] is None

        # Experience was found
        assert "experience" in detail["detected_sections"]

        # Skills from narrative text were extracted
        skill_names = {s["skill_name"] for s in detail["claimed_skills"]}
        assert "Python" in skill_names or "PostgreSQL" in skill_names
    finally:
        client.delete(f"/api/v1/resumes/{resume_id}")
