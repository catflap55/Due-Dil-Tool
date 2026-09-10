"""Financial summary from Companies House filing history (lightweight metrics, no full iXBRL parse)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.uk.companies_house import CompaniesHouseClient


def _parse_ch_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def summarize_filings(api_key: str, company_number: str) -> Dict[str, Any]:
    """
    Extract filing recency and latest accounts indicator from filing history.
    Full balance-sheet extraction would require downloading and parsing iXBRL (future work).
    """

    ch = CompaniesHouseClient(api_key)
    hist = ch.filing_history(company_number, size=100)
    items: List[Dict[str, Any]] = hist.get("items") or []
    latest_accounts: Optional[Dict[str, Any]] = None
    for it in items:
        desc = (it.get("description") or "").lower()
        ctype = (it.get("type") or "").upper()
        if "accounts" in desc or ctype in ("AA", "AUD"):
            latest_accounts = {
                "filed_on": it.get("date"),
                "description": it.get("description"),
                "type": it.get("type"),
                "transaction_id": it.get("transaction_id"),
            }
            break
    overdue_pattern = re.compile(r"overdue|late", re.I)
    red_hints: List[str] = []
    for it in items[:30]:
        d = it.get("description") or ""
        if overdue_pattern.search(d):
            red_hints.append(d[:200])
            break

    filing_dates = [_parse_ch_date(it.get("date")) for it in items]
    filing_dates_valid = [d for d in filing_dates if d]
    newest = max(filing_dates_valid) if filing_dates_valid else None
    oldest = min(filing_dates_valid) if filing_dates_valid else None

    metrics = {
        "latest_accounts_filing": latest_accounts,
        "filing_count_in_window": len(items),
        "newest_filing_date": newest.isoformat() if newest else None,
        "note": (
            "Key line-item balance sheet figures require iXBRL download/parse (optional future module). "
            "This summary uses official filing metadata only."
        ),
        "overdue_or_late_hints": red_hints[:5],
    }
    return metrics


def days_since_accounts(latest_accounts: Optional[Dict[str, Any]]) -> Optional[float]:
    """Return approximate days since last accounts filing for scoring."""

    if not latest_accounts:
        return None
    filed = _parse_ch_date(latest_accounts.get("filed_on"))
    if not filed:
        return None
    now = datetime.now(timezone.utc)
    return (now - filed).total_seconds() / 86400.0
