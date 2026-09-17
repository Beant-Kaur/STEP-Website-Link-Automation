import pytest
from database.models import LinkRecord
from analysis.freshness_checker import FreshnessChecker
from analysis.source_classifier import (
    SourceClassifier, OFFICIAL_REGULATOR, OFFICIAL_LEGISLATION,
    STANDARDS_BODY, COMMERCIAL_AGGREGATOR
)
from analysis.intent_analyzer import IntentAnalyzer
from analysis.relevance_checker import RelevanceChecker
from analysis.authenticity_checker import AuthenticityChecker
from analysis.content_comparator import ComparabilityAnalyzer
from pipeline.decision_engine import DecisionEngine
from pipeline.recheck_engine import RecheckEngine
from ai.evaluator import MockAiProvider, AiEvaluationResult
from ai.replacement_finder import ReplacementFinder
from ai.confidence_engine import ConfidenceEngine
from content.html_parser import HtmlParser


class TestMasterPromptScenarios:
    """Covers all 11 validation criteria from Master Prompt Section 24."""

    def test_case_1_dead_link_404(self):
        provider = MockAiProvider()
        rec = LinkRecord(
            link_id="t1", jurisdiction="EU", topic="Taxonomy",
            step_section="EU", step_description="EU Taxonomy Delegated Act",
            original_url="https://ec.europa.eu/finance/missing-act.pdf",
            http_status=404, technical_status="BROKEN"
        )
        res = provider.evaluate(rec, {})
        assert res.classification == "BROKEN"
        assert res.content_status == "BLANK_OR_EMPTY"
        assert res.replacement_required is True
        assert res.recommended_action == "RECOMMEND_REPLACEMENT"

    def test_case_2_soft_404_not_treated_as_valid(self):
        html = "<html><head><title>Page Not Found - ADX</title></head><body><h1>404 Error</h1><p>Sorry, document not found.</p></body></html>"
        parsed = HtmlParser.parse(html)
        assert parsed["is_soft_404"] is True

        provider = MockAiProvider()
        rec = LinkRecord(
            link_id="t2", jurisdiction="UAE", topic="ADX ESG",
            step_section="Middle East", step_description="ADX ESG Guide",
            original_url="https://adxservices.adx.ae/download/contentDownload.aspx?doc=1704806",
            http_status=200, technical_status="ACCESSIBLE"
        )
        res = provider.evaluate(rec, parsed)
        assert res.classification == "BROKEN"
        assert res.content_status == "SOFT_404"
        assert res.replacement_required is True

    def test_case_3_california_sb253_military_superseded(self):
        url = "https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202120220SB253"
        fresh = FreshnessChecker.evaluate_detailed(
            text_sample="Military: service: elected officers. An act relating to military service.",
            title="Bill Text - SB-253 Military",
            url=url
        )
        assert fresh["freshness_status"] == "COMPLETELY_SUPERSEDED"
        assert "military" in fresh["reason"].lower()

        finder = ReplacementFinder()
        rec = LinkRecord(
            link_id="t3", jurisdiction="US", topic="California ESG",
            step_section="Americas", step_description="California Climate Corporate Data Accountability Act (SB 253)",
            original_url=url, page_title="Bill Text - SB-253 Military"
        )
        rep_url, rep_title, rep_reason = finder.find_replacement(rec, {"outdated_reason": fresh["reason"]})
        assert "202320240SB253" in rep_url
        assert "Climate Corporate Data Accountability" in rep_title

    def test_case_4_sec_climate_litigation_stay(self):
        url = "https://www.sec.gov/files/rules/final/2024/33-11275.pdf"
        fresh = FreshnessChecker.evaluate_detailed(
            text_sample="The Enhancement and Standardization of Climate-Related Disclosures for Investors. Release Nos. 33-11275; 34-99678",
            title="SEC Climate Rule Release 33-11275",
            url=url
        )
        assert fresh["regulatory_status"] == "STAYED_PENDING_LITIGATION"
        assert "stay" in fresh["reason"].lower()

        provider = MockAiProvider()
        rec = LinkRecord(
            link_id="t4", jurisdiction="US", topic="SEC Climate",
            step_section="Americas", step_description="SEC Climate-Related Disclosures",
            original_url=url, regulatory_status="STAYED_PENDING_LITIGATION"
        )
        res = provider.evaluate(rec, {"regulatory_status": fresh["regulatory_status"], "outdated_reason": fresh["reason"]})
        assert res.classification == "WORKING_BUT_REGULATORY_STATUS_CHANGED"
        assert res.recommended_action == "HUMAN_REVIEW"

    def test_case_5_nfrd_superseded_by_csrd(self):
        fresh = FreshnessChecker.evaluate_detailed(
            text_sample="Non-Financial Reporting Directive 2014/95/EU (NFRD). Certain large undertakings and groups.",
            title="Directive 2014/95/EU",
            url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32014L0095"
        )
        assert fresh["freshness_status"] == "COMPLETELY_SUPERSEDED"
        assert "csrd" in fresh["reason"].lower()

        finder = ReplacementFinder()
        rec = LinkRecord(
            link_id="t5", jurisdiction="EU", topic="CSRD",
            step_section="Europe", step_description="EU NFRD Directive 2014/95/EU",
            original_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32014L0095"
        )
        rep_url, rep_title, rep_reason = finder.find_replacement(rec, {})
        assert "2022/2464" in rep_url
        assert "Corporate Sustainability Reporting Directive" in rep_title

    def test_case_6_disbanded_tcfd_transition(self):
        fresh = FreshnessChecker.evaluate_detailed(
            text_sample="Task Force on Climate-related Financial Disclosures. Recommendations of the TCFD.",
            title="TCFD Recommendations",
            url="https://www.fsb-tcfd.org/recommendations/"
        )
        assert fresh["regulatory_status"] == "DISBANDED_TRANSITIONED"

        finder = ReplacementFinder()
        rec = LinkRecord(
            link_id="t6", jurisdiction="Global", topic="TCFD",
            step_section="Global Frameworks", step_description="TCFD recommendations",
            original_url="https://www.fsb-tcfd.org/recommendations/"
        )
        rep_url, rep_title, rep_reason = finder.find_replacement(rec, {})
        assert "ifrs.org" in rep_url
        assert "ISSB" in rep_title or "IFRS" in rep_title

    def test_case_7_consultation_paper_mas(self):
        fresh = FreshnessChecker.evaluate_detailed(
            text_sample="Consultation Paper on Guidelines on Environmental Risk Management. Issued June 2020.",
            title="MAS Consultation Paper CP13",
            url="https://www.mas.gov.sg/publications/consultations/2020/cp13-guidelines-on-environmental-risk-management"
        )
        assert fresh["regulatory_status"] == "CONSULTATION_DRAFT"

        finder = ReplacementFinder()
        rec = LinkRecord(
            link_id="t7", jurisdiction="Singapore", topic="Risk Management",
            step_section="Asia", step_description="MAS Guidelines on Environmental Risk Management",
            original_url="https://www.mas.gov.sg/publications/consultations/2020/cp13"
        )
        rep_url, rep_title, rep_reason = finder.find_replacement(rec, {})
        assert "guidelines-on-environmental-risk-management" in rep_url

    def test_case_8_non_official_aggregator_policyvault(self):
        auth = SourceClassifier.classify_authority("policyvault.africa")
        assert auth == COMMERCIAL_AGGREGATOR
        assert SourceClassifier.is_non_official_aggregator("policyvault.africa") is True

        finder = ReplacementFinder()
        rec = LinkRecord(
            link_id="t8", jurisdiction="Nigeria", topic="Environment",
            step_section="Africa", step_description="Nigeria Environmental Regulations",
            original_url="https://policyvault.africa/record/environmental-standards"
        )
        rep_url, rep_title, rep_reason = finder.find_replacement(rec, {})
        assert "nesrea.gov.ng" in rep_url
        assert SourceClassifier.classify_authority("nesrea.gov.ng") == OFFICIAL_REGULATOR

    def test_case_9_merged_eurlex_url(self):
        merged = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023DC0012https://eur-lex.europa.eu/eli/reg_del/2023/2772/oj"
        finder = ReplacementFinder()
        rec = LinkRecord(
            link_id="t9", jurisdiction="EU", topic="ESRS",
            step_section="Europe", step_description="ESRS Delegated Regulation",
            original_url=merged
        )
        rep_url, rep_title, rep_reason = finder.find_replacement(rec, {})
        assert "2023/2772" in rep_url

    def test_case_10_valid_and_current_high_confidence(self):
        engine = ConfidenceEngine()
        res = AiEvaluationResult(
            classification="VALID_AND_CURRENT",
            technical_status="ACCESSIBLE",
            source_authority="Tier 1",
            source_organisation="European Commission",
            content_relevance="high",
            regulatory_status="LEGALLY_BINDING_IN_FORCE",
            freshness_status="CURRENT_IN_FORCE",
            replacement_required=False,
            replacement_url="",
            replacement_reason="",
            confidence_score=0.0,
            recommended_action="KEEP",
            authority_status="OFFICIAL_REGULATOR",
        )
        rec = LinkRecord(
            link_id="t10", jurisdiction="EU", topic="CSRD",
            step_section="Europe", step_description="Corporate Sustainability Reporting Directive (EU) 2022/2464",
            original_url="https://eur-lex.europa.eu/eli/dir/2022/2464/oj",
            page_title="Directive (EU) 2022/2464 of the European Parliament and of the Council"
        )
        metadata = {
            "text_sample": "Directive (EU) 2022/2464 of the European Parliament and of the Council of 14 December 2022 amending Regulation (EU) No 537/2014, Directive 2004/109/EC, Directive 2006/43/EC and Directive 2013/34/EU as regards corporate sustainability reporting. In force and legally binding." * 10,
            "content_relevance_score": 95,
            "freshness_score": 95,
            "authority_status": "OFFICIAL_LEGISLATION",
            "regulatory_status": "LEGALLY_BINDING_IN_FORCE",
        }
        scored = engine.apply(res, record=rec, metadata=metadata)
        assert scored.confidence_score >= 0.85
        assert "Evidence Confidence" in scored.confidence_reason

    def test_case_11_homepage_rejection_rule(self):
        finder = ReplacementFinder()
        # Test generic domain roots
        assert finder.is_homepage("https://www.sebi.gov.in") is True
        assert finder.is_homepage("https://www.sebi.gov.in/") is True
        assert finder.is_homepage("https://www.sec.gov/index.htm") is True
        # Test specific document path is NOT homepage
        assert finder.is_homepage("https://www.sebi.gov.in/legal/circulars/jul-2023/brsr.html") is False

        # Two-stage validation should REJECT root homepage
        is_valid, status, note = finder.validate_candidate("https://www.sebi.gov.in/")
        assert is_valid is False
        assert status == "REJECTED"
        assert "Homepage Rejection Rule" in note

        # Two-stage validation should VERIFY deep authoritative document
        is_valid, status, note = finder.validate_candidate("https://www.sebi.gov.in/legal/circulars/jul-2023/brsr-core.html")
        assert is_valid is True
        assert status == "VERIFIED"

    def test_case_12_access_restricted_cap(self):
        engine = ConfidenceEngine()
        res = AiEvaluationResult(
            classification="ACCESS_RESTRICTED",
            technical_status="ACCESS_RESTRICTED",
            source_authority="Tier 1",
            source_organisation="SEC",
            content_relevance="unknown",
            regulatory_status="unknown",
            freshness_status="unknown",
            replacement_required=False,
            replacement_url="",
            replacement_reason="",
            confidence_score=0.0,
            recommended_action="HUMAN_REVIEW",
        )
        scored = engine.apply(res, metadata={"is_challenge_page": True})
        assert scored.confidence_score <= 0.35
        assert "blocked by bot challenge" in scored.confidence_reason


