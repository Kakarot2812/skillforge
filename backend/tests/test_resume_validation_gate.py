import io
import os
import uuid
from pathlib import Path
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.main import app
from app.config import settings
from app.db.database import SessionLocal
from app.db.models import Resume, UserClaimedSkill
from tests.test_resume_parser import generate_test_pdf_bytes, generate_test_docx_bytes

client = TestClient(app)

NITIN_RESUME_PATH = Path("/Users/niteshyadav/Downloads/NITIN_RESUME.pdf")
UNIT_1_PS_PATH = Path("/Users/niteshyadav/Downloads/Unit_1_PS.pdf")


# ---------------------------------------------------------------------------
# POSITIVE TESTS: Legitimate resumes that MUST succeed (HTTP 201 Created)
# ---------------------------------------------------------------------------


def test_positive_standard_student_resume():
    """
    Standard student/fresh-graduate resume:
    Contains Education, Projects, and Skills without professional work experience
    and with privacy-redacted contact details.
    """
    lines = [
        "Alex Student",
        "Education",
        "B.S. in Computer Science, University of Technology (2020 - 2024)",
        "GPA: 3.8 / 4.0",
        "Projects",
        "SkillForge Platform - Evidence-based career navigator built with FastAPI and PostgreSQL",
        "Mini LLM - Transformer model built from scratch in PyTorch",
        "Skills",
        "Python, PyTorch, FastAPI, SQL, Git, Linux",
    ]
    pdf_bytes = generate_test_pdf_bytes(lines)
    files = {"file": ("student_resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    response = client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 201
    data = response.json()

    assert data["status"] == "uploaded"
    assert "education" in data["extracted_sections"]
    assert "projects" in data["extracted_sections"]
    assert "skills" in data["extracted_sections"]
    assert data["claimed_skills_count"] > 0

    # Cleanup DB and disk
    client.delete(f"/api/v1/resumes/{data['resume_id']}")


def test_positive_experience_and_education_resume():
    """
    Candidate resume containing Work Experience and Education,
    without an explicit skills section or phone number.
    """
    lines = [
        "Morgan Taylor",
        "Professional Experience",
        "Senior Backend Engineer at CloudTech (2021 - Present)",
        "Designed and maintained distributed microservices handling 50k requests per second.",
        "Education",
        "B.Tech in Information Technology, State University (2017 - 2021)",
    ]
    pdf_bytes = generate_test_pdf_bytes(lines)
    files = {"file": ("morgan_resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    response = client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 201
    data = response.json()

    assert "experience" in data["extracted_sections"]
    assert "education" in data["extracted_sections"]

    client.delete(f"/api/v1/resumes/{data['resume_id']}")


def test_positive_contact_signal_and_sections():
    """
    Resume containing contact details (email, phone, LinkedIn, GitHub)
    alongside canonical resume sections.
    """
    lines = [
        "Jordan Lee",
        "Email: jordan.lee@example.com | Phone: +1 555-234-5678",
        "GitHub: github.com/jordanlee | LinkedIn: linkedin.com/in/jordanlee",
        "Technical Skills",
        "Python, Go, Docker, Kubernetes, PostgreSQL",
        "Key Projects",
        "Distributed KV Store in Go",
    ]
    pdf_bytes = generate_test_pdf_bytes(lines)
    files = {"file": ("jordan_resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    response = client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 201
    data = response.json()

    assert "skills" in data["extracted_sections"]
    assert "projects" in data["extracted_sections"]

    client.delete(f"/api/v1/resumes/{data['resume_id']}")


def test_positive_docx_resume():
    """
    Genuine DOCX resume with tables and standard resume sections.
    """
    docx_bytes = generate_test_docx_bytes(
        header="Taylor Reed | email: taylor.reed@example.com",
        skills="Python, TypeScript, React, Docker, Redis",
        experience="Software Engineer at DataCorp (2022 - 2024)",
        projects="Event-Driven Streaming Pipeline",
        education="M.S. in Computer Science, Georgia Tech",
    )
    files = {
        "file": (
            "taylor_resume.docx",
            io.BytesIO(docx_bytes),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }

    response = client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 201
    data = response.json()

    assert data["file_type"] == "docx"
    assert "skills" in data["extracted_sections"]
    assert "experience" in data["extracted_sections"]

    client.delete(f"/api/v1/resumes/{data['resume_id']}")


def test_positive_legitimate_multipage_resume():
    """
    Legitimate multi-page PDF resume. Page count alone must not cause rejection.
    """
    p1 = generate_test_pdf_bytes([
        "Senior Architect",
        "Email: architect@enterprise.io",
        "Professional Summary",
        "Experienced software architect with 10+ years designing enterprise platforms.",
        "Technical Skills",
        "Python, Java, Go, Kubernetes, Kafka, Terraform",
    ])
    p2 = generate_test_pdf_bytes([
        "Work Experience",
        "Principal Architect at Enterprise Solutions (2019 - Present)",
        "Led migration of monolith to microservices across 12 engineering teams.",
        "Senior Engineer at Tech Corp (2014 - 2019)",
        "Education",
        "M.S. in Software Engineering, Carnegie Mellon",
    ])

    writer = PdfWriter()
    writer.append(io.BytesIO(p1))
    writer.append(io.BytesIO(p2))
    buf = io.BytesIO()
    writer.write(buf)
    multipage_bytes = buf.getvalue()

    files = {"file": ("multipage_resume.pdf", io.BytesIO(multipage_bytes), "application/pdf")}
    response = client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 201
    data = response.json()

    assert "skills" in data["extracted_sections"]
    assert "experience" in data["extracted_sections"]
    assert "education" in data["extracted_sections"]

    client.delete(f"/api/v1/resumes/{data['resume_id']}")


def test_positive_actual_nitin_resume():
    """
    Tests the actual NITIN_RESUME.pdf file against the upload endpoint.
    Must be accepted with 201 Created and normalized skills.
    """
    if not NITIN_RESUME_PATH.exists():
        return

    with open(NITIN_RESUME_PATH, "rb") as f:
        content = f.read()

    files = {"file": ("NITIN_RESUME.pdf", io.BytesIO(content), "application/pdf")}
    response = client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 201
    data = response.json()

    assert data["filename"] == "NITIN_RESUME.pdf"
    assert data["file_type"] == "pdf"
    assert data["claimed_skills_count"] > 0
    assert "skills" in data["extracted_sections"] or "projects" in data["extracted_sections"]

    client.delete(f"/api/v1/resumes/{data['resume_id']}")


# ---------------------------------------------------------------------------
# NEGATIVE TESTS: Non-resume documents that MUST be rejected (HTTP 422)
# ---------------------------------------------------------------------------


def test_negative_actual_unit_1_ps_pdf():
    """
    The problem statement document Unit_1_PS.pdf:
    A 46-page scanned/presentation PDF containing zero extractable text layer.
    Must be rejected with 422 Unprocessable Entity.
    """
    if not UNIT_1_PS_PATH.exists():
        return

    with open(UNIT_1_PS_PATH, "rb") as f:
        content = f.read()

    files = {"file": ("Unit_1_PS.pdf", io.BytesIO(content), "application/pdf")}
    response = client.post("/api/v1/resumes/upload", files=files)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "no extractable text" in body["error"]["message"].lower()


def test_negative_zero_extractable_text_pdf():
    """
    A genuinely valid PDF container with blank pages and zero extractable text content.
    Must be rejected with HTTP 422.
    """
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    zero_text_pdf = buf.getvalue()

    files = {"file": ("scanned_blank.pdf", io.BytesIO(zero_text_pdf), "application/pdf")}
    response = client.post("/api/v1/resumes/upload", files=files)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "no extractable text" in body["error"]["message"].lower()


def test_negative_whitespace_only_extracted_text():
    """
    A PDF whose extracted text contains only spaces, tabs, and newlines.
    Must be rejected with HTTP 422.
    """
    whitespace_lines = ["   ", "\t\t", "     "]
    pdf_bytes = generate_test_pdf_bytes(whitespace_lines)
    files = {"file": ("whitespace_only.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post("/api/v1/resumes/upload", files=files)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "no extractable text" in body["error"]["message"].lower()


def test_negative_extremely_sparse_text_document():
    """
    A document containing only 1 or 2 words (e.g. 'Hello World').
    Must be rejected with HTTP 422.
    """
    sparse_lines = ["Hello World"]
    pdf_bytes = generate_test_pdf_bytes(sparse_lines)
    files = {"file": ("sparse.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post("/api/v1/resumes/upload", files=files)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "insufficient text" in body["error"]["message"].lower() or "not appear to be a resume" in body["error"]["message"].lower()


def test_negative_arbitrary_pdf_with_english_text_no_resume_signals():
    """
    An arbitrary document with meaningful English text (e.g. a recipe or article)
    but completely lacking resume section headers and candidate profile details.
    Must be rejected with HTTP 422.
    """
    prose_lines = [
        "Grandma's Classic Chocolate Chip Cookies Recipe",
        "Ingredients and Directions for Baking",
        "Preheat the oven to 375 degrees Fahrenheit.",
        "In a large bowl, cream together softened butter, granulated sugar, and brown sugar.",
        "Beat in the eggs one at a time, then stir in vanilla extract.",
        "Gradually blend in the all-purpose flour, baking soda, and a pinch of salt.",
        "Fold in two cups of semisweet chocolate morsels until evenly distributed.",
        "Drop by rounded tablespoonfuls onto ungreased baking sheets.",
        "Bake for nine to eleven minutes until golden brown around the edges.",
        "Allow cookies to cool on the baking sheet for two minutes before transferring to wire racks.",
    ]
    pdf_bytes = generate_test_pdf_bytes(prose_lines)
    files = {"file": ("cookie_recipe.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post("/api/v1/resumes/upload", files=files)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "not appear to be a resume" in body["error"]["message"].lower()


def test_negative_technical_terms_no_resume_structure():
    """
    A technical article or textbook excerpt mentioning programming languages
    and tools (Python, Docker, Kubernetes) but containing zero resume structure
    or candidate identity.
    Must be rejected with HTTP 422 to prevent false skill extraction.
    """
    tech_prose = [
        "Chapter 4: Microservice Deployment Patterns",
        "Containers encapsulate application code along with their runtime dependencies.",
        "Docker is an open-source platform that enables developers to build and package applications.",
        "Kubernetes provides container orchestration, automated scaling, and cluster management.",
        "PostgreSQL serves as a reliable relational database for transactional microservices.",
        "Python and FastAPI provide asynchronous request processing with low latency overhead.",
        "Continuous integration pipelines automatically run automated test suites on every pull request.",
    ]
    pdf_bytes = generate_test_pdf_bytes(tech_prose)
    files = {"file": ("tech_chapter.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post("/api/v1/resumes/upload", files=files)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "not appear to be a resume" in body["error"]["message"].lower()


# ---------------------------------------------------------------------------
# CLEANUP & INTEGRITY TESTS: Ensure rejected uploads leave zero footprint
# ---------------------------------------------------------------------------


def test_rejected_upload_does_not_create_resume_record():
    """
    Verifies that a rejected upload does not create a record in the resumes table.
    """
    db = SessionLocal()
    try:
        initial_resume_count = db.query(Resume).count()

        sparse_lines = ["Invalid Non-Resume"]
        pdf_bytes = generate_test_pdf_bytes(sparse_lines)
        files = {"file": ("should_fail.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        response = client.post("/api/v1/resumes/upload", files=files)
        assert response.status_code == 422

        after_resume_count = db.query(Resume).count()
        assert after_resume_count == initial_resume_count
    finally:
        db.close()


def test_rejected_upload_does_not_create_claimed_skills():
    """
    Verifies that rejected uploads containing technical terms do NOT leak
    or persist candidate claimed skills into user_claimed_skills.
    """
    db = SessionLocal()
    try:
        initial_skills_count = db.query(UserClaimedSkill).count()

        tech_prose = [
            "Technical Article on Systems",
            "Python and PostgreSQL and Docker and Redis are great software tools.",
            "This is an encyclopedia entry about open source software architecture.",
        ]
        pdf_bytes = generate_test_pdf_bytes(tech_prose)
        files = {"file": ("encyclopedia.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        response = client.post("/api/v1/resumes/upload", files=files)
        assert response.status_code == 422

        after_skills_count = db.query(UserClaimedSkill).count()
        assert after_skills_count == initial_skills_count
    finally:
        db.close()


def test_rejected_upload_does_not_leave_orphaned_file():
    """
    Verifies that when post-extraction validation fails, the temporary file
    stored on disk is immediately removed and not orphaned.
    """
    upload_dir = Path(settings.UPLOAD_DIR)
    if not upload_dir.is_absolute():
        upload_dir = Path(__file__).resolve().parent.parent / settings.UPLOAD_DIR

    upload_dir.mkdir(parents=True, exist_ok=True)
    initial_files = set(upload_dir.glob("*.pdf"))

    # Upload invalid document
    sparse_lines = ["No Resume Signal Here"]
    pdf_bytes = generate_test_pdf_bytes(sparse_lines)
    files = {"file": ("orphaned_check.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 422

    after_files = set(upload_dir.glob("*.pdf"))
    new_files = after_files - initial_files
    assert len(new_files) == 0, f"Orphaned files left on disk: {new_files}"
