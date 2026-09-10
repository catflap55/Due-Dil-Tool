"""Optional Open BRIS aggregator (third-party; user supplies API key in Admin)."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests


def query_open_bris(
    api_key: Optional[str],
    *,
    country: str,
    query: str,
    base_url: str = "https://openbris.eu/api/v1",
) -> Dict[str, Any]:
    """
    Placeholder request shape — Open BRIS paths vary; user must align with their account docs.

    When no key: return skip. When key set: attempt a generic search GET (adjust to official docs).
    """

    if not api_key:
        return {
            "ok": False,
            "skipped": True,
            "reason": "Open BRIS API key not set (optional third-party service).",
        }
    # Conservative stub: documented endpoints may differ; returns structured hint.
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    try:
        # Example-only URL — replace after verifying current Open BRIS docs
        url = f"{base_url}/search"
        r = requests.get(
            url,
            params={"country": country, "q": query},
            headers=headers,
            timeout=25,
        )
        if r.status_code >= 400:
            return {
                "ok": False,
                "error": r.text[:800],
                "status": r.status_code,
                "note": "Adjust open_bris URL/params per your Open BRIS dashboard documentation.",
            }
        try:
            return {"ok": True, "data": r.json()}
        except ValueError:
            return {"ok": True, "data": {"raw": r.text[:2000]}}
    except requests.RequestException as e:
        return {"ok": False, "error": str(e)}

