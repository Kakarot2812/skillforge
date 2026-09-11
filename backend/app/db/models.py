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
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.config import settings
from app.db.database import Base


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


class MarketJob(Base):
    """
    Persistent representation of an ingested market job posting.
    Post-MVP Phase 1, Checkpoint P1-C.

    Stores normalized job postings ingested from external providers (e.g., Adzuna)
    prior to downstream role classification and skill extraction.
    Isolated from the MVP skill_demand table.
    """
    __tablename__ = "market_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String(64), nullable=False, index=True)
    external_job_id = Column(String(255), nullable=False)
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    company_name = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    category = Column(String(128), nullable=True)
    contract_type = Column(String(64), nullable=True)
    contract_time = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True, index=True)
    redirect_url = Column(String(1024), nullable=True)
    raw_data = Column(JSONB, nullable=False, default=dict)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("source", "external_job_id", name="uq_market_jobs_source_external_job_id"),
    )

    extracted_skills = relationship("MarketJobSkill", back_populates="market_job", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<MarketJob {self.source}:{self.external_job_id} '{self.title}'>"


class MarketJobSkill(Base):
    """
    Association between an ingested market job posting and an extracted canonical skill.
    Post-MVP Phase 1, Checkpoint P1-D.

    Records deterministic taxonomy matches, retaining evidence text snippets
    and matched alias metadata for auditing and provenance.
    """
    __tablename__ = "market_job_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_job_id = Column(UUID(as_uuid=True), ForeignKey("market_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    matched_alias = Column(String(128), nullable=False)
    source_field = Column(String(32), nullable=False)  # 'title' or 'description'
    evidence_text = Column(Text, nullable=True)
    extraction_method = Column(String(64), nullable=False, default="deterministic_taxonomy_match")
    confidence_score = Column(Float, nullable=False, default=1.0)
    extracted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("market_job_id", "skill_id", name="uq_market_job_skills_job_skill"),
    )

    market_job = relationship("MarketJob", back_populates="extracted_skills")
    skill = relationship("Skill")

    def __repr__(self) -> str:
        return f"<MarketJobSkill job={self.market_job_id} skill={self.skill_id} alias='{self.matched_alias}'>"


class MarketSkillDemand(Base):
    """
    Computed market-demand snapshot aggregated from persisted market jobs and extracted skills.
    Post-MVP Phase 1, Checkpoint P1-E.

    Represents live demand computed empirically from current market jobs:
    - job_count: Number of unique market jobs demanding the canonical skill.
    - sample_size: Total number of market jobs in the analyzed source scope.
    - demand_share: Raw ratio (job_count / sample_size).
    - demand_score: Normalized demand score in [0.0, 1.0] mathematically compatible
      with SkillForge demand intelligence.
    - computed_at: Timestamp when this demand snapshot was aggregated.

    Strictly isolated from frozen MVP skill_demand records.
    """
    __tablename__ = "market_skill_demand"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(64), nullable=False, default="adzuna", index=True)
    job_count = Column(Integer, nullable=False, default=0)
    sample_size = Column(Integer, nullable=False)
    demand_share = Column(Float, nullable=False)
    demand_score = Column(Float, nullable=False, index=True)
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("source", "skill_id", name="uq_market_skill_demand_source_skill"),
        CheckConstraint("demand_score >= 0.0 AND demand_score <= 1.0", name="chk_market_skill_demand_score_range"),
        CheckConstraint("demand_share >= 0.0 AND demand_share <= 1.0", name="chk_market_skill_demand_share_range"),
        CheckConstraint("job_count >= 0", name="chk_market_skill_demand_job_count_non_negative"),
        CheckConstraint("sample_size >= 0", name="chk_market_skill_demand_sample_size_non_negative"),
    )

    skill = relationship("Skill")

    def __repr__(self) -> str:
        return f"<MarketSkillDemand source={self.source} skill={self.skill_id} jobs={self.job_count}/{self.sample_size} score={self.demand_score}>"


