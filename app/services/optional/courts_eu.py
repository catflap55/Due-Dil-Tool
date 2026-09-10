"""EU / ECLI-oriented link-out for case research."""

from __future__ import annotations

from typing import Any, Dict


def ecli_search_hint(company_name: str) -> Dict[str, Any]:
    """Best-effort: point to EU case law resources; national courts vary."""

    return {
        "summary": (
            "EU-wide case search is fragmented. Use Curia and national portals "
            "with the company or party name; this module does not ingest judgment text."
        ),
        "curia_portal": "https://curia.europa.eu/",
        "eu_law_portal": "https://europa.eu/european-union/law_en",
        "query_suggestion": company_name,
        "disclaimer": "Not legal advice.",
    }
