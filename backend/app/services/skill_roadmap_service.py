import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    Roadmap,
    RoadmapStage,
    RoadmapSkill,
    RoadmapPrerequisite,
    LearningResource,
    UserRoadmapProgress,
    UserPracticeProgress,
    SkillGap,
    IndustrySkillDemand,
    User,
)
from app.schemas.skill_roadmap import (
    LearningResourceItem,
    PracticeProblemItem,
    RoadmapListItem,
    RoadmapPrerequisiteItem,
    RoadmapSkillItem,
    RoadmapStageItem,
    RoadmapSummary,
    RoadmapDetailData,
    UserProgressItem,
    UserPracticeProgressItem,
)


class RoadmapService:
    def get_roadmaps_catalog(self, db: Session) -> List[RoadmapListItem]:
        """
        Retrieves all roadmaps in the catalog.
        Canonical roles with verified market data appear first, followed by curated tracks.
        """
        roadmaps = (
            db.query(Roadmap)
            .options(
                joinedload(Roadmap.stages).joinedload(RoadmapStage.skills)
            )
            .order_by(Roadmap.has_market_data.desc(), Roadmap.title.asc())
            .all()
        )

        catalog_items = []
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

    def get_roadmap_detail(
        self,
        db: Session,
        roadmap_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        ordering: str = "curated",
    ) -> RoadmapDetailData:
        """
        Retrieves a full roadmap including stages, skills, prerequisites, and learning resources.
        Personalizes with:
        1. User's saved progress state (NOT_STARTED, LEARNING, DONE, SKIPPED).
        2. Skill gap classification and priority scores for canonical roles.
        3. Deterministic topological sorting for 'recommended' ordering mode.
        """
        roadmap = (
            db.query(Roadmap)
            .filter(Roadmap.id == roadmap_id)
            .first()
        )
        if not roadmap:
            raise KeyError(f"Roadmap with id '{roadmap_id}' not found.")

        # Load user roadmap progress map (skill_id -> status)
        progress_map: Dict[uuid.UUID, str] = {}
        practice_progress_map: Dict[Tuple[uuid.UUID, str], str] = {}
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
            practice_progress_map = {(row.roadmap_skill_id, row.problem_id): row.status for row in user_practice_rows}

        # Load candidate skill gaps if canonical role
        gap_map: Dict[uuid.UUID, SkillGap] = {}
        demand_map: Dict[uuid.UUID, float] = {}

        if roadmap.role_id and roadmap.has_market_data:
            # Query market demands for baseline demand_score
            demands = (
                db.query(IndustrySkillDemand)
                .filter(IndustrySkillDemand.role_id == roadmap.role_id)
                .all()
            )
            demand_map = {d.skill_id: d.demand_score for d in demands}

            if user_id:
                # Query user-specific skill gaps
                gaps = (
                    db.query(SkillGap)
                    .filter(
                        SkillGap.user_id == user_id,
                        SkillGap.role_id == roadmap.role_id,
                    )
                    .all()
                )
                gap_map = {g.skill_id: g for g in gaps}

        # Fetch stages and skills ordered
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
        high_priority_gap_count = 0
        medium_priority_gap_count = 0

        # Mapping of skill ID to prereq slugs/names for topological sorting
        prereq_graph: Dict[uuid.UUID, Set[uuid.UUID]] = {}
        skill_metadata_lookup: Dict[uuid.UUID, Dict[str, Any]] = {}

        for stage in stages:
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

                # Resolve candidate gap and priority metrics
                gap_status = None
                priority_level = None
                priority_score = None
                demand_score = None

                if skill.canonical_skill_id:
                    demand_score = demand_map.get(skill.canonical_skill_id)
                    user_gap = gap_map.get(skill.canonical_skill_id)
                    if user_gap:
                        gap_status = user_gap.status
                        priority_level = user_gap.priority_level
                        priority_score = user_gap.priority_score
                        if user_gap.demand_score is not None:
                            demand_score = user_gap.demand_score

                if priority_level == "HIGH":
                    high_priority_gap_count += 1
                elif priority_level == "MEDIUM":
                    medium_priority_gap_count += 1

                # Fetch prerequisites
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

                # Fetch resources
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

                # Parse practice problems
                practice_problems_data = skill.practice_problems or []
                practice_problem_items = []
                for p in practice_problems_data:
                    prob_status = practice_progress_map.get((skill.id, p["problem_id"]), "NOT_STARTED")
                    practice_problem_items.append(
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
                            user_status=prob_status,
                        )
                    )

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
                    gap_status=gap_status,
                    priority_level=priority_level,
                    priority_score=priority_score,
                    demand_score=demand_score,
                )

                stage_skills.append(skill_item)
                all_skill_items.append(skill_item)

                skill_metadata_lookup[skill.id] = {
                    "stage_order": stage.stage_order,
                    "skill_order": skill.skill_order,
                    "priority_level": priority_level,
                    "priority_score": priority_score or 0.0,
                    "gap_status": gap_status,
                    "user_status": user_status,
                }

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
            high_priority_gap_count=high_priority_gap_count,
            medium_priority_gap_count=medium_priority_gap_count,
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

        # Build topological recommended ordering if requested
        recommended_skills = None
        if ordering.lower() == "recommended":
            recommended_skills = self._compute_recommended_ordering(
                all_skills=all_skill_items,
                prereq_graph=prereq_graph,
                metadata_lookup=skill_metadata_lookup,
            )

        return RoadmapDetailData(
            roadmap=roadmap_list_item,
            ordering=ordering.lower(),
            summary=summary,
            stages=stage_items,
            recommended_skills=recommended_skills,
        )

    def _compute_recommended_ordering(
        self,
        all_skills: List[RoadmapSkillItem],
        prereq_graph: Dict[uuid.UUID, Set[uuid.UUID]],
        metadata_lookup: Dict[uuid.UUID, Dict[str, Any]],
    ) -> List[RoadmapSkillItem]:
        """
        Computes a personalized topological sort:
        - NEVER violates prerequisite order (if A is prerequisite of B, A strictly precedes B).
        - Bubbles up high and medium priority missing/partial skills and their unmet prerequisites
          to the earliest possible position in the sequence.
        """
        skill_by_id = {s.id: s for s in all_skills}
        in_degree = {s_id: len(prereqs) for s_id, prereqs in prereq_graph.items()}
        dependents: Dict[uuid.UUID, Set[uuid.UUID]] = {s_id: set() for s_id in prereq_graph}
        for s_id, prereqs in prereq_graph.items():
            for p_id in prereqs:
                if p_id in dependents:
                    dependents[p_id].add(s_id)

        # Identify skills required to unlock high and medium gaps
        high_gap_ancestors: Set[uuid.UUID] = set()
        medium_gap_ancestors: Set[uuid.UUID] = set()

        def collect_ancestors(target_id: uuid.UUID, visited: Set[uuid.UUID]):
            for p in prereq_graph.get(target_id, set()):
                if p not in visited:
                    visited.add(p)
                    collect_ancestors(p, visited)

        for s_id, meta in metadata_lookup.items():
            if meta["priority_level"] == "HIGH":
                collect_ancestors(s_id, high_gap_ancestors)
            elif meta["priority_level"] == "MEDIUM":
                collect_ancestors(s_id, medium_gap_ancestors)

        def score_candidate(candidate_id: uuid.UUID) -> Tuple[int, float, int, int]:
            meta = metadata_lookup[candidate_id]
            p_level = meta["priority_level"]
            user_status = meta["user_status"]
            is_done = user_status == "DONE"

            # Priority tier:
            # 0: Unmet prerequisite of HIGH priority gap
            # 1: HIGH priority gap itself
            # 2: Unmet prerequisite of MEDIUM priority gap
            # 3: MEDIUM priority gap itself
            # 4: LOW priority gap
            # 5: Done or general skill
            if not is_done and candidate_id in high_gap_ancestors:
                tier = 0
            elif not is_done and p_level == "HIGH":
                tier = 1
            elif not is_done and candidate_id in medium_gap_ancestors:
                tier = 2
            elif not is_done and p_level == "MEDIUM":
                tier = 3
            elif not is_done and p_level == "LOW":
                tier = 4
            else:
                tier = 5

            # Tie-breakers: higher priority_score (-score), then stage_order, then skill_order
            p_score = -meta["priority_score"]
            stage_order = meta["stage_order"]
            skill_order = meta["skill_order"]
            return (tier, p_score, stage_order, skill_order)

        # Kahn's algorithm with priority selection
        available: Set[uuid.UUID] = {s_id for s_id, deg in in_degree.items() if deg == 0}
        ordered_skills: List[RoadmapSkillItem] = []

        while available:
            # Select the most urgent available skill
            best_skill_id = min(available, key=score_candidate)
            available.remove(best_skill_id)
            ordered_skills.append(skill_by_id[best_skill_id])

            for dep_id in dependents.get(best_skill_id, set()):
                in_degree[dep_id] -= 1
                if in_degree[dep_id] == 0:
                    available.add(dep_id)

        # Handle any disconnected or cyclic remnants safely
        if len(ordered_skills) < len(all_skills):
            seen = {s.id for s in ordered_skills}
            remnants = [s for s in all_skills if s.id not in seen]
            remnants.sort(key=lambda s: (metadata_lookup[s.id]["stage_order"], metadata_lookup[s.id]["skill_order"]))
            ordered_skills.extend(remnants)

        return ordered_skills

    def get_roadmap_skill(
        self,
        db: Session,
        roadmap_id: uuid.UUID,
        skill_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> RoadmapSkillItem:
        """
        Retrieves detail for a single skill within a roadmap.
        """
        skill = (
            db.query(RoadmapSkill)
            .filter(
                RoadmapSkill.id == skill_id,
                RoadmapSkill.roadmap_id == roadmap_id,
            )
            .first()
        )
        if not skill:
            raise KeyError(f"Skill '{skill_id}' not found in roadmap '{roadmap_id}'.")

        roadmap = db.query(Roadmap).filter(Roadmap.id == roadmap_id).first()

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

        # Gap info if applicable
        gap_status = None
        priority_level = None
        priority_score = None
        demand_score = None

        if roadmap and roadmap.role_id and roadmap.has_market_data and skill.canonical_skill_id:
            demand = (
                db.query(IndustrySkillDemand)
                .filter(
                    IndustrySkillDemand.role_id == roadmap.role_id,
                    IndustrySkillDemand.skill_id == skill.canonical_skill_id,
                )
                .first()
            )
            if demand:
                demand_score = demand.demand_score

            if user_id:
                gap = (
                    db.query(SkillGap)
                    .filter(
                        SkillGap.user_id == user_id,
                        SkillGap.role_id == roadmap.role_id,
                        SkillGap.skill_id == skill.canonical_skill_id,
                    )
                    .first()
                )
                if gap:
                    gap_status = gap.status
                    priority_level = gap.priority_level
                    priority_score = gap.priority_score
                    if gap.demand_score is not None:
                        demand_score = gap.demand_score

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

        # Load practice problem progress for single skill
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
            roadmap_id=roadmap_id,
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
            gap_status=gap_status,
            priority_level=priority_level,
            priority_score=priority_score,
            demand_score=demand_score,
        )

    def update_user_progress(
        self,
        db: Session,
        user_id: uuid.UUID,
        skill_id: uuid.UUID,
        status: str,
    ) -> UserProgressItem:
        """
        Updates or creates a user's progress for a specific roadmap skill.
        Validates status against allowed set: NOT_STARTED, LEARNING, DONE, SKIPPED.
        Enforces user ownership and cross-user isolation.
        """
        clean_status = status.strip().upper()
        if clean_status not in {"NOT_STARTED", "LEARNING", "DONE", "SKIPPED"}:
            raise ValueError(f"Invalid progress status '{status}'.")

        # Verify skill exists
        skill = db.query(RoadmapSkill).filter(RoadmapSkill.id == skill_id).first()
        if not skill:
            raise KeyError(f"Roadmap skill with id '{skill_id}' not found.")

        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise KeyError(f"User with id '{user_id}' not found.")

        progress = (
            db.query(UserRoadmapProgress)
            .filter(
                UserRoadmapProgress.user_id == user_id,
                UserRoadmapProgress.roadmap_skill_id == skill_id,
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
                roadmap_skill_id=skill_id,
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
            updated_at=progress.updated_at,
        )

    def get_user_progress_map(
        self,
        db: Session,
        user_id: uuid.UUID,
    ) -> Dict[str, str]:
        """
        Retrieves a map of {skill_id: status} for all skills tracked by the user.
        """
        rows = (
            db.query(UserRoadmapProgress)
            .filter(UserRoadmapProgress.user_id == user_id)
            .all()
        )
        return {str(r.roadmap_skill_id): r.status for r in rows}

    def update_user_practice_progress(
        self,
        db: Session,
        user_id: uuid.UUID,
        skill_id: uuid.UUID,
        problem_id: str,
        status: str,
    ) -> UserPracticeProgressItem:
        """
        Updates or creates a user's progress for a specific practice problem in a skill.
        Validates status against allowed set: NOT_STARTED, IN_PROGRESS, COMPLETED.
        Enforces user ownership and cross-user isolation.
        """
        clean_status = status.strip().upper()
        if clean_status not in {"NOT_STARTED", "IN_PROGRESS", "COMPLETED"}:
            raise ValueError(f"Invalid practice problem status '{status}'.")

        skill = db.query(RoadmapSkill).filter(RoadmapSkill.id == skill_id).first()
        if not skill:
            raise KeyError(f"Roadmap skill with id '{skill_id}' not found.")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise KeyError(f"User with id '{user_id}' not found.")

        # Check if problem_id exists in skill.practice_problems
        problems = skill.practice_problems or []
        valid_prob_ids = {p.get("problem_id") for p in problems if isinstance(p, dict)}
        if valid_prob_ids and problem_id not in valid_prob_ids:
            raise KeyError(f"Practice problem '{problem_id}' not found for skill '{skill.name}'.")

        progress = (
            db.query(UserPracticeProgress)
            .filter(
                UserPracticeProgress.user_id == user_id,
                UserPracticeProgress.roadmap_skill_id == skill_id,
                UserPracticeProgress.problem_id == problem_id,
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
                roadmap_skill_id=skill_id,
                problem_id=problem_id,
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
            updated_at=progress.updated_at,
        )



skill_roadmap_service = RoadmapService()
roadmap_service = skill_roadmap_service  # Alias for catalog roadmap compatibility

