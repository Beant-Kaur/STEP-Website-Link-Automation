from __future__ import annotations

from ai.confidence_engine import ConfidenceEngine
from ai.evaluator import AiEvaluationResult
from analysis.source_classifier import SourceClassifier
from analysis.freshness_checker import FreshnessChecker
from analysis.content_comparator import ContentComparator


class TestSourceClassifier:
    def test_tier1(self):
        assert SourceClassifier.classify("ec.europa.eu") == "Tier 1"
        assert SourceClassifier.classify("sec.gov") == "Tier 1"

    def test_tier2(self):
        assert SourceClassifier.classify("iso.org") == "Tier 2"

    def test_tier4(self):
        assert SourceClassifier.classify("example.com") == "Tier 4"


class TestFreshnessChecker:
    def test_outdated(self):
        assert FreshnessChecker.evaluate("This document has been replaced by a newer version.") == "outdated"

    def test_current(self):
        assert FreshnessChecker.evaluate("Current regulation in force effective from 2024.") == "current"


class TestConfidenceEngine:
    def test_high_confidence(self):
        engine = ConfidenceEngine()
        result = AiEvaluationResult(
            classification="VALID_AND_CURRENT",
            technical_status="accessible",
            source_authority="Tier 1",
            source_organisation="Official regulator",
            content_relevance="high",
            regulatory_status="current",
            freshness_status="current",
            replacement_required=False,
            replacement_url="",
            replacement_reason="",
            confidence_score=0.0,
            recommended_action="KEEP",
        )
        scored = engine.apply(result)
        assert scored.confidence_score > 0.7


class TestContentComparator:
    def test_hash_changes(self):
        comparator = ContentComparator()
        h1 = comparator.hash_text("alpha")
        h2 = comparator.hash_text("beta")
        assert comparator.has_changed(h1, h2) is True
        assert comparator.has_changed(h1, h1) is False

    def test_similarity(self):
        comparator = ContentComparator()
        sim = comparator.similarity("esg regulation reporting", "esg regulation reporting framework")
        assert sim > 0.0


class TestHtmlParser:
    def test_soft_404(self):
        from content.html_parser import HtmlParser
        html = "<html><head><title>404 - Page Not Found</title></head><body><h1>404 Not Found</h1></body></html>"
        res = HtmlParser.parse(html)
        assert res["is_soft_404"] is True

    def test_maintenance(self):
        from content.html_parser import HtmlParser
        html = "<html><head><title>Maintenance</title></head><body>System temporarily down</body></html>"
        res = HtmlParser.parse(html)
        assert res["is_maintenance"] is True

    def test_substantive_extraction(self):
        from content.html_parser import HtmlParser
        html = """
        <html>
          <head><title>CSRD Guidance</title></head>
          <body>
            <nav>Menu items here</nav>
            <main>
              <h1>Corporate Sustainability Reporting Directive</h1>
              <p>Effective from 1 January 2024 for public interest entities.</p>
            </main>
            <footer>Copyright info</footer>
          </body>
        </html>
        """
        res = HtmlParser.parse(html)
        assert "Corporate Sustainability Reporting" in res["text_sample"]
        assert "Effective from" in res["text_sample"]
        assert res["is_soft_404"] is False


