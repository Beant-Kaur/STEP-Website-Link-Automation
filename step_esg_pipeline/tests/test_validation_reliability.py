import pytest
from database.models import LinkRecord
from crawler.url_checker import UrlChecker
from content.html_parser import HtmlParser
from analysis.freshness_checker import FreshnessChecker
from pipeline.decision_engine import DecisionEngine


def make_record(**kwargs):
    defaults = {
        "link_id": "test_1",
        "jurisdiction": "Test Country",
        "topic": "ESG Reporting",
        "step_section": "ESG Legislative Landscape",
        "step_description": "Test Regulation",
    }
    defaults.update(kwargs)
    return LinkRecord(**defaults)


def test_scenario_1_valid_current_content():
    """Test 1: HTTP 200 + valid current in-force content -> KEEP"""
    rec = make_record(
        original_url="https://www.legislation.gov.uk/ukpga/2021/30/contents/enacted",
        http_status=200,
        technical_status="ACCESSIBLE",
        access_status="ACCESSIBLE",
        content_status="INTENDED_CONTENT_PRESENT",
        regulatory_status="LEGALLY_BINDING_IN_FORCE",
        freshness_status="CURRENT_IN_FORCE",
        confidence_score=0.88,
        classification="VALID_AND_CURRENT",
    )
    decision = DecisionEngine().decide(rec)
    assert decision == "KEEP"


def test_scenario_2_http_404_broken():
    """Test 2: HTTP 404 dead link cannot be KEEP"""
    rec = make_record(
        original_url="https://example.gov/deleted-regulation.pdf",
        http_status=404,
        technical_status="BROKEN",
        access_status="BROKEN",
        classification="BROKEN",
        confidence_score=0.75,
        replacement_url="https://example.gov/active-regulation.pdf",
        replacement_verified=True,
    )
    decision = DecisionEngine().decide(rec)
    assert decision == "REPLACE"

    # Without replacement -> cannot be KEEP
    rec_no_rep = make_record(
        original_url="https://example.gov/deleted-regulation.pdf",
        http_status=404,
        technical_status="BROKEN",
        classification="BROKEN",
        confidence_score=0.75,
    )
    assert DecisionEngine().decide(rec_no_rep) == "HUMAN_REVIEW_REQUIRED"


def test_scenario_3_soft_404_detection():
    """Test 3: HTTP 200 + 'Page Not Found' in HTML title/body is detected as soft-404 and cannot be KEEP"""
    html = "<html><head><title>404 - Page Not Found</title></head><body><h1>Page Not Found</h1><p>The requested page could not be found.</p></body></html>"
    parsed = HtmlParser.parse(html)
    assert parsed["is_soft_404"] is True

    rec = make_record(
        original_url="https://example.gov/missing",
        http_status=200,
        technical_status="BROKEN",
        access_status="BROKEN_SOFT_404",
        content_status="SOFT_404",
        classification="BROKEN",
        confidence_score=0.80,
        replacement_url="https://example.gov/active",
        replacement_verified=True,
    )
    decision = DecisionEngine().decide(rec)
    assert decision == "REPLACE"


def test_scenario_4_generic_homepage_redirect():
    """Test 4: Deep document link redirecting to root domain is WRONG_DESTINATION and cannot be KEEP"""
    rec = make_record(
        original_url="https://example.gov/regulations/2021/guidelines.pdf",
        final_url="https://example.gov/",
        http_status=200,
        technical_status="WRONG_DESTINATION",
        access_status="WRONG_DESTINATION",
        classification="WRONG_DESTINATION",
        confidence_score=0.70,
        replacement_url="https://example.gov/regulations/current/guidelines.pdf",
        replacement_verified=True,
    )
    decision = DecisionEngine().decide(rec)
    assert decision == "REPLACE"


