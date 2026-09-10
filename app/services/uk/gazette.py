"""UK Gazette / insolvency hints — best-effort link and search URL (no scraping by default)."""

from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import quote_plus


def gazette_search_url(company_name: str) -> str:
    """Return official The Gazette search URL for user follow-up."""

    q = quote_plus(company_name.strip())
    return f"https://www.thegazette.co.uk/all-notices/notice?text={q}"


def insolvency_search_hint(
    company_name: str,
    company_number: Optional[str] = None,
) -> Dict[str, Any]:
    """Structured hint row for dashboard (Companies House API covers many insolvency events)."""

    out: Dict[str, Any] = {
        "gazette_search_url": gazette_search_url(company_name),
        "disclaimer": (
            "Verify insolvency and Gazette notices on official sources. This link opens a search on The Gazette website."
        ),
    }
    if company_number:
        out["companies_house_profile_url"] = (
            "https://find-and-update.company-information.service.gov.uk/company/"
            f"{company_number}"
        )
    return out
