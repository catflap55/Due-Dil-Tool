"""Official sanctions / watchlist search links (no scraping, no API keys)."""

from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import quote_plus


def screening_links(company_name: str, country_code: str) -> Dict[str, Any]:
    q = quote_plus((company_name or "").strip())
    cc = (country_code or "").upper()
    links: List[Dict[str, str]] = [
        {
            "name": "UK OFSI consolidated list",
            "href": "https://sanctionssearchapp.ofsi.hmtreasury.gov.uk/",
            "note": "HM Treasury financial sanctions search. Paste the legal name.",
        },
        {
            "name": "EU sanctions map",
            "href": "https://www.sanctionsmap.eu/",
            "note": "Council of the EU restrictive measures overview.",
        },
        {
            "name": "US OFAC SDN search",
            "href": "https://sanctionssearch.ofac.treas.gov/",
            "note": "US Treasury specially designated nationals.",
        },
        {
            "name": "UN Security Council lists",
            "href": "https://www.un.org/securitycouncil/content/un-sc-consolidated-list",
            "note": "United Nations consolidated sanctions list.",
        },
        {
            "name": "OpenSanctions search",
            "href": f"https://www.opensanctions.org/search/?q={q}",
            "note": "Independent aggregation of official lists. Verify on the source register.",
        },
    ]
    if cc == "GB":
        links.insert(
            1,
            {
                "name": "UK disqualified directors",
                "href": f"https://find-and-update.company-information.service.gov.uk/register-of-disqualifications/directors?q={q}",
                "note": "Companies House register of disqualified directors.",
            },
        )
    return {
        "query": company_name,
        "country": cc,
        "links": links,
        "disclaimer": "These open official or well-known search pages. This workstation does not scrape watchlists.",
    }
