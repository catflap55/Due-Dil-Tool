"""Built-in sample dossier so the product works with no API keys."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from app.services.local.identifiers import inspect_identifiers
from app.services.screening.registers import register_links
from app.services.screening.sanctions import screening_links
from app.services.types import DueDiligenceReport, ModuleResult, RedFlag


SAMPLE_NAME = "Northbridge Provisions Ltd"
SAMPLE_NUMBER = "01234567"


def sample_report() -> DueDiligenceReport:
    ts = datetime.now(timezone.utc).isoformat()
    ids = inspect_identifiers(
        country_code="GB",
        company_name=SAMPLE_NAME,
        registration_number=SAMPLE_NUMBER,
        uk_vat_number="GB123456715",
        eu_vat_input=None,
    )
    sanctions = screening_links(SAMPLE_NAME, "GB")
    registers = register_links(
        company_name=SAMPLE_NAME, country_code="GB", company_number=SAMPLE_NUMBER
    )
    modules = {
        "identifiers": ModuleResult(
            module="identifiers",
            ok=True,
            summary="Local format checks on the sample identifiers.",
            data=ids,
            source="On this computer",
        ),
        "identity": ModuleResult(
            module="identity",
            ok=True,
            summary=f"Sample profile {SAMPLE_NUMBER}: {SAMPLE_NAME}",
            data={
                "sample": True,
                "profile": {
                    "company_name": SAMPLE_NAME,
                    "company_number": SAMPLE_NUMBER,
                    "company_status": "active",
                    "date_of_creation": "2014-03-11",
                    "type": "ltd",
                    "jurisdiction": "england-wales",
                    "sic_codes": ["46390"],
                    "registered_office_address": {
                        "address_line_1": "1 Example Wharf",
                        "locality": "Manchester",
                        "postal_code": "M1 1AA",
                    },
                },
            },
            source="Sample dossier (not a live register)",
        ),
        "psc": ModuleResult(
            module="psc",
            ok=True,
            summary="PSC records: 1 (sample)",
            data={
                "sample": True,
                "total": 1,
                "items": [
                    {
                        "name": "Alex Example",
                        "natures_of_control": ["ownership-of-shares-75-to-100-percent"],
                        "notified_on": "2016-04-06",
                    }
                ],
            },
            source="Sample dossier",
        ),
        "vat": ModuleResult(
            module="vat",
            ok=True,
            summary="Sample VAT marked valid for demonstration.",
            data={"sample": True, "valid": True, "message": "Demonstration only — not an HMRC response."},
            source="Sample dossier",
        ),
        "financial": ModuleResult(
            module="financial",
            ok=True,
            summary="Last accounts filed within a normal cycle (sample).",
            data={
                "sample": True,
                "latest_accounts_filing": {"date": "2025-09-30", "type": "accounts", "description": "accounts"},
                "overdue_or_late_hints": [],
            },
            source="Sample dossier",
        ),
        "courts": ModuleResult(
            module="courts",
            ok=True,
            summary="UK case law search link",
            data={"search_url": "https://caselaw.nationalarchives.gov.uk/judgments?query=Northbridge+Provisions"},
            source="National Archives / manual",
        ),
        "insolvency": ModuleResult(
            module="insolvency",
            ok=True,
            summary="Insolvency and Gazette pointers",
            data={
                "gazette_search_url": "https://www.thegazette.co.uk/all-notices/notice?text=Northbridge+Provisions+Ltd",
                "companies_house_profile_url": f"https://find-and-update.company-information.service.gov.uk/company/{SAMPLE_NUMBER}",
            },
            source="The Gazette / CH",
        ),
        "sanctions": ModuleResult(
            module="sanctions",
            ok=True,
            summary="Official watchlist search pages for this name.",
            data=sanctions,
            source="Official search pages",
        ),
        "registers": ModuleResult(
            module="registers",
            ok=True,
            summary="Public register links for analyst follow-up.",
            data=registers,
            source="Public registers",
        ),
        "credit_proxy": ModuleResult(
            module="credit_proxy",
            ok=True,
            summary="Proxy risk score (0–100, higher is lower risk): 78.0",
            data={"sample": True, "formula": "demonstration"},
            source="Internal model (sample)",
        ),
    }
    flags = [
        RedFlag(
            severity="info",
            code="SAMPLE_DOSSIER",
            explanation="This is a built-in demonstration. It is not a live Companies House or HMRC result.",
            evidence_refs=["Sample data"],
        )
    ]
    return DueDiligenceReport(
        query_name=SAMPLE_NAME,
        country_code="GB",
        company_number=SAMPLE_NUMBER,
        modules_requested={k: True for k in modules},
        modules=modules,
        red_flags=flags,
        credit_proxy_score=78.0,
        credit_proxy_breakdown={"sample": True},
        cached=False,
        timestamp_iso=ts,
    )


def sample_report_dict() -> Dict[str, Any]:
    from app.services.orchestrator import report_to_dict

    d = report_to_dict(sample_report())
    d["sample"] = True
    return d
