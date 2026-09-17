import logging
from typing import Dict, Any, Tuple, List, Optional

from database.models import LinkRecord
from ai.evaluator import AiEvaluationResult


class RecheckEngine:
    """
    Implements the Low-Confidence Recheck Engine per Section 11 of the Master Prompt.
    If initial confidence is below 50% (0.50), triggers an automatic second
    verification pass to re-examine evidence, alternative sources, and metadata.
    """

    CONFIDENCE_THRESHOLD = 0.50

    @classmethod
    def needs_recheck(cls, confidence_score: float) -> bool:
        return confidence_score < cls.CONFIDENCE_THRESHOLD

    @classmethod
    def execute_recheck(
        cls,
        record: LinkRecord,
        metadata: dict,
        ai_result: AiEvaluationResult,
        replacement_finder: Any,
        confidence_engine: Any,
    ) -> Dict[str, Any]:
        """
        Runs the second verification pass:
        1. Logs initial confidence and reason.
        2. Tries secondary authoritative candidate lookup using anchor text & heading.
        3. Re-evaluates comparability and freshness signals.
        4. Re-computes confidence score.
        5. If final confidence remains < 50%, marks HUMAN_REVIEW_REQUIRED = True.
        """
        initial_conf = round(float(ai_result.confidence_score or 0.0), 2)
        recheck_reason = f"Initial confidence ({int(initial_conf * 100)}%) is below 50% threshold."
        sources_checked: List[str] = [record.original_url]
        if record.final_url and record.final_url != record.original_url:
            sources_checked.append(record.final_url)

        evidence_added = [f"Second verification pass triggered: {recheck_reason}"]

        # Second pass candidate lookup if replacement was missing or unverified
        if not ai_result.replacement_url or not getattr(ai_result, "replacement_verified", False):
            # Try finding alternative candidate using anchor text, heading, and title
            combined_context = f"{record.anchor_text} {record.section_heading} {record.step_description} {record.page_title}"
            alt_rep_url, alt_rep_title, alt_rep_reason = replacement_finder.find_replacement(
                record,
                {"text_sample": combined_context, "outdated_reason": "Low confidence recheck pass"}
            )
            if alt_rep_url:
                sources_checked.append(alt_rep_url)
                is_valid, rep_status, note = replacement_finder.validate_candidate(alt_rep_url, record=record)
                if is_valid:
                    ai_result.replacement_url = alt_rep_url
                    ai_result.replacement_title = alt_rep_title
                    ai_result.replacement_reason = alt_rep_reason
                    ai_result.replacement_verified = True
                    ai_result.replacement_status = "VERIFIED"
                    evidence_added.append(f"Recheck identified verified replacement: {alt_rep_title}")

        # Re-score confidence after recheck
        ai_result.evidence.extend(evidence_added)
        rescored = confidence_engine.apply(ai_result, record=record, metadata=metadata)
        final_conf = rescored.confidence_score

        # Determine human review flag
        human_review_required = final_conf < cls.CONFIDENCE_THRESHOLD or ai_result.recommended_action in (
            "HUMAN_REVIEW", "HUMAN_REVIEW_REQUIRED", "HUMAN_REVIEW_AND_REPLACE", "ACCESSIBLE_BUT_REVIEW"
        )

        return {
            "recheck_performed": True,
            "recheck_reason": recheck_reason,
            "initial_confidence": initial_conf,
            "final_confidence": final_conf,
            "sources_checked": sources_checked,
            "human_review_required": human_review_required,
            "ai_result": rescored,
        }
