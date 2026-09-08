import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import SessionLocal
from app.db.models import (
    JobRole,
    IndustrySkillDemand,
    Skill,
    User,
    Resume,
    UserClaimedSkill,
    GitHubRepository,
    ProjectEvidence,
    DemonstratedSkill,
    SkillGap,
)

client = TestClient(app)


def test_historical_resume_isolation_user():
    """
    A. Historical resume isolation:
    User has:
      Resume A: HTML claim
      Resume B: Python + Java only
    Request using Resume B.
    Assert: HTML candidate resume_claims == [] and status == MISSING.
    """
    db = SessionLocal()
    user = User(id=uuid.uuid4(), email=f"iso-user-{uuid.uuid4()}@example.com")
    role = db.query(JobRole).filter(JobRole.slug == "frontend-engineer").first()
    assert role is not None, "frontend-engineer role required"
    role_id = role.id

    html_skill = db.query(Skill).filter(Skill.slug == "html").first()
    python_skill = db.query(Skill).filter(Skill.slug == "python").first()
    java_skill = db.query(Skill).filter(Skill.slug == "java").first()
    assert html_skill is not None, "html skill required"
    html_skill_id = html_skill.id

    db.add(user)
    db.commit()

    # Resume A with HTML claim
    resume_a = Resume(
        id=uuid.uuid4(),
        user_id=user.id,
        file_name="Resume_A_Old.pdf",
        file_type="pdf",
        file_size=1024,
        storage_path="/resumes/a.pdf",
    )
    db.add(resume_a)
    db.commit()

    claim_html = UserClaimedSkill(
        id=uuid.uuid4(),
        user_id=user.id,
        resume_id=resume_a.id,
        skill_id=html_skill_id,
        raw_mention="HTML5 Semantic Elements",
        confidence_score=0.9,
    )
    db.add(claim_html)

    # Resume B with Python + Java only (no HTML)
    resume_b = Resume(
        id=uuid.uuid4(),
        user_id=user.id,
        file_name="Resume_B_New.pdf",
        file_type="pdf",
        file_size=2048,
        storage_path="/resumes/b.pdf",
    )
    db.add(resume_b)
    db.commit()

    if python_skill:
        claim_py = UserClaimedSkill(
            id=uuid.uuid4(),
            user_id=user.id,
            resume_id=resume_b.id,
            skill_id=python_skill.id,
            raw_mention="Python 3",
            confidence_score=0.8,
        )
        db.add(claim_py)
    if java_skill:
        claim_java = UserClaimedSkill(
            id=uuid.uuid4(),
            user_id=user.id,
            resume_id=resume_b.id,
            skill_id=java_skill.id,
            raw_mention="Java 17",
            confidence_score=0.8,
        )
        db.add(claim_java)
    db.commit()

    u_id = user.id
    res_b_id = resume_b.id
    res_a_id = resume_a.id
    db.close()

    try:
        # Request HTML evidence scoping to Resume B
        res = client.get(
            f"/api/v1/gaps/{role_id}/skills/{html_skill_id}/evidence"
            f"?location=India&user_id={u_id}&resume_id={res_b_id}"
        )
        assert res.status_code == 200
        data = res.json()["data"]

        # Assert HTML claims are empty and status is MISSING
        assert data["candidate_evidence"]["resume_claims"] == []
        assert data["status"] == "MISSING"
        assert "Missing because" in data["reasoning"]["classification_reason"]

        # Contrasting check: scoping to Resume A returns Resume A's claim
        res_a = client.get(
            f"/api/v1/gaps/{role_id}/skills/{html_skill_id}/evidence"
            f"?location=India&user_id={u_id}&resume_id={res_a_id}"
        )
        assert res_a.status_code == 200
        data_a = res_a.json()["data"]
        assert len(data_a["candidate_evidence"]["resume_claims"]) == 1
        assert data_a["candidate_evidence"]["resume_claims"][0]["resume_id"] == str(res_a_id)
        assert data_a["status"] == "PARTIAL"
    finally:
        db = SessionLocal()
        u = db.query(User).filter(User.id == u_id).first()
        if u:
            db.delete(u)
            db.commit()
        db.close()


