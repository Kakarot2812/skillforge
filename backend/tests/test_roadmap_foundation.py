"""
Test suite for Phase 1: Database Foundation of the Static Skill Roadmap.
Validates:
1. All 7 static roadmap models exist and inherit properly from Base.
2. Table names, column structures, and constraints match specification.
3. Relationships on User, Skill, and JobRole are correctly configured.
4. Export contract in app.db.__init__ includes all 7 models.
5. Alembic migration 0021_skill_roadmaps has valid metadata and revision chain.
6. Existing P4 / P5 models remain unmodified and intact.
"""

import importlib
import pytest
from sqlalchemy import inspect
from app.db.database import Base
from app.db import (
    Roadmap,
    RoadmapStage,
    RoadmapSkill,
    RoadmapPrerequisite,
    LearningResource,
    UserRoadmapProgress,
    UserPracticeProgress,
    User,
    Skill,
    JobRole,
)
from app.db.models import (
    CandidateRoadmap,
    RoadmapMilestone,
    MilestoneVerification,
    SkillGap,
)


def test_models_exist_and_subclass_base():
    models = [
        Roadmap,
        RoadmapStage,
        RoadmapSkill,
        RoadmapPrerequisite,
        LearningResource,
        UserRoadmapProgress,
        UserPracticeProgress,
    ]
    for model in models:
        assert issubclass(model, Base), f"{model.__name__} must inherit from Base"


def test_table_names():
    expected = {
        Roadmap: "roadmaps",
        RoadmapStage: "roadmap_stages",
        RoadmapSkill: "roadmap_skills",
        RoadmapPrerequisite: "roadmap_prerequisites",
        LearningResource: "learning_resources",
        UserRoadmapProgress: "user_roadmap_progress",
        UserPracticeProgress: "user_practice_progress",
    }
    for model, expected_name in expected.items():
        assert model.__tablename__ == expected_name, f"Expected {expected_name}, got {model.__tablename__}"


def test_roadmap_model_columns():
    mapper = inspect(Roadmap)
    col_names = {c.key for c in mapper.columns}
    required = {
        "id", "role_id", "slug", "title", "domain", "category",
        "description", "version", "last_reviewed", "has_market_data",
        "created_at", "updated_at",
    }
    assert required.issubset(col_names), f"Missing columns in Roadmap: {required - col_names}"


def test_roadmap_stage_model_columns():
    mapper = inspect(RoadmapStage)
    col_names = {c.key for c in mapper.columns}
    required = {"id", "roadmap_id", "name", "description", "stage_order", "created_at"}
    assert required.issubset(col_names), f"Missing columns in RoadmapStage: {required - col_names}"


def test_roadmap_skill_model_columns():
    mapper = inspect(RoadmapSkill)
    col_names = {c.key for c in mapper.columns}
    required = {
        "id", "stage_id", "roadmap_id", "canonical_skill_id", "name", "slug",
        "description", "difficulty", "skill_order", "key_topics", "practice_project",
        "practice_problems", "role_relevance", "created_at",
    }
    assert required.issubset(col_names), f"Missing columns in RoadmapSkill: {required - col_names}"


def test_roadmap_prerequisite_columns():
    mapper = inspect(RoadmapPrerequisite)
    col_names = {c.key for c in mapper.columns}
    required = {"id", "roadmap_skill_id", "prerequisite_skill_id", "created_at"}
    assert required.issubset(col_names), f"Missing columns in RoadmapPrerequisite: {required - col_names}"


def test_learning_resource_columns():
    mapper = inspect(LearningResource)
    col_names = {c.key for c in mapper.columns}
    required = {"id", "roadmap_skill_id", "resource_type", "title", "url", "description", "created_at"}
    assert required.issubset(col_names), f"Missing columns in LearningResource: {required - col_names}"


