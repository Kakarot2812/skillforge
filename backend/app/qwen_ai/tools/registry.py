"""
Future-ready tool registry for SkillForge AI.

This is an extension point only. No tools are registered by default and the
chat endpoint does not execute tool calls yet. When a SkillForge module is
ready (e.g. the skill-gap engine), its owner registers a real async handler
here; the registry can then advertise it to Qwen in Ollama's tool format.

Example (in the owning module, not here):

    class SkillGapArgs(BaseModel):
        user_id: UUID
        target_role_id: UUID

    async def get_skill_gaps(args: SkillGapArgs) -> dict:
        ...  # call the real service

    tool_registry.register(ToolDefinition(
        name="get_skill_gaps",
        description="Return the user's deterministic skill gaps for a role.",
        parameters=SkillGapArgs,
        handler=get_skill_gaps,
    ))
"""
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Type

from pydantic import BaseModel, ValidationError

# Names reserved for planned integrations. Documentation only; nothing here is implemented.
PLANNED_TOOL_NAMES = frozenset({
    "get_user_profile",
    "get_user_skills",
    "get_skill_gaps",
    "get_market_demand",
    "get_role_requirements",
    "get_roadmap",
    "get_resume_analysis",
    "get_github_evidence",
    "search_knowledge",
})

_NAME = re.compile(r"^[a-z][a-z0-9_]{2,63}$")

ToolHandler = Callable[[BaseModel], Awaitable[Any]]


class ToolRegistrationError(ValueError):
    pass


class ToolNotFoundError(KeyError):
    pass


class ToolArgumentsError(ValueError):
    pass


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: Type[BaseModel]
    handler: ToolHandler

    def to_ollama_schema(self) -> Dict[str, Any]:
        """Ollama /api/chat ``tools`` entry (OpenAI-style function schema)."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters.model_json_schema(),
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition, *, replace: bool = False) -> None:
        if not _NAME.match(tool.name):
            raise ToolRegistrationError(f"Invalid tool name '{tool.name}' (use snake_case, 3-64 chars).")
        if not tool.description.strip():
            raise ToolRegistrationError(f"Tool '{tool.name}' needs a description.")
        if tool.name in self._tools and not replace:
            raise ToolRegistrationError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def names(self) -> List[str]:
        return sorted(self._tools)

    def __contains__(self, name: object) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)

    def to_ollama_tools(self) -> List[Dict[str, Any]]:
        return [self._tools[n].to_ollama_schema() for n in self.names()]

    async def invoke(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Validate arguments against the tool's schema and run its handler."""
        tool = self._tools.get(name)
        if tool is None:
            raise ToolNotFoundError(name)
        try:
            args = tool.parameters.model_validate(arguments or {})
        except ValidationError as exc:
            raise ToolArgumentsError(f"Invalid arguments for tool '{name}'.") from exc
        return await tool.handler(args)


# Process-wide registry. Intentionally empty until real modules register tools.
tool_registry = ToolRegistry()