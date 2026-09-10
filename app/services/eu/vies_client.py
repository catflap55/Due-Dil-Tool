"""VIES SOAP client for EU VAT number validation."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from zeep import Client

LOG = logging.getLogger(__name__)

WSDL = "https://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl"

_client_singleton: Optional[Client] = None


def _client() -> Client:
    global _client_singleton  # noqa: PLW0603 — single process desktop app
    if _client_singleton is None:
        _client_singleton = Client(WSDL)
    return _client_singleton


def _split_country_and_number(full_vat: str) -> tuple[str, str]:
    """Return (country_code, national_number_digits) — country is first two letters if present."""

    s = full_vat.strip().upper().replace(" ", "")
    if len(s) >= 2 and s[0:2].isalpha():
        return s[0:2], s[2:]
    return "", s


def check_vat(vat_number: str) -> Dict[str, Any]:
    """
    Call VIES checkVat. Pass full VAT including country prefix (e.g. DE123...).
    """

    country, num = _split_country_and_number(vat_number)
    if len(country) != 2:
        return {"valid": False, "error": "VAT number should start with a 2-letter EU country code."}
    if not num:
        return {"valid": False, "error": "Missing national VAT number after country code."}
    try:
        result = _client().service.checkVat(country, num)
    except Exception as e:  # noqa: BLE001
        LOG.warning("VIES error: %s", e)
        return {"valid": False, "error": str(e)}
    return {
        "valid": bool(result.get("valid")) if isinstance(result, dict) else bool(getattr(result, "valid", False)),
        "country_code": country,
        "name": result.get("name") if isinstance(result, dict) else getattr(result, "name", None),
        "address": result.get("address") if isinstance(result, dict) else getattr(result, "address", None),
        "request_date": str(
            result.get("requestDate") if isinstance(result, dict) else getattr(result, "requestDate", "")
        ),
    }


def check_vat_simple(country_code: str, vat_digits: str) -> Dict[str, Any]:
    """Validate using separate country and number (UI may collect separately)."""

    cc = country_code.strip().upper()
    num = re.sub(r"\s+", "", vat_digits or "")
    return check_vat(f"{cc}{num}")
