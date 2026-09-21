import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

from ai.confidence_engine import ConfidenceEngine
from ai.evaluator import AiEvaluator
from ai.replacement_finder import ReplacementFinder
from ai.web_researcher import WebResearcher
from analysis.authenticity_checker import AuthenticityChecker
from analysis.content_comparator import ContentComparator, ComparabilityAnalyzer
from analysis.currentness_engine import CurrentnessEngine
from analysis.date_engine import UniversalDateEngine
from analysis.evidence_engine import EvidenceTrail, EvidenceItem
from analysis.freshness_checker import FreshnessChecker
from analysis.intent_analyzer import IntentAnalyzer
from analysis.regulatory_identity import RegulatoryIdentityEngine, RegulatoryIdentity
from analysis.relevance_checker import RelevanceChecker
from analysis.source_classifier import SourceClassifier
from analysis.version_chain import VersionChainEngine
from content.html_parser import TECHNICAL_TITLE_PATTERNS
from content.metadata_extractor import MetadataExtractor
from content.pdf_engine import PdfEngine
from crawler.link_discovery import LinkDiscoveryEngine, LinkRelevance
from crawler.playwright_engine import PlaywrightEngine
from crawler.redirect_checker import RedirectChecker
from crawler.step_extractor import StepExtractor
from crawler.url_checker import UrlChecker
from crawler.url_normalizer import UrlNormalizer
from database.models import DatabaseRepository, LinkRecord
from jurisdictions.registry import JurisdictionRegistry
from pipeline.decision_engine import DecisionEngine

logger = logging.getLogger("pipeline_orchestrator")


