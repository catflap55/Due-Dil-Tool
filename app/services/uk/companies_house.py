"""Companies House Public Data API client (UK company identity, filings, insolvency hints)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

BASE = "https://api.company-information.service.gov.uk"


def _auth_header(api_key: str) -> Dict[str, str]:
    # CH expects API key as HTTP Basic with empty password (common pattern).
    import base64

    token = base64.b64encode(f"{api_key}:".encode("ascii")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


class CompaniesHouseClient:
    """Thin wrapper around REST endpoints used by the DD tool."""

    def __init__(self, api_key: str) -> None:
        self._key = api_key
        self.session = requests.Session()

    def search_companies(self, query: str, items_per_page: int = 10) -> Dict[str, Any]:
        r = self.session.get(
            f"{BASE}/search/companies",
            params={"q": query, "items_per_page": items_per_page},
            headers=_auth_header(self._key),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def company_profile(self, company_number: str) -> Dict[str, Any]:
        r = self.session.get(
            f"{BASE}/company/{requests.utils.quote(company_number, safe='')}",
            headers=_auth_header(self._key),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def filing_history(self, company_number: str, size: int = 50) -> Dict[str, Any]:
        r = self.session.get(
            f"{BASE}/company/{requests.utils.quote(company_number, safe='')}/filing-history",
            params={"size": size},
            headers=_auth_header(self._key),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def persons_with_significant_control_raw(self, company_number: str) -> requests.Response:
        return self.session.get(
            f"{BASE}/company/{requests.utils.quote(company_number, safe='')}/persons-with-significant-control",
            headers=_auth_header(self._key),
            timeout=30,
        )

    def officers(self, company_number: str) -> Dict[str, Any]:
        r = self.session.get(
            f"{BASE}/company/{requests.utils.quote(company_number, safe='')}/officers",
            headers=_auth_header(self._key),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def charges(self, company_number: str) -> Dict[str, Any]:
        r = self.session.get(
            f"{BASE}/company/{requests.utils.quote(company_number, safe='')}/charges",
            headers=_auth_header(self._key),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()


def resolve_uk_company(
    *,
    api_key: str,
    name: Optional[str],
    registration: Optional[str],
) -> Dict[str, Any]:
    """Resolve Companies House profile and optionally search by name."""

    ch = CompaniesHouseClient(api_key)
    upper_reg = (registration or "").strip().upper().replace(" ", "")
    number: Optional[str] = None
    if upper_reg:
        try:
            prof = ch.company_profile(upper_reg)
            return {"company_number": prof.get("company_number") or upper_reg, "profile": prof}
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code != 404:
                raise
    q = (name or "").strip()
    if not q:
        raise ValueError("Enter a company name or UK company number.")
    data = ch.search_companies(q, items_per_page=5)
    items: List[Dict[str, Any]] = data.get("items") or []
    if not items:
        raise LookupError(f"No Companies House matches for '{q}'.")
    first = items[0]
    num = first.get("company_number")
    if not num:
        raise LookupError("Search result missing company_number.")
    prof = ch.company_profile(num)
    return {"company_number": num, "profile": prof, "search_hits": items}
