import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    BigInteger,
    Boolean,
    Float,
    DateTime,
    ForeignKey,
    func,
    UniqueConstraint,
    CheckConstraint,
    Computed,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.db.database import Base

# Fixed at migration time (see alembic/versions/0012_rag_documents_and_chunks.py
# and app/rag/config.py::RagSettings.RAG_EMBEDDING_DIMENSIONS). Changing this
# requires a new migration that alters the column and a full re-ingest.
RAG_EMBEDDING_DIMENSIONS = 1024


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(128), nullable=True)
    target_role = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    claimed_skills = relationship("UserClaimedSkill", back_populates="user", cascade="all, delete-orphan")
    github_repositories = relationship("GitHubRepository", back_populates="user", cascade="all, delete-orphan")
    project_evidence = relationship("ProjectEvidence", back_populates="user", cascade="all, delete-orphan")
    demonstrated_skills = relationship("DemonstratedSkill", back_populates="user", cascade="all, delete-orphan")
    skill_gaps = relationship("SkillGap", back_populates="user", cascade="all, delete-orphan")
    rag_documents = relationship("RagDocument", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class Skill(Base):
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(128), unique=True, index=True, nullable=False)
    slug = Column(String(128), unique=True, index=True, nullable=False)
    category = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    aliases = relationship("SkillAlias", back_populates="skill", cascade="all, delete-orphan")
    claimed_by_users = relationship("UserClaimedSkill", back_populates="skill", cascade="all, delete-orphan")
    project_evidence = relationship("ProjectEvidence", back_populates="skill", cascade="all, delete-orphan")
    demonstrated_by_users = relationship("DemonstratedSkill", back_populates="skill", cascade="all, delete-orphan")
    industry_demands = relationship("IndustrySkillDemand", back_populates="skill", cascade="all, delete-orphan")
    skill_gaps = relationship("SkillGap", back_populates="skill", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Skill {self.name}>"


class SkillAlias(Base):
    __tablename__ = "skill_aliases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    alias = Column(String(128), nullable=False)
    normalized_alias = Column(String(128), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    skill = relationship("Skill", back_populates="aliases")

    def __repr__(self) -> str:
        return f"<SkillAlias {self.alias} -> {self.skill_id}>"


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(64), nullable=False)
    file_size = Column(Integer, nullable=False)
    storage_path = Column(String(512), nullable=False)
    raw_text = Column(Text, nullable=True)
    parsed_data = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="resumes")
    claimed_skills = relationship("UserClaimedSkill", back_populates="resume", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Resume {self.file_name} ({self.id})>"


class UserClaimedSkill(Base):
    __tablename__ = "user_claimed_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True, index=True)
    source = Column(String(32), nullable=False, default="resume")
    raw_mention = Column(String(128), nullable=True)
    confidence_score = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_user_claimed_skills_user_skill"),
    )

    user = relationship("User", back_populates="claimed_skills")
    skill = relationship("Skill", back_populates="claimed_by_users")
    resume = relationship("Resume", back_populates="claimed_skills")

    def __repr__(self) -> str:
        return f"<UserClaimedSkill {self.raw_mention} (confidence: {self.confidence_score})>"


class GitHubRepository(Base):
    __tablename__ = "github_repositories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    github_repository_id = Column(BigInteger, nullable=True, index=True)
    repo_name = Column(String(128), nullable=False, index=True)
    full_name = Column(String(255), nullable=True, index=True)
    repo_url = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    default_branch = Column(String(64), nullable=True, default="main")
    visibility = Column(String(32), nullable=True, default="public")
    primary_language = Column(String(64), nullable=True)
    is_fork = Column(Boolean, nullable=False, default=False)
    stars_count = Column(Integer, nullable=False, default=0)
    forks_count = Column(Integer, nullable=False, default=0)
    last_pushed_at = Column(DateTime(timezone=True), nullable=True)
    repo_metadata = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    synced_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "repo_url", name="uq_github_repos_user_repo_url"),
    )

    user = relationship("User", back_populates="github_repositories")
    evidence_items = relationship("ProjectEvidence", back_populates="repository", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<GitHubRepository {self.full_name or self.repo_name} ({self.id})>"


class ProjectEvidence(Base):
    __tablename__ = "project_evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    repo_id = Column(UUID(as_uuid=True), ForeignKey("github_repositories.id", ondelete="CASCADE"), nullable=True, index=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_type = Column(String(64), nullable=False, index=True)
    file_path = Column(String(255), nullable=True)
    artifact_name = Column(String(128), nullable=True)
    evidence_description = Column(Text, nullable=True)
    matched_content = Column(Text, nullable=True)
    evidence_metadata = Column(JSONB, nullable=False, default=dict)
    confidence_score = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("repo_id", "skill_id", "evidence_type", "file_path", name="uq_project_evidence_repo_skill_type_path"),
    )

    user = relationship("User", back_populates="project_evidence")
    repository = relationship("GitHubRepository", back_populates="evidence_items")
    skill = relationship("Skill", back_populates="project_evidence")

    @property
    def repository_id(self):
        return self.repo_id

    @property
    def artifact_path(self):
        return self.file_path

    def __repr__(self) -> str:
        return f"<ProjectEvidence {self.evidence_type} ({self.skill_id}) in {self.file_path}>"


