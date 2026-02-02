"""
BaseTool subclasses for NPI and CMS coverage with explicit args_schema and Field descriptions.
CrewAI best practice: explicit Pydantic schema so the LLM sees parameter semantics.
"""

from __future__ import annotations

import json
from typing import Any, Type

from crewai.tools.base_tool import BaseTool
from pydantic import BaseModel, Field

from . import context as tool_context
from .cms_coverage_lookup import lookup_cms_coverage
from .npi_lookup import lookup_npi


class LookupNPIInput(BaseModel):
    """Input schema for NPI lookup."""

    npi: str = Field(
        ...,
        description="10-digit National Provider Identifier from Input.provider.npi. Use for provider validation.",
    )


class LookupNPIBaseTool(BaseTool):
    """Look up provider by NPI using the CMS NPI Registry API."""

    name: str = "lookup_npi"
    description: str = (
        "Look up provider by NPI using the CMS NPI Registry API. Use for provider validation. "
        "Returns provider_name, active, taxonomy, state, source_urls."
    )
    args_schema: Type[BaseModel] = LookupNPIInput

    def _run(self, npi: str) -> dict[str, Any]:
        skill = tool_context.get_current_skill() or "unknown"
        args_str = json.dumps({"npi": npi}, default=str)[:200]
        print(f"[TOOL] {skill} -> {self.name}({args_str})")
        return lookup_npi(npi)


class LookupCMSCoverageInput(BaseModel):
    """Input schema for CMS coverage lookup."""

    cpt_code: str = Field(
        ...,
        description="CPT or HCPCS procedure code from Input.procedures_requested. Use for coverage eligibility.",
    )


class LookupCMSCoverageBaseTool(BaseTool):
    """Look up CMS NCD/LCD coverage for a CPT code."""

    name: str = "lookup_cms_coverage"
    description: str = (
        "Look up CMS NCD/LCD coverage for a CPT code. Use for coverage eligibility. "
        "Returns ncd_lcd_references, coverage_notes, source_urls."
    )
    args_schema: Type[BaseModel] = LookupCMSCoverageInput

    def _run(self, cpt_code: str) -> dict[str, Any]:
        skill = tool_context.get_current_skill() or "unknown"
        args_str = json.dumps({"cpt_code": cpt_code}, default=str)[:200]
        print(f"[TOOL] {skill} -> {self.name}({args_str})")
        return lookup_cms_coverage(cpt_code)
