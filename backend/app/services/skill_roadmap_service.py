"""
Static Skill Roadmap Service for SkillForge AI.
Phase 3: Static Roadmap Schemas & Service.

Provides domain operations for the curated and canonical static skill roadmaps:
- Roadmap catalog retrieval with deterministic ordering
- Detailed roadmap hierarchy (stages, skills, prerequisites, resources, practice problems)
- Deterministic topological sorting for recommended learning pathways (Kahn's algorithm)
- Single skill retrieval with relationship validation
- User skill learning progress tracking (NOT_STARTED, LEARNING, DONE, SKIPPED)
- User practice problem progress tracking (NOT_STARTED, IN_PROGRESS, COMPLETED)
- User progress summary calculation
- Strict roadmap/skill relationship validation and user isolation
"""

from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Set, Tuple, Union
import uuid
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    LearningResource,
    Roadmap,
    RoadmapPrerequisite,
    RoadmapSkill,
    RoadmapStage,
    User,
    UserPracticeProgress,
    UserRoadmapProgress,
)
from app.schemas.skill_roadmap import (
    LearningResourceItem,
    PracticeProblemItem,
    RoadmapDetailData,
    RoadmapListItem,
    RoadmapPrerequisiteItem,
    RoadmapSkillItem,
    RoadmapStageItem,
    RoadmapSummary,
    UserPracticeProgressItem,
    UserProgressItem,
    UserRoadmapProgressSummary,
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Domain Exceptions
# -----------------------------------------------------------------------------

class SkillRoadmapError(Exception):
    """Base exception for static skill roadmap operations."""
    pass


class RoadmapNotFoundError(SkillRoadmapError):
    """Raised when a requested roadmap cannot be found by ID or slug."""
    pass


class RoadmapSkillNotFoundError(SkillRoadmapError):
    """Raised when a requested skill cannot be found by ID or slug."""
    pass


class RoadmapRelationshipError(SkillRoadmapError):
    """Raised when a skill or problem does not belong to the specified roadmap."""
    pass


class PracticeProblemNotFoundError(SkillRoadmapError):
    """Raised when a practice problem is not found within the specified roadmap skill."""
    pass


class InvalidProgressStatusError(SkillRoadmapError, ValueError):
    """Raised when an invalid progress status string is submitted."""
    pass


class PrerequisiteCycleError(SkillRoadmapError):
    """Raised when a cycle is detected during topological sorting of prerequisites."""
    pass


# -----------------------------------------------------------------------------
# Service Implementation
# -----------------------------------------------------------------------------

class SkillRoadmapService:
    """
    Core domain service for static skill roadmaps catalog, recommendations,
    and user progress tracking.
    """

    ALLOWED_SKILL_STATUSES: Set[str] = {"NOT_STARTED", "LEARNING", "DONE", "SKIPPED"}
    ALLOWED_PRACTICE_STATUSES: Set[str] = {"NOT_STARTED", "IN_PROGRESS", "COMPLETED"}

    # -------------------------------------------------------------------------
    # Catalog
    # -------------------------------------------------------------------------

    def get_roadmap_catalog(self, db: Session) -> List[RoadmapListItem]:
        """
        Retrieves all static roadmaps in the catalog.
        Deterministic ordering: canonical tracks (has_market_data=True) appear first,
        followed by curated tracks, ordered alphabetically by title.
        """
        roadmaps = (
            db.query(Roadmap)
            .options(
                joinedload(Roadmap.stages).joinedload(RoadmapStage.skills)
            )
            .order_by(Roadmap.has_market_data.desc(), Roadmap.title.asc())
            .all()
        )

        catalog_items: List[RoadmapListItem] = []
        for r in roadmaps:
            total_stages = len(r.stages)
            total_skills = sum(len(st.skills) for st in r.stages)
            catalog_items.append(
                RoadmapListItem(
                    id=r.id,
                    role_id=r.role_id,
                    slug=r.slug,
                    title=r.title,
                    domain=r.domain,
                    category=r.category,
                    description=r.description,
                    version=r.version,
                    has_market_data=r.has_market_data,
                    total_stages=total_stages,
                    total_skills=total_skills,
                    last_reviewed=r.last_reviewed,
                )
            )
        return catalog_items

    # -------------------------------------------------------------------------
    # Roadmap Detail
    # -------------------------------------------------------------------------

    def get_roadmap_detail(
        self,
        db: Session,
        roadmap_identifier: Union[UUID, str],
        user_id: Optional[UUID] = None,
        ordering: str = "curated",
    ) -> RoadmapDetailData:
        """
        Retrieves a full roadmap including stages, skills, prerequisites, and learning resources.
        Personalizes with:
        1. User's saved progress state (NOT_STARTED, LEARNING, DONE, SKIPPED).
        2. User's practice problem progress (NOT_STARTED, IN_PROGRESS, COMPLETED).
        3. Deterministic topological sorting for 'recommended' ordering mode.
        """
        normalized_ordering = ordering.strip().lower()
        if normalized_ordering not in {"curated", "recommended"}:
            raise ValueError(f"Invalid ordering '{ordering}'. Allowed values: 'curated', 'recommended'.")

        roadmap = self._resolve_roadmap(db, roadmap_identifier)

        # Load user roadmap progress map (skill_id -> status)
        progress_map: Dict[UUID, str] = {}
        practice_progress_map: Dict[Tuple[UUID, str], str] = {}
        if user_id:
            user_progress_rows = (
                db.query(UserRoadmapProgress)
                .filter(UserRoadmapProgress.user_id == user_id)
                .all()
            )
            progress_map = {row.roadmap_skill_id: row.status for row in user_progress_rows}

            user_practice_rows = (
                db.query(UserPracticeProgress)
                .filter(UserPracticeProgress.user_id == user_id)
                .all()
            )
            practice_progress_map = {
                (row.roadmap_skill_id, row.problem_id): row.status for row in user_practice_rows
            }

        # Load stages ordered by stage_order ASC
        stages = (
            db.query(RoadmapStage)
            .filter(RoadmapStage.roadmap_id == roadmap.id)
            .order_by(RoadmapStage.stage_order.asc())
            .all()
        )

        stage_items: List[RoadmapStageItem] = []
        all_skill_items: List[RoadmapSkillItem] = []

        total_skills_count = 0
        completed_skills_count = 0
        learning_skills_count = 0
        skipped_skills_count = 0
        not_started_skills_count = 0

        prereq_graph: Dict[UUID, Set[UUID]] = {}
        stage_order_map: Dict[UUID, int] = {}

        for stage in stages:
            stage_order_map[stage.id] = stage.stage_order
            skills = (
                db.query(RoadmapSkill)
                .filter(RoadmapSkill.stage_id == stage.id)
                .order_by(RoadmapSkill.skill_order.asc())
                .all()
            )

            stage_skills: List[RoadmapSkillItem] = []
            stage_completed = 0

            for skill in skills:
                total_skills_count += 1
                user_status = progress_map.get(skill.id, "NOT_STARTED")

                if user_status == "DONE":
                    completed_skills_count += 1
                    stage_completed += 1
                elif user_status == "LEARNING":
                    learning_skills_count += 1
                elif user_status == "SKIPPED":
                    skipped_skills_count += 1
                else:
                    not_started_skills_count += 1

                # Prerequisites
                prereq_rows = (
                    db.query(RoadmapPrerequisite, RoadmapSkill)
                    .join(RoadmapSkill, RoadmapPrerequisite.prerequisite_skill_id == RoadmapSkill.id)
                    .filter(RoadmapPrerequisite.roadmap_skill_id == skill.id)
                    .all()
                )
                prereq_items = [
                    RoadmapPrerequisiteItem(
                        skill_id=target.id,
                        skill_name=target.name,
                        skill_slug=target.slug,
                        difficulty=target.difficulty,
                    )
                    for _, target in prereq_rows
                ]
                prereq_graph[skill.id] = {target.id for _, target in prereq_rows}

                # Resources
                resources = (
                    db.query(LearningResource)
                    .filter(LearningResource.roadmap_skill_id == skill.id)
                    .order_by(LearningResource.resource_type.asc(), LearningResource.title.asc())
                    .all()
                )
                resource_items = [
                    LearningResourceItem(
                        id=r.id,
                        resource_type=r.resource_type,
                        title=r.title,
                        url=r.url,
                        description=r.description,
                    )
                    for r in resources
                ]

                # Practice problems
                practice_problems_data = skill.practice_problems or []
                practice_problem_items = [
                    PracticeProblemItem(
                        problem_id=p["problem_id"],
                        title=p["title"],
                        difficulty=p.get("difficulty", "BEGINNER"),
                        order=p.get("order", 1),
                        objective=p.get("objective", ""),
                        problem_statement=p.get("problem_statement", ""),
                        requirements=p.get("requirements", []),
                        concepts_tested=p.get("concepts_tested", []),
                        expected_outcome=p.get("expected_outcome", ""),
                        optional_hints=p.get("optional_hints", []),
                        user_status=practice_progress_map.get((skill.id, p["problem_id"]), "NOT_STARTED"),
                    )
                    for p in practice_problems_data
                ]

                skill_item = RoadmapSkillItem(
                    id=skill.id,
                    stage_id=stage.id,
                    roadmap_id=roadmap.id,
                    canonical_skill_id=skill.canonical_skill_id,
                    name=skill.name,
                    slug=skill.slug,
                    description=skill.description,
                    difficulty=skill.difficulty,
                    skill_order=skill.skill_order,
                    key_topics=skill.key_topics or [],
                    practice_project=skill.practice_project,
                    practice_problems=practice_problem_items,
                    role_relevance=skill.role_relevance,
                    user_status=user_status,
                    prerequisites=prereq_items,
                    resources=resource_items,
                )

                stage_skills.append(skill_item)
                all_skill_items.append(skill_item)

            stage_items.append(
                RoadmapStageItem(
                    id=stage.id,
                    roadmap_id=roadmap.id,
                    name=stage.name,
                    description=stage.description,
                    stage_order=stage.stage_order,
                    total_skills=len(stage_skills),
                    completed_skills=stage_completed,
                    skills=stage_skills,
                )
            )

        progress_percentage = (
            round((completed_skills_count / total_skills_count) * 100, 1)
            if total_skills_count > 0
            else 0.0
        )

        summary = RoadmapSummary(
            total_skills=total_skills_count,
            completed_skills=completed_skills_count,
            learning_skills=learning_skills_count,
            skipped_skills=skipped_skills_count,
            not_started_skills=not_started_skills_count,
            progress_percentage=progress_percentage,
        )

        roadmap_list_item = RoadmapListItem(
            id=roadmap.id,
            role_id=roadmap.role_id,
            slug=roadmap.slug,
            title=roadmap.title,
            domain=roadmap.domain,
            category=roadmap.category,
            description=roadmap.description,
            version=roadmap.version,
            has_market_data=roadmap.has_market_data,
            total_stages=len(stage_items),
            total_skills=total_skills_count,
            last_reviewed=roadmap.last_reviewed,
        )

        recommended_skills = None
        if normalized_ordering == "recommended":
            recommended_skills = self._compute_recommended_ordering(
                roadmap_slug=roadmap.slug,
                all_skills=all_skill_items,
                prereq_graph=prereq_graph,
                stage_order_map=stage_order_map,
            )

        return RoadmapDetailData(
            roadmap=roadmap_list_item,
            ordering=normalized_ordering,
            summary=summary,
            stages=stage_items,
            recommended_skills=recommended_skills,
        )

    # -------------------------------------------------------------------------
    # Topological Sort / Recommended Ordering
    # -------------------------------------------------------------------------

    def _compute_recommended_ordering(
        self,
        roadmap_slug: str,
        all_skills: List[RoadmapSkillItem],
        prereq_graph: Dict[UUID, Set[UUID]],
        stage_order_map: Dict[UUID, int],
    ) -> List[RoadmapSkillItem]:
        """
        Computes a deterministic topological sort respecting all prerequisite constraints using Kahn's algorithm:
        1. Every prerequisite strictly precedes its dependent skill.
        2. Detects cycles: raises PrerequisiteCycleError if a cycle is present.
        3. Deterministic tie-breaking hierarchy (independent of user / skill-gap state):
           - Stage order ASC
           - Skill order ASC
           - String representation of Skill UUID ASC (stable final tie-breaker)
        """
        skill_by_id = {s.id: s for s in all_skills}
        in_degree = {s_id: len(prereqs) for s_id, prereqs in prereq_graph.items()}
        dependents: Dict[UUID, Set[UUID]] = {s_id: set() for s_id in prereq_graph}

        for s_id, prereqs in prereq_graph.items():
            for p_id in prereqs:
                if p_id in dependents:
                    dependents[p_id].add(s_id)

        def tie_break_key(candidate_id: UUID) -> Tuple[int, int, str]:
            skill = skill_by_id[candidate_id]
            stage_order = stage_order_map.get(skill.stage_id, 0)
            return (stage_order, skill.skill_order, str(candidate_id))

        # Kahn's algorithm
        available: Set[UUID] = {s_id for s_id, deg in in_degree.items() if deg == 0}
        ordered_skills: List[RoadmapSkillItem] = []

        while available:
            best_skill_id = min(available, key=tie_break_key)
            available.remove(best_skill_id)
            ordered_skills.append(skill_by_id[best_skill_id])

            for dep_id in dependents.get(best_skill_id, set()):
                in_degree[dep_id] -= 1
                if in_degree[dep_id] == 0:
                    available.add(dep_id)

        # Cycle detection
        if len(ordered_skills) < len(all_skills):
            raise PrerequisiteCycleError(
                f"Prerequisite cycle detected in roadmap '{roadmap_slug}'! "
                f"Topological sort visited {len(ordered_skills)} / {len(all_skills)} skills."
            )

        return ordered_skills

    # -------------------------------------------------------------------------
    # Single Skill Detail
    # -------------------------------------------------------------------------

    def get_roadmap_skill(
        self,
        db: Session,
        roadmap_identifier: Union[UUID, str],
        skill_identifier: Union[UUID, str],
        user_id: Optional[UUID] = None,
    ) -> RoadmapSkillItem:
        """
        Retrieves detail for a single skill within a roadmap.
        Validates that the skill strictly belongs to the specified roadmap.
        """
        roadmap = self._resolve_roadmap(db, roadmap_identifier)
        skill = self._resolve_skill(db, roadmap.id, skill_identifier)

        # Strict relationship verification
        if skill.roadmap_id != roadmap.id:
            raise RoadmapRelationshipError(
                f"Skill '{skill_identifier}' does not belong to roadmap '{roadmap_identifier}'."
            )

        user_status = "NOT_STARTED"
        if user_id:
            progress = (
                db.query(UserRoadmapProgress)
                .filter(
                    UserRoadmapProgress.user_id == user_id,
                    UserRoadmapProgress.roadmap_skill_id == skill.id,
                )
                .first()
            )
            if progress:
                user_status = progress.status

        # Prerequisites
        prereq_rows = (
            db.query(RoadmapPrerequisite, RoadmapSkill)
            .join(RoadmapSkill, RoadmapPrerequisite.prerequisite_skill_id == RoadmapSkill.id)
            .filter(RoadmapPrerequisite.roadmap_skill_id == skill.id)
            .all()
        )
        prereq_items = [
            RoadmapPrerequisiteItem(
                skill_id=target.id,
                skill_name=target.name,
                skill_slug=target.slug,
                difficulty=target.difficulty,
            )
            for _, target in prereq_rows
        ]

        # Resources
        resources = (
            db.query(LearningResource)
            .filter(LearningResource.roadmap_skill_id == skill.id)
            .order_by(LearningResource.resource_type.asc(), LearningResource.title.asc())
            .all()
        )
        resource_items = [
            LearningResourceItem(
                id=r.id,
                resource_type=r.resource_type,
                title=r.title,
                url=r.url,
                description=r.description,
            )
            for r in resources
        ]

        # Practice problems
        practice_progress_map: Dict[str, str] = {}
        if user_id:
            user_practice_rows = (
                db.query(UserPracticeProgress)
                .filter(
                    UserPracticeProgress.user_id == user_id,
                    UserPracticeProgress.roadmap_skill_id == skill.id,
                )
                .all()
            )
            practice_progress_map = {row.problem_id: row.status for row in user_practice_rows}

        practice_problems_data = skill.practice_problems or []
        practice_problem_items = [
            PracticeProblemItem(
                problem_id=p["problem_id"],
                title=p["title"],
                difficulty=p.get("difficulty", "BEGINNER"),
                order=p.get("order", 1),
                objective=p.get("objective", ""),
                problem_statement=p.get("problem_statement", ""),
                requirements=p.get("requirements", []),
                concepts_tested=p.get("concepts_tested", []),
                expected_outcome=p.get("expected_outcome", ""),
                optional_hints=p.get("optional_hints", []),
                user_status=practice_progress_map.get(p["problem_id"], "NOT_STARTED"),
            )
            for p in practice_problems_data
        ]

        return RoadmapSkillItem(
            id=skill.id,
            stage_id=skill.stage_id,
            roadmap_id=roadmap.id,
            canonical_skill_id=skill.canonical_skill_id,
            name=skill.name,
            slug=skill.slug,
            description=skill.description,
            difficulty=skill.difficulty,
            skill_order=skill.skill_order,
            key_topics=skill.key_topics or [],
            practice_project=skill.practice_project,
            practice_problems=practice_problem_items,
            role_relevance=skill.role_relevance,
            user_status=user_status,
            prerequisites=prereq_items,
            resources=resource_items,
        )

    # -------------------------------------------------------------------------
    # Progress Operations
    # -------------------------------------------------------------------------

    def update_user_progress(
        self,
        db: Session,
        user_id: UUID,
        roadmap_identifier: Optional[Union[UUID, str]] = None,
        skill_identifier: Optional[Union[UUID, str]] = None,
        status: Optional[str] = None,
        *,
        skill_id: Optional[Union[UUID, str]] = None,
    ) -> UserProgressItem:
        """
        Updates or creates a user's progress for a specific roadmap skill.
        Validates status against: NOT_STARTED, LEARNING, DONE, SKIPPED.
        Enforces user ownership and relationship constraints.
        Matches Phase 1 database model UserRoadmapProgress.
        Supports both (roadmap_identifier, skill_identifier) and direct skill_id contexts.
        """
        if status is None:
            # Called as update_user_progress(db, user_id, skill_id, status)
            target_skill = roadmap_identifier
            target_status = skill_identifier
            target_roadmap = None
        elif skill_id is not None:
            # Called with skill_id keyword arg
            target_skill = skill_id
            target_status = status
            target_roadmap = roadmap_identifier
        else:
            # Called with roadmap_identifier, skill_identifier, status
            target_skill = skill_identifier
            target_status = status
            target_roadmap = roadmap_identifier

        if not target_status or not isinstance(target_status, str):
            raise InvalidProgressStatusError("Status must be a non-empty string.")

        clean_status = target_status.strip().upper()
        if clean_status not in self.ALLOWED_SKILL_STATUSES:
            raise InvalidProgressStatusError(
                f"Invalid progress status '{target_status}'. Allowed statuses: {', '.join(sorted(self.ALLOWED_SKILL_STATUSES))}."
            )

        if target_roadmap is not None:
            roadmap = self._resolve_roadmap(db, target_roadmap)
            skill = self._resolve_skill(db, roadmap.id, target_skill)
            if skill.roadmap_id != roadmap.id:
                raise RoadmapRelationshipError(
                    f"Skill '{target_skill}' does not belong to roadmap '{target_roadmap}'."
                )
        else:
            skill = self._resolve_skill_direct(db, target_skill)

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with id '{user_id}' not found.")

        progress = (
            db.query(UserRoadmapProgress)
            .filter(
                UserRoadmapProgress.user_id == user_id,
                UserRoadmapProgress.roadmap_skill_id == skill.id,
            )
            .first()
        )

        now = datetime.now(timezone.utc)
        if progress:
            progress.status = clean_status
            progress.updated_at = now
        else:
            progress = UserRoadmapProgress(
                id=uuid.uuid4(),
                user_id=user_id,
                roadmap_skill_id=skill.id,
                status=clean_status,
                created_at=now,
                updated_at=now,
            )
            db.add(progress)

        db.commit()
        db.refresh(progress)

        return UserProgressItem(
            id=progress.id,
            user_id=progress.user_id,
            roadmap_skill_id=progress.roadmap_skill_id,
            status=progress.status,
            created_at=progress.created_at,
            updated_at=progress.updated_at,
        )

    def get_user_roadmap_progress(
        self,
        db: Session,
        user_id: UUID,
        roadmap_id: Optional[Union[UUID, str]] = None,
    ) -> Dict[UUID, str]:
        """
        Retrieves a map of {skill_id: status} for all skills tracked by the user.
        Optionally filtered to a specific roadmap.
        """
        query = db.query(UserRoadmapProgress).filter(UserRoadmapProgress.user_id == user_id)
        if roadmap_id:
            resolved_roadmap = self._resolve_roadmap(db, roadmap_id)
            query = query.join(RoadmapSkill, UserRoadmapProgress.roadmap_skill_id == RoadmapSkill.id).filter(
                RoadmapSkill.roadmap_id == resolved_roadmap.id
            )
        rows = query.all()
        return {r.roadmap_skill_id: r.status for r in rows}

    def update_user_practice_progress(
        self,
        db: Session,
        user_id: UUID,
        roadmap_identifier: Optional[Union[UUID, str]] = None,
        skill_identifier: Optional[Union[UUID, str]] = None,
        problem_id: Optional[str] = None,
        status: Optional[str] = None,
        *,
        skill_id: Optional[Union[UUID, str]] = None,
    ) -> UserPracticeProgressItem:
        """
        Updates or creates a user's progress for a specific practice problem in a skill.
        Validates status against: NOT_STARTED, IN_PROGRESS, COMPLETED.
        Sets completed_at when transitioning to COMPLETED, and clears it when transitioning away.
        Matches Phase 1 database model UserPracticeProgress.
        Supports both (roadmap_identifier, skill_identifier) and direct skill_id contexts.
        """
        if status is None:
            # Called as update_user_practice_progress(db, user_id, skill_id, problem_id, status)
            target_skill = roadmap_identifier
            target_problem = skill_identifier
            target_status = problem_id
            target_roadmap = None
        elif skill_id is not None:
            # Called with skill_id keyword arg
            target_skill = skill_id
            target_problem = problem_id
            target_status = status
            target_roadmap = roadmap_identifier
        else:
            # Called with roadmap_identifier, skill_identifier, problem_id, status
            target_skill = skill_identifier
            target_problem = problem_id
            target_status = status
            target_roadmap = roadmap_identifier

        if not target_status or not isinstance(target_status, str):
            raise InvalidProgressStatusError("Status must be a non-empty string.")

        clean_status = target_status.strip().upper()
        if clean_status not in self.ALLOWED_PRACTICE_STATUSES:
            raise InvalidProgressStatusError(
                f"Invalid practice problem status '{target_status}'. Allowed statuses: {', '.join(sorted(self.ALLOWED_PRACTICE_STATUSES))}."
            )

        if target_roadmap is not None:
            roadmap = self._resolve_roadmap(db, target_roadmap)
            skill = self._resolve_skill(db, roadmap.id, target_skill)
            if skill.roadmap_id != roadmap.id:
                raise RoadmapRelationshipError(
                    f"Skill '{target_skill}' does not belong to roadmap '{target_roadmap}'."
                )
        else:
            skill = self._resolve_skill_direct(db, target_skill)

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with id '{user_id}' not found.")

        # Validate that target_problem exists in skill.practice_problems
        problems = skill.practice_problems or []
        valid_prob_ids = {p.get("problem_id") for p in problems if isinstance(p, dict)}
        if valid_prob_ids and target_problem not in valid_prob_ids:
            raise PracticeProblemNotFoundError(
                f"Practice problem '{target_problem}' not found in skill '{skill.name}'."
            )

        progress = (
            db.query(UserPracticeProgress)
            .filter(
                UserPracticeProgress.user_id == user_id,
                UserPracticeProgress.roadmap_skill_id == skill.id,
                UserPracticeProgress.problem_id == target_problem,
            )
            .first()
        )

        now = datetime.now(timezone.utc)
        completed_at = now if clean_status == "COMPLETED" else None

        if progress:
            progress.status = clean_status
            progress.updated_at = now
            if clean_status == "COMPLETED":
                if not progress.completed_at:
                    progress.completed_at = now
            else:
                progress.completed_at = None
        else:
            progress = UserPracticeProgress(
                id=uuid.uuid4(),
                user_id=user_id,
                roadmap_skill_id=skill.id,
                problem_id=target_problem,
                status=clean_status,
                completed_at=completed_at,
                created_at=now,
                updated_at=now,
            )
            db.add(progress)

        db.commit()
        db.refresh(progress)

        return UserPracticeProgressItem(
            id=progress.id,
            user_id=progress.user_id,
            roadmap_skill_id=progress.roadmap_skill_id,
            problem_id=progress.problem_id,
            status=progress.status,
            completed_at=progress.completed_at,
            created_at=progress.created_at,
            updated_at=progress.updated_at,
        )

    def get_user_practice_progress_map(
        self,
        db: Session,
        user_id: UUID,
        skill_id: Optional[UUID] = None,
    ) -> Dict[Tuple[UUID, str], str]:
        """
        Retrieves practice progress mapping for a user: {(skill_id, problem_id): status}.
        """
        query = db.query(UserPracticeProgress).filter(UserPracticeProgress.user_id == user_id)
        if skill_id:
            query = query.filter(UserPracticeProgress.roadmap_skill_id == skill_id)
        rows = query.all()
        return {(r.roadmap_skill_id, r.problem_id): r.status for r in rows}

    def get_user_roadmap_summary(
        self,
        db: Session,
        user_id: UUID,
        roadmap_identifier: Union[UUID, str],
    ) -> UserRoadmapProgressSummary:
        """
        Calculates aggregate user progress across an entire roadmap:
        skill completion counts and practice problem completion counts.
        """
        roadmap = self._resolve_roadmap(db, roadmap_identifier)
        skills = (
            db.query(RoadmapSkill)
            .filter(RoadmapSkill.roadmap_id == roadmap.id)
            .all()
        )

        skill_ids = [s.id for s in skills]
        total_skills = len(skills)
        total_practice_problems = sum(len(s.practice_problems or []) for s in skills)

        if total_skills == 0:
            return UserRoadmapProgressSummary(
                roadmap_id=roadmap.id,
                total_skills=0,
                completed_skills=0,
                learning_skills=0,
                skipped_skills=0,
                not_started_skills=0,
                progress_percentage=0.0,
                total_practice_problems=0,
                completed_practice_problems=0,
            )

        progress_rows = (
            db.query(UserRoadmapProgress)
            .filter(
                UserRoadmapProgress.user_id == user_id,
                UserRoadmapProgress.roadmap_skill_id.in_(skill_ids),
            )
            .all()
        )
        progress_dict = {p.roadmap_skill_id: p.status for p in progress_rows}

        completed = sum(1 for s in progress_dict.values() if s == "DONE")
        learning = sum(1 for s in progress_dict.values() if s == "LEARNING")
        skipped = sum(1 for s in progress_dict.values() if s == "SKIPPED")
        not_started = total_skills - (completed + learning + skipped)

        progress_pct = round((completed / total_skills) * 100, 1) if total_skills > 0 else 0.0

        practice_rows = (
            db.query(UserPracticeProgress)
            .filter(
                UserPracticeProgress.user_id == user_id,
                UserPracticeProgress.roadmap_skill_id.in_(skill_ids),
                UserPracticeProgress.status == "COMPLETED",
            )
            .all()
        )
        completed_practice_problems = len(practice_rows)

        return UserRoadmapProgressSummary(
            roadmap_id=roadmap.id,
            total_skills=total_skills,
            completed_skills=completed,
            learning_skills=learning,
            skipped_skills=skipped,
            not_started_skills=not_started,
            progress_percentage=progress_pct,
            total_practice_problems=total_practice_problems,
            completed_practice_problems=completed_practice_problems,
        )

    # -------------------------------------------------------------------------
    # Internal Resolvers
    # -------------------------------------------------------------------------

    def _resolve_roadmap(self, db: Session, identifier: Union[UUID, str]) -> Roadmap:
        """Resolves a Roadmap record by UUID or slug."""
        if isinstance(identifier, UUID):
            roadmap = db.query(Roadmap).filter(Roadmap.id == identifier).first()
        else:
            try:
                parsed_uuid = UUID(str(identifier))
                roadmap = db.query(Roadmap).filter(Roadmap.id == parsed_uuid).first()
            except (ValueError, AttributeError):
                roadmap = db.query(Roadmap).filter(Roadmap.slug == str(identifier)).first()

        if not roadmap:
            raise RoadmapNotFoundError(f"Roadmap '{identifier}' not found.")
        return roadmap

    def _resolve_skill(
        self,
        db: Session,
        roadmap_id: UUID,
        identifier: Union[UUID, str],
    ) -> RoadmapSkill:
        """
        Resolves a RoadmapSkill record by UUID or slug.
        Validates whether the skill exists anywhere in the database and whether
        it belongs to the specified roadmap.
        """
        skill = None
        if isinstance(identifier, UUID):
            skill = db.query(RoadmapSkill).filter(RoadmapSkill.id == identifier).first()
        else:
            try:
                parsed_uuid = UUID(str(identifier))
                skill = db.query(RoadmapSkill).filter(RoadmapSkill.id == parsed_uuid).first()
            except (ValueError, AttributeError):
                # Try by slug within roadmap first
                skill = (
                    db.query(RoadmapSkill)
                    .filter(RoadmapSkill.slug == str(identifier), RoadmapSkill.roadmap_id == roadmap_id)
                    .first()
                )
                if not skill:
                    # Check if skill slug exists anywhere in database
                    skill = db.query(RoadmapSkill).filter(RoadmapSkill.slug == str(identifier)).first()

        if not skill:
            raise RoadmapSkillNotFoundError(
                f"Roadmap skill '{identifier}' not found in roadmap '{roadmap_id}'."
            )

        if skill.roadmap_id != roadmap_id:
            raise RoadmapRelationshipError(
                f"Skill '{identifier}' does not belong to roadmap '{roadmap_id}'."
            )

        return skill

    def _resolve_skill_direct(
        self,
        db: Session,
        identifier: Union[UUID, str],
    ) -> RoadmapSkill:
        """
        Resolves a RoadmapSkill record by UUID or slug without restricting to a specific roadmap.
        Used by user progress endpoints where skill_id is passed directly in the path.
        """
        skill = None
        if isinstance(identifier, UUID):
            skill = db.query(RoadmapSkill).filter(RoadmapSkill.id == identifier).first()
        else:
            try:
                parsed_uuid = UUID(str(identifier))
                skill = db.query(RoadmapSkill).filter(RoadmapSkill.id == parsed_uuid).first()
            except (ValueError, AttributeError):
                skill = db.query(RoadmapSkill).filter(RoadmapSkill.slug == str(identifier)).first()

        if not skill:
            raise RoadmapSkillNotFoundError(
                f"Roadmap skill '{identifier}' not found."
            )

        return skill


skill_roadmap_service = SkillRoadmapService()
