"""
Thin wrapper around Tavily search. Uses allowed domains aligned with
authoritative_web_search skill. Used by all web-backed tools.
"""

from __future__ import annotations

import os
from typing import Any

# Allowed domains from authoritative_web_search skill (coding, provider, FDA, clinical)
TAVILY_ALLOWED_DOMAINS = [
    "cms.gov",
    "icd.codes",
    "icd10data.com",
    "ama-assn.org",
    "npiregistry.cms.hhs.gov",
    "providerdata.cms.gov",
    "fda.gov",
    "pubmed.ncbi.nlm.nih.gov",
]


def tavily_search(
    query: str,
    include_domains: list[str] | None = None,
    max_results: int = 5,
) -> dict[str, Any]:
    """
    Run Tavily search. Returns raw Tavily response or {"results": [], "answer": ""} on failure.
    """
    domains = include_domains if include_domains is not None else TAVILY_ALLOWED_DOMAINS
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return {"results": [], "answer": ""}

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            include_domains=domains,
            max_results=max_results,
        )
        if isinstance(response, dict):
            return response
        return {"results": getattr(response, "results", []) or [], "answer": getattr(response, "answer", "") or ""}
    except Exception:
        return {"results": [], "answer": ""}
