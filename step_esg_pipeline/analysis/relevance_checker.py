import re
from urllib.parse import urlparse
from typing import Optional

from analysis.intent_analyzer import IntentProfile


class RelevanceChecker:
    def evaluate(self, record, metadata: dict, intent_profile: IntentProfile) -> dict:
        title = metadata.get("title", "") or (record.page_title if record else "")
        text = metadata.get("text_sample", "") or ""
        url = (record.final_url if record else "") or (record.original_url if record else "")
        return self.calculate(
            intent=intent_profile,
            candidate_title=title,
            candidate_text=text,
            candidate_url=url,
            candidate_metadata=metadata,
        )

    @staticmethod
    def calculate(
        intent: IntentProfile,
        candidate_title: str,
        candidate_text: str,
        candidate_url: str,
        candidate_metadata: Optional[dict] = None,
        freshness_status: str = "current",
    ) -> dict:
        meta = candidate_metadata or {}
        combined_candidate = f"{candidate_title} {candidate_text[:4000]} {candidate_url}".lower()
        url_lower = candidate_url.lower().strip()
        parsed_url = urlparse(url_lower)

        # 1. Check Homepage Rejection Rule (Section 7 & 8)
        # If the candidate URL is just the root domain (or e.g. /index.html) and doesn't contain document specifics
        is_homepage = parsed_url.path in ("", "/", "/index.html", "/index.php", "/home", "/en", "/default.aspx")
        framework_lower = intent.expected_framework.lower()

        matched_keywords = []
        for kw in intent.mandatory_keywords:
            if kw.lower() in combined_candidate:
                matched_keywords.append(kw)

        keyword_ratio = len(matched_keywords) / max(len(intent.mandatory_keywords), 1)

        # Base scoring breakdown
        authority_score = 0.0
        framework_score = 0.0
        keyword_score = 0.0
        doc_type_score = 0.0

        # A. Authority alignment (max 25 pts)
        if intent.expected_authority:
            auth_parts = [p.lower() for p in re.findall(r"\b[A-Za-z]{3,}\b", intent.expected_authority) if p.lower() not in ("the", "and", "for", "state")]
            if any(p in combined_candidate or p in parsed_url.netloc for p in auth_parts):
                authority_score = 25.0
            else:
                authority_score = 10.0
        else:
            authority_score = 20.0

        # B. Specific document / framework match (max 35 pts)
        has_framework = False
        if intent.expected_framework:
            core_terms = [t for t in framework_lower.split() if len(t) > 3 and t not in ("directive", "standard", "guidelines", "framework", "legislative")]
            if core_terms and any(t in combined_candidate for t in core_terms):
                framework_score += 25.0
                has_framework = True
            if intent.expected_document_number and intent.expected_document_number.lower() in combined_candidate:
                framework_score += 10.0
        else:
            framework_score = 25.0

        # C. Keyword match (max 25 pts)
        keyword_score = round(keyword_ratio * 25.0, 1)

        # D. Document specificity (max 15 pts)
        if is_homepage:
            if not has_framework and keyword_ratio < 0.4:
                # Fatal Homepage Rejection: e.g. SEBI homepage instead of SEBI BRSR Core circular
                return {
                    "content_relevance_score": 15.0,
                    "content_accuracy_score": 10.0,
                    "relevance_status": "HOMEPAGE_NOT_DOCUMENT",
                    "reason": f"Candidate URL '{candidate_url}' is a generic organization homepage, not the specific regulatory document '{intent.expected_subject}'.",
                    "is_valid_replacement": False,
                    "matched_keywords": matched_keywords,
                }
            doc_type_score = 5.0
        else:
            doc_type_score = 15.0

        relevance_score = round(min(authority_score + framework_score + keyword_score + doc_type_score, 100.0), 1)

        # Calculate Content Accuracy Score (Section 16)
        # Represents how closely the page currently matches the complete, applicable regulation
        accuracy_score = relevance_score
        accuracy_reasons = []

        if freshness_status == "superseded" or freshness_status == "outdated":
            accuracy_score = round(accuracy_score * 0.4, 1)
            accuracy_reasons.append("Document is superseded or obsolete")
        elif freshness_status == "regulatory_status_changed":
            accuracy_score = round(accuracy_score * 0.75, 1)
            accuracy_reasons.append("Document subject to litigation stay or transition")
        elif "circular" in intent.expected_document_type.lower() and "2023" in intent.expected_document_number:
            # E.g. SEBI BRSR Core July 2023 circular: official historical circular; subsequent updates exist
            accuracy_reasons.append("Contains official circular; subsequent industry reporting standards apply")
        else:
            accuracy_reasons.append("Substantive regulatory requirements aligned with current framework")

        # Determine relevance classification
        if relevance_score >= 80:
            relevance_status = "HIGHLY_RELEVANT"
            is_valid_rep = True
        elif relevance_score >= 60:
            relevance_status = "MODERATELY_RELEVANT"
            is_valid_rep = True
        elif relevance_score >= 35:
            relevance_status = "LOW_RELEVANCE"
            is_valid_rep = False
        else:
            relevance_status = "IRRELEVANT"
            is_valid_rep = False

        reason = f"Relevance {relevance_score}/100 based on authority ({authority_score}pts), framework ({framework_score}pts), and keywords ({keyword_score}pts). {'; '.join(accuracy_reasons)}."

        return {
            "content_relevance_score": relevance_score,
            "content_accuracy_score": accuracy_score,
            "relevance_status": relevance_status,
            "reason": reason,
            "is_valid_replacement": is_valid_rep,
            "matched_keywords": matched_keywords,
        }
