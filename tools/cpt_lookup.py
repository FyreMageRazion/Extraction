"""
CPT/HCPCS lookup via Tavily search. Returns code, description, active, source_urls.
"""

from __future__ import annotations

from typing import Any

from .tavily_client import tavily_search

CPT_DOMAINS = ["cms.gov", "ama-assn.org"]


def lookup_cpt(code: str) -> dict[str, Any]:
    """
    Look up CPT or HCPCS code. Returns code, description, active, source_urls.
    On no results or error returns status "unverified".
    """
    result: dict[str, Any] = {
        "code": str(code).strip() if code else "",
        "description": "",
        "active": False,
        "source_urls": [],
    }
    if not code or not str(code).strip():
        result["status"] = "unverified"
        return result

    code_clean = str(code).strip()
    result["code"] = code_clean

    try:
        resp = tavily_search(
            query=f"CPT HCPCS code {code_clean}",
            include_domains=CPT_DOMAINS,
            max_results=3,
        )
        results_list = resp.get("results") or []
        answer = (resp.get("answer") or "").strip()

        urls = []
        for r in results_list:
            u = (r.get("url") or "").strip()
            if u:
                urls.append(u)

        if urls:
            result["source_urls"] = urls[:5]
        if answer:
            result["description"] = answer[:500]
            result["active"] = "deleted" not in answer.lower() and "invalid" not in answer.lower()
        if results_list and not result["description"]:
            content = " ".join((r.get("content") or "")[:200] for r in results_list)
            result["description"] = content[:500]

        if not result["source_urls"] and not result["description"]:
            result["status"] = "unverified"
    except Exception:
        result["status"] = "unverified"

    return result
