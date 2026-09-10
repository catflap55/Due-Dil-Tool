"""HMRC OAuth2 client credentials + Check VAT Number lookup (UK)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests

LOG = logging.getLogger(__name__)

TOKEN_URL = "https://api.service.hmrc.gov.uk/oauth/token"
VAT_LOOKUP_BASE = "https://api.service.hmrc.gov.uk/organisations/vat/check-vat-number/lookup"


class HmrcVatClient:
    """
    Uses client_id / client_secret (application-restricted) to obtain Bearer token,
    then calls check VAT lookup. User must register an app at HMRC Developer Hub.

    Sandbox host differs; production URL above used by default — override via config if needed.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        sandbox: bool = False,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.sandbox = sandbox
        base = (
            "https://test-api.service.hmrc.gov.uk"
            if sandbox
            else "https://api.service.hmrc.gov.uk"
        )
        self._token_url = f"{base}/oauth/token"
        self._vat_base = f"{base}/organisations/vat/check-vat-number/lookup"

    def _token(self) -> str:
        r = requests.post(
            self._token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        return str(data["access_token"])

    def check_vat(self, uk_vat_number: str, requester_vat: Optional[str] = None) -> Dict[str, Any]:
        """
        `uk_vat_number` — 9 digits or GB-prefixed as per API docs.
        `requester_vat` — optional; if your app requires it for fraud headers, pass your VAT.
        """

        token = self._token()
        path = f"{self._vat_base}/{requests.utils.quote(uk_vat_number.strip(), safe='')}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.hmrc.1.0+json",
        }
        if requester_vat:
            headers["X-Requester-VAT-Number"] = requester_vat.strip()
        r = requests.get(path, headers=headers, timeout=30)
        if r.status_code == 404:
            return {"valid": False, "message": "Not found / invalid", "raw": None}
        r.raise_for_status()
        return {"valid": True, "message": "OK", "raw": r.json()}


def check_uk_vat_if_configured(
    *,
    client_id: Optional[str],
    client_secret: Optional[str],
    vat_to_check: str,
    sandbox: bool = False,
) -> Dict[str, Any]:
    """Return structured result; if credentials missing, return skip state."""

    if not client_id or not client_secret:
        return {
            "ok": False,
            "skipped": True,
            "reason": "HMRC client_id / client_secret not configured in Admin.",
        }
    try:
        c = HmrcVatClient(client_id, client_secret, sandbox=sandbox)
        return c.check_vat(vat_to_check)
    except requests.HTTPError as e:
        body = e.response.text if e.response is not None else ""
        LOG.warning("HMRC VAT error: %s %s", e, body[:500])
        return {"ok": False, "error": str(e), "body": body[:2000]}
    except Exception as e:  # noqa: BLE001
        LOG.exception("HMRC VAT failure")
        return {"ok": False, "error": str(e)}
