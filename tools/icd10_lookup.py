"""
ICD-10 lookup via Tavily search.
- By code: returns code, description, valid, source_urls, confidence.
- By condition: returns condition, codes (list of {code, description}), source_urls, confidence.
"""

from __future__ import annotations

import re
from typing import Any

from .tavily_client import tavily_search

ICD10_DOMAINS = ["cms.gov", "icd.codes", "icd10data.com"]

# Rough pattern for ICD-10 code (e.g. M54.5, E11.9, Z00.00)
ICD10_CODE_PATTERN = re.compile(r"\b([A-Z]\d{2}(?:\.\d{2,4})?)\b", re.IGNORECASE)


def _lookup_by_code(code_clean: str) -> dict[str, Any]:
    """Look up a single ICD-10 code; returns code, description, valid, source_urls, confidence."""
    result: dict[str, Any] = {
        "code": code_clean,
        "description": "",
        "valid": False,
        "source_urls": [],
        "confidence": "low",
    }
    try:
        resp = tavily_search(
            query=f"ICD-10 code {code_clean}",
            include_domains=ICD10_DOMAINS,
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
            result["valid"] = "invalid" not in answer.lower() and "not found" not in answer.lower()
        if results_list:
            content = " ".join((r.get("content") or "")[:200] for r in results_list)
            if content and not result["description"]:
                result["description"] = content[:500]
            if len(results_list) >= 2:
                result["confidence"] = "high"
            elif len(results_list) == 1:
                result["confidence"] = "medium"

        if not result["source_urls"] and not result["description"]:
            result["status"] = "unverified"
    except Exception:
        result["status"] = "unverified"

    return result


def _lookup_by_condition(condition_clean: str) -> dict[str, Any]:
    """Look up ICD-10 codes for a disease or medical condition."""
    result: dict[str, Any] = {
        "condition": condition_clean,
        "codes": [],
        "source_urls": [],
        "confidence": "low",
    }
    try:
        resp = tavily_search(
            query=f"ICD-10 code for {condition_clean}",
            include_domains=ICD10_DOMAINS,
            max_results=5,
        )
        results_list = resp.get("results") or []
        answer = (resp.get("answer") or "").strip()
        combined = answer + " " + " ".join((r.get("content") or "")[:300] for r in results_list)

        urls = []
        for r in results_list:
            u = (r.get("url") or "").strip()
            if u:
                urls.append(u)
        if urls:
            result["source_urls"] = urls[:5]

        # Extract code–description pairs (e.g. "M54.5 - Low back pain" or "E11.9 Type 2 diabetes")
        seen = set()
        for match in ICD10_CODE_PATTERN.finditer(combined):
            code = match.group(1).upper()
            if code in seen:
                continue
            seen.add(code)
            start, end = match.start(), match.end()
            # Take surrounding text as description (up to ~80 chars)
            snippet = combined[max(0, start - 5) : end + 80].strip()
            desc = re.sub(r"^[^\w\-]*", "", snippet).strip()[:120]
            result["codes"].append({"code": code, "description": desc or code})

        if not result["codes"] and combined:
            # No structured codes found; put raw snippet as one entry
            result["codes"].append({"code": "", "description": combined[:400]})
        if len(result["codes"]) >= 2:
            result["confidence"] = "high"
        elif len(result["codes"]) == 1:
            result["confidence"] = "medium"

        if not result["source_urls"] and not result["codes"]:
            result["status"] = "unverified"
    except Exception:
        result["status"] = "unverified"

    return result


def lookup_icd10(code: str | None = None, condition: str | None = None) -> dict[str, Any]:
    """
    Look up ICD-10 by code and/or by disease/medical condition.

    - code: ICD-10 code (e.g. M54.5). Returns code, description, valid, source_urls, confidence.
    - condition: Disease or medical condition (e.g. low back pain, type 2 diabetes). Returns
      condition, codes (list of {code, description}), source_urls, confidence.

    Use code for validation of a known code; use condition to find ICD-10 codes for a diagnosis.
    At least one of code or condition must be provided.
    """
    code_clean = (code or "").strip()
    condition_clean = (condition or "").strip()

    if not code_clean and not condition_clean:
        return {"status": "unverified", "error": "Provide either code or condition."}

    if code_clean and not condition_clean:
        return _lookup_by_code(code_clean)

    if condition_clean and not code_clean:
        return _lookup_by_condition(condition_clean)

    # Both provided: return both code lookup and condition lookup
    by_code = _lookup_by_code(code_clean)
    by_condition = _lookup_by_condition(condition_clean)
    return {
        "by_code": by_code,
        "by_condition": by_condition,
    }
