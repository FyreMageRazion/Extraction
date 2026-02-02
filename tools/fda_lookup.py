"""
FDA device/drug approval and recall lookup via Tavily search.
"""

from __future__ import annotations

from typing import Any

from .tavily_client import tavily_search

FDA_DOMAINS = ["fda.gov"]


def lookup_fda(name: str) -> dict[str, Any]:
    """
    Look up FDA approval and recall for device or drug. Returns approval_status, indication_match, recall_info, source_urls.
    On no results or error returns status "unverified".
    """
    result: dict[str, Any] = {
        "approval_status": "",
        "indication_match": False,
        "recall_info": "",
        "source_urls": [],
    }
    if not name or not str(name).strip():
        result["status"] = "unverified"
        return result

    try:
        resp = tavily_search(
            query=f"FDA approval recall {name}",
            include_domains=FDA_DOMAINS,
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
            result["approval_status"] = answer[:500]
            result["indication_match"] = "approved" in answer.lower() and "recall" not in answer.lower()
            if "recall" in answer.lower():
                result["recall_info"] = answer[:500]
        if not result["source_urls"] and not result["approval_status"]:
            result["status"] = "unverified"
    except Exception:
        result["status"] = "unverified"

    return result
