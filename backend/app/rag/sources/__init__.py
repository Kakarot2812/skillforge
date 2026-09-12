"""
Source adapters turn real SkillForge data (or manually-supplied text) into
``NormalizedDocument`` objects for ingestion. Adding a new evidence source
means adding one adapter here and registering it — no retrieval or ranking
code changes.
"""
from typing import Dict

from app.rag.sources.base import SourceAdapter
from app.rag.sources.github import GitHubRepositorySourceAdapter, ProjectEvidenceSourceAdapter
from app.rag.sources.manual import ManualSourceAdapter
from app.rag.sources.resume import ResumeSourceAdapter

SOURCE_ADAPTERS: Dict[str, SourceAdapter] = {
    adapter.source_type: adapter
    for adapter in (
        GitHubRepositorySourceAdapter(),
        ProjectEvidenceSourceAdapter(),
        ResumeSourceAdapter(),
        ManualSourceAdapter(),
    )
}

__all__ = [
    "SourceAdapter",
    "SOURCE_ADAPTERS",
    "GitHubRepositorySourceAdapter",
    "ProjectEvidenceSourceAdapter",
    "ResumeSourceAdapter",
    "ManualSourceAdapter",
]
