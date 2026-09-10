"""Eel bridge: expose Python functions to the HTML/JS front end."""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import eel

from app import __version__
from app.config.defaults import country_list
from app.reporting.pdf_reportlab import build_pdf
from app.services.orchestrator import report_to_dict, run_due_diligence
from app.services.sample import sample_report_dict
from app.storage.db import Db
from app.storage.paths import exports_dir, resource_base

LOG = logging.getLogger(__name__)

_db: Optional[Db] = None
_last_report: Optional[Dict[str, Any]] = None

ALLOWED_KEYS = {
    "companies_house",
    "hmrc_client_id",
    "hmrc_client_secret",
    "newsapi",
    "open_bris",
}


def get_db() -> Db:
    global _db  # noqa: PLW0603
    if _db is None:
        _db = Db()
    return _db


def ping() -> Dict[str, Any]:
    return {"ok": True, "version": __version__}


def get_country_list() -> list[dict]:
    return country_list()


def dd_run(payload: Dict[str, Any]) -> Dict[str, Any]:
    db = get_db()
    modules = payload.get("modules") or {}
    try:
        rep = run_due_diligence(
            db=db,
            company_name=str(payload.get("company_name") or ""),
            registration_number=payload.get("registration_number"),
            country_code=str(payload.get("country_code") or "GB"),
            eu_vat_input=payload.get("eu_vat_input"),
            uk_vat_number=payload.get("uk_vat_number"),
            modules={k: bool(v) for k, v in modules.items()},
            use_cache=payload.get("use_cache", True),
        )
    except Exception as e:  # noqa: BLE001
        LOG.exception("dd_run")
        return {"ok": False, "error": str(e)}
    d = report_to_dict(rep)
    global _last_report  # noqa: PLW0603
    _last_report = d
    return {"ok": True, "report": d}


def dd_run_sample() -> Dict[str, Any]:
    d = sample_report_dict()
    global _last_report  # noqa: PLW0603
    _last_report = d
    return {"ok": True, "report": d}


def dd_export_pdf() -> Dict[str, Any]:
    global _last_report  # noqa: PLW0603
    if not _last_report:
        return {"ok": False, "error": "No report to export — run a search first."}
    stamp = _last_report.get("timestamp_iso", "export").replace(":", "-")
    out = exports_dir() / f"duedil_report_{stamp}.pdf"
    try:
        build_pdf(_last_report, out)
        return {"ok": True, "path": str(out)}
    except Exception as e:  # noqa: BLE001
        LOG.exception("PDF export")
        return {"ok": False, "error": str(e)}


def dd_export_csv() -> Dict[str, Any]:
    global _last_report  # noqa: PLW0603
    if not _last_report:
        return {"ok": False, "error": "No report to export — run a search first."}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = exports_dir() / f"duedil_flags_{stamp}.csv"
    try:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["severity", "code", "explanation", "evidence"])
        for flag in _last_report.get("red_flags") or []:
            writer.writerow(
                [
                    flag.get("severity", ""),
                    flag.get("code", ""),
                    flag.get("explanation", ""),
                    "; ".join(flag.get("evidence_refs") or []),
                ]
            )
        writer.writerow([])
        writer.writerow(["module", "ok", "summary", "source"])
        for key, mod in (_last_report.get("modules") or {}).items():
            writer.writerow(
                [key, mod.get("ok"), mod.get("summary", ""), mod.get("source", "")]
            )
        out.write_text(buf.getvalue(), encoding="utf-8")
        return {"ok": True, "path": str(out)}
    except Exception as e:  # noqa: BLE001
        LOG.exception("CSV export")
        return {"ok": False, "error": str(e)}


def settings_key_mask() -> Dict[str, Any]:
    db = get_db()
    masked = {k: db.mask_key(k) for k in ALLOWED_KEYS}
    has = {k: bool(db.get_api_key(k)) for k in ALLOWED_KEYS}
    return {"ok": True, "masked": masked, "has_value": has}


def settings_set_api_key(name: str, value: str) -> Dict[str, Any]:
    if name not in ALLOWED_KEYS:
        return {"ok": False, "error": "Unknown key name"}
    if not (value or "").strip():
        return {"ok": True, "skipped": True}
    if (value or "").strip() == "-":
        get_db().set_api_key(name, "")
        return {"ok": True, "removed": True}
    get_db().set_api_key(name, value)
    return {"ok": True}


def settings_get_config() -> Dict[str, Any]:
    return {"ok": True, "config": get_db().get_config()}


def settings_set_config(config: Dict[str, Any]) -> Dict[str, Any]:
    get_db().set_config(config)
    return {"ok": True}


def settings_clear_cache() -> Dict[str, Any]:
    n = get_db().clear_cache()
    return {"ok": True, "removed": n}


def settings_recent_searches() -> Dict[str, Any]:
    return {"ok": True, "items": get_db().list_recent_searches(20)}


def init_eel() -> None:
    web = resource_base() / "web"
    eel.init(
        str(web),
        allowed_extensions=[".js", ".html", ".css", ".svg", ".png", ".woff2", ".ico"],
    )


def register_exposables() -> None:
    for fn in (
        ping,
        get_country_list,
        dd_run,
        dd_run_sample,
        dd_export_pdf,
        dd_export_csv,
        settings_key_mask,
        settings_set_api_key,
        settings_get_config,
        settings_set_config,
        settings_clear_cache,
        settings_recent_searches,
    ):
        eel.expose(fn)