class TestEsgFreshnessAndReplacements:
    def test_california_sb253_military_detected_outdated(self):
        status = FreshnessChecker.evaluate(
            "Military: service: elected officers.",
            title="Bill Text - SB-253 Military",
            url="https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202120220SB253",
        )
        assert status == "outdated"

    def test_nfrd_superseded_by_csrd(self):
        status = FreshnessChecker.evaluate(
            "Non-Financial Reporting Directive 2014/95/EU requirements for companies.",
            title="NFRD Requirements",
        )
        assert status == "outdated"

    def test_sec_stay_status(self):
        status = FreshnessChecker.evaluate(
            "The Enhancement and Standardization of Climate-Related Disclosures for Investors",
            url="https://www.sec.gov/files/rules/final/2024/33-11275.pdf",
        )
        assert status == "regulatory_status_changed"

    def test_replacement_finder_sb253(self):
        from ai.replacement_finder import ReplacementFinder
        from database.models import LinkRecord
        finder = ReplacementFinder()
        rec = LinkRecord(
            link_id="test_1",
            jurisdiction="US",
            topic="Climate",
            step_section="Landscape",
            step_description="California SB-253",
            original_url="https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202120220SB253",
            page_title="Bill Text - SB-253 Military",
        )
        url, title, reason = finder.find_replacement(rec, {})
        assert "202320240SB253" in url
        assert "Climate" in title

    def test_mock_ai_evaluates_soft_404(self):
        from ai.evaluator import MockAiProvider
        from database.models import LinkRecord
        provider = MockAiProvider()
        rec = LinkRecord(
            link_id="test_soft_404",
            jurisdiction="",
            topic="",
            step_section="",
            step_description="ADX download",
            original_url="https://adxservices.adx.ae/download",
            http_status=200,
        )
        res = provider.evaluate(rec, {"is_soft_404": True})
        assert res.classification == "BROKEN"
        assert res.recommended_action == "RECOMMEND_REPLACEMENT"

    def test_mock_ai_evaluates_outdated_freshness(self):
        from ai.evaluator import MockAiProvider
        from database.models import LinkRecord
        provider = MockAiProvider()
        rec = LinkRecord(
            link_id="test_outdated",
            jurisdiction="",
            topic="",
            step_section="",
            step_description="Outdated link",
            original_url="https://example.com/old",
            http_status=200,
            freshness_status="outdated",
        )
        res = provider.evaluate(rec, {})
        assert res.classification == "WORKING_BUT_OUTDATED"
        assert res.recommended_action == "RECOMMEND_REPLACEMENT"

    def test_outdated_with_replacement_high_confidence(self):
        engine = ConfidenceEngine()
        result = AiEvaluationResult(
            classification="WORKING_BUT_OUTDATED",
            technical_status="accessible",
            source_authority="Tier 1",
            source_organisation="Legislature",
            content_relevance="high",
            regulatory_status="superseded",
            freshness_status="outdated",
            replacement_required=True,
            replacement_url="https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240SB253",
            replacement_reason="Original URL linked to 2021 Military bill; updated to 2023-2024 Climate Act.",
            confidence_score=0.0,
            recommended_action="RECOMMEND_REPLACEMENT",
        )
        scored = engine.apply(result, metadata={"outdated_reason": "Military bill session mismatch"})
        assert scored.confidence_score >= 0.90
        assert "obsolescence" in scored.confidence_reason.lower()

    def test_access_restricted_low_confidence(self):
        engine = ConfidenceEngine()
        result = AiEvaluationResult(
            classification="ACCESS_RESTRICTED",
            technical_status="access_restricted",
            source_authority="Tier 1",
            source_organisation="",
            content_relevance="unknown",
            regulatory_status="unknown",
            freshness_status="unknown",
            replacement_required=False,
            replacement_url="",
            replacement_reason="",
            confidence_score=0.0,
            recommended_action="HUMAN_REVIEW",
        )
        scored = engine.apply(result)
        assert scored.confidence_score <= 0.35

    def test_replacement_finder_csrd(self):
        from ai.replacement_finder import ReplacementFinder
        from database.models import LinkRecord
        finder = ReplacementFinder()
        rec = LinkRecord(
            link_id="test_nfrd",
            jurisdiction="EU",
            topic="Reporting",
            step_section="Landscape",
            step_description="NFRD Directive 2014/95/EU",
            original_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32014L0095",
        )
        url, title, reason = finder.find_replacement(rec, {})
        assert "2022/2464" in url
        assert "CSRD" in title

    def test_replacement_finder_tcfd_to_issb(self):
        from ai.replacement_finder import ReplacementFinder
        from database.models import LinkRecord
        finder = ReplacementFinder()
        rec = LinkRecord(
            link_id="test_tcfd",
            jurisdiction="Global",
            topic="Climate",
            step_section="Landscape",
            step_description="TCFD recommendations",
            original_url="https://www.fsb-tcfd.org/recommendations/",
        )
        url, title, reason = finder.find_replacement(rec, {})
        assert "ifrs.org" in url
        assert "ISSB" in title or "IFRS" in title

    def test_replacement_finder_merged_eurlex(self):
        from ai.replacement_finder import ReplacementFinder
        from database.models import LinkRecord
        finder = ReplacementFinder()
        rec = LinkRecord(
            link_id="test_merged",
            jurisdiction="EU",
            topic="ESRS",
            step_section="Standards",
            step_description="ESRS Set 1",
            original_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023DC0012https://eur-lex.europa.eu/eli/reg_del/2023/2772/oj",
        )
        url, title, reason = finder.find_replacement(rec, {})
        assert "2023/2772" in url

    def test_freshness_checker_sebi_brsr_2021(self):
        status = FreshnessChecker.evaluate(
            "SEBI Circular CIR/2021/562 on Business Responsibility and Sustainability Reporting",
            title="BRSR 2021 Circular",
            url="https://www.sebi.gov.in/legal/circulars/may-2021/business-responsibility-and-sustainability-reporting_50097.html",
        )
        assert status == "outdated"

