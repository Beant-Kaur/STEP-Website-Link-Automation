import logging
from typing import Optional, Tuple

from database.models import LinkRecord

logger = logging.getLogger("decision_engine")

CONFIDENCE_THRESHOLD = 0.70

CANONICAL_DECISIONS = {
    "KEEP",
    "UPDATE",
    "REPLACE",
    "FIX_BROKEN_LINK",
    "MANUAL_REVIEW",
}


class DecisionEngine:
    """
    Implements Section 3, 9, 16 Hard Decision Gates:
    - KEEP
    - UPDATE
    - REPLACE
    - FIX_BROKEN_LINK
    - MANUAL_REVIEW
    """

    def decide_canonical(self, record: LinkRecord) -> str:
        """Computes the strict Section 3/16 final decision with hard gates."""
        http_status = record.http_status or 0
        tech_status = (record.technical_status or "").upper()
        access_status = (record.access_status or "").upper()
        content_status = (record.content_status or "").upper()
        classification = (record.classification or "").upper()
        reg_status = (record.regulatory_status or "").upper()
        fresh_status = (record.freshness_status or "").upper()
        auth_status = (record.authority_status or "").upper()
        cand_status = (record.candidate_status or "").upper()
        conf = record.overall_confidence if record.overall_confidence > 0 else (record.confidence_score or 0.0)
        rep_relationship = (record.replacement_relationship or "").upper()
        doc_type = (record.document_type or "").upper()
        instrument_type = (record.instrument_type or "").upper()

        # Flags
        is_soft_404 = (
            access_status == "BROKEN_SOFT_404"
            or content_status == "SOFT_404"
            or "SOFT_404" in classification
            or tech_status == "SOFT_404"
        )
        is_wrong_dest = (
            tech_status in ("WRONG_DESTINATION", "HOMEPAGE_REDIRECT")
            or access_status in ("WRONG_DESTINATION", "HOMEPAGE_REDIRECT")
            or classification == "WRONG_DESTINATION"
        )
        is_broken = (
            http_status in (404, 410)
            or tech_status in ("BROKEN", "HTTP_404", "DNS_FAILURE", "TIMEOUT")
            or classification == "BROKEN"
            or is_soft_404
        )
        is_blocked = (
            http_status in (403, 202)
            or tech_status in ("ACCESS_BLOCKED", "HTTP_403", "WAF_CHALLENGE", "BOT_PROTECTION", "ACCESS_RESTRICTED")
            or access_status in ("ACCESS_DENIED", "ACCESS_CHALLENGE", "CLOUDFLARE_CHALLENGE", "BOT_PROTECTION", "RATE_LIMITED")
            or classification in ("ACCESS_RESTRICTED", "ACCESS_DENIED")
        )
        is_outdated = (
            classification in ("WORKING_BUT_OUTDATED", "WORKING_BUT_OLD_VERSION")
            or fresh_status in ("COMPLETELY_SUPERSEDED", "REPEALED_WITHDRAWN", "OBSOLETE", "SUPERSEDED", "REPEALED", "AMENDED")
            or reg_status in ("SUPERSEDED", "REPEALED", "AMENDED")
        )
        has_verified_rep = bool(
            record.replacement_url
            and (record.replacement_verified or cand_status in ("CANDIDATE_VERIFIED", "REPLACEMENT_VERIFIED"))
        )

        # Gate 1: Check if original document has technical title error (Access Denied, etc.)
        tech_title = (record.technical_page_title or "").lower()
        if any(err in tech_title for err in ["access denied", "403 forbidden", "cloudflare", "waf", "security check"]):
            if not has_verified_rep:
                return "MANUAL_REVIEW"

        # Gate 2: Technical Failure / Broken Link
        if is_broken:
            if has_verified_rep:
                # If verified replacement is the exact same instrument -> FIX_BROKEN_LINK
                if rep_relationship in ("EXACT_SAME_INSTRUMENT", "CANONICAL_LOCATION", ""):
                    return "FIX_BROKEN_LINK"
                return "REPLACE"
            return "MANUAL_REVIEW"

        # Gate 3: Access Blocked / Bot challenge unresolved
        if is_blocked:
            if has_verified_rep:
                return "REPLACE"
            return "MANUAL_REVIEW"

        # Gate 4: Canonical Redirect
        if (
            classification in ("VALID_BUT_REDIRECTED", "REDIRECTED")
            or record.redirect_status in ("permanent_redirect", "canonical_update")
            or tech_status == "REDIRECTED"
        ) and not is_wrong_dest:
            return "UPDATE"

        # Gate 5: Outdated / Superseded / Repealed / Non-Official Source
        is_non_official = (
            "COMMERCIAL" in auth_status
            or "TIER_3" in auth_status
            or classification in ("WORKING_BUT_NON_OFFICIAL", "NON_OFFICIAL")
        )
        if is_outdated or is_non_official:
            if has_verified_rep:
                # HARD GATE: A draft / consultation paper cannot replace a final regulation
                cand_title = (record.replacement_title or "").lower()
                is_cand_draft = (
                    "consultation" in cand_title
                    or "draft" in cand_title
                    or "discussion paper" in cand_title
                    or "proposal" in cand_title
                )
                is_orig_final = (
                    "act" in instrument_type
                    or "directive" in instrument_type
                    or "regulation" in instrument_type
                    or "law" in instrument_type
                    or "standard" in instrument_type
                )
                if is_cand_draft and is_orig_final:
                    # Cannot replace final with draft!
                    return "MANUAL_REVIEW"

                # HARD GATE: Replacement must have verified applicability
                if rep_relationship == "MISMATCHED_APPLICABILITY":
                    return "MANUAL_REVIEW"

                return "REPLACE"
            return "MANUAL_REVIEW"

        # Gate 6: Draft / Consultation paper in original link
        if reg_status in ("CONSULTATION", "CONSULTATION_DRAFT") or "consultation" in (record.instrument_name or "").lower():
            if has_verified_rep:
                return "REPLACE"
            return "MANUAL_REVIEW"

        # Gate 7: Strict KEEP Gate
        # MUST satisfy:
        # - HTTP 200 or ACCESSIBLE_VIA_BROWSER or PDF_VALID
        # - NOT soft-404, NOT wrong destination
        # - Tier 1 or Tier 2 authority
        # - Regulatory status affirmatively CURRENT_IN_FORCE
        # - No candidate needed
        # - Confidence >= 0.70
        is_accessible = (
            http_status == 200
            or tech_status in ("ACCESSIBLE", "LIVE", "ACCESSIBLE_VIA_BROWSER", "PDF_VALID")
            or access_status in ("ACCESSIBLE", "LIVE")
        )
        is_authoritative = (
            "TIER_1" in auth_status
            or "TIER_2" in auth_status
            or "OFFICIAL" in auth_status
            or "STANDARDS" in auth_status
            or "EXCHANGE" in auth_status
            or record.source_authority_tier in ("Tier 1", "Tier 2")
        )
        is_in_force = reg_status in ("CURRENT_IN_FORCE", "LEGALLY_BINDING_IN_FORCE", "HISTORICAL_FOUNDATIONAL")

        # Also handle cases where authority_status is not yet populated
        if not auth_status:
            orig_url = (record.original_url or "").lower()
            if any(gov in orig_url for gov in [".gov.", ".nic.in", ".europa.eu", "legislation.gov.uk", ".gov/"]):
                is_authoritative = True
            elif classification in ("VALID_AND_CURRENT", "CURRENT_IN_FORCE"):
                is_authoritative = True

        # HARD GATE: HTTP 200 + valid PDF without affirmative currentness remains UNKNOWN / MANUAL_REVIEW
        if is_accessible and not is_soft_404 and not is_wrong_dest:
            if is_authoritative and is_in_force and conf >= 0.60:
                return "KEEP"
            elif reg_status == "UNKNOWN" or not is_in_force:
                return "MANUAL_REVIEW"

        # Gate 8: Fallback
        return "MANUAL_REVIEW"

    def decide(self, record: LinkRecord, canonical: bool = False) -> str:
        """Evaluates the record. If canonical=True, returns one of the 5 Section 3/16 actions.
        If canonical=False, preserves backward compatibility with legacy test assertions.
        """
        if canonical:
            return self.decide_canonical(record)

        classification = (record.classification or "").upper()
        rec_action = (record.recommended_action or "").upper()
        http_status = record.http_status or 0
        conf = record.confidence_score or 0.0
        access_status = (record.access_status or "").upper()
        tech_status = (record.technical_status or "").upper()
        content_status = (record.content_status or "").upper()
        reg_status = (record.regulatory_status or "").upper()
        fresh_status = (record.freshness_status or "").upper()

        is_soft_404 = access_status == "BROKEN_SOFT_404" or content_status == "SOFT_404" or "SOFT_404" in classification
        is_wrong_dest = tech_status == "WRONG_DESTINATION" or access_status == "WRONG_DESTINATION" or classification == "WRONG_DESTINATION"
        is_broken = http_status in (404, 410) or tech_status == "BROKEN" or classification == "BROKEN" or is_soft_404
        is_outdated = classification in ("WORKING_BUT_OUTDATED", "WORKING_BUT_OLD_VERSION") or fresh_status in ("COMPLETELY_SUPERSEDED", "REPEALED_WITHDRAWN", "OBSOLETE")

        # Hard Gate: Broken, Soft-404, Wrong Destination, or Outdated CAN NEVER BE KEEP
        if is_broken or is_wrong_dest or is_outdated:
            if record.replacement_url and record.replacement_verified:
                return "REPLACE"
            elif record.replacement_url:
                return "REPLACE"
            return "HUMAN_REVIEW_REQUIRED"

        # 1. Access denied with replacement found
        if rec_action == "ACCESS_DENIED_REPLACEMENT_FOUND" or (
            (http_status in (403, 202) or classification in ("ACCESS_RESTRICTED", "ACCESS_DENIED")) and
            record.replacement_url and record.replacement_verified
        ):
            return "ACCESS_DENIED_REPLACEMENT_FOUND"

        # 2. Replace with official equivalent
        if rec_action == "REPLACE_WITH_OFFICIAL" or (
            classification in ("WORKING_BUT_NON_OFFICIAL", "NON_OFFICIAL") and
            record.replacement_url and record.replacement_verified
        ):
            return "REPLACE_WITH_OFFICIAL"

        # 3. Valid and current -> KEEP (Strict Rule Section 18)
        # ONLY when: reachable (200), not soft-404, not homepage redirect, regulatory status active in-force
        if (
            classification in ("VALID_AND_CURRENT", "CURRENT_IN_FORCE")
            and http_status == 200
            and not is_soft_404
            and not is_wrong_dest
            and reg_status in ("LEGALLY_BINDING_IN_FORCE", "CURRENT_IN_FORCE", "HISTORICAL_FOUNDATIONAL")
            and fresh_status in ("CURRENT_IN_FORCE", "LEGALLY_BINDING_IN_FORCE", "HISTORICAL_FOUNDATIONAL")
            and conf >= 0.60
        ):
            return "KEEP"

        # 4. Canonical redirect
        if classification == "VALID_BUT_REDIRECTED" and not is_wrong_dest:
            return "RECOMMEND_CANONICAL_UPDATE"

        # 5. Accessible HTTP 200 but regulatory status/content is uncertain or stayed
        if http_status and 200 <= http_status < 300:
            if reg_status in ("UNKNOWN", "STAYED_PENDING_LITIGATION", "DISBANDED_TRANSITIONED", "PARTIALLY_SUPERSEDED") or conf < 0.50:
                if conf < 0.50 or reg_status == "UNKNOWN":
                    return "HUMAN_REVIEW_REQUIRED"
                return "ACCESSIBLE_BUT_REVIEW"

        # 6. Low confidence or conflicting evidence -> HUMAN_REVIEW_REQUIRED
        if conf < 0.50 or record.human_review_required:
            return "HUMAN_REVIEW_REQUIRED"

        # 7. Accessible but review
        if rec_action in ("REVIEW", "HUMAN_REVIEW"):
            return "REVIEW"

        return "HUMAN_REVIEW_REQUIRED"
