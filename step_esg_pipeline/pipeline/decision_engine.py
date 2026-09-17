from typing import Optional

from database.models import LinkRecord


CONFIDENCE_THRESHOLD = 0.8


class DecisionEngine:
    """
    Implements Master Prompt Section 15 Final Decision Logic:
    - KEEP
    - REVIEW
    - REPLACE
    - REPLACE_WITH_OFFICIAL
    - ACCESSIBLE_BUT_REVIEW
    - ACCESS_DENIED_REPLACEMENT_FOUND
    - HUMAN_REVIEW_REQUIRED
    """

    def decide(self, record: LinkRecord) -> str:
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
