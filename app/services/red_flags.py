"""Central red-flag evaluation from module outputs."""

from __future__ import annotations

from typing import Any, Dict, List

from app.services.types import RedFlag


def collect_red_flags(
    *,
    country: str,
    profile: Dict[str, Any] | None,
    vat_result: Dict[str, Any] | None,
    financial: Dict[str, Any] | None,
    psc_data: Dict[str, Any] | None,
) -> List[RedFlag]:
    """Derive red flags from structured artefacts (best-effort rules)."""

    flags: List[RedFlag] = []

    if profile:
        status = (profile.get("company_status") or "").lower()
        if status and "liquidation" in status:
            flags.append(
                RedFlag(
                    severity="critical",
                    code="UK_STATUS_LIQUIDATION",
                    explanation=f"Company status suggests liquidation-related state: {profile.get('company_status')}",
                    evidence_refs=["Companies House profile"],
                )
            )
        if status and "administration" in status:
            flags.append(
                RedFlag(
                    severity="warning",
                    code="UK_STATUS_ADMINISTRATION",
                    explanation=f"Company status: {profile.get('company_status')}",
                    evidence_refs=["Companies House profile"],
                )
            )

    if vat_result and not vat_result.get("skipped"):
        if vat_result.get("error"):
            flags.append(
                RedFlag(
                    severity="warning",
                    code="VAT_CHECK_FAILED",
                    explanation=str(vat_result.get("error"))[:500],
                    evidence_refs=["HMRC or VIES"],
                )
            )
        elif vat_result.get("valid") is False:
            flags.append(
                RedFlag(
                    severity="warning",
                    code="VAT_INVALID",
                    explanation="VAT register reports invalid / not found for this number.",
                    evidence_refs=["HMRC or VIES"],
                )
            )

    if financial:
        hints = financial.get("overdue_or_late_hints") or []
        if hints:
            flags.append(
                RedFlag(
                    severity="warning",
                    code="FILING_LATE_HINT",
                    explanation="Filing history text suggests overdue/late accounts (verify on CH).",
                    evidence_refs=hints[:3],
                )
            )

    if psc_data and (psc_data.get("total") == 0):
        flags.append(
            RedFlag(
                severity="info",
                code="PSC_EMPTY",
                explanation="No PSC entries returned (may be exempt or not yet filed).",
                evidence_refs=["Companies House PSC"],
            )
        )

    return flags
