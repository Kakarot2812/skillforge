"""
Resource Service for SkillForge AI.
Post-MVP Phase 4.

Provides controlled access to curated learning resources and practical projects.
Authority boundary:
- approved_resources is the sole authority.
- Arbitrary web scraping and runtime URL ingestion are prohibited.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import ApprovedProject, ApprovedResource, Skill
from app.schemas.roadmap import ApprovedResourceListResponse, RoadmapResourceItem


class ResourceService:
    """Provides validated access to approved learning resources and projects."""

    @staticmethod
    def get_resources_by_skill(
        db: Session,
        skill_id: UUID,
    ) -> ApprovedResourceListResponse:
        """Retrieves all approved learning resources for a canonical skill."""
        skill = db.query(Skill).filter(Skill.id == skill_id).first()
        if not skill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skill with id '{skill_id}' not found in canonical taxonomy.",
            )

        rows = (
            db.query(ApprovedResource)
            .filter(
                ApprovedResource.skill_id == skill_id,
                ApprovedResource.is_approved == True,
            )
            .order_by(ApprovedResource.difficulty.asc(), ApprovedResource.title.asc())
            .all()
        )

        items = [
            RoadmapResourceItem(
                id=r.id,
                title=r.title,
                url=r.url,
                resource_type=r.resource_type,
                provider=r.provider,
                difficulty=r.difficulty,
                estimated_minutes=r.estimated_minutes,
            )
            for r in rows
        ]

        return ApprovedResourceListResponse(
            skill_id=skill.id,
            skill_name=skill.name,
            total_resources=len(items),
            resources=tuple(items),
        )


resource_service = ResourceService()
