"""
PubMed / literature search via Tavily. Returns list of items with pmid, citation, relevance_summary, source_urls.
"""

from __future__ import annotations

from typing import Any

from .tavily_client import tavily_search

PUBMED_DOMAINS = ["pubmed.ncbi.nlm.nih.gov"]


def search_pubmed(query: str) -> list[dict[str, Any]]:
    """
    Search PubMed/literature. Returns list of {pmid, citation, relevance_summary, source_urls}.
    On failure returns [] or one item with status "unverified".
    """
    if not query or not str(query).strip():
        return [{"pmid": None, "citation": "", "relevance_summary": "", "source_urls": [], "status": "unverified"}]

    try:
        resp = tavily_search(
            query=f"site:pubmed.ncbi.nlm.nih.gov {query}",
            include_domains=PUBMED_DOMAINS,
            max_results=3,
        )
        results_list = resp.get("results") or []
        out: list[dict[str, Any]] = []

        for r in results_list:
            url = (r.get("url") or "").strip()
            title = (r.get("title") or "").strip()
            content = (r.get("content") or "")[:300]
            pmid = None
            if "pubmed.ncbi.nlm.nih.gov" in url:
                try:
                    import re
                    m = re.search(r"(\d{6,})", url)
                    if m:
                        pmid = m.group(1)
                except Exception:
                    pass
            out.append({
                "pmid": pmid,
                "citation": title or content or "",
                "relevance_summary": content,
                "source_urls": [url] if url else [],
            })

        if not out:
            out.append({"pmid": None, "citation": "", "relevance_summary": "", "source_urls": [], "status": "unverified"})
        return out
    except Exception:
        return [{"pmid": None, "citation": "", "relevance_summary": "", "source_urls": [], "status": "unverified"}]
