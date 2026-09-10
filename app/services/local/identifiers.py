"""Local identifier checks — no network, no API keys."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


_UK_VAT_WEIGHTS = (8, 7, 6, 5, 4, 3, 2)


def normalize_uk_company_number(raw: str) -> str:
    s = re.sub(r"[\s-]", "", (raw or "").upper())
    if re.fullmatch(r"\d{1,8}", s):
        return s.zfill(8)
    return s


def uk_company_number_ok(raw: str) -> bool:
    compact = re.sub(r"[\s-]", "", (raw or "").upper())
    if re.fullmatch(r"\d{6,8}", compact):
        return True
    return bool(re.fullmatch(r"(SC|NI|OC|SO|NC|R|IP|SP|NP|NO)\d{6,8}", compact))


def normalize_uk_vat(raw: str) -> str:
    s = re.sub(r"[\s.-]", "", (raw or "").upper())
    if s.startswith("GB"):
        s = s[2:]
    s = re.sub(r"[A-Z]", "", s)
    return s


def uk_vat_checksum_ok(raw: str) -> bool:
    """Standard 9-digit GB VAT modulus-97 check (branch numbers ignored)."""

    digits = normalize_uk_vat(raw)
    if len(digits) not in (9, 12):
        return False
    body = digits[:9]
    if not body.isdigit():
        return False
    total = sum(w * int(d) for w, d in zip(_UK_VAT_WEIGHTS, body[:7]))
    check = int(body[7:9])
    # Primary algorithm; some older numbers use 97 - remainder.
    remainder = total % 97
    return remainder == check or (97 - remainder) == check


_EU_VAT_PATTERNS = {
    "AT": r"U\d{8}",
    "BE": r"0\d{9}",
    "BG": r"\d{9,10}",
    "CY": r"\d{8}[A-Z]",
    "CZ": r"\d{8,10}",
    "DE": r"\d{9}",
    "DK": r"\d{8}",
    "EE": r"\d{9}",
    "EL": r"\d{9}",
    "GR": r"\d{9}",
    "ES": r"[A-Z0-9]\d{7}[A-Z0-9]",
    "FI": r"\d{8}",
    "FR": r"[A-Z0-9]{2}\d{9}",
    "HR": r"\d{11}",
    "HU": r"\d{8}",
    "IE": r"\d{7}[A-Z]{1,2}",
    "IT": r"\d{11}",
    "LT": r"(\d{9}|\d{12})",
    "LU": r"\d{8}",
    "LV": r"\d{11}",
    "MT": r"\d{8}",
    "NL": r"\d{9}B\d{2}",
    "PL": r"\d{10}",
    "PT": r"\d{9}",
    "RO": r"\d{2,10}",
    "SE": r"\d{12}",
    "SI": r"\d{8}",
    "SK": r"\d{10}",
}


def parse_eu_vat(raw: str) -> Optional[tuple[str, str]]:
    s = re.sub(r"[\s.-]", "", (raw or "").upper())
    if len(s) < 4:
        return None
    cc, rest = s[:2], s[2:]
    if cc == "GB":
        return ("GB", rest)
    if cc not in _EU_VAT_PATTERNS and cc != "EL":
        return None
    return cc, rest


def eu_vat_format_ok(raw: str) -> bool:
    parsed = parse_eu_vat(raw)
    if not parsed:
        return False
    cc, rest = parsed
    if cc == "GB":
        return uk_vat_checksum_ok(rest)
    pat = _EU_VAT_PATTERNS.get("EL" if cc == "GR" else cc) or _EU_VAT_PATTERNS.get(cc)
    if not pat:
        return False
    return re.fullmatch(pat, rest) is not None


def inspect_identifiers(
    *,
    country_code: str,
    company_name: str,
    registration_number: Optional[str],
    uk_vat_number: Optional[str],
    eu_vat_input: Optional[str],
) -> Dict[str, Any]:
    """Structured local checks for the dossier."""

    cc = (country_code or "").upper()
    name = (company_name or "").strip()
    findings = []
    ok = True

    if len(name) < 2:
        ok = False
        findings.append({"ok": False, "label": "Legal name", "detail": "Enter at least two characters."})
    else:
        findings.append({"ok": True, "label": "Legal name", "detail": name})

    if registration_number:
        if cc == "GB":
            valid = uk_company_number_ok(registration_number)
            ok = ok and valid
            findings.append(
                {
                    "ok": valid,
                    "label": "UK company number",
                    "detail": normalize_uk_company_number(registration_number)
                    if valid
                    else "Expected 8 digits (or SC/NI/OC prefix).",
                }
            )
        else:
            findings.append(
                {
                    "ok": True,
                    "label": "Registration number",
                    "detail": registration_number.strip(),
                }
            )
    else:
        findings.append(
            {
                "ok": True,
                "label": "Registration number",
                "detail": "Not supplied — name search will be used where the register allows it.",
            }
        )

    vat_raw = (uk_vat_number if cc == "GB" else eu_vat_input) or ""
    if vat_raw.strip():
        if cc == "GB":
            valid = uk_vat_checksum_ok(vat_raw)
            ok = ok and valid
            findings.append(
                {
                    "ok": valid,
                    "label": "UK VAT format",
                    "detail": "Checksum passed." if valid else "Does not match the GB VAT checksum.",
                }
            )
        else:
            valid = eu_vat_format_ok(vat_raw)
            ok = ok and valid
            findings.append(
                {
                    "ok": valid,
                    "label": "EU VAT format",
                    "detail": "Matches the published national pattern." if valid else "Does not match that country’s VAT pattern.",
                }
            )
    else:
        findings.append({"ok": True, "label": "VAT number", "detail": "Not supplied for this run."})

    return {
        "country": cc,
        "ok": ok,
        "findings": findings,
    }