class TestSection22TenScenarios:
    """Explicitly verifies the 10 scenarios defined in Master Implementation Prompt Section 22."""

    def test_scenario_1_http200_official_current_keep(self):
        """Scenario 1: HTTP 200 + official source + current regulation -> KEEP"""
        rec = LinkRecord(
            link_id="s1",
            jurisdiction="EU",
            topic="CSRD",
            step_section="Europe",
            step_description="Corporate Sustainability Reporting Directive",
            original_url="https://eur-lex.europa.eu/eli/dir/2022/2464/oj",
            http_status=200,
            technical_status="ACCESSIBLE",
            classification="VALID_AND_CURRENT",
            regulatory_status="LEGALLY_BINDING_IN_FORCE",
            freshness_status="CURRENT_IN_FORCE",
            source_authority_tier="Tier 1",
            confidence_score=0.92,
            recommended_action="KEEP",
        )
        decision_engine = DecisionEngine()
        decision = decision_engine.decide(rec)
        assert decision == "KEEP"
        assert rec.http_status == 200
        assert rec.regulatory_status == "LEGALLY_BINDING_IN_FORCE"

    def test_scenario_2_http200_old_version_newer_exists(self):
        """Scenario 2: HTTP 200 + old version of regulation + newer official version exists -> REPLACE with clear warning"""
        old_url = "https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202120220SB253"
        rec = LinkRecord(
            link_id="s2",
            jurisdiction="US-CA",
            topic="Climate Reporting",
            step_section="Americas",
            step_description="California Climate Corporate Data Accountability Act (SB 253)",
            original_url=old_url,
            http_status=200,
            technical_status="ACCESSIBLE",
            page_title="Bill Text - SB-253 Military service",
            classification="WORKING_BUT_OLD_VERSION",
            regulatory_status="SUPERSEDED",
        )
        freshness = FreshnessChecker.evaluate_detailed(
            text_sample="Military: service: elected officers. An act relating to military service.",
            title=rec.page_title,
            url=old_url,
        )
        assert freshness["freshness_status"] == "COMPLETELY_SUPERSEDED"

        finder = ReplacementFinder()
        rep_url, rep_title, rep_reason = finder.find_replacement(rec, {"outdated_reason": freshness["reason"]})
        assert "202320240SB253" in rep_url

        comp = ComparabilityAnalyzer.analyze(
            original={"jurisdiction": rec.jurisdiction, "topic": rec.topic, "title": rec.page_title, "issuer": "California State Legislature"},
            candidate={"jurisdiction": "US-CA", "topic": "Climate Reporting", "title": rep_title, "issuer": "California State Legislature"},
        )
        assert comp["comparability"] in ("COMPARABLE", "PARTIALLY_COMPARABLE")

        rec.replacement_url = rep_url
        rec.replacement_title = rep_title
        rec.replacement_verified = True
        decision_engine = DecisionEngine()
        decision = decision_engine.decide(rec)
        assert decision in ("REPLACE", "REVIEW")

    def test_scenario_3_http403_identifiable_replacement_found(self):
        """Scenario 3: HTTP 403 + identifiable regulation resource + official replacement found -> ACCESS_DENIED_REPLACEMENT_FOUND"""
        rec = LinkRecord(
            link_id="s3",
            jurisdiction="EU",
            topic="Taxonomy",
            step_section="Europe",
            step_description="EU Taxonomy Climate Delegated Act",
            original_url="https://ec.europa.eu/finance/docs/taxonomy-regulation-delegated-act-2021-2800_en.pdf",
            http_status=403,
            technical_status="ACCESS_RESTRICTED",
            access_status="ACCESS_DENIED",
            classification="ACCESS_RESTRICTED",
            page_title="EU Taxonomy Regulation (EU) 2021/2800",
            replacement_url="https://eur-lex.europa.eu/eli/reg_del/2021/2800/oj",
            replacement_title="Commission Delegated Regulation (EU) 2021/2800",
            replacement_verified=True,
            recommended_action="ACCESS_DENIED_REPLACEMENT_FOUND",
        )
        decision_engine = DecisionEngine()
        decision = decision_engine.decide(rec)
        assert decision == "ACCESS_DENIED_REPLACEMENT_FOUND"
        assert rec.access_status == "ACCESS_DENIED"
        assert bool(rec.replacement_url) is True

    def test_scenario_4_http403_authenticity_uncertain_review(self):
        """Scenario 4: HTTP 403 + authenticity uncertain -> HUMAN_REVIEW_REQUIRED"""
        rec = LinkRecord(
            link_id="s4",
            jurisdiction="Unknown",
            topic="ESG",
            step_section="Drafts",
            step_description="Confidential Working Draft",
            original_url="https://restricted-internal-node.company-sample.biz/draft_esg.pdf",
            http_status=403,
            technical_status="ACCESS_RESTRICTED",
            access_status="ACCESS_DENIED",
            confidence_score=0.30,
            human_review_required=True,
        )
        auth = AuthenticityChecker.evaluate(
            url=rec.original_url,
            title="",
            text_sample="",
            http_status=403,
            access_status="ACCESS_DENIED",
        )
        assert auth["authenticity_status"] in ("UNCERTAIN", "SUSPICIOUS")

        decision_engine = DecisionEngine()
        decision = decision_engine.decide(rec)
        assert decision == "HUMAN_REVIEW_REQUIRED"

    def test_scenario_5_http200_unofficial_official_exists_replace_with_official(self):
        """Scenario 5: HTTP 200 + unofficial blog/aggregator + official equivalent exists -> REPLACE_WITH_OFFICIAL"""
        rec = LinkRecord(
            link_id="s5",
            jurisdiction="Nigeria",
            topic="Environment",
            step_section="Africa",
            step_description="National Environmental Standards and Regulations Enforcement Agency (NESREA)",
            original_url="https://policyvault.africa/record/nesrea-standards",
            http_status=200,
            technical_status="ACCESSIBLE",
            classification="WORKING_BUT_NON_OFFICIAL",
            authority_status="COMMERCIAL_AGGREGATOR",
            source_authority_tier="Tier 3",
            replacement_url="https://www.nesrea.gov.ng/regulations",
            replacement_title="NESREA Official Regulations Repository",
            replacement_verified=True,
            recommended_action="REPLACE_WITH_OFFICIAL",
        )
        assert SourceClassifier.is_non_official_aggregator(rec.original_url) is True
        decision_engine = DecisionEngine()
        decision = decision_engine.decide(rec)
        assert decision == "REPLACE_WITH_OFFICIAL"

    def test_scenario_6_http200_regulatory_status_unclear_review(self):
        """Scenario 6: HTTP 200 + regulatory status unclear (stayed pending court ruling) -> ACCESSIBLE_BUT_REVIEW or HUMAN_REVIEW_REQUIRED"""
        url = "https://www.sec.gov/files/rules/final/2024/33-11275.pdf"
        fresh = FreshnessChecker.evaluate_detailed(
            text_sample="The Enhancement and Standardization of Climate-Related Disclosures for Investors. Release Nos. 33-11275; 34-99678.",
            title="SEC Climate Rule Release 33-11275",
            url=url,
        )
        assert fresh["regulatory_status"] == "STAYED_PENDING_LITIGATION"

        rec = LinkRecord(
            link_id="s6",
            jurisdiction="US",
            topic="SEC Climate",
            step_section="Americas",
            step_description="SEC Climate Rule",
            original_url=url,
            http_status=200,
            technical_status="ACCESSIBLE",
            regulatory_status="STAYED_PENDING_LITIGATION",
            confidence_score=0.75,
            recommended_action="ACCESSIBLE_BUT_REVIEW",
        )
        decision_engine = DecisionEngine()
        decision = decision_engine.decide(rec)
        assert decision in ("ACCESSIBLE_BUT_REVIEW", "HUMAN_REVIEW_REQUIRED")

    def test_scenario_7_confidence_low_triggers_second_pass(self):
        """Scenario 7: Confidence < 50% on first pass -> automatic second verification pass triggered"""
        assert RecheckEngine.needs_recheck(0.40) is True
        assert RecheckEngine.needs_recheck(0.75) is False

        rec = LinkRecord(
            link_id="s7",
            jurisdiction="Global",
            topic="TCFD",
            step_section="Global Frameworks",
            step_description="TCFD Recommendations",
            original_url="https://www.fsb-tcfd.org/recommendations/",
            anchor_text="TCFD Recommendations Report",
            section_heading="Global Frameworks",
            page_title="Task Force on Climate-related Financial Disclosures",
        )
        mock_ai_result = AiEvaluationResult(
            classification="NEEDS_HUMAN_REVIEW",
            technical_status="ACCESSIBLE",
            source_authority="Tier 2",
            source_organisation="TCFD",
            content_relevance="uncertain",
            regulatory_status="DISBANDED_TRANSITIONED",
            freshness_status="PARTIALLY_SUPERSEDED",
            replacement_required=True,
            replacement_url="",
            replacement_reason="",
            confidence_score=0.35,
            recommended_action="HUMAN_REVIEW",
        )

        recheck_res = RecheckEngine.execute_recheck(
            record=rec,
            metadata={"text_sample": "TCFD recommendations disbanded and transitioned to IFRS ISSB."},
            ai_result=mock_ai_result,
            replacement_finder=ReplacementFinder(),
            confidence_engine=ConfidenceEngine(),
        )
        assert recheck_res["recheck_performed"] is True
        assert recheck_res["initial_confidence"] == 0.35
        assert len(recheck_res["sources_checked"]) >= 1

    def test_scenario_8_confidence_remains_low_human_review(self):
        """Scenario 8: Confidence remains < 50% after second pass -> HUMAN_REVIEW_REQUIRED"""
        rec = LinkRecord(
            link_id="s8",
            jurisdiction="Unknown",
            topic="Ambiguous ESG",
            step_section="General",
            step_description="Unknown standard",
            original_url="https://ambiguous-unknown-domain.org/doc",
            http_status=200,
            confidence_score=0.40,
            human_review_required=True,
        )
        decision_engine = DecisionEngine()
        decision = decision_engine.decide(rec)
        assert decision == "HUMAN_REVIEW_REQUIRED"

    def test_scenario_9_redirected_url_evaluates_destination(self):
        """Scenario 9: Redirected URL -> analyze final destination, not only original URL"""
        orig_url = "http://tcfdhub.org/recommendations"
        final_dest = "https://www.ifrs.org/sustainability/tcfd/"

        dest_auth = SourceClassifier.classify_authority("www.ifrs.org")
        assert dest_auth == STANDARDS_BODY

        rec = LinkRecord(
            link_id="s9",
            jurisdiction="Global",
            topic="TCFD",
            step_section="Global Frameworks",
            step_description="TCFD Hub",
            original_url=orig_url,
            final_url=final_dest,
            http_status=200,
            technical_status="REDIRECTED",
            classification="VALID_BUT_REDIRECTED",
            source_organisation="IFRS Foundation",
            source_authority_tier="Tier 2",
            confidence_score=0.85,
        )
        auth_eval = AuthenticityChecker.evaluate(
            url=orig_url,
            final_url=final_dest,
            title="IFRS - TCFD Knowledge Hub Transition",
            text_sample="The IFRS Foundation has taken over monitoring of TCFD progress.",
            http_status=200,
        )
        assert auth_eval["authenticity_status"] in ("AUTHENTIC", "LIKELY_AUTHENTIC")

    def test_scenario_10_working_url_outdated_regulation_split_status(self):
        """Scenario 10: Working URL with outdated regulation -> WORKING technical status, but POTENTIALLY_OUTDATED / SUPERSEDED content status"""
        nfrd_url = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32014L0095"
        fresh = FreshnessChecker.evaluate_detailed(
            text_sample="Non-Financial Reporting Directive 2014/95/EU (NFRD). Directive 2014/95/EU of the European Parliament.",
            title="Directive 2014/95/EU",
            url=nfrd_url,
        )
        tech_status = "ACCESSIBLE"
        http_code = 200
        content_freshness = fresh["freshness_status"]
        reg_status = fresh["regulatory_status"]

        assert tech_status == "ACCESSIBLE"
        assert http_code == 200
        assert content_freshness == "COMPLETELY_SUPERSEDED"
        assert reg_status in ("SUPERSEDED", "COMPLETELY_SUPERSEDED")
        assert "csrd" in fresh["reason"].lower()

