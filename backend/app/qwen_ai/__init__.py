"""
SkillForge AI — local Qwen 3 (Ollama) reasoning and explanation layer.

SkillForge's deterministic modules remain the source of truth; this package
only explains supplied facts. See docs/qwen_ai.md.
"""
from app.qwen_ai.config import QwenSettings, get_qwen_settings
from app.qwen_ai.context import SkillForgeContext
from app.qwen_ai.qwen_client import QwenClient
from app.qwen_ai.qwen_service import QwenService

__all__ = ["QwenClient", "QwenService", "QwenSettings", "SkillForgeContext", "get_qwen_settings"]