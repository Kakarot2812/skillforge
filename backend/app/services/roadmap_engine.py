"""
Deterministic Career Roadmap Engine for SkillForge AI.
Post-MVP Phase 4.

Core architectural invariants:
- "The LLM never decides what is true."
- "Deterministic systems decide what is true."
- 100% deterministic, reproducible milestone ordering.
- HARD dependencies strictly enforce topological constraints.
- RECOMMENDED dependencies do NOT block scheduling and do NOT alter topological constraints.
- Transitive-only prerequisites do NOT have fabricated priority scores or levels (priority_score=None).
- Cycles in dependency data raise a typed RoadmapDependencyCycleError (no arbitrary fallback ordering).
- Approved resources come exclusively from the approved_resources catalog.
- Milestone status starts strictly at NOT_STARTED (no P5 verification logic).
"""

from collections import defaultdict, deque
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from app.schemas.roadmap import (
    CanonicalRoadmapData,
    DependencyType,
    MilestoneStatus,
    RoadmapLifecycleStatus,
    RoadmapMilestoneItem,
    RoadmapPrerequisiteItem,
    RoadmapProjectItem,
    RoadmapResourceItem,
)
from app.schemas.skill_gap import PrioritizedGapItem

logger = logging.getLogger(__name__)


class RoadmapError(Exception):
    """Base exception for roadmap engine failures."""
    pass


class RoadmapDependencyCycleError(RoadmapError):
    """Raised when the dependency graph contains an illegal cyclic dependency."""
    def __init__(self, cycle_nodes: List[str]):
        self.cycle_nodes = [str(n) for n in cycle_nodes]
        super().__init__(
            f"Illegal cyclic dependency detected in canonical skill prerequisites among: "
            f"{', '.join(self.cycle_nodes)}. Dependency graph must be a strict Directed Acyclic Graph (DAG)."
        )


class RoadmapValidationError(RoadmapError):
    """Raised when roadmap input data is invalid or inconsistent."""
    pass


