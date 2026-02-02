"""
CMS NCD/LCD coverage lookup via Tavily search.
"""

from __future__ import annotations

from typing import Any

from .tavily_client import tavily_search

CMS_DOMAINS = ["cms.gov"]


def lookup_cms_coverage(cpt_code: str) -> dict[str, Any]:
    """
    Look up CMS NCD/LCD coverage for a CPT code. Returns ncd_lcd_references, coverage_notes, source_urls.
    On no results or error returns status "unverified".
    """
    result: dict[str, Any] = {
        "ncd_lcd_references": [],
        "coverage_notes": "",
        "source_urls": [],
    }
    if not cpt_code or not str(cpt_code).strip():
        result["status"] = "unverified"
        return result

    try:
        resp = tavily_search(
            query=f"CMS NCD LCD coverage {cpt_code}",
            include_domains=CMS_DOMAINS,
            max_results=3,
        )
        results_list = resp.get("results") or []
        answer = (resp.get("answer") or "").strip()

        urls = []
        refs = []
        for r in results_list:
            u = (r.get("url") or "").strip()
            if u:
                urls.append(u)
            title = (r.get("title") or "").strip()
            if title and ("NCD" in title or "LCD" in title or "coverage" in title.lower()):
                refs.append(title)

        if urls:
            result["source_urls"] = urls[:5]
        if answer:
            result["coverage_notes"] = answer[:1000]
        if refs:
            result["ncd_lcd_references"] = refs[:10]
        if not result["source_urls"] and not result["coverage_notes"]:
            result["status"] = "unverified"
    except Exception:
        result["status"] = "unverified"

    return result
