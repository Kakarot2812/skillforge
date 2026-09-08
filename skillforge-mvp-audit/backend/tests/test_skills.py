import io
import os
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.database import SessionLocal
from app.db.models import Resume, Skill, SkillAlias, UserClaimedSkill
from app.services.skill_extractor import extract_candidate_mentions
from app.services.skill_normalizer import normalize_skills, normalize_string_key
from app.services.skill_service import process_and_persist_resume_skills

client = TestClient(app)


def test_normalize_string_key():
    """Verify alphanumeric key normalization."""
    assert normalize_string_key("React.js") == "reactjs"
    assert normalize_string_key("Postgre-SQL") == "postgresql"
    assert normalize_string_key("C++") == "c++"
    assert normalize_string_key("C#") == "c#"


def test_exact_skill_extraction_and_normalization():
    """
    Requirement A: Exact skill extraction
    Input: 'Python, Docker, PostgreSQL'
    Expected: Python, Docker, PostgreSQL
    """
    db = SessionLocal()
    try:
        sections = {"skills": "Python, Docker, PostgreSQL"}
        candidates = extract_candidate_mentions(sections)
        matches = normalize_skills(db, candidates)

        matched_names = {m.skill.name for m in matches}
        assert "Python" in matched_names
        assert "Docker" in matched_names
        assert "PostgreSQL" in matched_names
        assert len(matches) == 3

        # Requirement G: Confidence range
        for m in matches:
            assert 0.0 <= m.confidence_score <= 1.0
            assert m.confidence_score >= 0.90  # exact canonical match
    finally:
        db.close()


def test_case_normalization():
    """
    Requirement B: Case normalization
    'python', 'PYTHON', 'Python' -> same canonical skill
    """
    db = SessionLocal()
    try:
        for variation in ["python", "PYTHON", "Python"]:
            candidates = [(variation, "skills")]
            matches = normalize_skills(db, candidates)
            assert len(matches) == 1
            assert matches[0].skill.name == "Python"
            assert matches[0].skill.slug == "python"
    finally:
        db.close()


def test_alias_normalization():
    """
    Requirement C: Alias normalization
    'React.js', 'ReactJS' -> React
    'postgres', 'psql' -> PostgreSQL
    """
    db = SessionLocal()
    try:
        for alias in ["React.js", "ReactJS", "react js"]:
            candidates = [(alias, "skills")]
            matches = normalize_skills(db, candidates)
            assert len(matches) == 1, f"Failed for {alias}"
            assert matches[0].skill.name == "React"

        for pg_alias in ["postgres", "psql", "postgre sql"]:
            candidates = [(pg_alias, "skills")]
            matches = normalize_skills(db, candidates)
            assert len(matches) == 1, f"Failed for {pg_alias}"
            assert matches[0].skill.name == "PostgreSQL"
    finally:
        db.close()


def test_multiple_skills_extraction():
    """
    Requirement D: Multiple skills
    'Python, FastAPI, Docker, PostgreSQL, React' -> five canonical skills
    """
    db = SessionLocal()
    try:
        sections = {"skills": "Python, FastAPI, Docker, PostgreSQL, React"}
        candidates = extract_candidate_mentions(sections)
        matches = normalize_skills(db, candidates)

        matched_names = {m.skill.name for m in matches}
        assert matched_names == {"Python", "FastAPI", "Docker", "PostgreSQL", "React"}
        assert len(matches) == 5
    finally:
        db.close()


def test_duplicate_mentions_deduplicated():
    """
    Requirement E: Duplicate mentions
    'Python Python python' -> one canonical user skill
    """
    db = SessionLocal()
    try:
        sections = {
            "skills": "Python, python, PYTHON",
            "projects": "Built REST services in Python",
        }
        candidates = extract_candidate_mentions(sections)
        matches = normalize_skills(db, candidates, full_text_scan="Python python PYTHON")

        matched_names = [m.skill.name for m in matches if m.skill.name == "Python"]
        assert len(matched_names) == 1
    finally:
        db.close()


def test_unknown_skill_not_created():
    """
    Requirement F: Unknown skill
    An unknown technology should NOT automatically create a canonical skill.
    """
    db = SessionLocal()
    try:
        initial_skill_count = db.query(Skill).count()

        sections = {"skills": "SuperFakeFrameworkXYZ, ImaginaryLang123, team, communication"}
        candidates = extract_candidate_mentions(sections)
        matches = normalize_skills(db, candidates)

        assert len(matches) == 0
        final_skill_count = db.query(Skill).count()
        assert final_skill_count == initial_skill_count  # no arbitrary skills inserted
    finally:
        db.close()


def test_resume_upload_skill_persistence_and_association():
    """
    Requirements H & I:
    - Resume upload extracts and normalizes skills
    - user_claimed_skills records are persisted
    - Extracted skills reference the correct resume
    - GET /api/v1/skills/claimed returns the normalized records
    """
    # Create test PDF content
    pdf_lines = [
        "Alex Candidate",
        "Email: alex.candidate@skillforge.test",
        "Technical Skills",
        "Python, React.js, FastAPI, Docker, PostgreSQL, Redis",
        "Professional Experience",
        "Backend Developer at Apex Corp",
        "Projects",
        "Microservices Architecture using Docker Compose and Next.js",
        "Education",
        "B.S. in Computer Science",
    ]

    # Use text stream for PDF
    stream_content = "BT\n/F1 12 Tf\n50 750 Td\n15 TL\n"
    for line in pdf_lines:
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
    pdf_bytes = pdf_str.encode("latin1")

    files = {"file": ("alex_resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post("/api/v1/resumes/upload", files=files)
    assert upload_res.status_code == 201
    upload_data = upload_res.json()

    resume_id = upload_data["resume_id"]
    assert upload_data["claimed_skills_count"] > 0
    claimed_names = {s["skill_name"] for s in upload_data["claimed_skills"]}

    # Verify canonical names extracted (including normalized alias React.js -> React)
    assert "Python" in claimed_names
    assert "React" in claimed_names  # normalized from React.js!
    assert "FastAPI" in claimed_names
    assert "Docker" in claimed_names
    assert "PostgreSQL" in claimed_names

    # Test GET /api/v1/skills/claimed
    get_res = client.get(f"/api/v1/skills/claimed?resume_id={resume_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()

    assert "data" in get_data
    assert "meta" in get_data
    assert get_data["meta"]["total"] >= 5

    api_skill_names = {item["skill_name"] for item in get_data["data"]}
    assert "Python" in api_skill_names
    assert "React" in api_skill_names

    # Requirement H: Verify DB association
    db = SessionLocal()
    try:
        claimed_db = db.query(UserClaimedSkill).filter(UserClaimedSkill.resume_id == uuid.UUID(resume_id)).all()
        assert len(claimed_db) >= 5
        for rec in claimed_db:
            assert str(rec.resume_id) == resume_id
            assert rec.source == "resume"
            assert 0.0 <= rec.confidence_score <= 1.0

        # Cleanup
        resume = db.query(Resume).filter(Resume.id == uuid.UUID(resume_id)).first()
        if resume:
            if os.path.exists(resume.storage_path):
                os.remove(resume.storage_path)
            db.delete(resume)
            db.commit()
    finally:
        db.close()
