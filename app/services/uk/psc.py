"""Persons with Significant Control (UK) via Companies House."""

from __future__ import annotations

import base64
from typing import Any, Dict, List

import requests

from app.services.uk.companies_house import BASE


def fetch_psc(api_key: str, company_number: str) -> Dict[str, Any]:
    """Return PSC list summary for AML display (not legal advice)."""

    auth = base64.b64encode(f"{api_key}:".encode("ascii")).decode("ascii")
    r = requests.get(
        f"{BASE}/company/{requests.utils.quote(company_number, safe='')}/persons-with-significant-control",
        headers={"Authorization": f"Basic {auth}"},
        timeout=30,
    )
    if r.status_code == 404:
        return {"items": [], "note": "No PSC register or not yet filed."}
    r.raise_for_status()
    data = r.json()
    items: List[Dict[str, Any]] = data.get("items") or []
    simplified: List[Dict[str, Any]] = []
    for it in items:
        simplified.append(
            {
                "kind": it.get("kind"),
                "name": it.get("name"),
                "notified_on": it.get("notified_on"),
                "ceased_on": it.get("ceased_on"),
                "natures_of_control": (it.get("natures_of_control") or [])[:5],
            }
        )
    return {"items": simplified, "total": len(simplified), "aml_note": True}
