"""
NPI Registry lookup using the public CMS API. No auth required.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any

NPI_API_BASE = "https://npiregistry.cms.hhs.gov/api/"


def lookup_npi(npi: str) -> dict[str, Any]:
    """
    Look up provider by NPI. Returns provider_name, active, taxonomy, state, source_urls.
    On failure returns status "unverified".
    """
    result: dict[str, Any] = {
        "provider_name": "",
        "active": False,
        "taxonomy": "",
        "state": "",
        "source_urls": [],
    }
    if not npi or not str(npi).strip():
        result["status"] = "unverified"
        return result

    npi_clean = str(npi).strip()
    url = f"{NPI_API_BASE}?version=2.1&number={npi_clean}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PA-POC/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        result["status"] = "unverified"
        return result

    results_list = data.get("results") or []
    if not results_list:
        result["status"] = "unverified"
        return result

    first = results_list[0]
    basic = first.get("basic") or {}
    result["provider_name"] = basic.get("name") or basic.get("organization_name") or ""
    result["active"] = (basic.get("status") or "").lower() == "active"
    taxonomies = first.get("taxonomies") or []
    if taxonomies:
        result["taxonomy"] = (taxonomies[0].get("desc") or taxonomies[0].get("code") or "")
    addresses = first.get("addresses") or []
    if addresses:
        result["state"] = (addresses[0].get("state") or "")
    result["source_urls"] = [f"https://npiregistry.cms.hhs.gov/search?number={npi_clean}"]

    return result
