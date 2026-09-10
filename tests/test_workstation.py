from app.services.local.identifiers import eu_vat_format_ok, uk_company_number_ok, uk_vat_checksum_ok
from app.services.orchestrator import _credit_proxy
from app.services.sample import SAMPLE_NAME, sample_report_dict
from app.services.screening.sanctions import screening_links
from app.config.defaults import DEFAULT_SCORING_WEIGHTS


def test_uk_company_number_pads_and_accepts():
    assert uk_company_number_ok("1234567")
    assert uk_company_number_ok("SC123456")
    assert not uk_company_number_ok("12")


def test_uk_vat_checksum():
    assert uk_vat_checksum_ok("GB123456715")
    assert not uk_vat_checksum_ok("GB123456789")


def test_eu_vat_patterns():
    assert eu_vat_format_ok("DE123456789")
    assert not eu_vat_format_ok("DE12")


def test_credit_proxy_bounds():
    score, breakdown = _credit_proxy(
        weights=DEFAULT_SCORING_WEIGHTS,
        filing_days_ago=30,
        vat_ok=True,
        identity_confidence=1.0,
        psc_count=1,
    )
    assert 0 <= score <= 100
    assert "parts_raw" in breakdown


def test_sanctions_links_include_query():
    data = screening_links("Northbridge Provisions Ltd", "GB")
    hrefs = " ".join(x["href"] for x in data["links"])
    assert "opensanctions.org" in hrefs
    assert "ofac" in hrefs.lower() or "OFAC" in hrefs
    assert any("disqualif" in x["name"].lower() for x in data["links"])


def test_sample_dossier_is_marked():
    d = sample_report_dict()
    assert d["sample"] is True
    assert d["query_name"] == SAMPLE_NAME
    assert d["credit_proxy_score"] == 78.0
    assert "sanctions" in d["modules"]
    assert "registers" in d["modules"]
    assert any(f["code"] == "SAMPLE_DOSSIER" for f in d["red_flags"])
