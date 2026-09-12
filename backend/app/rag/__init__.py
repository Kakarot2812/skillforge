"""
SkillForge RAG — evidence retrieval and grounding layer.

Retrieves supporting evidence (GitHub artifacts, resume text, curated
documents) for a user's question and hands it to the existing Qwen AI layer
as ``SkillForgeContext.evidence``. RAG never computes authoritative
SkillForge facts (scores, skill gaps, roadmap order) — it only retrieves and
ranks textual evidence for Qwen to explain and cite.

See ``app.qwen_ai`` for the reasoning/explanation layer this module feeds.
"""
from app.rag.config import RagSettings, get_rag_settings
from app.rag.service import RagService, get_rag_service

__all__ = ["RagSettings", "get_rag_settings", "RagService", "get_rag_service"]
