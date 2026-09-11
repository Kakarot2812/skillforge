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
    roadmap_progress = relationship("UserRoadmapProgress", back_populates="user", cascade="all, delete-orphan")
    practice_progress = relationship("UserPracticeProgress", back_populates="user", cascade="all, delete-orphan")

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
    roadmap_skills = relationship("RoadmapSkill", back_populates="canonical_skill")

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
    roadmaps = relationship("Roadmap", back_populates="role")

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


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id = Column(UUID(as_uuid=True), ForeignKey("job_roles.id", ondelete="SET NULL"), nullable=True, index=True)
    slug = Column(String(128), unique=True, index=True, nullable=False)
    title = Column(String(128), nullable=False)
    domain = Column(String(128), nullable=False, index=True)
    category = Column(String(64), nullable=False)
    description = Column(Text, nullable=False)
    version = Column(String(32), nullable=False, default="v1.0")
    last_reviewed = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    has_market_data = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    role = relationship("JobRole", back_populates="roadmaps")
    stages = relationship("RoadmapStage", back_populates="roadmap", cascade="all, delete-orphan", order_by="RoadmapStage.stage_order")
    skills = relationship("RoadmapSkill", back_populates="roadmap", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Roadmap {self.title} ({self.slug})>"


class RoadmapStage(Base):
    __tablename__ = "roadmap_stages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    roadmap_id = Column(UUID(as_uuid=True), ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    stage_order = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("roadmap_id", "stage_order", name="uq_roadmap_stages_roadmap_stage_order"),
    )

    roadmap = relationship("Roadmap", back_populates="stages")
    skills = relationship("RoadmapSkill", back_populates="stage", cascade="all, delete-orphan", order_by="RoadmapSkill.skill_order")

    def __repr__(self) -> str:
        return f"<RoadmapStage {self.name} (order: {self.stage_order})>"


class RoadmapSkill(Base):
    __tablename__ = "roadmap_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stage_id = Column(UUID(as_uuid=True), ForeignKey("roadmap_stages.id", ondelete="CASCADE"), nullable=False, index=True)
    roadmap_id = Column(UUID(as_uuid=True), ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False, index=True)
    canonical_skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(128), nullable=False)
    slug = Column(String(128), nullable=False, index=True)
    description = Column(Text, nullable=False)
    difficulty = Column(String(32), nullable=False, default="BEGINNER")
    skill_order = Column(Integer, nullable=False)
    key_topics = Column(JSONB, nullable=False, default=list)
    practice_project = Column(Text, nullable=True)
    practice_problems = Column(JSONB, nullable=False, default=list)
    role_relevance = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("stage_id", "skill_order", name="uq_roadmap_skills_stage_order"),
        CheckConstraint("difficulty IN ('BEGINNER', 'INTERMEDIATE', 'ADVANCED')", name="chk_roadmap_skill_difficulty"),
    )

    stage = relationship("RoadmapStage", back_populates="skills")
    roadmap = relationship("Roadmap", back_populates="skills")
    canonical_skill = relationship("Skill", back_populates="roadmap_skills")
    resources = relationship("LearningResource", back_populates="roadmap_skill", cascade="all, delete-orphan")
    user_progress = relationship("UserRoadmapProgress", back_populates="roadmap_skill", cascade="all, delete-orphan")
    practice_progress = relationship("UserPracticeProgress", back_populates="roadmap_skill", cascade="all, delete-orphan")

    prerequisites = relationship(
        "RoadmapPrerequisite",
        foreign_keys="RoadmapPrerequisite.roadmap_skill_id",
        back_populates="roadmap_skill",
        cascade="all, delete-orphan",
    )
    dependents = relationship(
        "RoadmapPrerequisite",
        foreign_keys="RoadmapPrerequisite.prerequisite_skill_id",
        back_populates="prerequisite_skill",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<RoadmapSkill {self.name} ({self.difficulty})>"


class RoadmapPrerequisite(Base):
    __tablename__ = "roadmap_prerequisites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    roadmap_skill_id = Column(UUID(as_uuid=True), ForeignKey("roadmap_skills.id", ondelete="CASCADE"), nullable=False, index=True)
    prerequisite_skill_id = Column(UUID(as_uuid=True), ForeignKey("roadmap_skills.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("roadmap_skill_id", "prerequisite_skill_id", name="uq_roadmap_prereqs_skill_prereq"),
    )

    roadmap_skill = relationship("RoadmapSkill", foreign_keys=[roadmap_skill_id], back_populates="prerequisites")
    prerequisite_skill = relationship("RoadmapSkill", foreign_keys=[prerequisite_skill_id], back_populates="dependents")

    def __repr__(self) -> str:
        return f"<RoadmapPrerequisite {self.roadmap_skill_id} requires {self.prerequisite_skill_id}>"


class LearningResource(Base):
    __tablename__ = "learning_resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    roadmap_skill_id = Column(UUID(as_uuid=True), ForeignKey("roadmap_skills.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_type = Column(String(32), nullable=False)  # 'DOCUMENTATION', 'YOUTUBE'
    title = Column(String(255), nullable=False)
    url = Column(String(512), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("resource_type IN ('DOCUMENTATION', 'YOUTUBE')", name="chk_learning_resource_type"),
    )

    roadmap_skill = relationship("RoadmapSkill", back_populates="resources")

    def __repr__(self) -> str:
        return f"<LearningResource {self.resource_type}: {self.title}>"


class UserRoadmapProgress(Base):
    __tablename__ = "user_roadmap_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    roadmap_skill_id = Column(UUID(as_uuid=True), ForeignKey("roadmap_skills.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="NOT_STARTED", index=True)  # 'NOT_STARTED', 'LEARNING', 'DONE', 'SKIPPED'
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "roadmap_skill_id", name="uq_user_roadmap_progress_user_skill"),
        CheckConstraint("status IN ('NOT_STARTED', 'LEARNING', 'DONE', 'SKIPPED')", name="chk_user_roadmap_status"),
    )

    user = relationship("User", back_populates="roadmap_progress")
    roadmap_skill = relationship("RoadmapSkill", back_populates="user_progress")

    def __repr__(self) -> str:
        return f"<UserRoadmapProgress user={self.user_id} skill={self.roadmap_skill_id} status={self.status}>"


class UserPracticeProgress(Base):
    __tablename__ = "user_practice_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    roadmap_skill_id = Column(UUID(as_uuid=True), ForeignKey("roadmap_skills.id", ondelete="CASCADE"), nullable=False, index=True)
    problem_id = Column(String(128), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="NOT_STARTED", index=True)  # 'NOT_STARTED', 'IN_PROGRESS', 'COMPLETED'
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "roadmap_skill_id", "problem_id", name="uq_user_practice_progress_user_skill_prob"),
        CheckConstraint("status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED')", name="chk_user_practice_status"),
    )

    user = relationship("User", back_populates="practice_progress")
    roadmap_skill = relationship("RoadmapSkill", back_populates="practice_progress")

    def __repr__(self) -> str:
        return f"<UserPracticeProgress user={self.user_id} skill={self.roadmap_skill_id} problem={self.problem_id} status={self.status}>"



