from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from app.schemas.skill import PaginationMeta


class ResumeUploadResponse(BaseModel):
    resume_id: UUID
    user_id: Optional[UUID] = None
    filename: str
    file_type: str
    file_size: int
    status: str = "uploaded"
    message: str = "Resume uploaded, parsed, and skills normalized successfully."
    extracted_sections: List[str] = []
    claimed_skills_count: int = 0
    claimed_skills: List[Dict[str, Any]] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResumeListItem(BaseModel):
    resume_id: UUID
    user_id: Optional[UUID] = None
    filename: str
    file_type: str
    file_size: int
    status: str = "uploaded"
    detected_sections: List[str] = []
    claimed_skills_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResumeListResponse(BaseModel):
    data: List[ResumeListItem]
    meta: PaginationMeta


class ResumeDetailResponse(BaseModel):
    resume_id: UUID
    user_id: Optional[UUID] = None
    filename: str
    file_type: str
    file_size: int
    has_raw_text: bool
    raw_text: Optional[str] = None
    detected_sections: List[str] = []
    contact_info: Dict[str, Optional[str]] = {}
    claimed_skills_count: int = 0
    claimed_skills: List[Dict[str, Any]] = []
    parsed_data: Dict[str, Any] = {}
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
