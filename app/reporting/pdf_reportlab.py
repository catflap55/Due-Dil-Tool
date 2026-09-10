"""Multi-page Due Diligence PDF using ReportLab."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle


def build_pdf(report_dict: Dict[str, Any], out_path: Path) -> Path:
    """
    Produce a professional multi-page PDF from orchestrator serialised report.

    Includes disclaimer pages and sources — not legal or financial advice.
    """

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "DDTitle",
        parent=styles["Title"],
        fontSize=18,
        spaceAfter=12,
    )
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=6)
    body = ParagraphStyle(
        "BodyTiny",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
    )
    elements: List[Any] = []

    elements.append(Paragraph("Due Diligence Workstation", title))
    elements.append(Spacer(1, 0.3 * cm))
    meta = (
        f"<b>Generated:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} &nbsp; "
        f"<b>Query:</b> {escape_xml(report_dict.get('query_name', ''))} &nbsp; "
        f"<b>Jurisdiction:</b> {escape_xml(report_dict.get('country_code', ''))}"
    )
    elements.append(Paragraph(meta, body))
    if report_dict.get("company_number"):
        elements.append(
            Paragraph(
                f"<b>Company number:</b> {escape_xml(str(report_dict.get('company_number')))}",
                body,
            )
        )
    elements.append(Spacer(1, 0.4 * cm))
    elements.append(
        Paragraph(
            "<b>Disclaimer.</b> This tool is for information only. It is not legal, credit, tax, or "
            "financial advice. You must do your own independent checks at the official source before you act. "
            "The authors are not liable for decisions you make from these results. "
            "This report is compiled from automated queries to public registers "
            "and optional third-party modules configured by the operator.",
            body,
        )
    )
    elements.append(PageBreak())

    score = report_dict.get("credit_proxy_score")
    if score is not None:
        elements.append(Paragraph("Executive summary", h2))
        elements.append(
            Paragraph(
                f"Internal proxy score (0–100, higher suggests lower operational risk in this model): "
                f"<b>{float(score):.1f}</b>",
                body,
            )
        )
        elements.append(Spacer(1, 0.2 * cm))

    flags = report_dict.get("red_flags") or []
    elements.append(Paragraph("Red flags", h2))
    if not flags:
        elements.append(Paragraph("No automated red flags triggered.", body))
    else:
        tbl_data: List[List[str]] = [["Severity", "Code", "Explanation"]]
        for f in flags:
            tbl_data.append(
                [
                    escape_xml(str(f.get("severity", ""))),
                    escape_xml(str(f.get("code", ""))),
                    escape_xml(str(f.get("explanation", "")))[:500],
                ]
            )
        t = Table(tbl_data, colWidths=[2.5 * cm, 3.5 * cm, 10 * cm])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        elements.append(t)
    elements.append(PageBreak())

    modules = report_dict.get("modules") or {}
    elements.append(Paragraph("Module results", h2))
    for key in sorted(modules.keys()):
        m = modules[key]
        elements.append(Paragraph(f"<b>{escape_xml(key)}</b> — {escape_xml(m.get('summary', ''))}", body))
        src = m.get("source") or ""
        if src:
            elements.append(Paragraph(f"<i>Source: {escape_xml(src)}</i>", body))
        err = m.get("error")
        if err:
            elements.append(Paragraph(f"<font color='red'>Error: {escape_xml(str(err))}</font>", body))
        data = m.get("data")
        if isinstance(data, dict):
            elements.append(
                Preformatted(
                    _pretty_json(data)[:8000],
                    ParagraphStyle(name="mono", fontName="Courier", fontSize=7, leading=9),
                )
            )
        elements.append(Spacer(1, 0.15 * cm))

    elements.append(PageBreak())
    elements.append(Paragraph("Data sources & privacy", h2))
    elements.append(
        Paragraph(
            "Data left this machine only to reach APIs you enabled (e.g. Companies House, HMRC, VIES). "
            "Optional NewsAPI/Open BRIS modules send queries to those providers if you saved keys in Settings.",
            body,
        )
    )

    doc.build(elements)
    return out_path


def escape_xml(text: str) -> str:

    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _pretty_json(obj: Any) -> str:
    import json

    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except TypeError:
        return str(obj)
