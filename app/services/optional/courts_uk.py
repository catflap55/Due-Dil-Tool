"""UK case-law — search link-outs (National Archives Find Case Law style)."""

from __future__ import annotations

from typing import Any, Dict
from urllib.parse import quote_plus


def find_case_law_search_url(query: str) -> str:
    """Official-ish search URL builder for manual follow-up."""

    q = quote_plus(query.strip())
    return f"https://caselaw.nationalarchives.gov.uk/search?q={q}"


def court_findings_stub(company_name: str) -> Dict[str, Any]:
    """
    Best-effort dashboard row: external search link — no scraped judgment text in v1.

    Automated judgment APIs are jurisdiction-specific; this module stays transparent.
    """

    return {
        "summary": (
            "No automated extraction in this release. "
            "Use the link below to search UK tribunal / court judgments (beta services may change)."
        ),
        "search_url": find_case_law_search_url(company_name),
        "national_archives_notice": True,
        "disclaimer": "Not legal advice. Verify citations independently.",
    }