class MarketSkillDemandSnapshot(Base):
    """
    Immutable historical snapshot of aggregated market demand for a canonical skill.
    Post-MVP Phase 1, Checkpoint P1-F.

    Captures the demand state at an exact snapshot timestamp:
    - job_count: Unique jobs demanding the skill at snapshot time.
    - sample_size: Total jobs evaluated at snapshot time.
    - demand_share: Unrounded proportion (job_count / sample_size).
    - demand_score: Normalized demand score in [0.0, 1.0].
    - snapshot_at: Historical timestamp of this snapshot observation.

    Strictly immutable once written; historical records are never overwritten.
    """
    __tablename__ = "market_skill_demand_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(64), nullable=False, default="adzuna", index=True)
    job_count = Column(Integer, nullable=False)
    sample_size = Column(Integer, nullable=False)
    demand_share = Column(Float, nullable=False)
    demand_score = Column(Float, nullable=False)
    snapshot_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("source", "skill_id", "snapshot_at", name="uq_market_skill_demand_snapshots_source_skill_time"),
        CheckConstraint("demand_score >= 0.0 AND demand_score <= 1.0", name="chk_market_skill_demand_snapshots_score_range"),
        CheckConstraint("demand_share >= 0.0 AND demand_share <= 1.0", name="chk_market_skill_demand_snapshots_share_range"),
        CheckConstraint("job_count >= 0", name="chk_market_skill_demand_snapshots_job_count_non_negative"),
        CheckConstraint("sample_size >= 0", name="chk_market_skill_demand_snapshots_sample_size_non_negative"),
    )

    skill = relationship("Skill")

    def __repr__(self) -> str:
        return f"<MarketSkillDemandSnapshot source={self.source} skill={self.skill_id} at={self.snapshot_at} score={self.demand_score}>"


class MarketSkillDemandGrowth(Base):
    """
    Materialized latest growth comparison between the current and immediately preceding snapshot.
    Post-MVP Phase 1, Checkpoint P1-F.

    Represents the live growth state for a canonical skill within a source scope:
    - previous_snapshot_id: Preceding snapshot reference (or NULL if first snapshot).
    - current_snapshot_id: Latest snapshot reference.
    - previous_demand_score: Score from preceding snapshot (or 0.0).
    - current_demand_score: Score from latest snapshot.
    - growth_rate: Deterministic rate of change.
    - growth_class: Deterministic classification ('RISING', 'STABLE', 'DECLINING').
    - computed_at: Timestamp when growth was evaluated.
    """
    __tablename__ = "market_skill_demand_growth"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(64), nullable=False, default="adzuna", index=True)
    previous_snapshot_id = Column(UUID(as_uuid=True), ForeignKey("market_skill_demand_snapshots.id", ondelete="SET NULL"), nullable=True)
    current_snapshot_id = Column(UUID(as_uuid=True), ForeignKey("market_skill_demand_snapshots.id", ondelete="CASCADE"), nullable=False)
    previous_demand_score = Column(Float, nullable=False)
    current_demand_score = Column(Float, nullable=False)
    growth_rate = Column(Float, nullable=False)
    growth_class = Column(String(16), nullable=False, index=True)
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("source", "skill_id", name="uq_market_skill_demand_growth_source_skill"),
    )

    skill = relationship("Skill")
    previous_snapshot = relationship("MarketSkillDemandSnapshot", foreign_keys=[previous_snapshot_id])
    current_snapshot = relationship("MarketSkillDemandSnapshot", foreign_keys=[current_snapshot_id])

    def __repr__(self) -> str:
        return f"<MarketSkillDemandGrowth source={self.source} skill={self.skill_id} rate={self.growth_rate} class={self.growth_class}>"


class RAGDocument(Base):
    """
    Persistent representation of an approved evidence document for RAG retrieval.
    Post-MVP Phase 2, Checkpoint P3.

    Stores explicitly approved, bounded evidence documents (e.g. verified market summaries,
    deterministic analysis explanations, bounded code artifact snippets).
    Arbitrary raw resumes, entire GitHub repositories, and unrestricted database dumps
    are strictly prohibited from entering this table.
    """
    __tablename__ = "rag_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type = Column(String(32), nullable=False, index=True)
    source_reference = Column(String(512), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    document_metadata = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    chunks = relationship("RAGChunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<RAGDocument {self.id} source_type={self.source_type} title='{self.title}'>"


class RAGChunk(Base):
    """
    Persistent representation of a deterministically chunked evidence segment with pgvector embedding.
    Post-MVP Phase 2, Checkpoint P3.

    Stores bounded text chunks and their local embedding vectors for similarity retrieval.
    Retains explicit provenance, source reference, and canonical skill association.
    """
    __tablename__ = "rag_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("rag_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=False)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="SET NULL"), nullable=True, index=True)
    source_type = Column(String(32), nullable=False, index=True)
    source_reference = Column(String(512), nullable=False, index=True)
    chunk_metadata = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_rag_chunks_document_chunk_index"),
        CheckConstraint("chunk_index >= 0", name="chk_rag_chunks_chunk_index_non_negative"),
    )

    document = relationship("RAGDocument", back_populates="chunks")
    skill = relationship("Skill")

    def __repr__(self) -> str:
        return f"<RAGChunk {self.id} doc={self.document_id} idx={self.chunk_index}>"
