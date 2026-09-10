"""Optional NewsAPI.org integration — sends query to third-party; off by default."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests


def fetch_headlines(
    api_key: Optional[str],
    *,
    company_query: str,
    language: str = "en",
    page_size: int = 10,
) -> Dict[str, Any]:
    """Return recent articles matching query; privacy-sensitive (non-government)."""

    if not api_key:
        return {"ok": False, "skipped": True, "reason": "NewsAPI key not configured."}
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": company_query,
        "language": language,
        "pageSize": page_size,
        "sortBy": "publishedAt",
    }
    r = requests.get(url, params=params, headers={"X-Api-Key": api_key}, timeout=25)
    if r.status_code >= 400:
        return {"ok": False, "error": r.text[:800], "status": r.status_code}
    data = r.json()
    arts = data.get("articles") or []
    trimmed = [
        {
            "title": a.get("title"),
            "description": (a.get("description") or "")[:500],
            "url": a.get("url"),
            "publishedAt": a.get("publishedAt"),
            "source": (a.get("source") or {}).get("name"),
        }
        for a in arts[:page_size]
    ]
    return {"ok": True, "articles": trimmed, "privacy_note": "Queries are sent to NewsAPI.org."}
