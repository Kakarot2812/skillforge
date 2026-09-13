"""
Idempotent Seeder for SkillForge AI Static Skill Roadmaps Catalog.

Populates the 12 curated and canonical career roadmaps, stages, skills,
learning resources, practice problems, and prerequisite DAG edges.
"""

import argparse
import logging
import sys
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import (
    JobRole,
    LearningResource,
    Roadmap,
    RoadmapPrerequisite,
    RoadmapSkill,
    RoadmapStage,
    Skill,
)
from app.db.roadmaps_data import (
    CANONICAL_ROLE_IDS,
    ROADMAPS_SEED_DATA,
)

logger = logging.getLogger("skillforge.seed_roadmaps")

CANONICAL_ROLE_SLUGS: Set[str] = {
    "backend-engineer",
    "full-stack-engineer",
    "frontend-engineer",
    "cloud-devops-engineer",
    "ai-ml-engineer",
}


def validate_seeded_roadmaps(db: Session) -> Dict[str, Any]:
    """
    Validates all structural and semantic invariants of the seeded roadmaps.
    Raises ValueError on any discrepancy.
    """
    roadmaps_count = db.query(Roadmap).count()
    stages_count = db.query(RoadmapStage).count()
    skills_count = db.query(RoadmapSkill).count()
    prereqs_count = db.query(RoadmapPrerequisite).count()
    resources_count = db.query(LearningResource).count()

    skills = db.query(RoadmapSkill).all()
    total_problems = sum(len(s.practice_problems or []) for s in skills)

    # 1. Total counts check
    expected_counts = {
        "roadmaps": 12,
        "stages": 56,
        "skills": 130,
        "prerequisites": 174,
        "resources": 260,
        "problems": 390,
    }
    actual_counts = {
        "roadmaps": roadmaps_count,
        "stages": stages_count,
        "skills": skills_count,
        "prerequisites": prereqs_count,
        "resources": resources_count,
        "problems": total_problems,
    }
    for entity, expected in expected_counts.items():
        actual = actual_counts[entity]
        if actual != expected:
            raise ValueError(
                f"Validation invariant failed for '{entity}': expected {expected}, got {actual}"
            )

    # 2. Resource validation (exactly 1 DOCUMENTATION, 1 YOUTUBE per skill)
    for skill in skills:
        res_types = [r.resource_type for r in skill.resources]
        if len(res_types) != 2 or sorted(res_types) != ["DOCUMENTATION", "YOUTUBE"]:
            raise ValueError(
                f"Skill '{skill.name}' ({skill.slug}) has invalid resources: {res_types}. Expected exactly 1 DOCUMENTATION and 1 YOUTUBE."
            )

    # 3. Practice problem validation (exactly 1 BEGINNER, 1 INTERMEDIATE, 1 ADVANCED per skill)
    for skill in skills:
        probs = skill.practice_problems or []
        diffs = [p.get("difficulty") for p in probs]
        if len(probs) != 3 or sorted(diffs) != ["ADVANCED", "BEGINNER", "INTERMEDIATE"]:
            raise ValueError(
                f"Skill '{skill.name}' ({skill.slug}) has invalid practice problems: {diffs}. Expected 1 BEGINNER, 1 INTERMEDIATE, 1 ADVANCED."
            )

    # 4. Role mapping validation (5 canonical tracks with role_id and has_market_data=True, 7 curated with None/False)
    roadmaps = db.query(Roadmap).all()
    canonical_roadmaps = [r for r in roadmaps if r.slug in CANONICAL_ROLE_SLUGS]
    curated_roadmaps = [r for r in roadmaps if r.slug not in CANONICAL_ROLE_SLUGS]

    if len(canonical_roadmaps) != 5:
        raise ValueError(f"Expected 5 canonical roadmaps, got {len(canonical_roadmaps)}")
    if len(curated_roadmaps) != 7:
        raise ValueError(f"Expected 7 curated roadmaps, got {len(curated_roadmaps)}")

    for r in canonical_roadmaps:
        if r.role_id is None or not r.has_market_data:
            raise ValueError(
                f"Canonical roadmap '{r.slug}' must have role_id and has_market_data=True "
                f"(got role_id={r.role_id}, has_market_data={r.has_market_data})"
            )

    for r in curated_roadmaps:
        if r.role_id is not None or r.has_market_data:
            raise ValueError(
                f"Curated roadmap '{r.slug}' must have role_id=None and has_market_data=False "
                f"(got role_id={r.role_id}, has_market_data={r.has_market_data})"
            )

    # 5. Canonical skills mapping (50 mapped, 80 unmapped)
    mapped_skills = [s for s in skills if s.canonical_skill_id is not None]
    unmapped_skills = [s for s in skills if s.canonical_skill_id is None]
    if len(mapped_skills) != 50:
        raise ValueError(f"Expected 50 canonical mapped skills, got {len(mapped_skills)}")
    if len(unmapped_skills) != 80:
        raise ValueError(f"Expected 80 unmapped skills, got {len(unmapped_skills)}")

    # 6. Prerequisites validation (each edge stays inside its roadmap, acyclic DAG)
    prereqs = db.query(RoadmapPrerequisite).all()
    for p in prereqs:
        if p.roadmap_skill.roadmap_id != p.prerequisite_skill.roadmap_id:
            raise ValueError(
                f"Cross-roadmap prerequisite edge detected: skill '{p.roadmap_skill.name}' "
                f"(roadmap {p.roadmap_skill.roadmap_id}) requires '{p.prerequisite_skill.name}' "
                f"(roadmap {p.prerequisite_skill.roadmap_id})"
            )

    # Kahn's algorithm per roadmap
    for r in roadmaps:
        r_skills = [s for s in skills if s.roadmap_id == r.id]
        skill_ids = {s.id for s in r_skills}
        adj: Dict[uuid.UUID, List[uuid.UUID]] = {sid: [] for sid in skill_ids}
        in_degree: Dict[uuid.UUID, int] = {sid: 0 for sid in skill_ids}

        for s in r_skills:
            for p in s.prerequisites:
                adj[p.prerequisite_skill_id].append(s.id)
                in_degree[s.id] += 1

        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        visited = 0
        while queue:
            curr = queue.pop(0)
            visited += 1
            for nxt in adj[curr]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        if visited != len(skill_ids):
            raise ValueError(
                f"Cycle detected in roadmap '{r.slug}' ({r.title})! "
                f"Kahn's algorithm processed {visited}/{len(skill_ids)} nodes."
            )

    return actual_counts


