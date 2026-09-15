"""Roadmaps data package aggregating all 12 domain roadmaps with progressive practice problems."""
from typing import Any, Dict, List
from app.db.roadmaps_data.common import CANONICAL_ROLE_IDS, ROADMAP_IDS
from app.db.roadmaps_data.backend import BACKEND_ROADMAP
from app.db.roadmaps_data.fullstack import FULLSTACK_ROADMAP
from app.db.roadmaps_data.frontend import FRONTEND_ROADMAP
from app.db.roadmaps_data.devops import DEVOPS_ROADMAP
from app.db.roadmaps_data.aiml import AIML_ROADMAP
from app.db.roadmaps_data.android import ANDROID_ROADMAP
from app.db.roadmaps_data.data_eng import DATA_ENGINEER_ROADMAP
from app.db.roadmaps_data.data_sci import DATA_SCIENTIST_ROADMAP
from app.db.roadmaps_data.cybersecurity import CYBERSECURITY_ROADMAP
from app.db.roadmaps_data.qa import QA_AUTOMATION_ROADMAP
from app.db.roadmaps_data.ios import IOS_ROADMAP
from app.db.roadmaps_data.ui_ux import UI_UX_ROADMAP

ROADMAPS_SEED_DATA: List[Dict[str, Any]] = [
    BACKEND_ROADMAP,
    FULLSTACK_ROADMAP,
    FRONTEND_ROADMAP,
    DEVOPS_ROADMAP,
    AIML_ROADMAP,
    ANDROID_ROADMAP,
    DATA_ENGINEER_ROADMAP,
    DATA_SCIENTIST_ROADMAP,
    CYBERSECURITY_ROADMAP,
    QA_AUTOMATION_ROADMAP,
    IOS_ROADMAP,
    UI_UX_ROADMAP,
]

__all__ = [
    "CANONICAL_ROLE_IDS",
    "ROADMAP_IDS",
    "ROADMAPS_SEED_DATA",
    "BACKEND_ROADMAP",
    "FULLSTACK_ROADMAP",
    "FRONTEND_ROADMAP",
    "DEVOPS_ROADMAP",
    "AIML_ROADMAP",
    "ANDROID_ROADMAP",
    "DATA_ENGINEER_ROADMAP",
    "DATA_SCIENTIST_ROADMAP",
    "CYBERSECURITY_ROADMAP",
    "QA_AUTOMATION_ROADMAP",
    "IOS_ROADMAP",
    "UI_UX_ROADMAP",
]
