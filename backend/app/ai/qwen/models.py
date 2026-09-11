"""
Data contracts for local Qwen 3 8B / Ollama client.
Post-MVP Phase 2, Checkpoint P2-A.

Defines generic request/response representations for Ollama interaction.
Strictly decoupled from SkillForge candidate, skill, demand, or roadmap domains.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class QwenMessage:
    """
    Controlled message representation for Ollama chat API.
    """
    role: str
    content: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "role": self.role,
            "content": self.content,
        }


@dataclass
class QwenChatResponse:
    """
    Controlled response representation from Ollama chat API.
    """
    model: str
    message: QwenMessage
    done: bool = True
    done_reason: Optional[str] = None
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    eval_count: Optional[int] = None

    @property
    def content(self) -> str:
        """Convenience property returning the generated assistant content."""
        return self.message.content

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "message": self.message.to_dict(),
            "done": self.done,
            "done_reason": self.done_reason,
            "total_duration": self.total_duration,
            "load_duration": self.load_duration,
            "prompt_eval_count": self.prompt_eval_count,
            "eval_count": self.eval_count,
        }


@dataclass
class QwenGenerateResponse:
    """
    Controlled response representation from Ollama generate API.
    """
    model: str
    response: str
    done: bool = True
    done_reason: Optional[str] = None
    total_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    eval_count: Optional[int] = None

    @property
    def content(self) -> str:
        """Convenience property returning the generated text content."""
        return self.response

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "response": self.response,
            "done": self.done,
            "done_reason": self.done_reason,
            "total_duration": self.total_duration,
            "prompt_eval_count": self.prompt_eval_count,
            "eval_count": self.eval_count,
        }


@dataclass
class QwenHealthStatus:
    """
    Audit and connectivity status for the local Ollama / Qwen model service.
    """
    reachable: bool
    model_available: bool
    configured_model: str
    available_models: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        """True only if Ollama is reachable AND the configured model is installed."""
        return self.reachable and self.model_available

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reachable": self.reachable,
            "model_available": self.model_available,
            "configured_model": self.configured_model,
            "is_healthy": self.is_healthy,
            "available_models": list(self.available_models),
            "details": dict(self.details),
        }