def seed_roadmaps(db: Session, auto_commit: bool = True, validate: bool = True) -> Dict[str, int]:
    """
    Seed static skill roadmaps, stages, skills, resources, and prerequisite edges.
    Idempotent: safe to run multiple times without duplicating rows.
    """
    try:
        # Load canonical roles lookup from database
        roles = db.query(JobRole).all()
        roles_by_slug = {r.slug: r for r in roles}

        # Load canonical skills lookup from database
        skills_db = db.query(Skill).all()
        skills_by_slug = {s.slug: s for s in skills_db}

        # Maps for resolving relationships during seeding
        roadmap_map: Dict[str, Roadmap] = {}
        skill_lookup: Dict[Tuple[uuid.UUID, str], RoadmapSkill] = {}

        # --- STEP 1: UPSERT ROADMAPS ---
        for r_data in ROADMAPS_SEED_DATA:
            r_slug = r_data["slug"]

            # Resolve canonical role
            if r_slug in CANONICAL_ROLE_SLUGS:
                role = roles_by_slug.get(r_slug)
                if not role and r_slug in CANONICAL_ROLE_IDS:
                    role = db.query(JobRole).filter(JobRole.id == CANONICAL_ROLE_IDS[r_slug]).one_or_none()
                if not role:
                    raise ValueError(
                        f"Canonical role for track '{r_slug}' not found in JobRole table. Seed canonical roles first."
                    )
                role_id = role.id
                has_market_data = True
            else:
                role_id = None
                has_market_data = False

            roadmap = db.query(Roadmap).filter(Roadmap.slug == r_slug).one_or_none()
            if roadmap:
                roadmap.title = r_data["title"]
                roadmap.domain = r_data["domain"]
                roadmap.category = r_data["category"]
                roadmap.description = r_data["description"]
                roadmap.version = r_data.get("version", "v1.0")
                roadmap.role_id = role_id
                roadmap.has_market_data = has_market_data
            else:
                roadmap = Roadmap(
                    id=r_data.get("id", uuid.uuid4()),
                    slug=r_slug,
                    title=r_data["title"],
                    domain=r_data["domain"],
                    category=r_data["category"],
                    description=r_data["description"],
                    version=r_data.get("version", "v1.0"),
                    role_id=role_id,
                    has_market_data=has_market_data,
                )
                db.add(roadmap)

            db.flush()
            roadmap_map[r_slug] = roadmap

        # --- STEP 2: UPSERT STAGES & SKILLS & RESOURCES ---
        for r_data in ROADMAPS_SEED_DATA:
            roadmap = roadmap_map[r_data["slug"]]

            for st_data in r_data.get("stages", []):
                st_order = st_data["order"]
                stage = (
                    db.query(RoadmapStage)
                    .filter(
                        RoadmapStage.roadmap_id == roadmap.id,
                        RoadmapStage.stage_order == st_order,
                    )
                    .one_or_none()
                )
                if stage:
                    stage.name = st_data["name"]
                    stage.description = st_data.get("description")
                else:
                    stage = RoadmapStage(
                        roadmap_id=roadmap.id,
                        stage_order=st_order,
                        name=st_data["name"],
                        description=st_data.get("description"),
                    )
                    db.add(stage)

                db.flush()

                for sk_idx, sk_data in enumerate(st_data.get("skills", [])):
                    sk_slug = sk_data["slug"]
                    cslug = sk_data.get("canonical_slug")
                    canonical_skill_id = None

                    if cslug:
                        cskill = skills_by_slug.get(cslug)
                        if not cskill:
                            raise ValueError(
                                f"Canonical skill '{cslug}' referenced by '{sk_data['name']}' in roadmap '{r_data['slug']}' not found in skills table!"
                            )
                        canonical_skill_id = cskill.id

                    skill = (
                        db.query(RoadmapSkill)
                        .filter(
                            RoadmapSkill.roadmap_id == roadmap.id,
                            RoadmapSkill.slug == sk_slug,
                        )
                        .one_or_none()
                    )

                    skill_order = sk_idx + 1
                    if skill:
                        skill.stage_id = stage.id
                        skill.canonical_skill_id = canonical_skill_id
                        skill.name = sk_data["name"]
                        skill.description = sk_data["description"]
                        skill.difficulty = sk_data.get("difficulty", "BEGINNER")
                        skill.skill_order = skill_order
                        skill.key_topics = sk_data.get("key_topics", [])
                        skill.practice_project = sk_data.get("practice_project")
                        skill.practice_problems = sk_data.get("practice_problems", [])
                        skill.role_relevance = sk_data.get("role_relevance")
                    else:
                        skill = RoadmapSkill(
                            stage_id=stage.id,
                            roadmap_id=roadmap.id,
                            canonical_skill_id=canonical_skill_id,
                            name=sk_data["name"],
                            slug=sk_slug,
                            description=sk_data["description"],
                            difficulty=sk_data.get("difficulty", "BEGINNER"),
                            skill_order=skill_order,
                            key_topics=sk_data.get("key_topics", []),
                            practice_project=sk_data.get("practice_project"),
                            practice_problems=sk_data.get("practice_problems", []),
                            role_relevance=sk_data.get("role_relevance"),
                        )
                        db.add(skill)

                    db.flush()
                    skill_lookup[(roadmap.id, sk_slug)] = skill

                    # Upsert learning resources for this skill
                    for res_data in sk_data.get("resources", []):
                        r_type = res_data["type"]
                        resource = (
                            db.query(LearningResource)
                            .filter(
                                LearningResource.roadmap_skill_id == skill.id,
                                LearningResource.resource_type == r_type,
                            )
                            .one_or_none()
                        )
                        if resource:
                            resource.title = res_data["title"]
                            resource.url = res_data["url"]
                            resource.description = res_data["description"]
                        else:
                            resource = LearningResource(
                                roadmap_skill_id=skill.id,
                                resource_type=r_type,
                                title=res_data["title"],
                                url=res_data["url"],
                                description=res_data["description"],
                            )
                            db.add(resource)

                    db.flush()

        # --- STEP 3: UPSERT PREREQUISITE EDGES ---
        for r_data in ROADMAPS_SEED_DATA:
            roadmap = roadmap_map[r_data["slug"]]
            for st_data in r_data.get("stages", []):
                for sk_data in st_data.get("skills", []):
                    source_skill = skill_lookup[(roadmap.id, sk_data["slug"])]
                    for prereq_slug in sk_data.get("prerequisites", []):
                        target_skill = skill_lookup.get((roadmap.id, prereq_slug))
                        if not target_skill:
                            raise ValueError(
                                f"Prerequisite '{prereq_slug}' for skill '{sk_data['slug']}' in roadmap '{r_data['slug']}' not found!"
                            )
                        edge = (
                            db.query(RoadmapPrerequisite)
                            .filter(
                                RoadmapPrerequisite.roadmap_skill_id == source_skill.id,
                                RoadmapPrerequisite.prerequisite_skill_id == target_skill.id,
                            )
                            .one_or_none()
                        )
                        if not edge:
                            edge = RoadmapPrerequisite(
                                roadmap_skill_id=source_skill.id,
                                prerequisite_skill_id=target_skill.id,
                            )
                            db.add(edge)

        db.flush()

        # --- STEP 4: VALIDATE INVARIANTS ---
        if validate:
            counts = validate_seeded_roadmaps(db)
        else:
            counts = {
                "roadmaps": db.query(Roadmap).count(),
                "stages": db.query(RoadmapStage).count(),
                "skills": db.query(RoadmapSkill).count(),
                "prerequisites": db.query(RoadmapPrerequisite).count(),
                "resources": db.query(LearningResource).count(),
            }

        if auto_commit:
            db.commit()

        logger.info("Successfully seeded roadmaps catalog: %s", counts)
        return counts

    except Exception as exc:
        if auto_commit:
            db.rollback()
        logger.error("Error during roadmaps seeding: %s", exc)
        raise exc


def main():
    """CLI entrypoint to execute the seeder."""
    parser = argparse.ArgumentParser(description="Seed SkillForge AI static skill roadmaps catalog.")
    parser.add_argument("--no-validate", action="store_true", help="Skip post-seed validation checks.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    print("Connecting to database and running static roadmap seeder...")

    session = SessionLocal()
    try:
        counts = seed_roadmaps(session, auto_commit=True, validate=not args.no_validate)
        print("\nSeeding completed successfully!")
        print(f"  Roadmaps:        {counts.get('roadmaps')}")
        print(f"  Stages:          {counts.get('stages')}")
        print(f"  Skills:          {counts.get('skills')}")
        print(f"  Prerequisites:   {counts.get('prerequisites')}")
        print(f"  Resources:       {counts.get('resources')}")
        print(f"  Problems:        {counts.get('problems')}")
    except Exception as exc:
        print(f"\nERROR seeding roadmaps: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
