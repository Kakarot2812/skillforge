"""
Personalization Context Module for SkillForge AI Chatbot.
Phase: Persistent Personalization Architecture (Checkpoint 5: Personalized Context Assembly & Qwen Integration).

Maintains strict architectural boundaries:
1. VerifiedContext = Absolute Authoritative Ground Truth for candidate skills, gaps, priorities, evidence.
2. UserProfile = Non-Authoritative Personalization Information (user-provided demographic, academic, role preferences).
3. Conversation History = Non-Authoritative Dialogue Context.
4. Qwen = Generative Explanation & Personalization Layer over pre-verified facts.

Profile data and conversation dialogue can NEVER override, modify, or establish verified candidate skills.
"""

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple
from langchain_core.messages import BaseMessage

from app.ai.context.models import VerifiedContext
from app.db.models import UserProfile


@dataclass(frozen=True)
class ProfileContext:
    """
    Immutable representation of user-provided profile context.
    Contains strictly user-provided demographic and academic preferences.
    Never treated as verified evidence or skill proficiency.
    """
    name: Optional[str] = None
    education: Optional[str] = None
    college: Optional[str] = None
    degree: Optional[str] = None
    branch: Optional[str] = None
    semester: Optional[int] = None
    target_role: Optional[str] = None
    experience_level: Optional[str] = None

    @classmethod
    def from_model(cls, profile: Optional[UserProfile]) -> "ProfileContext":
        """Builds an immutable ProfileContext from a UserProfile SQLAlchemy model."""
        if profile is None:
            return cls()
        return cls(
            name=profile.name,
            education=profile.education,
            college=profile.college,
            degree=profile.degree,
            branch=profile.branch,
            semester=profile.semester,
            target_role=profile.target_role,
            experience_level=profile.experience_level,
        )

    def is_available(self) -> bool:
        """Returns True if at least one profile field contains non-empty data."""
        return any(
            v is not None
            for v in (
                self.name,
                self.education,
                self.college,
                self.degree,
                self.branch,
                self.semester,
                self.target_role,
                self.experience_level,
            )
        )

    def serialize(self) -> str:
        """
        Formats user profile into a deterministic, clearly delimited format.
        Omits unavailable/None fields.
        If empty or unavailable, explicitly indicates profile information is unavailable.
        Never outputs 'None' values.
        """
        if not self.is_available():
            return "<user_profile>\nProfile information is unavailable.\n</user_profile>"

        lines = ["<user_profile>"]
        if self.name:
            lines.append(f"Name: {self.name}")
        if self.education:
            lines.append(f"Education: {self.education}")
        if self.college:
            lines.append(f"College: {self.college}")
        if self.degree:
            lines.append(f"Degree: {self.degree}")
        if self.branch:
            lines.append(f"Branch: {self.branch}")
        if self.semester is not None:
            lines.append(f"Semester: {self.semester}")
        if self.target_role:
            lines.append(f"Target role: {self.target_role}")
        if self.experience_level:
            lines.append(f"Experience level: {self.experience_level}")
        lines.append("</user_profile>")
        return "\n".join(lines)


@dataclass(frozen=True)
class PersonalizationContext:
    """
    Dedicated tripartite container maintaining strict source boundaries:
    1. profile: user-provided context for personalizing tone, examples, and academic framing.
    2. chat_history: bounded chronological dialogue turns (dialogue context only).
    3. verified_context: authoritative ground truth SkillForge facts (unflattened and sovereign).
    """
    profile: ProfileContext
    chat_history: Tuple[BaseMessage, ...]
    verified_context: VerifiedContext


def assemble_personalization_context(
    verified_context: VerifiedContext,
    profile: Optional[UserProfile] = None,
    chat_history: Optional[Sequence[BaseMessage]] = None,
) -> PersonalizationContext:
    """
    Deterministically constructs the immutable PersonalizationContext.
    Does not query databases directly; operates over pre-loaded domain objects.
    """
    profile_ctx = ProfileContext.from_model(profile)
    history_tuple = tuple(chat_history or ())
    return PersonalizationContext(
        profile=profile_ctx,
        chat_history=history_tuple,
        verified_context=verified_context,
    )
