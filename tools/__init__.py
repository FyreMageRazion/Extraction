"""
PA POC tools: ICD-10, CPT, NPI, CMS coverage, FDA, PubMed.
Each tool is wrapped to log [TOOL] current_skill -> tool_name(args).
"""

from __future__ import annotations

import functools
import inspect
import json
from inspect import Parameter
from typing import Any, Callable, List

from crewai.tools.base_tool import BaseTool, Tool
from pydantic import BaseModel, Field, create_model

from . import context as tool_context
from .base_lookups import LookupCMSCoverageBaseTool, LookupNPIBaseTool
from .cms_coverage_lookup import lookup_cms_coverage
from .cpt_lookup import lookup_cpt
from .fda_lookup import lookup_fda
from .icd10_lookup import lookup_icd10
from .npi_lookup import lookup_npi
from .pubmed_lookup import search_pubmed


def _cache_lookup(_args: Any = None, _result: Any = None) -> bool:
    """Cache lookup results within a run to avoid duplicate Tavily/NPI calls for same args."""
    return True


def _wrap_with_logging(
    tool_name: str,
    func: Callable[..., Any],
) -> Callable[..., Any]:
    """Wrap func to log [TOOL] current_skill -> tool_name(args) then call func.
    Preserves func's signature so CrewAI infers correct argument schema."""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        skill = tool_context.get_current_skill() or "unknown"
        args_str = json.dumps({"args": args, "kwargs": kwargs}, default=str)[:200]
        print(f"[TOOL] {skill} -> {tool_name}({args_str})")
        return func(*args, **kwargs)
    wrapper.__signature__ = inspect.signature(func)
    return wrapper


# Param descriptions for LLM (CrewAI best practice: Field descriptions in schema)
_PARAM_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "lookup_icd10": {"code": "ICD-10 code from Input.diagnoses.", "condition": "Disease or condition from Input.diagnoses for finding codes."},
    "lookup_cpt": {"code": "CPT or HCPCS procedure code from Input.procedures_requested."},
    "lookup_fda": {"name": "Device or drug name from the case for FDA approval/recall lookup."},
    "search_pubmed": {"query": "Search query built from Input (diagnoses, procedure_descriptions, clinical_findings, or denial reasons)."},
}


def _schema_from_function(
    tool_name: str,
    func: Callable[..., Any],
    param_descriptions: dict[str, str] | None = None,
) -> type[BaseModel]:
    """Build a Pydantic args_schema from a function's signature with optional Field descriptions."""
    sig = inspect.signature(func)
    descriptions = param_descriptions or _PARAM_DESCRIPTIONS.get(tool_name, {})
    fields: dict[str, Any] = {}
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        if param.kind in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD):
            continue
        annotation = param.annotation if param.annotation is not Parameter.empty else Any
        desc = descriptions.get(name, "")
        if param.default is Parameter.empty:
            fields[name] = (annotation, Field(..., description=desc)) if desc else (annotation, ...)
        else:
            fields[name] = (annotation, Field(default=param.default, description=desc)) if desc else (annotation, param.default)
    schema_name = "".join(w.title() for w in tool_name.split("_")) + "Input"
    if fields:
        return create_model(schema_name, **fields)
    return create_model(schema_name, __base__=BaseModel)


def get_pa_tools(skill_name: str | None = None) -> List[BaseTool]:
    """
    Return list of CrewAI Tool instances for PA flow.
    Each tool logs which skill triggered it (runner sets current_skill before kickoff).
    """
    tools: List[BaseTool] = [
        Tool(
            name="lookup_icd10",
            description="Look up ICD-10 by code OR by disease/medical condition. (1) code: ICD-10 code (e.g. M54.5) returns code, description, valid, source_urls, confidence. (2) condition: disease or condition (e.g. low back pain, type 2 diabetes) returns condition, codes list with code and description, source_urls, confidence. Use for diagnosis validation and for finding ICD-10 codes from a condition. Provide at least one of code or condition.",
            func=_wrap_with_logging("lookup_icd10", lookup_icd10),
            args_schema=_schema_from_function("lookup_icd10", lookup_icd10),
            cache_function=_cache_lookup,
        ),
        Tool(
            name="lookup_cpt",
            description="Look up CPT or HCPCS procedure code from AMA/CMS sources. Use for procedure code validation. Returns code, description, active, source_urls.",
            func=_wrap_with_logging("lookup_cpt", lookup_cpt),
            args_schema=_schema_from_function("lookup_cpt", lookup_cpt),
            cache_function=_cache_lookup,
        ),
        LookupNPIBaseTool(cache_function=_cache_lookup),
        LookupCMSCoverageBaseTool(cache_function=_cache_lookup),
        Tool(
            name="lookup_fda",
            description="Look up FDA device or drug approval and recall status. Use for coverage and medical necessity when devices/drugs are involved. Returns approval_status, indication_match, recall_info, source_urls.",
            func=_wrap_with_logging("lookup_fda", lookup_fda),
            args_schema=_schema_from_function("lookup_fda", lookup_fda),
            cache_function=_cache_lookup,
        ),
        Tool(
            name="search_pubmed",
            description="Search PubMed for literature and clinical evidence. Use for medical necessity and appeal drafting. Returns list of items with pmid, citation, relevance_summary, source_urls.",
            func=_wrap_with_logging("search_pubmed", search_pubmed),
            args_schema=_schema_from_function("search_pubmed", search_pubmed),
            cache_function=_cache_lookup,
        ),
    ]
    return tools
