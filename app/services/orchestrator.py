"""Run selected due diligence modules and aggregate results."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.eu import eu_identity, vies_client
from app.services.local.identifiers import inspect_identifiers
from app.services.news import newsapi as newsapi_mod
from app.services.optional import courts_eu, courts_uk, open_bris as open_bris_mod
from app.services.red_flags import collect_red_flags
from app.services.screening.registers import register_links
from app.services.screening.sanctions import screening_links
from app.services.types import DueDiligenceReport, ModuleResult, RedFlag
from app.services.uk import accounts as accounts_mod
from app.services.uk import companies_house, gazette, hmrc_vat, psc

LOG = logging.getLogger(__name__)


def _credit_proxy(
    *,
    weights: Dict[str, float],
    filing_days_ago: Optional[float],
    vat_ok: Optional[bool],
    identity_confidence: float,
    psc_count: int,
) -> tuple[float, Dict[str, Any]]:
    """Weighted score 0–100 (informal proxy — not a credit bureau score)."""

    total_w = sum(max(0.0, float(v)) for v in weights.values()) or 1.0
    parts: Dict[str, float] = {}

    # Filing recency: lower days = better, cap at 800 days
    fr = 0.0
    if filing_days_ago is not None:
        fr = max(0.0, 1.0 - min(filing_days_ago, 800.0) / 800.0)
    parts["filing_recency"] = fr * float(weights.get("filing_recency", 0))

    parts["net_assets_positive"] = 0.5 * float(weights.get("net_assets_positive", 0))  # placeholder without XBRL

    vv = 1.0 if vat_ok is True else 0.0 if vat_ok is False else 0.5
    parts["vat_valid"] = vv * float(weights.get("vat_valid", 0))

    parts["identity_confidence"] = max(0.0, min(1.0, identity_confidence)) * float(
        weights.get("identity_confidence", 0)
    )

    psc_trans = 1.0 if psc_count > 0 else 0.3
    parts["psc_transparency"] = psc_trans * float(weights.get("psc_transparency", 0))

    score = sum(parts.values())
    score = max(0.0, min(100.0, 100.0 * score / total_w))

    breakdown = {"parts_raw": parts, "weights_used": weights, "formula": "weighted_sum_normalized_to_100"}
    return score, breakdown


def run_due_diligence(
    *,
    db: Any,
    company_name: str,
    registration_number: Optional[str],
    country_code: str,
    eu_vat_input: Optional[str],
    uk_vat_number: Optional[str],
    modules: Dict[str, bool],
    use_cache: bool = True,
) -> DueDiligenceReport:
    """
    Execute checks per `modules`. `db` is storage Db instance for keys and cache.

    EU VAT: pass full VAT in `eu_vat_input` when country is EU.
    UK VAT: optional `uk_vat_number` (9 digits or GB...).
    """

    cc = country_code.strip().upper()
    modules = {k: bool(v) for k, v in modules.items()}

    if use_cache:
        cached = db.cache_get(
            query_name=company_name,
            registration=registration_number,
            country=cc,
            modules=modules,
        )
        if cached and isinstance(cached, dict) and "report" in cached:
            rep_dict = cached["report"]
            rep_obj = DueDiligenceReport(
                query_name=rep_dict.get("query_name", company_name),
                country_code=rep_dict.get("country_code", cc),
                company_number=rep_dict.get("company_number"),
                modules_requested=rep_dict.get("modules_requested", modules),
                modules={k: _dict_to_module_result(v) for k, v in rep_dict.get("modules", {}).items()},
                red_flags=[RedFlag(**x) for x in rep_dict.get("red_flags", [])],
                credit_proxy_score=rep_dict.get("credit_proxy_score"),
                credit_proxy_breakdown=rep_dict.get("credit_proxy_breakdown") or {},
                cached=True,
                timestamp_iso=rep_dict.get("timestamp_iso", ""),
            )
            return rep_obj

    ch_key = db.get_api_key("companies_house")
    hmrc_id = db.get_api_key("hmrc_client_id")
    hmrc_secret = db.get_api_key("hmrc_client_secret")
    news_key = db.get_api_key("newsapi")
    open_bris_key = db.get_api_key("open_bris")

    weights = db.get_scoring_weights()
    results: Dict[str, ModuleResult] = {}
    profile: Optional[Dict[str, Any]] = None
    company_number: Optional[str] = None
    vat_artefact: Dict[str, Any] = {}
    financial_artefact: Dict[str, Any] = {}
    psc_artefact: Dict[str, Any] = {}

    ts = datetime.now(timezone.utc).isoformat()

    if modules.get("identifiers", True):
        ident = inspect_identifiers(
            country_code=cc,
            company_name=company_name,
            registration_number=registration_number,
            uk_vat_number=uk_vat_number,
            eu_vat_input=eu_vat_input,
        )
        results["identifiers"] = ModuleResult(
            module="identifiers",
            ok=bool(ident.get("ok")),
            summary="Local format checks on name, company number, and VAT.",
            data=ident,
            source="On this computer",
        )

    # --- Identity + UK core ---
    if cc == "GB" and modules.get("identity") and ch_key:
        try:
            resolved = companies_house.resolve_uk_company(
                api_key=ch_key, name=company_name or None, registration=registration_number
            )
            profile = resolved.get("profile") or {}
            company_number = resolved.get("company_number")
            results["identity"] = ModuleResult(
                module="identity",
                ok=True,
                summary=f"Resolved company {company_number}: {profile.get('company_name', '')}",
                data={"profile": profile, "search_hits": resolved.get("search_hits")},
                source="Companies House",
            )
        except Exception as e:  # noqa: BLE001
            LOG.exception("CH identity")
            results["identity"] = ModuleResult(
                module="identity",
                ok=False,
                summary="Companies House identity failed",
                error=str(e),
                source="Companies House",
            )
    elif cc == "GB" and modules.get("identity") and not ch_key:
        results["identity"] = ModuleResult(
            module="identity",
            ok=False,
            summary="Companies House API key missing",
            error="Add a Companies House API key in Settings to run live UK identity.",
            source="Companies House",
        )
    elif cc != "GB" and modules.get("identity"):
        cap = eu_identity.explain_capability(cc)
        hint: Dict[str, Any]
        if modules.get("open_bris"):
            hint = open_bris_mod.query_open_bris(open_bris_key, country=cc, query=company_name)
        else:
            hint = {"skipped": True, "reason": "Open BRIS module disabled or not selected."}
        results["identity"] = ModuleResult(
            module="identity",
            ok=True,
            summary="EU identity — phased automation",
            data={**cap, "open_bris": hint},
            source="EU adapter / optional Open BRIS",
        )

    # --- PSC (UK) ---
    if cc == "GB" and modules.get("psc") and ch_key and company_number:
        try:
            psc_artefact = psc.fetch_psc(ch_key, company_number)
            results["psc"] = ModuleResult(
                module="psc",
                ok=True,
                summary=f"PSC records: {psc_artefact.get('total', 0)}",
                data=psc_artefact,
                source="Companies House PSC",
            )
        except Exception as e:  # noqa: BLE001
            results["psc"] = ModuleResult(
                module="psc",
                ok=False,
                summary="PSC fetch failed",
                error=str(e),
                source="Companies House PSC",
            )
    elif cc != "GB" and modules.get("psc"):
        results["psc"] = ModuleResult(
            module="psc",
            ok=False,
            summary="PSC is a UK register in this release",
            data={"note": "Use national BO registers for EU countries."},
            source="N/A",
        )

    # --- VAT ---
    if modules.get("vat"):
        if cc == "GB":
            vat_num = (uk_vat_number or "").strip()
            if not vat_num:
                vat_artefact = {"skipped": True, "reason": "Enter a UK VAT number to call HMRC lookup."}
                results["vat"] = ModuleResult(
                    module="vat",
                    ok=False,
                    summary="UK VAT number required for HMRC check",
                    data=vat_artefact,
                    source="HMRC",
                )
            else:
                check = hmrc_vat.check_uk_vat_if_configured(
                    client_id=hmrc_id,
                    client_secret=hmrc_secret,
                    vat_to_check=vat_num,
                )
                vat_artefact = check
                if check.get("skipped"):
                    results["vat"] = ModuleResult(
                        module="vat",
                        ok=False,
                        summary="HMRC VAT not configured",
                        data=check,
                        source="HMRC",
                    )
                elif check.get("error"):
                    results["vat"] = ModuleResult(
                        module="vat",
                        ok=False,
                        summary="HMRC VAT request failed",
                        data=check,
                        error=str(check.get("error")),
                        source="HMRC",
                    )
                else:
                    results["vat"] = ModuleResult(
                        module="vat",
                        ok=bool(check.get("valid")),
                        summary=check.get("message") or "HMRC VAT response",
                        data=check,
                        source="HMRC",
                    )
        else:
            evat = (eu_vat_input or registration_number or "").strip()
            if not evat:
                results["vat"] = ModuleResult(
                    module="vat",
                    ok=False,
                    summary="Enter EU VAT number for VIES",
                    error="Missing VAT",
                    source="VIES",
                )
            else:
                vr = vies_client.check_vat(evat)
                vat_artefact = vr
                results["vat"] = ModuleResult(
                    module="vat",
                    ok=bool(vr.get("valid")),
                    summary="VIES VAT validation",
                    data=vr,
                    source="VIES",
                )

    # --- Financial ---
    if cc == "GB" and modules.get("financial") and ch_key and company_number:
        try:
            financial_artefact = accounts_mod.summarize_filings(ch_key, company_number)
            results["financial"] = ModuleResult(
                module="financial",
                ok=True,
                summary="Filing-based financial summary",
                data=financial_artefact,
                source="Companies House filing history",
            )
        except Exception as e:  # noqa: BLE001
            results["financial"] = ModuleResult(
                module="financial",
                ok=False,
                summary="Financial summary failed",
                error=str(e),
                source="Companies House",
            )
    elif modules.get("financial") and cc != "GB":
        results["financial"] = ModuleResult(
            module="financial",
            ok=False,
            summary="EU financials are country-specific (phased)",
            data={"note": "Connect national business register filings in a future adapter."},
            source="N/A",
        )

    # --- Courts ---
    if modules.get("courts"):
        if cc == "GB":
            results["courts"] = ModuleResult(
                module="courts",
                ok=True,
                summary="UK case law search link",
                data=courts_uk.court_findings_stub(company_name),
                source="National Archives / manual",
            )
        else:
            results["courts"] = ModuleResult(
                module="courts",
                ok=True,
                summary="EU case law pointers",
                data=courts_eu.ecli_search_hint(company_name),
                source="Curia / manual",
            )

    # --- Insolvency / Gazette hints ---
    if modules.get("insolvency"):
        results["insolvency"] = ModuleResult(
            module="insolvency",
            ok=True,
            summary="Insolvency and Gazette pointers",
            data=gazette.insolvency_search_hint(company_name, company_number),
            source="The Gazette / CH",
        )

    # --- News (optional third party) ---
    if modules.get("news"):
        nr = newsapi_mod.fetch_headlines(news_key, company_query=company_name)
        results["news"] = ModuleResult(
            module="news",
            ok=bool(nr.get("ok")),
            summary="News / reputation (optional)",
            data=nr,
            error=None if nr.get("ok") else nr.get("reason") or nr.get("error"),
            source="NewsAPI.org",
        )

    if modules.get("sanctions", True):
        results["sanctions"] = ModuleResult(
            module="sanctions",
            ok=True,
            summary="Official watchlist search pages for this name.",
            data=screening_links(company_name, cc),
            source="Official search pages",
        )

    if modules.get("registers", True):
        results["registers"] = ModuleResult(
            module="registers",
            ok=True,
            summary="Public register links for analyst follow-up.",
            data=register_links(
                company_name=company_name,
                country_code=cc,
                company_number=company_number,
            ),
            source="Public registers",
        )

    # --- Credit proxy ---
    identity_confidence = 0.8 if profile else 0.4
    if profile and (profile.get("company_name") or "").lower().strip() == (company_name or "").lower().strip():
        identity_confidence = 1.0

    filing_days = None
    if financial_artefact:
        la = financial_artefact.get("latest_accounts_filing") or {}
        filing_days = accounts_mod.days_since_accounts(la if la else None)

    vat_ok: Optional[bool] = None
    if vat_artefact:
        if "valid" in vat_artefact:
            vat_ok = bool(vat_artefact.get("valid"))
        elif vat_artefact.get("skipped"):
            vat_ok = None

    psc_count = int((psc_artefact or {}).get("total") or 0)

    score: Optional[float] = None
    breakdown: Dict[str, Any] = {}
    if modules.get("credit_proxy"):
        score, breakdown = _credit_proxy(
            weights=weights,
            filing_days_ago=filing_days,
            vat_ok=vat_ok,
            identity_confidence=identity_confidence,
            psc_count=psc_count,
        )
        results["credit_proxy"] = ModuleResult(
            module="credit_proxy",
            ok=True,
            summary=f"Proxy risk score (0–100, higher is lower risk): {score:.1f}",
            data=breakdown,
            source="Internal model",
        )

    flags = collect_red_flags(
        country=cc,
        profile=profile,
        vat_result=vat_artefact,
        financial=financial_artefact,
        psc_data=psc_artefact,
    )

    report = DueDiligenceReport(
        query_name=company_name,
        country_code=cc,
        company_number=company_number,
        modules_requested=modules,
        modules=results,
        red_flags=flags,
        credit_proxy_score=score,
        credit_proxy_breakdown=breakdown,
        cached=False,
        timestamp_iso=ts,
    )

    try:
        serializable = report_to_dict(report)
        db.cache_put(
            query_name=company_name,
            registration=registration_number,
            country=cc,
            modules=modules,
            payload={"report": serializable},
        )
    except Exception as e:  # noqa: BLE001
        LOG.warning("cache put failed: %s", e)

    return report


def report_to_dict(report: DueDiligenceReport) -> Dict[str, Any]:
    """JSON-serialisable dict for Eel and PDF."""

    return {
        "query_name": report.query_name,
        "country_code": report.country_code,
        "company_number": report.company_number,
        "modules_requested": report.modules_requested,
        "modules": {k: _module_to_dict(v) for k, v in report.modules.items()},
        "red_flags": [
            {
                "severity": f.severity,
                "code": f.code,
                "explanation": f.explanation,
                "evidence_refs": f.evidence_refs,
            }
            for f in report.red_flags
        ],
        "credit_proxy_score": report.credit_proxy_score,
        "credit_proxy_breakdown": report.credit_proxy_breakdown,
        "cached": report.cached,
        "timestamp_iso": report.timestamp_iso,
    }


def _module_to_dict(m: ModuleResult) -> Dict[str, Any]:
    return {
        "module": m.module,
        "ok": m.ok,
        "summary": m.summary,
        "data": m.data,
        "error": m.error,
        "source": m.source,
    }


def _dict_to_module_result(d: Dict[str, Any]) -> ModuleResult:
    return ModuleResult(
        module=d.get("module", ""),
        ok=bool(d.get("ok")),
        summary=d.get("summary", ""),
        data=d.get("data") or {},
        error=d.get("error"),
        source=d.get("source", ""),
    )