def test_evidence_audit_explicit_resume_scope():
    """
    B. Evidence audit explicit resume scope:
    Create multiple historical anonymous resumes with HTML claims.
    Request evidence with the newest resume_id.
    Assert only that resume's claims are returned.
    """
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "frontend-engineer").first()
    role_id = role.id
    html_skill = db.query(Skill).filter(Skill.slug == "html").first()
    html_skill_id = html_skill.id

    # Resume 1: Historical anonymous
    r1 = Resume(
        id=uuid.uuid4(),
        user_id=None,
        file_name="resume_v1.pdf",
        file_type="pdf",
        file_size=1000,
        storage_path="/resumes/v1.pdf",
    )
    # Resume 2: Target anonymous
    r2 = Resume(
        id=uuid.uuid4(),
        user_id=None,
        file_name="resume_v2.pdf",
        file_type="pdf",
        file_size=2000,
        storage_path="/resumes/v2.pdf",
    )
    db.add_all([r1, r2])
    db.commit()

    c1 = UserClaimedSkill(
        id=uuid.uuid4(),
        user_id=None,
        resume_id=r1.id,
        skill_id=html_skill_id,
        raw_mention="HTML 4.01",
        confidence_score=0.7,
    )
    c2 = UserClaimedSkill(
        id=uuid.uuid4(),
        user_id=None,
        resume_id=r2.id,
        skill_id=html_skill_id,
        raw_mention="HTML5 Modern",
        confidence_score=0.95,
    )
    db.add_all([c1, c2])
    db.commit()

    r1_id = r1.id
    r2_id = r2.id
    db.close()

    try:
        # Request with newest resume_id (r2)
        res = client.get(
            f"/api/v1/gaps/{role_id}/skills/{html_skill_id}/evidence"
            f"?location=India&resume_id={r2_id}"
        )
        assert res.status_code == 200
        claims = res.json()["data"]["candidate_evidence"]["resume_claims"]
        assert len(claims) == 1
        assert claims[0]["resume_id"] == str(r2_id)
        assert claims[0]["raw_mention"] == "HTML5 Modern"
        assert claims[0]["resume_file_name"] == "resume_v2.pdf"
    finally:
        db = SessionLocal()
        db.query(UserClaimedSkill).filter(UserClaimedSkill.resume_id.in_([r1_id, r2_id])).delete(synchronize_session=False)
        db.query(Resume).filter(Resume.id.in_([r1_id, r2_id])).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_anonymous_resume_isolation():
    """
    C. Anonymous resume isolation:
    user_id = None
    Multiple resumes exist.
    Request with resume_id = Resume B.
    Assert Resume A claims are NOT returned.
    """
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "frontend-engineer").first()
    role_id = role.id
    html_skill = db.query(Skill).filter(Skill.slug == "html").first()
    html_skill_id = html_skill.id

    anon_a = Resume(
        id=uuid.uuid4(),
        user_id=None,
        file_name="anon_a_with_html.pdf",
        file_type="pdf",
        file_size=1100,
        storage_path="/resumes/anon_a.pdf",
    )
    anon_b = Resume(
        id=uuid.uuid4(),
        user_id=None,
        file_name="anon_b_no_html.pdf",
        file_type="pdf",
        file_size=1200,
        storage_path="/resumes/anon_b.pdf",
    )
    db.add_all([anon_a, anon_b])
    db.commit()

    claim_anon_a = UserClaimedSkill(
        id=uuid.uuid4(),
        user_id=None,
        resume_id=anon_a.id,
        skill_id=html_skill_id,
        raw_mention="HTML from Anon A",
        confidence_score=0.8,
    )
    db.add(claim_anon_a)
    db.commit()

    anon_a_id = anon_a.id
    anon_b_id = anon_b.id
    db.close()

    try:
        # Request scoping to Anon B
        res = client.get(
            f"/api/v1/gaps/{role_id}/skills/{html_skill_id}/evidence"
            f"?location=India&resume_id={anon_b_id}"
        )
        assert res.status_code == 200
        data = res.json()["data"]

        # Anon A's HTML claim must NOT appear
        assert data["candidate_evidence"]["resume_claims"] == []
        assert data["status"] == "MISSING"
    finally:
        db = SessionLocal()
        db.query(UserClaimedSkill).filter(UserClaimedSkill.resume_id.in_([anon_a_id, anon_b_id])).delete(synchronize_session=False)
        db.query(Resume).filter(Resume.id.in_([anon_a_id, anon_b_id])).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_authenticated_idor_protection():
    """
    D. Authenticated IDOR protection:
    User A owns Resume A.
    User B owns Resume B.
    User A requests: user_id=A, resume_id=B.
    Assert: 403 FORBIDDEN.
    """
    db = SessionLocal()
    user_a = User(id=uuid.uuid4(), email=f"idor-a-{uuid.uuid4()}@example.com")
    user_b = User(id=uuid.uuid4(), email=f"idor-b-{uuid.uuid4()}@example.com")
    db.add_all([user_a, user_b])
    db.commit()

    resume_b = Resume(
        id=uuid.uuid4(),
        user_id=user_b.id,
        file_name="user_b_private.pdf",
        file_type="pdf",
        file_size=1500,
        storage_path="/resumes/b.pdf",
    )
    db.add(resume_b)
    db.commit()

    role = db.query(JobRole).filter(JobRole.slug == "frontend-engineer").first()
    role_id = role.id
    html_skill = db.query(Skill).filter(Skill.slug == "html").first()
    html_skill_id = html_skill.id

    u_a_id = user_a.id
    u_b_id = user_b.id
    res_b_id = resume_b.id
    db.close()

    try:
        # User A attempts to access User B's resume evidence
        res = client.get(
            f"/api/v1/gaps/{role_id}/skills/{html_skill_id}/evidence"
            f"?location=India&user_id={u_a_id}&resume_id={res_b_id}"
        )
        assert res.status_code == 403
        assert "Cross-user access denied" in res.json()["error"]["message"]

        # Also verify IDOR on main skill gaps endpoint
        res_gap = client.get(
            f"/api/v1/gaps/{role_id}?location=India&user_id={u_a_id}&resume_id={res_b_id}"
        )
        assert res_gap.status_code == 403

        # Also verify IDOR on priorities endpoint
        res_prio = client.get(
            f"/api/v1/gaps/{role_id}/priorities?location=India&user_id={u_a_id}&resume_id={res_b_id}"
        )
        assert res_prio.status_code == 403
    finally:
        db = SessionLocal()
        for uid in [u_a_id, u_b_id]:
            u = db.query(User).filter(User.id == uid).first()
            if u:
                db.delete(u)
        db.commit()
        db.close()


