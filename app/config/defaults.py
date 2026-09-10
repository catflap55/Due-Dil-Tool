"""Default scoring weights and module metadata (overridable in Settings)."""

import json
from typing import Any, Dict

# Default weights for credit proxy (0–100 scale components; normalized in scorer).
DEFAULT_SCORING_WEIGHTS: Dict[str, float] = {
    "filing_recency": 25.0,  # newer filings = better
    "net_assets_positive": 25.0,
    "vat_valid": 20.0,
    "identity_confidence": 15.0,
    "psc_transparency": 15.0,  # PSC present vs empty
}


def country_list() -> list[dict]:
    """UK + EU-27 ISO codes with display names."""

    eu = [
        ("AT", "Austria"),
        ("BE", "Belgium"),
        ("BG", "Bulgaria"),
        ("HR", "Croatia"),
        ("CY", "Cyprus"),
        ("CZ", "Czech Republic"),
        ("DK", "Denmark"),
        ("EE", "Estonia"),
        ("FI", "Finland"),
        ("FR", "France"),
        ("DE", "Germany"),
        ("GR", "Greece"),
        ("HU", "Hungary"),
        ("IE", "Ireland"),
        ("IT", "Italy"),
        ("LV", "Latvia"),
        ("LT", "Lithuania"),
        ("LU", "Luxembourg"),
        ("MT", "Malta"),
        ("NL", "Netherlands"),
        ("PL", "Poland"),
        ("PT", "Portugal"),
        ("RO", "Romania"),
        ("SK", "Slovakia"),
        ("SI", "Slovenia"),
        ("ES", "Spain"),
        ("SE", "Sweden"),
    ]
    rows = [{"code": "GB", "name": "United Kingdom"}]
    rows.extend({"code": c, "name": n} for c, n in sorted(eu, key=lambda x: x[1]))
    return rows


# Capability matrix: honesty for EU automation depth (read-only hints for UI).
EU_IDENTITY_CAPABILITY: Dict[str, str] = {
    "**": (
        "EU company registers vary by country. Full automated identity is phased; "
        "VIES validates VAT numbers EU-wide where applicable."
    ),
}


MODULE_KEYS = [
    "identifiers",
    "identity",
    "vat",
    "financial",
    "courts",
    "credit_proxy",
    "psc",
    "insolvency",
    "sanctions",
    "registers",
    "news",
    "open_bris",
]


def default_config_json() -> str:
    """Serialised default admin config (no secrets)."""

    return json.dumps(
        {
            "scoring_weights": DEFAULT_SCORING_WEIGHTS.copy(),
            "modules_enabled_defaults": {
                "identifiers": True,
                "identity": True,
                "vat": True,
                "financial": True,
                "courts": True,
                "credit_proxy": True,
                "psc": True,
                "insolvency": True,
                "sanctions": True,
                "registers": True,
                "news": False,
                "open_bris": False,
            },
        },
        indent=2,
    )
