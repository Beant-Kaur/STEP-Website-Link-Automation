import json
import re
import uuid
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse

from ai.confidence_engine import ConfidenceEngine
from ai.evaluator import AiEvaluator
from ai.replacement_finder import ReplacementFinder
from analysis.content_comparator import ContentComparator
from analysis.freshness_checker import FreshnessChecker
from analysis.intent_analyzer import IntentAnalyzer
from analysis.relevance_checker import RelevanceChecker
from analysis.source_classifier import SourceClassifier
from content.metadata_extractor import MetadataExtractor
from crawler.redirect_checker import RedirectChecker
from crawler.step_extractor import StepExtractor
from crawler.url_checker import UrlChecker
from database.models import DatabaseRepository, LinkRecord
from pipeline.decision_engine import DecisionEngine
from reference import ExcelReferenceDatabase, RegulatoryDatabaseError


class PipelineOrchestrator:
    def __init__(
        self,
        repository: DatabaseRepository,
        ai_evaluator: Optional[AiEvaluator] = None,
        reference_db: Optional[ExcelReferenceDatabase] = None,
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
        
        # Regulatory Reference Database (Source of Truth layer)
        self.reference_db = reference_db or ExcelReferenceDatabase()
        try:
            self.reference_db.load()
        except RegulatoryDatabaseError:
            # Re-raise explicit reference errors so missing files/sheets/columns are never silent
            raise
        except Exception:
            pass

    def _fetch_metadata(self, content_type: str, url: str, check: Optional[dict] = None) -> dict:
        is_pdf = (content_type or "").lower().startswith("application/pdf") or url.lower().endswith(".pdf") or ".pdf?" in url.lower()
        base_meta = {
            "is_soft_404": (check or {}).get("is_soft_404", False),
            "is_generic_homepage": (check or {}).get("is_generic_homepage", False),
            "title": (check or {}).get("page_title", ""),
            "technical_status": (check or {}).get("technical_status", "ACCESSIBLE"),
        }
        try:
            import requests
            import urllib.parse
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
                "Accept-Language": "en-US,en;q=0.9",
            }
            resp = requests.get(url, timeout=35, headers=headers)
            if resp.status_code == 200:
                raw_bytes = resp.content
                resp_ct = resp.headers.get("Content-Type", "").lower()
                if is_pdf or "application/pdf" in resp_ct or raw_bytes.startswith(b"%PDF"):
                    parsed_pdf = self.metadata_extractor.extract("application/pdf", raw_bytes)
                    if not parsed_pdf.get("publication_date"):
                        decoded_url = urllib.parse.unquote(url)
                        date_match = re.search(r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(?:19|20)\d{2}\b", decoded_url, re.I)
                        if date_match:
                            parsed_pdf["publication_date"] = date_match.group(0)
                    return {**base_meta, **parsed_pdf}

                encoding = resp.encoding or "utf-8"
                try:
                    html_text = raw_bytes.decode(encoding)
                except Exception:
                    html_text = raw_bytes.decode("utf-8", errors="replace")
                parsed_html = self.metadata_extractor.extract("text/html", html_text)
                if base_meta.get("is_soft_404"):
                    parsed_html["is_soft_404"] = True
                return {**base_meta, **parsed_html}
            elif resp.status_code == 202:
                return {**base_meta, "is_challenge_page": True, "title": "Access Challenge (HTTP 202)", "technical_status": "ACCESS_RESTRICTED"}
            elif resp.status_code == 403:
                return {**base_meta, "is_challenge_page": True, "title": "Access Denied (HTTP 403)", "technical_status": "ACCESS_RESTRICTED"}
            elif resp.status_code in (404, 410):
                return {**base_meta, "technical_status": "BROKEN", "http_status": resp.status_code}
        except Exception:
            pass
        return base_meta

    def run(self, step_html: str, base_url: str = "", jurisdiction: str = "", topic: str = "", step_section: str = "", limit: int = 0) -> str:
        run_id = uuid.uuid4().hex
        start_time = datetime.utcnow()
        links = self.extractor.extract_from_html(step_html, base_url, section=step_section)
        if jurisdiction:
            filtered = [
                l for l in links
                if l.get("jurisdiction", "").strip().lower() == jurisdiction.strip().lower()
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

        for idx, link in enumerate(links, 1):
            try:
                url = link["url"]
                link_id = f"{run_id}_{idx}"
                link_jurisdiction = link.get("jurisdiction", "") or jurisdiction
                link_desc = link.get("step_description") or link.get("text", "")
                link_anchor = link.get("anchor_text") or link.get("text", "")
                link_heading = link.get("section_heading", "") or link_jurisdiction

                # Query Regulatory Reference Database (Source of Truth layer)
                ref_resource = None
                if self.reference_db and getattr(self.reference_db, "loaded", False):
                    combined_text = f"{link_desc} {link_anchor} {link_heading}".strip()
                    ref_resource = self.reference_db.match_resource(
                        jurisdiction=link_jurisdiction,
                        url=url,
                        text=combined_text,
                    )

                record = self.repository.add_link(
                    link_id=link_id,
                    jurisdiction=link_jurisdiction,
                    topic=topic or (ref_resource.regulatory_topic if ref_resource else ""),
                    step_section=step_section or link_heading,
                    step_description=link_desc,
                    original_url=url,
                    link_text=link_anchor,
                )
                record.jurisdiction = link_jurisdiction
                record.step_description = link_desc
                record.anchor_text = link_anchor
                record.section_heading = link_heading

                # Check historical record for change detection
                previous_record = self.repository.get_latest_link_by_url(url, exclude_id=link_id)
                if previous_record and previous_record.content_hash:
                    record.previous_content_hash = previous_record.content_hash

                # 1. Technical Accessibility
                check = self.url_checker.check(url)
                record.http_status = check.get("http_status")
                record.technical_status = check.get("technical_status", "ACCESSIBLE")
                record.access_status = check.get("access_status", "ACCESSIBLE" if record.http_status == 200 else "BROKEN")
                record.final_url = check.get("final_url", url)
                record.current_url = url
                record.run_id = run_id

                redirect = self.redirect_checker.analyze(check)
                record.redirect_status = redirect.get("redirect_status", "")
                record.final_url = redirect.get("final_url", url)

                content_type = check.get("content_type", "")
                record.content_type = content_type
                final_url = redirect.get("final_url") or check.get("final_url", url)

                # Infer document type
                url_low = final_url.lower()
                if ref_resource and ref_resource.document_type:
                    record.document_type = ref_resource.document_type
                elif ".pdf" in url_low or "application/pdf" in (content_type or "").lower():
                    record.document_type = "PDF Regulation / Document"
                elif any(w in url_low for w in ("bill", "act", "directive", "statute", "eli")):
                    record.document_type = "Legislation / Statute"
                elif any(w in url_low for w in ("circular", "guideline", "guidance", "rule")):
                    record.document_type = "Regulatory Guidance"
                elif any(w in url_low for w in ("standard", "esrs", "ifrs", "gri")):
                    record.document_type = "Reporting Standard"
                else:
                    record.document_type = "Official Publication"
                
                # 2. Content & Metadata Extraction
                metadata = self._fetch_metadata(content_type, final_url, check=check)
                record.page_title = metadata.get("title", "") or check.get("page_title", "")
                record.source_organisation = metadata.get("organisation", "")
                record.source_domain = record.source_domain or urlparse(final_url).netloc.lower()
                metadata["access_status"] = record.access_status
                metadata["document_type"] = record.document_type

                # Enrich with Regulatory Reference Database context
                if ref_resource:
                    if not record.topic and ref_resource.regulatory_topic:
                        record.topic = ref_resource.regulatory_topic
                    if ref_resource.issuing_authority:
                        record.source_organisation = ref_resource.issuing_authority
                    if ref_resource.official_domain and not record.source_domain:
                        record.source_domain = ref_resource.official_domain

                    metadata["reference_resource"] = ref_resource.to_dict()
                    metadata["reference_resource_id"] = ref_resource.resource_id
                    metadata["reference_resource_name"] = ref_resource.name
                    metadata["reference_authority"] = ref_resource.issuing_authority
                    metadata["reference_official_domain"] = ref_resource.official_domain
                    metadata["reference_official_url"] = ref_resource.official_url
                    metadata["reference_document_type"] = ref_resource.document_type
                    metadata["reference_publication_date"] = ref_resource.publication_date
                    metadata["reference_lifecycle"] = ref_resource.lifecycle_notes
                    metadata["reference_validator_rule"] = ref_resource.validator_rule
                    metadata["reference_versions"] = [v.to_dict() for v in ref_resource.versions]
                    metadata["reference_related_url"] = ref_resource.related_updated_url
                
                # 3. Source Authority Classification (8 tiers & Section 5 Authority Assessment)
                record.authority_status = self.source_classifier.classify_authority(record.source_domain)
                record.source_authority_tier = self.source_classifier.classify(record.source_domain)
                if ref_resource and ref_resource.official_domain and (
                    ref_resource.official_domain.lower() in record.source_domain or
                    record.source_domain in ref_resource.official_domain.lower()
                ):
                    record.authority_status = "OFFICIAL_REGULATORY_SOURCE"
                metadata["authority_status"] = record.authority_status
                metadata["source_authority"] = record.source_authority_tier
                if self.source_classifier.is_non_official_aggregator(record.source_domain):
                    metadata["is_non_official"] = True

                record.publication_date = metadata.get("publication_date", "") or (ref_resource.publication_date if ref_resource else "")
                record.effective_date = metadata.get("effective_date", "")
                record.version = metadata.get("version", "")
                text_sample = metadata.get("text_sample", "") or ""
                # Cap to 4,000 chars to avoid AI token overflow while preserving enough for semantic analysis
                if len(text_sample) > 4000:
                    text_sample = text_sample[:4000]
                metadata["text_sample"] = text_sample
                metadata["technical_status"] = record.technical_status

                # Evidence collector
                evidence_list = []
                if ref_resource:
                    evidence_list.append(
                        f"Matched Regulatory Reference Database: [{ref_resource.resource_id}] {ref_resource.name} "
                        f"(Authority: {ref_resource.issuing_authority}, Official Domain: {ref_resource.official_domain})"
                    )
                    if ref_resource.validator_rule:
                        evidence_list.append(f"Reference Rule: {ref_resource.validator_rule}")

                # 4. Authenticity Assessment (Section 6)
                from analysis.authenticity_checker import AuthenticityChecker
                auth_res = AuthenticityChecker.evaluate(
                    url=url,
                    final_url=final_url,
                    title=record.page_title,
                    text_sample=text_sample,
                    organisation=record.source_organisation,
                    access_status=record.access_status,
                    http_status=record.http_status,
                    technical_status=record.technical_status,
                    is_challenge_page=metadata.get("is_challenge_page", False),
                )
                record.authenticity_status = auth_res["authenticity_status"]
                record.authenticity_reason = auth_res["explanation"]
                evidence_list.extend(auth_res.get("evidence", []))
                metadata["authenticity_status"] = record.authenticity_status
                metadata["authenticity_reason"] = record.authenticity_reason

                # 5. Original Link Intent Inference
                intent_profile = self.intent_analyzer.infer_intent(record)

                # 6. Content Relevance and Accuracy Scoring (with Homepage Rejection Rule)
                relevance_res = self.relevance_checker.evaluate(record, metadata, intent_profile)
                record.content_relevance_score = relevance_res["content_relevance_score"]
                record.content_accuracy_score = relevance_res["content_accuracy_score"]
                record.relevance_status = relevance_res["relevance_status"]
                metadata["content_relevance_score"] = record.content_relevance_score
                metadata["content_accuracy_score"] = record.content_accuracy_score
                metadata["relevance_status"] = record.relevance_status
                metadata["is_homepage"] = relevance_res.get("is_homepage", False)
                evidence_list.extend(relevance_res.get("evidence", []))

                # 7. Freshness & Regulatory Version Check
                freshness_res = self.freshness_checker.evaluate_detailed(text_sample, record.page_title, final_url)
                record.freshness_score = freshness_res["freshness_score"]
                record.freshness_status = freshness_res["freshness_status"]
                record.regulatory_status = freshness_res["regulatory_status"]
                record.regulatory_status_reason = freshness_res.get("regulatory_status_reason") or freshness_res.get("reason", "")
                metadata["freshness_score"] = record.freshness_score
                metadata["freshness_status"] = record.freshness_status
                metadata["regulatory_status"] = record.regulatory_status
                metadata["regulatory_status_reason"] = record.regulatory_status_reason
                metadata["outdated_reason"] = freshness_res.get("reason", "")
                evidence_list.extend(freshness_res.get("evidence", []))

                if record.freshness_status in ("COMPLETELY_SUPERSEDED", "REPEALED_WITHDRAWN", "OBSOLETE", "outdated"):
                    metadata["is_outdated"] = True

                metadata["evidence"] = evidence_list

                # 8. Historical Content Drift Comparison
                record.content_hash = self.content_comparator.hash_text(text_sample) if text_sample else ""
                if record.previous_content_hash and record.content_hash:
                    if self.content_comparator.has_changed(record.previous_content_hash, record.content_hash):
                        drift_msg = "Content has drifted since previous run (SHA-256 hash changed)"
                        record.issue_description = drift_msg
                        evidence_list.append(drift_msg)
                        self.repository.log_audit(
                            link_id=record.link_id,
                            event_type="CONTENT_CHANGED",
                            old_url=previous_record.final_url or url,
                            new_url=record.final_url or url,
                            date_detected=datetime.utcnow(),
                            date_approved=None,
                            reason=record.issue_description,
                            evidence=f"Hash changed from {record.previous_content_hash[:8]} to {record.content_hash[:8]}",
                            ai_confidence=0.8,
                            reviewer="system",
                            approval_status="pending",
                        )

                # 9. AI Evaluation & Two-Stage Replacement Finder
                ai_result = self.ai_evaluator.evaluate(record, metadata)

                # Find replacement if link is inaccessible (403/challenge), broken, soft-404, wrong destination, outdated, or non-official
                needs_replacement_check = (
                    ai_result.classification in ("BROKEN", "WORKING_BUT_OUTDATED", "WRONG_DESTINATION", "WORKING_BUT_OLD_VERSION", "WORKING_BUT_NON_OFFICIAL", "WORKING_BUT_REGULATORY_STATUS_CHANGED", "ACCESS_RESTRICTED", "BROKEN_SOFT_404")
                    or record.http_status in (403, 202, 404, 410)
                    or record.access_status in ("ACCESS_DENIED", "ACCESS_CHALLENGE", "CLOUDFLARE_CHALLENGE", "BOT_PROTECTION", "LOGIN_REQUIRED", "BROKEN_SOFT_404", "WRONG_DESTINATION")
                    or record.technical_status in ("BROKEN", "WRONG_DESTINATION")
                    or self.source_classifier.is_non_official_aggregator(record.source_domain)
                )
                if needs_replacement_check:
                    ai_result = self.replacement_finder.find(record, metadata)

                # 10. Multi-attribute Comparability Analysis (Section 9)
                from analysis.content_comparator import ComparabilityAnalyzer
                cand_auth = getattr(ai_result, "recommended_source_authority", "") or self.source_classifier.classify_authority(urlparse(ai_result.replacement_url).netloc if ai_result.replacement_url else "")
                orig_comp_dict = {
                    "issuer": record.source_organisation,
                    "jurisdiction": record.jurisdiction,
                    "topic": record.topic,
                    "title": record.page_title or record.step_description,
                    "url": record.original_url,
                    "document_type": record.document_type,
                }
                cand_comp_dict = {
                    "issuer": cand_auth,
                    "jurisdiction": record.jurisdiction,
                    "topic": record.topic,
                    "title": ai_result.replacement_title or getattr(ai_result, "recommended_source_title", ""),
                    "url": ai_result.replacement_url,
                    "document_type": record.document_type,
                }
                comp_res = ComparabilityAnalyzer.analyze(orig_comp_dict, cand_comp_dict)
                record.comparability = comp_res["comparability"]
                record.comparability_confidence = comp_res["comparability_confidence"]
                record.replacement_authority = cand_auth
                record.replacement_comparability = comp_res["comparability"]
                record.replacement_confidence = 0.90 if getattr(ai_result, "replacement_verified", False) else 0.40
                record.replacement_required = bool(ai_result.replacement_url or ai_result.replacement_required)
                if comp_res.get("evidence"):
                    for ce in comp_res["evidence"]:
                        if ce not in evidence_list:
                            evidence_list.append(ce)

                # 11. Initial Confidence Scoring
                ai_result = self.confidence_engine.apply(ai_result, record=record, metadata=metadata)
                record.initial_confidence = round(ai_result.confidence_score, 2)

                # 12. Low-Confidence Recheck Engine (Section 11)
                from pipeline.recheck_engine import RecheckEngine
                if RecheckEngine.needs_recheck(ai_result.confidence_score):
                    recheck_data = RecheckEngine.execute_recheck(
                        record=record,
                        metadata=metadata,
                        ai_result=ai_result,
                        replacement_finder=self.replacement_finder,
                        confidence_engine=self.confidence_engine,
                    )
                    record.recheck_performed = True
                    record.recheck_reason = recheck_data["recheck_reason"]
                    record.initial_confidence = recheck_data["initial_confidence"]
                    record.final_confidence = recheck_data["final_confidence"]
                    record.confidence_score = recheck_data["final_confidence"]
                    ai_result = recheck_data["ai_result"]
                else:
                    record.recheck_performed = False
                    record.recheck_reason = ""
                    record.final_confidence = record.initial_confidence
                    record.confidence_score = record.final_confidence

                # 13. Output Assignment & Section 15 Decision Logic
                record.classification = ai_result.classification
                record.final_status = ai_result.final_status or ai_result.classification
                record.content_status = ai_result.content_status
                record.freshness_status = ai_result.freshness_status or record.freshness_status
                record.regulatory_status = ai_result.regulatory_status or record.regulatory_status
                record.replacement_url = ai_result.replacement_url
                record.replacement_title = getattr(ai_result, "replacement_title", "") or record.replacement_title
                record.replacement_reason = ai_result.replacement_reason or record.replacement_reason
                record.replacement_verified = getattr(ai_result, "replacement_verified", False)
                record.replacement_status = getattr(ai_result, "replacement_status", "NOT_REQUIRED")
                record.confidence_reason = getattr(ai_result, "confidence_reason", "")
                record.recommended_action = self.decision_engine.decide(record)
                
                # Section 18 fields
                record.intended_subject = getattr(ai_result, "intended_subject", "") or record.step_description or ""
                record.original_content_summary = getattr(ai_result, "original_content_summary", "")
                record.comparison_summary = getattr(ai_result, "comparison_summary", "")
                record.updated_source_found = getattr(ai_result, "updated_source_found", False)
                
                # Evidence list serialization
                if ai_result.evidence:
                    for ev in ai_result.evidence:
                        if ev not in evidence_list:
                            evidence_list.append(ev)
                record.evidence = json.dumps(evidence_list)

                if not record.issue_description and record.replacement_reason:
                    record.issue_description = record.replacement_reason

                # Human review determination
                record.human_review_required = (
                    record.confidence_score < 0.50
                    or record.recommended_action in ("HUMAN_REVIEW_REQUIRED", "ACCESSIBLE_BUT_REVIEW", "REVIEW")
                    or record.classification in ("ACCESS_RESTRICTED", "TEMPORARILY_UNAVAILABLE", "WORKING_BUT_REGULATORY_STATUS_CHANGED", "UNCERTAIN", "NEEDS_HUMAN_REVIEW")
                    or (record.replacement_required and not record.replacement_verified)
                )
                if record.recommended_action == "KEEP":
                    record.final_status = "VALID_AND_CURRENT"
                elif record.recommended_action == "REPLACE":
                    if record.classification in ("WORKING_BUT_OUTDATED", "WORKING_BUT_OLD_VERSION"):
                        record.final_status = "WORKING_BUT_OUTDATED"
                    elif record.classification == "WRONG_DESTINATION":
                        record.final_status = "WRONG_DESTINATION"
                    elif record.classification in ("BROKEN", "BROKEN_SOFT_404") or record.content_status == "SOFT_404":
                        record.final_status = "BROKEN"
                    else:
                        record.final_status = record.classification
                elif record.recommended_action in ("ACCESS_DENIED_REPLACEMENT_FOUND", "REPLACE_WITH_OFFICIAL"):
                    record.final_status = record.recommended_action
                elif record.human_review_required:
                    record.final_status = "HUMAN_REVIEW_REQUIRED"

                record.updated_at = datetime.utcnow()

                if record.http_status and 200 <= record.http_status < 400 and record.http_status != 202:
                    successful += 1
                else:
                    failed += 1

                ai_evaluations += 1
                if record.replacement_required:
                    replacement_candidates += 1
                if record.human_review_required:
                    human_review_items += 1

                self.repository.upsert_link(record)
            except Exception as exc:
                failed += 1
                errors.append(f"Link {link.get('url')}: {exc}")

        end_time = datetime.utcnow()
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