def test_nonexistent_resume_404():
    """
    E. Nonexistent resume:
    Request a random valid UUID as resume_id.
    Assert: 404 NOT_FOUND.
    """
    fake_resume_id = uuid.uuid4()
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "frontend-engineer").first()
    role_id = role.id
    html_skill = db.query(Skill).filter(Skill.slug == "html").first()
    html_skill_id = html_skill.id
    db.close()

    res = client.get(
        f"/api/v1/gaps/{role_id}/skills/{html_skill_id}/evidence"
        f"?location=India&resume_id={fake_resume_id}"
    )
    assert res.status_code == 404
    assert "not found" in res.json()["error"]["message"].lower()

    # Verify on gaps endpoint as well
    res_gap = client.get(f"/api/v1/gaps/{role_id}?resume_id={fake_resume_id}")
    assert res_gap.status_code == 404


def test_current_candidate_integration_cv_pdf():
    """
    F. Current candidate integration:
    Current resume = CV_.pdf (12045a8f-2097-46d7-a380-4cce843210ca)
    GitHub = krr1ssh-29
    Request HTML evidence.
    Assert:
    - resume claims are empty []
    - NITIN_RESUME.pdf does not appear
    - GitHub artifacts remain scoped to krr1ssh-29
    - classification is MISSING
    """
    cv_resume_id = uuid.UUID("12045a8f-2097-46d7-a380-4cce843210ca")
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "frontend-engineer").first()
    role_id = role.id
    html_skill = db.query(Skill).filter(Skill.slug == "html").first()
    html_skill_id = html_skill.id
    db.close()

    # 1. With explicit resume_id = CV_.pdf
    res = client.get(
        f"/api/v1/gaps/{role_id}/skills/{html_skill_id}/evidence"
        f"?location=India&include_resume=true&include_github=true&username=krr1ssh-29&resume_id={cv_resume_id}"
    )
    assert res.status_code == 200
    data = res.json()["data"]

    # Resume claims must be empty; NITIN_RESUME.pdf must not appear
    assert data["candidate_evidence"]["resume_claims"] == []
    for claim in data["candidate_evidence"]["resume_claims"]:
        assert "NITIN_RESUME" not in (claim.get("resume_file_name") or "")

    # GitHub artifacts remain empty (no HTML in krr1ssh-29 repos)
    assert data["candidate_evidence"]["github_artifacts"] == []
    assert data["status"] == "MISSING"
    assert "Missing because" in data["reasoning"]["classification_reason"]

    # 2. Even WITHOUT resume_id, deterministic fallback selects CV_.pdf (latest unauthenticated resume)
    res_fallback = client.get(
        f"/api/v1/gaps/{role_id}/skills/{html_skill_id}/evidence"
        f"?location=India&include_resume=true&include_github=true&username=krr1ssh-29"
    )
    assert res_fallback.status_code == 200
    data_fb = res_fallback.json()["data"]

    # Deterministic fallback scopes to latest anonymous resume (CV_.pdf, which has no HTML)
    assert data_fb["candidate_evidence"]["resume_claims"] == []
    assert data_fb["status"] == "MISSING"
