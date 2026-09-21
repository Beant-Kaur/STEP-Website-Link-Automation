import json
import pytest
from database.models import LinkRecord
from crawler.step_extractor import StepExtractor
from content.html_parser import HtmlParser
from content.metadata_extractor import MetadataExtractor
from analysis.regulatory_identity import RegulatoryIdentityEngine, RegulatoryIdentity
from analysis.currentness_engine import CurrentnessEngine, CurrentnessResult
from analysis.evidence_engine import EvidenceTrail
from analysis.source_classifier import SourceClassifier
from jurisdictions.registry import JurisdictionRegistry
from pipeline.decision_engine import DecisionEngine
from ai.confidence_engine import ConfidenceEngine


class TestAuditEngineRequiredCases:
    """Comprehensive test suite for the 12 required regulatory audit scenarios."""

    def test_1_accessibility_not_equal_in_force(self):
        """Scenario 1: HTTP 200 + valid %PDF- on an old regulation without affirmative proof

        of being currently in force MUST NOT be marked KEEP (must be UNKNOWN / MANUAL_REVIEW).
        """
        rec = LinkRecord(
            link_id="t1",
            jurisdiction="Bahrain",
            topic="ESG",
            step_section="ESG Legislative Landscape",
            step_description="Bahrain Bourse ESG Reporting Guidance 2020",
            original_url="https://bahrainbourse.com/resources/files/Sustainability/ESG_11%20June%202020.pdf",
            http_status=200,
            technical_status="PDF_VALID",
            access_status="ACCESSIBLE",
            pdf_validation_status="VALID_PDF",
            pdf_magic_signature_verified=True,
            authority_status="TIER_2_EXCHANGE_BODY",
            # No affirmative proof that this 2020 document is still currently in force:
            regulatory_status="UNKNOWN",
            freshness_status="UNKNOWN",
            confidence_score=0.60,
        )
        decision_engine = DecisionEngine()
        canonical_decision = decision_engine.decide_canonical(rec)
        assert canonical_decision == "MANUAL_REVIEW", (
            f"Expected MANUAL_REVIEW for unverified lifecycle despite valid PDF, got: {canonical_decision}"
        )

    def test_2_access_denied_not_document_title(self):
        """Scenario 2: When a page returns 'Access Denied', that string must NOT become

        the document title, technical_page_title must capture it, and identity_conf <= 0.30.
        """
        html = "<html><head><title>Access Denied - 403 Forbidden</title></head><body><h1>Access Denied</h1></body></html>"
        meta = MetadataExtractor.extract("text/html", html, url="https://example.com/blocked")
        
        # Verify technical title rejection
        assert meta.get("technical_page_title") == "Access Denied - 403 Forbidden"
        assert meta.get("title") == "" or meta.get("title") != "Access Denied - 403 Forbidden"

        rec = LinkRecord(
            link_id="t2",
            jurisdiction="United States",
            topic="SEC Climate",
            step_section="ESG Legislative Landscape",
            step_description="SEC Climate Rule",
            original_url="https://www.sec.gov/files/rules/final/2024/33-11275.pdf",
            http_status=403,
            technical_status="ACCESS_BLOCKED",
            access_status="ACCESS_DENIED",
            technical_page_title="Access Denied - 403 Forbidden",
            page_title="",
        )
        sub_scores = ConfidenceEngine.compute_sub_scores(record=rec)
        assert sub_scores["identity_confidence"] <= 0.30
        assert sub_scores["overall_confidence"] <= 0.50

    def test_3_waf_challenge_resolution(self):
        """Scenario 3: Simulate Playwright handling AWS WAF challenge transitioning

        from HTTP 202 challenge to HTTP 200 ACCESSIBLE_VIA_BROWSER.
        """
        rec = LinkRecord(
            link_id="t3",
            jurisdiction="European Union",
            topic="CSRD",
            step_section="ESG Legislative Landscape",
            step_description="Directive (EU) 2022/2464",
            original_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2464",
            http_status=202,
            technical_status="ACCESS_BLOCKED",
            access_status="ACCESS_CHALLENGE",
        )
        # Simulate browser bypass
        rec.http_status = 200
        rec.technical_status = "ACCESSIBLE_VIA_BROWSER"
        rec.access_status = "ACCESSIBLE"
        rec.authority_status = "TIER_1_GOVERNMENT_GAZETTE"
        rec.regulatory_status = "CURRENT_IN_FORCE"
        rec.freshness_status = "CURRENT_IN_FORCE"
        rec.confidence_score = 0.85
        rec.overall_confidence = 0.85

        decision = DecisionEngine().decide_canonical(rec)
        assert decision == "KEEP"

    def test_4_section_scope_exclusivity(self):
        """Scenario 4: Extractor audits ONLY the 13 country accordions in the ESG Legislative

        Landscape section, 100% ignoring outside links.
        """
        html = """
        <html>
          <body>
            <header>
              <a href="https://step.org/about">About STEP</a>
              <a href="https://step.org/contact">Contact Us</a>
            </header>
            <section class="section">
              <h2>ESG Legislative Landscape</h2>
              <div class="block-type--accordion">
                <h5 class="media__body">India</h5>
                <div class="accordion-collapse">
                  <p><strong>SEBI BRSR Framework</strong></p>
                  <a href="https://www.sebi.gov.in/legal/circulars/may-2021/brsr.pdf">SEBI Circular</a>
                </div>
              </div>
            </section>
            <footer>
              <a href="https://step.org/terms">Terms of Service</a>
              <a href="https://step.org/privacy">Privacy Policy</a>
            </footer>
          </body>
        </html>
        """
        extractor = StepExtractor()
        links = extractor.extract_from_html(html, base_url="https://step.mykajabi.com")
        assert len(links) == 1
        assert links[0]["country"] == "India"
        assert links[0]["url"] == "https://www.sebi.gov.in/legal/circulars/may-2021/brsr.pdf"
        assert not any("about" in l["url"] or "terms" in l["url"] for l in links)

    def test_5_gazette_outranks_aggregator(self):
        """Scenario 5: Official gazette/regulator is TIER_1; commercial aggregator is TIER_3."""
        registry = JurisdictionRegistry.get_instance()
        uk_gazette = registry.lookup_domain("legislation.gov.uk", country="United Kingdom")
        assert "TIER_1" in uk_gazette["authority_tier"]

        aggregator = registry.lookup_domain("policyvault.africa", country="Nigeria")
        assert "TIER_3" in aggregator["authority_tier"]
        assert aggregator["is_official"] is False

    def test_6_draft_paper_cannot_replace_final(self):
        """Scenario 6: A draft or consultation paper CANNOT replace an enacted final regulation."""
        rec = LinkRecord(
            link_id="t6",
            jurisdiction="Singapore",
            topic="Environmental Risk Management",
            step_section="ESG Legislative Landscape",
            step_description="MAS Guidelines on Environmental Risk Management",
            original_url="https://www.mas.gov.sg/publications/guidelines/2020/guidelines-on-environmental-risk-management",
            http_status=200,
            technical_status="LIVE",
            instrument_type="Act / Legislation",
            regulatory_status="CURRENT_IN_FORCE",
            # Proposed candidate is a consultation paper:
            replacement_url="https://www.mas.gov.sg/publications/consultations/2020/cp13",
            replacement_title="MAS Consultation Paper CP13 on Guidelines",
            replacement_verified=True,
            candidate_status="CANDIDATE_VERIFIED",
        )
        decision = DecisionEngine().decide_canonical(rec)
        assert decision != "REPLACE", "A draft/consultation cannot replace a final regulation!"

    def test_7_scope_drift_rejection(self):
        """Scenario 7: Newer candidate with mismatched applicability (different topic/population)

        must be rejected for scope drift -> MANUAL_REVIEW.
        """
        rec = LinkRecord(
            link_id="t7",
            jurisdiction="European Union",
            topic="Corporate Sustainability",
            step_section="ESG Legislative Landscape",
            step_description="Corporate Sustainability Due Diligence Directive (CSDDD)",
            original_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024L1760",
            http_status=200,
            regulatory_topic="Due Diligence & Supply Chain",
            regulated_population="Large Enterprises / PIEs",
            # Candidate covers voluntary SME reporting, not supply chain due diligence:
            replacement_url="https://efrag.org/vsme-standards",
            replacement_title="VSME Voluntary Standard for Non-Listed SMEs",
            replacement_verified=True,
            candidate_status="CANDIDATE_VERIFIED",
            replacement_relationship="MISMATCHED_APPLICABILITY",
        )
        decision = DecisionEngine().decide_canonical(rec)
        assert decision == "MANUAL_REVIEW"

    def test_8_outdated_replacement(self):
        """Scenario 8: Superseded regulation with verified replacement -> REPLACE."""
        rec = LinkRecord(
            link_id="t8",
            jurisdiction="European Union",
            topic="CSRD",
            step_section="ESG Legislative Landscape",
            step_description="Non-Financial Reporting Directive (NFRD) 2014/95/EU",
            original_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32014L0095",
            http_status=200,
            technical_status="LIVE",
            regulatory_status="SUPERSEDED",
            freshness_status="COMPLETELY_SUPERSEDED",
            authority_status="TIER_1_OFFICIAL_REGULATOR",
            replacement_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2464",
            replacement_title="Corporate Sustainability Reporting Directive (CSRD) (EU) 2022/2464",
            replacement_verified=True,
            candidate_status="REPLACEMENT_VERIFIED",
            replacement_relationship="REPLACEMENT",
            confidence_score=0.90,
            overall_confidence=0.90,
        )
        decision = DecisionEngine().decide_canonical(rec)
        assert decision == "REPLACE"

    def test_9_broken_link_fix(self):
        """Scenario 9: Dead link (HTTP 404) with verified replacement for exact same instrument -> FIX_BROKEN_LINK."""
        rec = LinkRecord(
            link_id="t9",
            jurisdiction="India",
            topic="BRSR",
            step_section="ESG Legislative Landscape",
            step_description="SEBI BRSR Master Circular",
            original_url="https://www.sebi.gov.in/legal/circulars/old/broken-brsr.pdf",
            http_status=404,
            technical_status="HTTP_404",
            access_status="BROKEN",
            replacement_url="https://www.sebi.gov.in/legal/circulars/jul-2023/master-circular-for-brsr.pdf",
            replacement_title="SEBI Master Circular for BRSR",
            replacement_verified=True,
            candidate_status="REPLACEMENT_VERIFIED",
            replacement_relationship="EXACT_SAME_INSTRUMENT",
            confidence_score=0.90,
            overall_confidence=0.90,
        )
        decision = DecisionEngine().decide_canonical(rec)
        assert decision == "FIX_BROKEN_LINK"

    def test_10_canonical_redirect_update(self):
        """Scenario 10: Permanent canonical redirect within official authority -> UPDATE."""
        rec = LinkRecord(
            link_id="t10",
            jurisdiction="United Kingdom",
            topic="Environment",
            step_section="ESG Legislative Landscape",
            step_description="Environment Act 2021",
            original_url="https://legislation.gov.uk/ukpga/2021/30",
            final_url="https://www.legislation.gov.uk/ukpga/2021/30/contents/enacted",
            http_status=200,
            technical_status="REDIRECTED",
            redirect_status="permanent_redirect",
            classification="VALID_BUT_REDIRECTED",
            authority_status="TIER_1_GOVERNMENT_GAZETTE",
            confidence_score=0.85,
            overall_confidence=0.85,
        )
        decision = DecisionEngine().decide_canonical(rec)
        assert decision == "UPDATE"

    def test_11_unknown_lifecycle_safety(self):
        """Scenario 11: Insufficient affirmative evidence forces UNKNOWN and MANUAL_REVIEW."""
        rec = LinkRecord(
            link_id="t11",
            jurisdiction="Saudi Arabia",
            topic="Tadawul Guidelines",
            step_section="ESG Legislative Landscape",
            step_description="Tadawul ESG Disclosure Guidelines",
            original_url="https://www.saudiexchange.sa/wps/wcm/connect/tadawul/esg.pdf",
            http_status=200,
            technical_status="LIVE",
            regulatory_status="UNKNOWN",
            freshness_status="UNKNOWN",
            confidence_score=0.45,
            overall_confidence=0.45,
        )
        decision = DecisionEngine().decide_canonical(rec)
        assert decision == "MANUAL_REVIEW"
        assert rec.regulatory_status == "UNKNOWN"

    def test_12_evidence_trail_completeness(self):
        """Scenario 12: EvidenceTrail properly tags categories and produces human-readable 'Why?' summary."""
        trail = EvidenceTrail()
        trail.add(category="extraction", claim="Extracted from ESG Legislative Landscape", detail="India accordion")
        trail.add(category="technical", claim="HTTP 200 OK", detail="Direct PDF Stream")
        trail.add(category="authority", claim="SEBI verified as TIER_1_OFFICIAL_REGULATOR")
        trail.add(category="identity", claim="BRSR Core Framework for Top 1000 Listed Entities")
        trail.add(category="currentness", claim="Confirmed legally binding in force under SEBI LODR 2023")

        summary = trail.summary("KEEP")
        assert "Why was this marked KEEP?" in summary
        assert "Extraction" in summary
        assert "Technical" in summary
        assert "Authority" in summary
        assert "Identity" in summary
        assert "Currentness" in summary

        json_str = trail.to_json()
        data = json.loads(json_str)
        assert len(data) == 5
        assert data[0]["type"] == "extraction"

    def test_13_sec_fair_access_and_pdf_validation(self):
        """Scenario 13: SEC Fair Access header enables HTTP 200 PDF fetch with magic bytes."""
        from content.pdf_engine import PdfEngine
        from crawler.url_checker import UrlChecker

        # Verify default SEC Fair Access User-Agent format
        checker = UrlChecker()
        ua = checker.session.headers.get("User-Agent", "")
        assert "STEP-ESG-Auditor" in ua
        assert "compliance@step-monitoring.org" in ua

        # Verify PDF Engine handles direct PDF signature verification
        dummy_pdf = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
        sig_verified = PdfEngine.verify_magic_bytes(dummy_pdf)
        assert sig_verified is True

    def test_14_concatenated_url_normalization(self):
        """Scenario 14: Concatenated URLs with embedded query parameters are cleanly separated."""
        from crawler.url_normalizer import UrlNormalizer

        merged_raw = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023DC0012https://eur-lex.europa.eu/eli/reg_del/2023/2772/oj/eng&utm_source=gemini"
        clean = UrlNormalizer.normalize(merged_raw)
        assert clean == "https://eur-lex.europa.eu/eli/reg_del/2023/2772/oj/eng"

    def test_15_cloudflare_challenge_granular_classification(self):
        """Scenario 15: Cloudflare anti-bot challenge is accurately classified as BOT_PROTECTION."""
        from crawler.url_checker import UrlChecker
        from unittest.mock import MagicMock

        checker = UrlChecker()
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.headers = {"cf-ray": "8432a184e9123-AMS", "server": "cloudflare"}
        html_snippet = "<html><head><title>Just a moment...</title></head><body><div id='cf-wrapper'>cf-chl-</div></body></html>"
        
        status, reason = checker._classify_access(mock_resp, html_snippet, "Just a moment...")
        assert status == "CLOUDFLARE_CHALLENGE"
        assert "Cloudflare" in reason

    def test_16_playwright_internal_pdf_viewer_resolution(self):
        """Scenario 16: Chrome internal PDF viewer extension at HTTP 200 is resolved as ACCESSIBLE."""
        rec = LinkRecord(
            link_id="t16",
            jurisdiction="United Arab Emirates",
            topic="UAE Cabinet Resolution",
            step_section="ESG Legislative Landscape",
            step_description="Cabinet Resolution No. (67) of 2024",
            original_url="https://uaelegislation.gov.ae/en/legislations/2521/download",
            http_status=200,
            technical_status="ACCESSIBLE_VIA_BROWSER",
            access_status="ACCESSIBLE",
            document_type="PDF Regulation / Document",
            authority_status="TIER_1_GOVERNMENT_GAZETTE",
            regulatory_status="CURRENT_IN_FORCE",
            freshness_status="CURRENT_IN_FORCE",
            confidence_score=0.90,
            overall_confidence=0.90,
        )
        decision = DecisionEngine().decide_canonical(rec)
        assert decision == "KEEP"
        assert rec.access_status == "ACCESSIBLE"
        assert rec.technical_status == "ACCESSIBLE_VIA_BROWSER"

    def test_17_technical_error_title_filtering(self):
        """Scenario 17: Technical titles (Access Denied, Just a moment, JS disabled) are never used as document titles."""
        from content.html_parser import TECHNICAL_TITLE_PATTERNS
        import re

        test_titles = [
            "Access Denied",
            "403 Forbidden",
            "Just a moment...",
            "Attention Required! | Cloudflare",
            "JavaScript is disabled",
            "Rate threshold exceeded",
        ]
        for title in test_titles:
            is_match = any(re.search(pat, title, re.I) for pat in TECHNICAL_TITLE_PATTERNS)
            assert is_match, f"Failed to reject technical title: {title}"