def test_scenario_5_old_year_still_current():
    """Test 5: Older enactment year (e.g. 2013 Companies Act) still in force remains KEEP"""
    freshness = FreshnessChecker.evaluate_detailed(
        title="Companies Act 2013 Section 135",
        url="https://www.mca.gov.in/Ministry/pdf/CompaniesAct2013.pdf",
        publication_date="2013",
    )
    assert freshness["is_outdated"] is False
    assert freshness["freshness_status"] in ("CURRENT_IN_FORCE", "LEGALLY_BINDING_IN_FORCE")

    rec = make_record(
        original_url="https://www.mca.gov.in/Ministry/pdf/CompaniesAct2013.pdf",
        http_status=200,
        technical_status="ACCESSIBLE",
        access_status="ACCESSIBLE",
        content_status="INTENDED_CONTENT_PRESENT",
        regulatory_status="LEGALLY_BINDING_IN_FORCE",
        freshness_status="CURRENT_IN_FORCE",
        confidence_score=0.85,
        classification="VALID_AND_CURRENT",
    )
    decision = DecisionEngine().decide(rec)
    assert decision == "KEEP"


def test_scenario_6_superseded_regulation():
    """Test 6: Superseded regulation (e.g. California SB-253 2021 military bill) is marked OUTDATED / REPLACE"""
    freshness = FreshnessChecker.evaluate_detailed(
        title="SB-253",
        url="https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202120220SB253",
        text="military service elected officers",
    )
    assert freshness["is_outdated"] is True
    assert freshness["freshness_status"] == "COMPLETELY_SUPERSEDED"

    rec = make_record(
        original_url="https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202120220SB253",
        http_status=200,
        technical_status="ACCESSIBLE",
        classification="WORKING_BUT_OUTDATED",
        freshness_status="COMPLETELY_SUPERSEDED",
        confidence_score=0.90,
        replacement_url="https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240SB253",
        replacement_verified=True,
    )
    decision = DecisionEngine().decide(rec)
    assert decision == "REPLACE"


def test_scenario_7_amended_regulation():
    """Test 7: Preliminary circular superseded by newer framework (SEBI May 2021) -> REPLACE"""
    freshness = FreshnessChecker.evaluate_detailed(
        title="Business Responsibility and Sustainability Reporting",
        url="https://www.sebi.gov.in/legal/circulars/may-2021/business-responsibility-and-sustainability-reporting-by-listed-entities_50096.html",
        text="SEBI circular CIR/2021/562",
    )
    assert freshness["is_outdated"] is True
    assert freshness["freshness_status"] == "PARTIALLY_SUPERSEDED"


def test_scenario_8_nonofficial_aggregator():
    """Test 8: Commercial aggregator where official federal source exists -> REPLACE_WITH_OFFICIAL"""
    rec = make_record(
        original_url="https://www.policyvault.africa/policy/environmental-impact-assessment-act-2/",
        http_status=200,
        technical_status="ACCESSIBLE",
        classification="WORKING_BUT_NON_OFFICIAL",
        confidence_score=0.85,
        replacement_url="https://nesrea.gov.ng/policies-guidelines/",
        replacement_verified=True,
    )
    decision = DecisionEngine().decide(rec)
    assert decision == "REPLACE_WITH_OFFICIAL"


def test_scenario_9_access_restricted_with_replacement():
    """Test 9: 403 Access Restricted with verified canonical replacement -> ACCESS_DENIED_REPLACEMENT_FOUND"""
    rec = make_record(
        original_url="https://example.gov/blocked-by-akamai.pdf",
        http_status=403,
        technical_status="ACCESS_RESTRICTED",
        access_status="ACCESS_DENIED",
        classification="ACCESS_RESTRICTED",
        confidence_score=0.75,
        replacement_url="https://official-portal.gov/active-doc.pdf",
        replacement_verified=True,
    )
    decision = DecisionEngine().decide(rec)
    assert decision == "ACCESS_DENIED_REPLACEMENT_FOUND"


def test_scenario_10_conflicting_uncertain_evidence():
    """Test 10: Conflicting or uncertain evidence goes to HUMAN_REVIEW_REQUIRED"""
    rec = make_record(
        original_url="https://example.gov/ambiguous-rule",
        http_status=200,
        technical_status="ACCESSIBLE",
        classification="NEEDS_HUMAN_REVIEW",
        regulatory_status="UNKNOWN",
        freshness_status="UNKNOWN",
        confidence_score=0.40,
        human_review_required=True,
    )
    decision = DecisionEngine().decide(rec)
    assert decision == "HUMAN_REVIEW_REQUIRED"
