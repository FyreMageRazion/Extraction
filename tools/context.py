"""
Context for tool execution: current_skill is set by the runner before each
agent.kickoff so tools can log which skill triggered them.
"""

from __future__ import annotations

_current_skill: str | None = None


def set_current_skill(name: str | None) -> None:
    global _current_skill
    _current_skill = name


def get_current_skill() -> str | None:
    return _current_skill