class PipelineOrchestrator:
    """Advanced Regulatory Source & PDF Discovery Pipeline Orchestrator.

    Audits exclusively the ESG Legislative Landscape section across 13 target
    jurisdictions, evaluating technical accessibility, source authority,
    regulatory lifecycle, and verified official replacements.
    """

    def __init__(
        self,
        repository: DatabaseRepository,
        ai_evaluator: Optional[AiEvaluator] = None,
    ):
        self.repository = repository
        self.extractor = StepExtractor()
        self.url_checker = UrlChecker()
        self.redirect_checker = RedirectChecker()
        self.metadata_extractor = MetadataExtractor()
        self.source_classifier = SourceClassifier()
        self.intent_analyzer = IntentAnalyzer()
        self.relevance_checker = RelevanceChecker()
        self.freshness_checker = FreshnessChecker()
        self.content_comparator = ContentComparator()
        self.ai_evaluator = ai_evaluator or AiEvaluator()
        self.replacement_finder = ReplacementFinder(self.ai_evaluator, url_checker=self.url_checker)
        self.confidence_engine = ConfidenceEngine()
        self.decision_engine = DecisionEngine()
        self.link_discovery = LinkDiscoveryEngine(max_crawl_depth=2)
        self.jurisdiction_registry = JurisdictionRegistry()
        self.identity_engine = RegulatoryIdentityEngine(self.jurisdiction_registry)
        self.currentness_engine = CurrentnessEngine(self.jurisdiction_registry)
        self.playwright_engine = None  # Lazy initialized when needed

    def _get_playwright(self) -> PlaywrightEngine:
        if self.playwright_engine is None:
            self.playwright_engine = PlaywrightEngine(headless=True)
        return self.playwright_engine

    def close(self):
        if self.playwright_engine:
            try:
                self.playwright_engine.close()
            except Exception:
                pass
            self.playwright_engine = None

    def run(
        self,
        step_html: str,
        base_url: str = "",
        jurisdiction: str = "",
        topic: str = "",
        step_section: str = "",
        limit: int = 0,
    ) -> str:
        run_id = uuid.uuid4().hex
        start_time = datetime.now(timezone.utc)
        links = self.extractor.extract_from_html(step_html, base_url, section=step_section)

        if jurisdiction:
            filtered = [
                l for l in links
                if l.get("country", "").strip().lower() == jurisdiction.strip().lower()
                or l.get("jurisdiction", "").strip().lower() == jurisdiction.strip().lower()
                or jurisdiction.strip().lower() in l.get("section_heading", "").lower()
            ]
            if filtered:
                links = filtered

        if limit > 0:
            links = links[:limit]

        total = len(links)
        successful = 0
        failed = 0
        ai_evaluations = 0
        replacement_candidates = 0
        human_review_items = 0
        errors = []

        try:
            for idx, link in enumerate(links, 1):
                try:
                    self._process_single_link(
                        link=link,
                        idx=idx,
                        run_id=run_id,
                        jurisdiction=jurisdiction,
                        topic=topic,
                        step_section=step_section,
                    )
                    successful += 1
                except Exception as exc:
                    failed += 1
                    errors.append(f"Link {link.get('url')}: {exc}")
                    logger.error(f"Error processing link {link.get('url')}: {exc}", exc_info=True)
        finally:
            self.close()

        end_time = datetime.now(timezone.utc)
        self.repository.log_pipeline_run(
            run_id=run_id,
            start_time=start_time,
            end_time=end_time,
            total_links=total,
            successful_checks=successful,
            failed_checks=failed,
            ai_evaluations=ai_evaluations,
            replacement_candidates=replacement_candidates,
            human_review_items=human_review_items,
            errors="; ".join(errors),
        )
        return run_id

    def _process_single_link(
        self,
        link: dict,
        idx: int,
        run_id: str,
        jurisdiction: str,
        topic: str,
        step_section: str,
    ) -> LinkRecord:
        raw_url = link["url"]
        link_id = f"{run_id}_{idx}"
        link_country = link.get("country") or link.get("jurisdiction") or jurisdiction
        country_conf = link.get("country_confidence", 1.0)
        link_desc = link.get("step_description") or link.get("text") or link.get("link_text") or ""
        link_anchor = link.get("anchor_text") or link.get("text") or ""
        link_heading = link.get("section_heading", "") or link_country
        section_name = link.get("section") or step_section or "ESG Legislative Landscape"

        evidence_trail = EvidenceTrail()
        evidence_trail.add(
            category="extraction",
            claim=f"Extracted from section '{section_name}', Country '{link_country}'",
            status="CONFIRMED",
            confidence=country_conf,
            source="StepExtractor",
            detail=link.get("country_evidence", f"Section '{section_name}' -> '{link_country}'"),
        )

        # 1. URL Normalization
        norm_url = UrlNormalizer.normalize(raw_url)

        record = self.repository.add_link(
            link_id=link_id,
            jurisdiction=link_country,
            topic=topic,
            step_section=section_name,
            step_description=link_desc,
            original_url=raw_url,
            link_text=link_anchor,
        )
        record.section = section_name
        record.country = link_country
        record.country_confidence = country_conf
        record.jurisdiction = link_country
        record.step_description = link_desc
        record.anchor_text = link_anchor
        record.section_heading = link_heading
        record.current_url = norm_url
        record.run_id = run_id

        evidence_list: List[str] = [f"Extracted for {link_country}: '{link_desc}'"]
        discovered_trail: List[Dict[str, str]] = [{"stage": "ORIGINAL_URL", "url": raw_url}]

        # Check historical record for drift comparison
        previous_record = self.repository.get_latest_link_by_url(raw_url, exclude_id=link_id)
        if previous_record and previous_record.content_hash:
            record.previous_content_hash = previous_record.content_hash

        # 2. HTTP Check & Redirect Chain Analysis
        check = self.url_checker.check(norm_url)
        record.http_status = check.get("http_status")
        raw_tech = check.get("technical_status", "ACCESSIBLE")
        record.final_url = check.get("final_url", norm_url)
        record.content_type = check.get("content_type", "")

        redirect = self.redirect_checker.analyze(check)
        record.redirect_status = redirect.get("redirect_status", "no_redirect")
        final_url = redirect.get("final_url") or record.final_url
        record.final_url = final_url

        if record.redirect_status != "no_redirect":
            discovered_trail.append({"stage": "REDIRECTED_URL", "url": final_url})
            evidence_trail.add(
                category="technical",
                claim=f"Redirect detected ({record.redirect_status}) to: {final_url}",
                status="REDIRECTED",
                confidence=0.90,
                source="RedirectChecker",
                detail=f"Redirect chain length: {len(check.get('redirect_chain', []))}",
            )
            evidence_list.append(f"Redirected ({record.redirect_status}) to: {final_url}")

        record.source_domain = urlparse(final_url).netloc.lower()

        # Map initial technical status
        if record.http_status == 200:
            record.technical_status = "LIVE"
            record.access_status = "ACCESSIBLE"
        elif record.http_status in (403, 202):
            record.technical_status = "ACCESS_BLOCKED"
            record.access_status = "ACCESS_DENIED"
        elif record.http_status in (404, 410):
            record.technical_status = "HTTP_404"
            record.access_status = "BROKEN"
        elif check.get("is_soft_404"):
            record.technical_status = "SOFT_404"
            record.access_status = "BROKEN_SOFT_404"
        else:
            record.technical_status = raw_tech
            record.access_status = "ACCESSIBLE" if (record.http_status and record.http_status < 400) else "BROKEN"

        evidence_trail.add(
            category="technical",
            claim=f"HTTP {record.http_status} ({record.technical_status})",
            status=record.technical_status,
            confidence=0.90 if record.http_status else 0.50,
            source="UrlChecker",
            detail=f"Content-Type: {record.content_type}, Latency: {check.get('elapsed_ms', 0)}ms",
        )

        # 3. Authority Tier Classification
        domain_auth = self.jurisdiction_registry.lookup_domain(record.source_domain, country=link_country)
        if domain_auth.get("is_official"):
            if "GAZETTE" in domain_auth.get("authority_tier", ""):
                auth_tier_name = "TIER_1_GOVERNMENT_GAZETTE"
            else:
                auth_tier_name = "TIER_1_OFFICIAL_REGULATOR"
        elif "TIER_2" in domain_auth.get("authority_tier", "") or "EXCHANGE" in domain_auth.get("authority_tier", ""):
            auth_tier_name = "TIER_2_EXCHANGE_BODY"
        elif "COMMERCIAL" in domain_auth.get("authority_tier", ""):
            auth_tier_name = "TIER_3_COMMERCIAL_AGGREGATOR"
        elif "LAW_FIRM" in domain_auth.get("authority_tier", ""):
            auth_tier_name = "TIER_3_LAW_FIRM"
        elif "NEWS" in domain_auth.get("authority_tier", ""):
            auth_tier_name = "TIER_3_NEWS_MEDIA"
        else:
            auth_tier_name = self.source_classifier.classify_authority(record.source_domain)

        record.authority_status = auth_tier_name
        record.source_authority_tier = "Tier 1" if "TIER_1" in auth_tier_name else ("Tier 2" if "TIER_2" in auth_tier_name else "Tier 3")
        record.authority = domain_auth.get("authority_name") or record.source_domain

        evidence_trail.add(
            category="authority",
            claim=f"Source classified as {auth_tier_name} ({domain_auth.get('authority_name', record.source_domain)})",
            status="CONFIRMED",
            confidence=0.95 if domain_auth.get("is_official") else 0.80,
            source="JurisdictionRegistry",
            detail=f"Domain {record.source_domain} registered under {link_country}",
        )

        # 4. PDF Direct & Magic File Signature Check
        pdf_res: Optional[Dict[str, Any]] = None
        is_pdf_target = PdfEngine.is_pdf_url_or_endpoint(final_url, record.content_type)
        if is_pdf_target:
            pdf_res = PdfEngine.fetch_and_validate(final_url, timeout=25)
            if pdf_res.get("is_valid_pdf"):
                record.pdf_url = final_url
                record.pdf_magic_signature_verified = pdf_res.get("magic_signature_verified", False)
                record.pdf_validation_status = "VALID_PDF"
                record.technical_status = "PDF_VALID"
                record.document_type = "PDF Regulation / Document"
                discovered_trail.append({"stage": "VERIFIED_PDF", "url": final_url})
                evidence_trail.add(
                    category="document",
                    claim=f"PDF document verified with magic bytes %PDF-",
                    status="VALID_PDF",
                    confidence=1.0,
                    source="PdfEngine",
                    detail=f"Pages: {pdf_res.get('page_count', 0)}, Text length: {len(pdf_res.get('text_sample', ''))}",
                )
            elif pdf_res.get("is_soft_404"):
                record.technical_status = "SOFT_404"
                record.access_status = "BROKEN_SOFT_404"
                record.pdf_validation_status = "PDF_NOT_FOUND"
                evidence_trail.add(
                    category="technical",
                    claim="PDF endpoint returned Soft-404 HTML error page",
                    status="BROKEN_SOFT_404",
                    confidence=0.95,
                    source="PdfEngine",
                    detail="Content received was HTML error page, not PDF stream.",
                )

        # 5. Playwright Browser Validation (for WAF / Challenges / JavaScript Viewers)
        needs_browser = (
            record.http_status in (403, 202)
            or record.technical_status in ("ACCESS_BLOCKED", "SOFT_404")
            or record.access_status in ("ACCESS_DENIED", "ACCESS_CHALLENGE", "CLOUDFLARE_CHALLENGE", "BOT_PROTECTION", "BROKEN_SOFT_404")
            or not record.pdf_url
            or "viewer" in final_url.lower()
        )

        pw_info: Optional[Dict[str, Any]] = None
        discovered_links: List[Dict[str, Any]] = []

        if needs_browser:
            try:
                pw = self._get_playwright()
                pw_info = pw.inspect_url(final_url, click_download_buttons=True)
                if pw_info.get("final_url"):
                    record.final_url = pw_info["final_url"]
                    final_url = record.final_url

                raw_pw_title = pw_info.get("title", "").strip()

                # Check for technical page title rejection (Access Denied, Cloudflare, etc.)
                is_tech_title = any(re.search(pat, raw_pw_title, re.I) for pat in TECHNICAL_TITLE_PATTERNS)
                if is_tech_title:
                    record.technical_page_title = raw_pw_title
                    record.page_title = ""  # NEVER use technical title as document title!
                    evidence_trail.add(
                        category="browser",
                        claim=f"Rejected technical error page title: '{raw_pw_title}'",
                        status="REJECTED_TECHNICAL_TITLE",
                        confidence=0.95,
                        source="HtmlParser",
                        detail="Technical error page title cannot represent the regulatory document.",
                    )
                else:
                    if raw_pw_title and not record.page_title:
                        record.page_title = raw_pw_title

                # Check if browser resolved to a 404 error page / soft-404
                title_lower = (raw_pw_title or "").lower()
                final_lower = (record.final_url or "").lower()
                is_browser_soft_404 = (
                    "/404" in final_lower or "404 not found" in title_lower or "page not found" in title_lower
                    or any(re.search(pat, title_lower, re.I) for pat in UrlChecker.SOFT_404_PATTERNS)
                )
                if is_browser_soft_404:
                    record.technical_status = "SOFT_404"
                    record.access_status = "BROKEN_SOFT_404"
                    record.classification = "BROKEN_SOFT_404"
                    evidence_trail.add(
                        category="browser",
                        claim=f"Browser confirmed Soft-404 error page: '{raw_pw_title}'",
                        status="BROKEN_SOFT_404",
                        confidence=0.95,
                        source="PlaywrightEngine",
                        detail=f"URL: {record.final_url}",
                    )
                else:
                    # If browser overcame an initial bot/JS challenge or 202/403 status and rendered valid content
                    is_challenge_bypassed = (
                        pw_info.get("is_challenge_resolved")
                        or (
                            record.http_status in (202, 403)
                            and len(pw_info.get("text", "")) > 300
                            and not pw_info.get("is_access_denied")
                        )
                    )
                    if is_challenge_bypassed:
                        record.http_status = 200
                        record.access_status = "ACCESSIBLE"
                        record.technical_status = "ACCESSIBLE_VIA_BROWSER"
                        evidence_trail.add(
                            category="browser",
                            claim=f"Browser bypassed bot challenge (HTTP {record.http_status} -> 200)",
                            status="ACCESSIBLE_VIA_BROWSER",
                            confidence=0.90,
                            source="PlaywrightEngine",
                            detail=f"Resolved page title: '{record.page_title}'",
                        )

                # Check if underlying PDF was discovered via viewer or DOM links
                all_discovered_pdfs = pw_info.get("discovered_pdf_urls", [])
                for pdf_cand in all_discovered_pdfs:
                    cand_val = PdfEngine.fetch_and_validate(pdf_cand, timeout=20)
                    if cand_val.get("is_valid_pdf"):
                        record.pdf_url = pdf_cand
                        record.pdf_magic_signature_verified = cand_val.get("magic_signature_verified", False)
                        record.pdf_validation_status = "VALID_PDF"
                        record.technical_status = "PDF_VALID"
                        record.document_type = "PDF Regulation / Document"
                        discovered_trail.append({"stage": "DISCOVERED_PDF_VIA_BROWSER", "url": pdf_cand})
                        evidence_trail.add(
                            category="browser",
                            claim=f"Discovered underlying PDF: {pdf_cand}",
                            status="VALID_PDF",
                            confidence=0.95,
                            source="PlaywrightEngine",
                            detail="Magic %PDF- bytes verified.",
                        )
                        pdf_res = cand_val
                        break

            except Exception as e:
                logger.debug(f"Playwright browser crawling error: {e}")

        # 6. Text Sample Extraction
        text_sample = ""
        doc_refs: List[Dict[str, str]] = []
        extracted_dates_detail: List[Dict[str, Any]] = []

        if pdf_res and pdf_res.get("text_sample"):
            text_sample = pdf_res["text_sample"]
            record.page_title = record.page_title or pdf_res.get("title", "")
            record.source_organisation = record.source_organisation or pdf_res.get("organisation", "")
            doc_refs = VersionChainEngine.extract_references(text_sample)
            extracted_dates_detail = UniversalDateEngine.extract_dates(text_sample, url=final_url, jurisdiction=record.jurisdiction)
        else:
            meta = self.metadata_extractor.extract(record.content_type, (pw_info or {}).get("html", ""), url=final_url, jurisdiction=record.jurisdiction)
            record.page_title = record.page_title or meta.get("title", "")
            record.source_organisation = record.source_organisation or meta.get("organisation", "")
            text_sample = meta.get("text_sample", "") or (pw_info or {}).get("text", "")
            doc_refs = VersionChainEngine.extract_references(text_sample)
            extracted_dates_detail = UniversalDateEngine.extract_dates(text_sample, url=final_url, jurisdiction=record.jurisdiction)

        record.extracted_dates_detail = json.dumps(extracted_dates_detail)
        record.document_references = json.dumps([r["target_document"] for r in doc_refs])

        best_date = UniversalDateEngine.select_best_regulatory_date(extracted_dates_detail)
        if best_date:
            record.publication_date = best_date["original_date"]

        eff_date = next((d for d in extracted_dates_detail if d.get("context") == "EFFECTIVE_DATE"), None)
        if eff_date:
            record.effective_date = eff_date["original_date"]

        # 7. Regulatory Identity Extraction
        identity: RegulatoryIdentity = self.identity_engine.extract_identity(
            link_item=link,
            text_sample=text_sample,
            page_title=record.page_title,
            url=final_url,
        )
        record.country = identity.country or link_country
        record.authority = identity.authority or record.authority
        record.instrument_name = identity.instrument_name or link_desc
        record.instrument_type = identity.instrument_type
        record.regulatory_topic = identity.regulatory_topic
        record.regulated_population = identity.regulated_population
        record.source_organisation = record.source_organisation or identity.authority

        evidence_trail.add(
            category="identity",
            claim=f"Regulatory identity: {identity.instrument_name} ({identity.instrument_type})",
            status="CONFIRMED",
            confidence=0.90,
            source="RegulatoryIdentityEngine",
            detail=f"Topic: {identity.regulatory_topic}, Population: {identity.regulated_population}, Authority: {identity.authority}",
        )

        # 8. Regulatory Currentness Verification
        currentness_res = self.currentness_engine.evaluate(
            identity=identity,
            text_sample=text_sample,
            page_title=record.page_title,
            url=final_url,
            source_domain=record.source_domain,
            authority_status=record.authority_status,
        )
        record.regulatory_status = currentness_res["regulatory_status"]
        record.freshness_score = currentness_res["freshness_score"]
        record.freshness_status = currentness_res["regulatory_status"]
        record.regulatory_status_reason = currentness_res["rationale"]

        evidence_trail.add(
            category="currentness",
            claim=f"Lifecycle: {record.regulatory_status} ({currentness_res['rationale']})",
            status=record.regulatory_status,
            confidence=currentness_res.get("confidence", 0.70),
            source="CurrentnessEngine",
            detail="; ".join(currentness_res.get("signals", [])),
        )

        # 9. Official Replacement Discovery & Applicability Check
        metadata = {
            "title": record.page_title,
            "text_sample": text_sample[:4000],
            "access_status": record.access_status,
            "technical_status": record.technical_status,
            "content_type": record.content_type,
            "document_type": record.document_type,
            "authority_status": record.authority_status,
            "regulatory_status": record.regulatory_status,
            "is_soft_404": record.technical_status == "SOFT_404",
            "outdated_reason": record.regulatory_status_reason,
            "discovered_links": discovered_links,
            "evidence": evidence_list,
        }

        ai_result = self.ai_evaluator.evaluate(record, metadata)

        needs_replacement = (
            record.technical_status in ("BROKEN", "HTTP_404", "SOFT_404", "ACCESS_BLOCKED", "HOMEPAGE_REDIRECT")
            or "TIER_3" in record.authority_status
            or record.regulatory_status in ("SUPERSEDED", "REPEALED", "AMENDED", "CONSULTATION")
        )

        if needs_replacement:
            ai_result = self.replacement_finder.find(record, metadata)
            if ai_result.replacement_url:
                record.replacement_url = ai_result.replacement_url
                record.replacement_title = ai_result.replacement_title
                record.replacement_reason = ai_result.replacement_reason
                record.replacement_verified = ai_result.replacement_verified
                record.replacement_status = ai_result.replacement_status
                record.replacement_required = True
                record.candidate_authority = getattr(ai_result, "source_authority", "") or record.authority
                record.candidate_status = "REPLACEMENT_VERIFIED" if record.replacement_verified else "CANDIDATE_UNVERIFIED"
                record.replacement_relationship = "REPLACEMENT"

                if ai_result.replacement_url.lower().endswith(".pdf"):
                    record.candidate_pdf_url = ai_result.replacement_url

                evidence_trail.add(
                    category="discovery",
                    claim=f"Replacement candidate identified: {record.replacement_url}",
                    status="CANDIDATE_FOUND",
                    confidence=0.85 if record.replacement_verified else 0.50,
                    source="ReplacementFinder",
                    detail=f"Candidate title: '{record.replacement_title}', Verified: {record.replacement_verified}",
                )
            else:
                record.candidate_status = "NONE_FOUND"
        else:
            record.candidate_status = "NO_REPLACEMENT_REQUIRED"

        # 10. Multi-signal Confidence Engine
        ai_result = self.confidence_engine.apply(ai_result, record=record, metadata=metadata)
        record.confidence_score = round(ai_result.confidence_score, 2)
        record.classification = ai_result.classification

        # 11. Final Decision Engine with Hard Gates
        canonical_decision = self.decision_engine.decide_canonical(record)
        record.final_decision = canonical_decision
        record.recommended_action = self.decision_engine.decide(record, canonical=False)

        # Generate Human-Readable "Why?" Summary
        record.why_summary = evidence_trail.summary(record.final_decision)
        record.evidence_json = evidence_trail.to_json()
        record.evidence = json.dumps([item.detail for item in evidence_trail.items])

        # Backward compatibility final status
        if record.final_decision == "KEEP":
            record.final_status = "VALID PDF" if record.pdf_validation_status == "VALID_PDF" else "VALID"
        elif record.final_decision == "REPLACE":
            record.final_status = "REPLACEMENT VERIFIED" if record.replacement_verified else "REPLACEMENT FOUND"
        elif record.final_decision == "UPDATE":
            record.final_status = "REDIRECTED"
        elif record.final_decision == "FIX_BROKEN_LINK":
            record.final_status = "REPLACEMENT VERIFIED"
        else:
            record.final_status = "MANUAL REVIEW REQUIRED"

        record.human_review_required = (
            record.final_decision == "MANUAL_REVIEW"
            or record.overall_confidence < 0.65
            or record.confidence_score < 0.65
        )

        record.discovered_trail = json.dumps(discovered_trail)
        record.updated_at = datetime.now(timezone.utc)

        self.repository.upsert_link(record)
        return record