class DemonstratedSkill(Base):
    __tablename__ = "demonstrated_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    confidence_score = Column(Float, nullable=False, index=True)
    evidence_level = Column(String(32), nullable=False)
    evidence_count = Column(Integer, nullable=False, default=0)
    repository_count = Column(Integer, nullable=False, default=0)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    skill_metadata = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_demonstrated_skills_user_skill"),
    )

    user = relationship("User", back_populates="demonstrated_skills")
    skill = relationship("Skill", back_populates="demonstrated_by_users")

    def __repr__(self) -> str:
        return f"<DemonstratedSkill {self.skill_id} ({self.evidence_level}: {self.confidence_score})>"


class JobRole(Base):
    __tablename__ = "job_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(128), unique=True, index=True, nullable=False)
    slug = Column(String(128), unique=True, index=True, nullable=False)
    category = Column(String(64), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    skill_demands = relationship("IndustrySkillDemand", back_populates="role", cascade="all, delete-orphan")
    skill_gaps = relationship("SkillGap", back_populates="role", cascade="all, delete-orphan")

    @property
    def name(self) -> str:
        return self.title

    def __repr__(self) -> str:
        return f"<JobRole {self.title} ({self.slug})>"


class IndustrySkillDemand(Base):
    __tablename__ = "skill_demand"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id = Column(UUID(as_uuid=True), ForeignKey("job_roles.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    location = Column(String(64), nullable=False, default="India", index=True)
    sample_size = Column(Integer, nullable=False, default=10000)
    demand_score = Column(Float, nullable=False, index=True)
    growth_rate = Column(Float, nullable=False, default=0.0, index=True)
    data_updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("role_id", "skill_id", "location", name="uq_skill_demand_role_skill_loc"),
        CheckConstraint("demand_score >= 0.0 AND demand_score <= 1.0", name="chk_demand_score_range"),
        CheckConstraint("sample_size > 0", name="chk_sample_size_positive"),
    )

    role = relationship("JobRole", back_populates="skill_demands")
    skill = relationship("Skill", back_populates="industry_demands")

    def __repr__(self) -> str:
        return f"<IndustrySkillDemand role={self.role_id} skill={self.skill_id} score={self.demand_score}>"


# Alias for DATA_MODEL.md naming compatibility
SkillDemand = IndustrySkillDemand


class SkillGap(Base):
    __tablename__ = "skill_gaps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("job_roles.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    location = Column(String(64), nullable=False, default="India", index=True)
    status = Column(String(32), nullable=False, index=True)  # 'STRONG', 'PARTIAL', 'MISSING'
    demand_score = Column(Float, nullable=False, index=True)
    growth_rate = Column(Float, nullable=False, default=0.0)
    claimed = Column(Boolean, nullable=False, default=False)
    claim_confidence = Column(Float, nullable=False, default=0.0)
    demonstrated = Column(Boolean, nullable=False, default=False)
    demonstrated_score = Column(Float, nullable=False, default=0.0)
    evidence_level = Column(String(32), nullable=True)
    evidence_count = Column(Integer, nullable=False, default=0)
    priority_score = Column(Float, nullable=True, index=True)
    priority_level = Column(String(32), nullable=True, index=True)  # 'HIGH', 'MEDIUM', 'LOW'
    scoring_version = Column(String(16), nullable=False, default="v1")
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    gap_metadata = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "skill_id", "location", name="uq_skill_gaps_user_role_skill_loc"),
        CheckConstraint("demand_score >= 0.0 AND demand_score <= 1.0", name="chk_skill_gap_demand_score_range"),
        CheckConstraint("status IN ('STRONG', 'PARTIAL', 'MISSING')", name="chk_skill_gap_status"),
    )

    user = relationship("User", back_populates="skill_gaps")
    role = relationship("JobRole", back_populates="skill_gaps")
    skill = relationship("Skill", back_populates="skill_gaps")

    def __repr__(self) -> str:
        return f"<SkillGap user={self.user_id} role={self.role_id} skill={self.skill_id} status={self.status}>"


class RagDocument(Base):
    """A normalised, versioned unit of RAG evidence (one GitHub artifact, one
    resume, one manually-ingested document, ...). See app/rag/ingestion.py.
    """

    __tablename__ = "rag_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # 'github_repository' | 'project_evidence' | 'resume' | 'manual'
    source_type = Column(String(32), nullable=False, index=True)
    # String form of the source's real PK (or a stable slug for 'manual' docs).
    source_id = Column(String(128), nullable=False)
    # NULL = globally visible corpus (e.g. curated learning resources).
    # Non-NULL = private to that user; retrieval must never leak this cross-user.
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    source_url = Column(String(512), nullable=True)
    content_hash = Column(String(64), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    document_metadata = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("source_type", "source_id", name="uq_rag_documents_source"),
    )

    user = relationship("User", back_populates="rag_documents")
    chunks = relationship("RagChunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<RagDocument {self.source_type}:{self.source_id} v{self.version}>"


class RagChunk(Base):
    """One embeddable/searchable slice of a RagDocument. See app/rag/chunking.py."""

    __tablename__ = "rag_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("rag_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    embedding = Column(Vector(RAG_EMBEDDING_DIMENSIONS), nullable=True)
    # DB-generated (see migration 0012). Computed(..., persisted=True) tells
    # SQLAlchemy this column is server-generated so it is never sent on
    # INSERT/UPDATE (Postgres rejects writes to generated columns) and is
    # instead fetched back via RETURNING after a flush.
    search_vector = Column(TSVECTOR, Computed("to_tsvector('english', content)", persisted=True), nullable=True)
    chunk_metadata = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_rag_chunks_document_index"),
    )

    document = relationship("RagDocument", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<RagChunk {self.document_id}#{self.chunk_index}>"