class RoadmapEngine:
    """
    Pure deterministic sequencing engine for SkillForge AI.
    Converts prioritized gaps and prerequisite DAG constraints into an ordered roadmap.
    """

    @staticmethod
    def generate_roadmap(
        target_role_id: UUID,
        target_role_title: str,
        location: str,
        actionable_gaps: List[PrioritizedGapItem],
        strong_skill_ids: Set[UUID],
        all_skills_map: Dict[UUID, Any],  # skill_id -> Skill model/dict
        dependencies: List[Any],          # List of SkillDependency models/records
        approved_resources: Dict[UUID, List[Any]],  # skill_id -> List[ApprovedResource]
        approved_projects: Dict[UUID, List[Any]],   # skill_id -> List[ApprovedProject]
        transitive_skill_market_facts: Optional[Dict[UUID, Tuple[Optional[float], Optional[float]]]] = None,
        transitive_candidate_gap_facts: Optional[Dict[UUID, Tuple[str, float]]] = None,
        user_id: Optional[UUID] = None,
        persisted: bool = False,
    ) -> CanonicalRoadmapData:
        """
        Deterministically constructs a CanonicalRoadmapData instance.

        1. Identifies direct actionable gaps.
        2. Transitively resolves unfulfilled HARD prerequisites (without fabricating priority facts).
        3. Builds a directed subgraph of active skills on HARD dependencies.
        4. Validates DAG: detects cycles and raises RoadmapDependencyCycleError if found.
        5. Performs topological sequencing with deterministic priority tie-breaking.
        6. Maps curated approved resources and practical projects.
        7. Returns strongly-typed, frozen CanonicalRoadmapData.
        """
        transitive_skill_market_facts = transitive_skill_market_facts or {}
        transitive_candidate_gap_facts = transitive_candidate_gap_facts or {}

        # 1. Map direct actionable gaps by skill_id
        active_gaps_map: Dict[UUID, PrioritizedGapItem] = {
            gap.skill_id: gap for gap in actionable_gaps
        }

        # 2. Build complete dependency lookup:
        # skill_id -> list of (prerequisite_skill_id, dependency_type, description)
        skill_prereqs_map: Dict[UUID, List[Tuple[UUID, DependencyType, Optional[str]]]] = defaultdict(list)
        for dep in dependencies:
            dep_type = DependencyType.HARD if str(dep.dependency_type).upper() == "HARD" else DependencyType.RECOMMENDED
            skill_prereqs_map[dep.skill_id].append((dep.prerequisite_skill_id, dep_type, getattr(dep, "description", None)))

        # 3. Transitive Prerequisite Discovery:
        # If active skill A has a HARD prerequisite B, and B is not in strong_skill_ids,
        # then B must be added to the active pool if not already present.
        dependency_only_skill_ids: Set[UUID] = set()
        queue = deque(list(active_gaps_map.keys()))
        visited_in_traversal: Set[UUID] = set(queue)

        while queue:
            curr_skill_id = queue.popleft()
            for prereq_id, dep_type, _ in skill_prereqs_map.get(curr_skill_id, []):
                # Only HARD dependencies force prerequisite inclusion
                if dep_type == DependencyType.HARD:
                    # If candidate already has STRONG evidence, prerequisite is satisfied
                    if prereq_id in strong_skill_ids:
                        continue
                    
                    # If not already in active gaps, candidate lacks this prerequisite!
                    if prereq_id not in active_gaps_map and prereq_id not in dependency_only_skill_ids:
                        dependency_only_skill_ids.add(prereq_id)
                        if prereq_id not in visited_in_traversal:
                            visited_in_traversal.add(prereq_id)
                            queue.append(prereq_id)

        # 4. Create representations for dependency-only skills (Correction 1: NO FABRICATED PRIORITY)
        for dep_skill_id in dependency_only_skill_ids:
            skill_entity = all_skills_map.get(dep_skill_id)
            if not skill_entity:
                logger.warning("Dependency skill %s not found in taxonomy. Skipping.", dep_skill_id)
                continue

            skill_name = str(getattr(skill_entity, "name", dep_skill_id))
            skill_slug = str(getattr(skill_entity, "slug", dep_skill_id))
            raw_cat = getattr(skill_entity, "category", None)
            skill_category = str(raw_cat) if raw_cat is not None else None

            # Candidate status for this prerequisite: from candidate facts if available, else MISSING
            cand_status, cand_demo_score = transitive_candidate_gap_facts.get(
                dep_skill_id, ("MISSING", 0.0)
            )

            # Market data if available: from market facts if available, else None
            mkt_demand, mkt_growth = transitive_skill_market_facts.get(
                dep_skill_id, (None, None)
            )

            # Deterministic rationale clearly stating dependency origin
            dep_explanation = (
                f"Foundational prerequisite competency required before downstream technical mastery. "
                f"Candidate lacks sufficient evidence ({cand_status})."
            )

            # Priority score and level are explicitly None: DO NOT FABRICATE
            active_gaps_map[dep_skill_id] = PrioritizedGapItem(
                skill_id=dep_skill_id,
                skill_name=skill_name,
                canonical_slug=skill_slug,
                category=skill_category,
                status=cand_status,
                priority_score=0.0,  # Schemas have float; we treat 0.0 or None in milestone
                priority_level="LOW",  # Will be represented as None in RoadmapMilestoneItem
                demand_score=mkt_demand if mkt_demand is not None else 0.0,
                growth_rate=mkt_growth if mkt_growth is not None else 0.0,
                claimed=False,
                claim_confidence=0.0,
                demonstrated=(cand_status == "PARTIAL"),
                demonstrated_score=cand_demo_score,
                evidence_level=None,
                evidence_count=0,
                location=location,
                explanation=dep_explanation,
            )

        # 5. Build Subgraph on Active Skills with HARD Dependencies Only (Correction 2)
        # in_degree[v] counts unsatisfied HARD prerequisites in active_gaps_map
        in_degree: Dict[UUID, int] = {sid: 0 for sid in active_gaps_map}
        hard_dependents: Dict[UUID, List[UUID]] = defaultdict(list)

        for skill_id in active_gaps_map:
            for prereq_id, dep_type, _ in skill_prereqs_map.get(skill_id, []):
                if dep_type == DependencyType.HARD:
                    # If prerequisite is an active gap (unsatisfied), it blocks skill_id
                    if prereq_id in active_gaps_map:
                        in_degree[skill_id] += 1
                        hard_dependents[prereq_id].append(skill_id)

        # 6. Cycle Detection Validation (Correction 7)
        # Verify DAG acyclicity before sequencing. Fails safely on cycle.
        cycle_check_in_degree = dict(in_degree)
        cycle_queue = deque([sid for sid, deg in cycle_check_in_degree.items() if deg == 0])
        processed_count = 0

        while cycle_queue:
            curr = cycle_queue.popleft()
            processed_count += 1
            for nxt in hard_dependents.get(curr, []):
                cycle_check_in_degree[nxt] -= 1
                if cycle_check_in_degree[nxt] == 0:
                    cycle_queue.append(nxt)

        if processed_count < len(active_gaps_map):
            cycle_skill_ids = [sid for sid, deg in cycle_check_in_degree.items() if deg > 0]
            cycle_names = [
                getattr(all_skills_map.get(sid), "name", str(sid))
                for sid in cycle_skill_ids
            ]
            raise RoadmapDependencyCycleError(cycle_nodes=cycle_names)

        # 7. Deterministic Sequencing via Kahn's Algorithm + Priority Tie-Breaking
        # Tie-breaker key:
        # - Transitive-only prerequisites unblock downstream skills: we prioritize by
        #   the highest priority score among downstream dependents!
        # - For direct gaps: priority_score DESC, demand_score DESC, growth_rate DESC, slug ASC
        def get_scheduling_weight(sid: UUID) -> float:
            gap = active_gaps_map[sid]
            if sid in dependency_only_skill_ids:
                # Inherit the urgency of its highest-priority dependent
                downstream_priorities = [
                    active_gaps_map[d].priority_score
                    for d in hard_dependents.get(sid, [])
                    if d in active_gaps_map and d not in dependency_only_skill_ids
                ]
                return max(downstream_priorities) if downstream_priorities else 0.0
            return gap.priority_score

        def tie_breaker_sort_key(sid: UUID):
            gap = active_gaps_map[sid]
            weight = get_scheduling_weight(sid)
            return (
                -round(weight, 4),
                -round(gap.demand_score, 4),
                -round(gap.growth_rate, 4),
                gap.canonical_slug.lower(),
                str(sid),
            )

        # Available queue: in_degree == 0
        ready_pool = [sid for sid, deg in in_degree.items() if deg == 0]
        ready_pool.sort(key=tie_breaker_sort_key)

        ordered_skill_ids: List[UUID] = []
        while ready_pool:
            next_sid = ready_pool.pop(0)
            ordered_skill_ids.append(next_sid)

            for dep_sid in hard_dependents.get(next_sid, []):
                in_degree[dep_sid] -= 1
                if in_degree[dep_sid] == 0:
                    ready_pool.append(dep_sid)
                    ready_pool.sort(key=tie_breaker_sort_key)

        # 8. Assemble Strongly-Typed Milestones
        milestones: List[RoadmapMilestoneItem] = []
        high_count = 0
        med_count = 0
        low_count = 0
        transitive_count = 0

        for order_idx, skill_id in enumerate(ordered_skill_ids, start=1):
            gap = active_gaps_map[skill_id]
            is_transitive = skill_id in dependency_only_skill_ids

            if is_transitive:
                transitive_count += 1
                prio_score = None
                prio_level = None
                mkt_demand = transitive_skill_market_facts.get(skill_id, (None, None))[0]
                mkt_growth = transitive_skill_market_facts.get(skill_id, (None, None))[1]
                
                # Identify downstream dependent name for rationale
                downstream_names = [
                    getattr(all_skills_map.get(d), "name", str(d))
                    for d in hard_dependents.get(skill_id, [])
                    if d in active_gaps_map
                ]
                dep_desc = f" for '{downstream_names[0]}'" if downstream_names else ""
                reason = (
                    f"Foundational prerequisite competency{dep_desc}. Scheduled before dependent tooling "
                    f"to establish core capabilities. (Candidate lacks verified evidence)."
                )
            else:
                prio_score = round(gap.priority_score, 2)
                prio_level = gap.priority_level
                mkt_demand = round(gap.demand_score, 2)
                mkt_growth = round(gap.growth_rate, 2)
                reason = gap.explanation

                if prio_level == "HIGH":
                    high_count += 1
                elif prio_level == "MEDIUM":
                    med_count += 1
                else:
                    low_count += 1

            # Build prerequisite metadata items (both HARD and RECOMMENDED)
            milestone_prereqs: List[RoadmapPrerequisiteItem] = []
            for prereq_id, dep_type, _ in skill_prereqs_map.get(skill_id, []):
                prereq_entity = all_skills_map.get(prereq_id)
                prereq_name = str(getattr(prereq_entity, "name", prereq_id))
                prereq_slug = str(getattr(prereq_entity, "slug", prereq_id))
                is_sat = (prereq_id in strong_skill_ids)
                milestone_prereqs.append(
                    RoadmapPrerequisiteItem(
                        skill_id=prereq_id,
                        skill_name=prereq_name,
                        canonical_slug=prereq_slug,
                        dependency_type=dep_type,
                        is_satisfied=is_sat,
                    )
                )

            # Build practical learning objectives
            objectives = RoadmapEngine._generate_learning_objectives(
                skill_name=gap.skill_name,
                gap_status=gap.status,
                category=gap.category,
            )

            # Map curated approved resources (Correction 5: Catalog is authority)
            curated_res_list = approved_resources.get(skill_id, [])
            mapped_resources: List[RoadmapResourceItem] = []
            for res in curated_res_list:
                mapped_resources.append(
                    RoadmapResourceItem(
                        id=res.id,
                        title=res.title,
                        url=res.url,
                        resource_type=res.resource_type,
                        provider=res.provider,
                        difficulty=res.difficulty,
                        estimated_minutes=res.estimated_minutes,
                    )
                )

            # Map approved project
            curated_proj_list = approved_projects.get(skill_id, [])
            mapped_project: Optional[RoadmapProjectItem] = None
            if curated_proj_list:
                # Match target role if available, otherwise general
                matching_proj = next(
                    (p for p in curated_proj_list if getattr(p, "role_id", None) == target_role_id),
                    curated_proj_list[0],
                )
                delivs = matching_proj.deliverables if isinstance(matching_proj.deliverables, list) else []
                criteria = matching_proj.verification_criteria if isinstance(matching_proj.verification_criteria, list) else []
                mapped_project = RoadmapProjectItem(
                    id=matching_proj.id,
                    title=matching_proj.title,
                    description=matching_proj.description,
                    difficulty=matching_proj.difficulty,
                    deliverables=tuple(delivs),
                    verification_criteria=tuple(criteria),
                    estimated_hours=matching_proj.estimated_hours,
                )

            milestones.append(
                RoadmapMilestoneItem(
                    milestone_id=None,
                    order_index=order_idx,
                    skill_id=skill_id,
                    skill_name=gap.skill_name,
                    canonical_slug=gap.canonical_slug,
                    category=gap.category,
                    gap_status=gap.status,
                    demonstrated_score=round(gap.demonstrated_score, 2),
                    demand_score=mkt_demand,
                    growth_rate=mkt_growth,
                    priority_score=prio_score,
                    priority_level=prio_level,
                    is_transitive_prerequisite=is_transitive,
                    reason=reason,
                    prerequisites=tuple(milestone_prereqs),
                    learning_objectives=tuple(objectives),
                    resources=tuple(mapped_resources),
                    project=mapped_project,
                    status=MilestoneStatus.NOT_STARTED,  # Correction 6: P4 strictly starts at NOT_STARTED
                )
            )

        return CanonicalRoadmapData(
            id=None,
            user_id=user_id,
            role_id=target_role_id,
            target_role_title=target_role_title,
            location=location,
            status=RoadmapLifecycleStatus.ACTIVE,
            roadmap_version="v1",
            persisted=persisted,
            total_milestones=len(milestones),
            high_priority_count=high_count,
            medium_priority_count=med_count,
            low_priority_count=low_count,
            transitive_prerequisite_count=transitive_count,
            milestones=tuple(milestones),
        )

    @staticmethod
    def _generate_learning_objectives(
        skill_name: str,
        gap_status: str,
        category: Optional[str] = None,
    ) -> List[str]:
        """Generates deterministic, actionable learning objectives without an LLM."""
        cat_lower = (category or "").lower()
        if gap_status == "PARTIAL":
            return [
                f"Review advanced and production patterns for {skill_name}.",
                f"Implement automated unit and integration tests covering {skill_name} components.",
                f"Refactor existing code artifacts to meet high-tier verification standards.",
            ]
        
        # MISSING gap
        if "language" in cat_lower:
            return [
                f"Master fundamental syntax, control flow, and data structures in {skill_name}.",
                f"Implement core idiomatic algorithms and standard library utilities in {skill_name}.",
                f"Build a standalone terminal or module project demonstrating clean code principles in {skill_name}.",
            ]
        elif "frontend" in cat_lower:
            return [
                f"Learn component hierarchy, declarative rendering, and state management in {skill_name}.",
                f"Build responsive, accessible user interfaces following design token conventions in {skill_name}.",
                f"Integrate client-side components with external REST endpoints in {skill_name}.",
            ]
        elif "devops" in cat_lower or "cloud" in cat_lower:
            return [
                f"Understand core architecture, configuration files, and lifecycle commands in {skill_name}.",
                f"Author production-ready, security-hardened manifests and configurations for {skill_name}.",
                f"Automate deployment and execution in a reproducible pipeline using {skill_name}.",
            ]
        elif "database" in cat_lower:
            return [
                f"Design normalized relational schemas and data access patterns using {skill_name}.",
                f"Write performant queries, indexes, and transactional migrations in {skill_name}.",
                f"Establish connection pooling and error-handling resilience for {skill_name}.",
            ]
        else:
            return [
                f"Study official documentation and fundamental architecture of {skill_name}.",
                f"Implement a hands-on technical demonstration exercising core features of {skill_name}.",
                f"Produce verified deliverables showcasing end-to-end integration with {skill_name}.",
            ]
