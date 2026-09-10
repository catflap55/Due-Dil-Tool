"""EU company identity placeholders — phased national adapters."""

from __future__ import annotations

from typing import Any, Dict

from app.config.defaults import EU_IDENTITY_CAPABILITY


def explain_capability(country_code: str) -> Dict[str, Any]:
    """Return UX message describing automation level for EU identity checks."""

    return {
        "country": country_code.upper(),
        "message": EU_IDENTITY_CAPABILITY.get(
            "**",
            "EU identity checks are phased; use VAT (VIES) and national register follow-up.",
        ),
        "open_bris_optional": True,
    }
