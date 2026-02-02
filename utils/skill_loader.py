"""
SkillLoader: reads .md files from ./skills/ and parses them into structured
Python objects. Skills are NOT executable tools — they are instructional
contracts (WHAT to do, WHEN, ROLE, INSTRUCTIONS, INPUT/OUTPUT schemas)
used to guide agent prompts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class Skill:
    """Parsed skill definition from a .md file."""

    name: str
    description: str
    execution_order: int
    condition: Optional[str] = None  # e.g. 'decision == "DENY"'
    role: str = ""
    instructions: str = ""
    input_schema: str = ""
    output_schema: str = ""
    raw_content: str = ""

    def __post_init__(self) -> None:
        if not self.role and self.raw_content:
            self._extract_sections()
        return None

    def _extract_sections(self) -> None:
        """Extract ## Role, ## Instructions, and code-block schemas from raw_content."""
        content = self.raw_content or ""
        # ## Role\n... until next ## or end
        role_m = re.search(r"##\s*Role\s*\n+(.*?)(?=\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
        if role_m:
            self.role = role_m.group(1).strip()

        inst_m = re.search(
            r"##\s*Instructions\s*\n+(.*?)(?=\n##\s*(?:Input|Output|Connectors|Key|Example|Resources|Notes|Quick)|\Z)",
            content,
            re.DOTALL | re.IGNORECASE,
        )
        if inst_m:
            self.instructions = inst_m.group(1).strip()

        # Input Schema ```json ... ```
        input_m = re.search(
            r"##\s*Input\s*Schema\s*\n+```(?:json)?\s*\n(.*?)```",
            content,
            re.DOTALL | re.IGNORECASE,
        )
        if input_m:
            self.input_schema = input_m.group(1).strip()

        output_m = re.search(
            r"##\s*Output\s*Schema\s*\n+```(?:json)?\s*\n(.*?)```",
            content,
            re.DOTALL | re.IGNORECASE,
        )
        if output_m:
            self.output_schema = output_m.group(1).strip()


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Split YAML frontmatter and body. Returns (frontmatter_dict, body)."""
    if not content.strip().startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    try:
        fm = yaml.safe_load(parts[1].strip()) or {}
    except Exception:
        fm = {}
    return fm, parts[2].strip()


def load_skill(path: Path) -> Skill:
    """Load a single skill from a .md file path."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    fm, body = _parse_frontmatter(raw)
    name = fm.get("name", path.stem)
    description = fm.get("description", "")
    execution_order = int(fm.get("execution_order", 99))
    condition = fm.get("condition")
    skill = Skill(
        name=name,
        description=description,
        execution_order=execution_order,
        condition=condition,
        raw_content=raw,
    )
    skill._extract_sections()
    return skill


def load_skills_from_dir(skills_dir: str | Path) -> list[Skill]:
    """
    Read all .md files in skills_dir, parse into Skill objects, sort by
    execution_order. Skills are instructional contracts, not tools.
    """
    path = Path(skills_dir)
    if not path.is_dir():
        return []
    skills: list[Skill] = []
    for f in path.glob("*.md"):
        try:
            skills.append(load_skill(f))
        except Exception:
            continue
    skills.sort(key=lambda s: s.execution_order)
    return skills