def test_user_roadmap_progress_columns():
    mapper = inspect(UserRoadmapProgress)
    col_names = {c.key for c in mapper.columns}
    required = {"id", "user_id", "roadmap_skill_id", "status", "created_at", "updated_at"}
    assert required.issubset(col_names), f"Missing columns in UserRoadmapProgress: {required - col_names}"


def test_user_practice_progress_columns():
    mapper = inspect(UserPracticeProgress)
    col_names = {c.key for c in mapper.columns}
    required = {"id", "user_id", "roadmap_skill_id", "problem_id", "status", "completed_at", "created_at", "updated_at"}
    assert required.issubset(col_names), f"Missing columns in UserPracticeProgress: {required - col_names}"


def test_relationships_on_existing_models():
    user_rel = inspect(User).relationships
    assert "roadmap_progress" in user_rel, "User must have roadmap_progress relationship"
    assert "practice_progress" in user_rel, "User must have practice_progress relationship"
    assert "roadmaps" in user_rel, "User must retain P4 roadmaps relationship"

    skill_rel = inspect(Skill).relationships
    assert "roadmap_skills" in skill_rel, "Skill must have roadmap_skills relationship"

    job_role_rel = inspect(JobRole).relationships
    assert "roadmaps" in job_role_rel, "JobRole must have roadmaps relationship"


def test_p4_p5_models_intact():
    assert CandidateRoadmap.__tablename__ == "candidate_roadmaps"
    assert RoadmapMilestone.__tablename__ == "roadmap_milestones"
    assert MilestoneVerification.__tablename__ == "milestone_verifications"
    assert SkillGap.__tablename__ == "skill_gaps"


def test_alembic_migration_metadata():
    spec = importlib.util.spec_from_file_location(
        "migration_0021",
        r"alembic/versions/0021_skill_roadmaps_and_practice_problems.py"
    )
    migration_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration_mod)

    assert migration_mod.revision == "0021_skill_roadmaps"
    assert migration_mod.down_revision == "0020_user_profiles"
    assert callable(migration_mod.upgrade)
    assert callable(migration_mod.downgrade)


def test_sqlalchemy_mappers_configure_cleanly():
    from sqlalchemy.orm import configure_mappers
    # This will raise an exception if any relationship or mapper configuration is invalid
    configure_mappers()


def test_in_memory_model_instantiation():
    import uuid

    user = User(email="test_roadmap@example.com")
    roadmap = Roadmap(
        title="Full Stack Engineering",
        slug="full-stack-engineering",
        domain="Full Stack Engineering",
        category="Engineering",
        description="Comprehensive full stack path.",
    )
    stage = RoadmapStage(
        roadmap=roadmap,
        name="Frontend Fundamentals",
        stage_order=1,
    )
    skill = RoadmapSkill(
        roadmap=roadmap,
        stage=stage,
        name="TypeScript",
        slug="typescript",
        description="Strongly typed JavaScript.",
        difficulty="INTERMEDIATE",
        skill_order=1,
        key_topics=["Interfaces", "Generics"],
        practice_problems=[{"id": "prob_ts_1", "title": "Type Narrowing"}],
    )
    res = LearningResource(
        roadmap_skill=skill,
        resource_type="DOCUMENTATION",
        title="TypeScript Handbook",
        url="https://www.typescriptlang.org/docs/",
        description="Official TS Docs",
    )
    user_prog = UserRoadmapProgress(
        user=user,
        roadmap_skill=skill,
        status="LEARNING",
    )
    practice_prog = UserPracticeProgress(
        user=user,
        roadmap_skill=skill,
        problem_id="prob_ts_1",
        status="COMPLETED",
    )

    assert skill in stage.skills
    assert stage in roadmap.stages
    assert res in skill.resources
    assert user_prog.user == user
    assert user_prog.roadmap_skill == skill
    assert practice_prog.user == user
    assert practice_prog.roadmap_skill == skill
    assert user_prog in user.roadmap_progress
    assert practice_prog in user.practice_progress

