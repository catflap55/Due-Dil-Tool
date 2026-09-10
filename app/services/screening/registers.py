"""Public register deep-links for analyst follow-up."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus


def register_links(
    *,
    company_name: str,
    country_code: str,
    company_number: Optional[str] = None,
) -> Dict[str, Any]:
    q = quote_plus((company_name or "").strip())
    cc = (country_code or "").upper()
    num = (company_number or "").strip().upper()
    links: List[Dict[str, str]] = [
        {
            "name": "OpenCorporates",
            "href": f"https://opencorporates.com/companies?q={q}",
            "note": "Cross-jurisdiction company index.",
        },
        {
            "name": "GLEIF LEI search",
            "href": f"https://search.gleif.org/#/search/{q}",
            "note": "Legal Entity Identifier records.",
        },
    ]
    if cc == "GB":
        if num:
            links.insert(
                0,
                {
                    "name": "Companies House profile",
                    "href": f"https://find-and-update.company-information.service.gov.uk/company/{num}",
                    "note": "Official UK filing profile.",
                },
            )
        else:
            links.insert(
                0,
                {
                    "name": "Companies House search",
                    "href": f"https://find-and-update.company-information.service.gov.uk/search?q={q}",
                    "note": "Official UK register search.",
                },
            )
        links.append(
            {
                "name": "The Gazette notices",
                "href": f"https://www.thegazette.co.uk/all-notices/notice?text={q}",
                "note": "Official public notices including insolvency.",
            }
        )
        links.append(
            {
                "name": "Find Case Law",
                "href": f"https://caselaw.nationalarchives.gov.uk/judgments?query={q}",
                "note": "National Archives UK judgments.",
            }
        )
    else:
        links.insert(
            0,
            {
                "name": "e-Justice business registers",
                "href": "https://e-justice.europa.eu/content_business_registers_in_member_states-106-en.do",
                "note": "EU member-state register directory.",
            },
        )
        links.append(
            {
                "name": "VIES VAT query",
                "href": "https://ec.europa.eu/taxation_customs/vies/",
                "note": "European Commission VAT information exchange.",
            },
        )
        links.append(
            {
                "name": "Curia case law",
                "href": "https://curia.europa.eu/juris/recherche.jsf?language=en",
                "note": "Court of Justice of the European Union.",
            },
        )
    return {"query": company_name, "country": cc, "company_number": num or None, "links": links}
