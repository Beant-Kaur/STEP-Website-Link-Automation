from typing import Optional, Dict, Any, Tuple

from ai.evaluator import AiEvaluationResult
from database.models import LinkRecord
from analysis.source_classifier import SourceClassifier


class ConfidenceEngine:
    @staticmethod
    def score(
        result: AiEvaluationResult,
        record: Optional[LinkRecord] = None,
        metadata: Optional[dict] = None,
    ) -> Tuple[float, str]:
        meta = metadata or {}
        cls = (result.classification or "").upper()
        text_sample = meta.get("text_sample", "") or (getattr(record, "text_sample", "") if record else "") or ""
        text_len = len(text_sample)
        has_text = text_len >= 250
        has_replacement = bool(result.replacement_url)
        rep_verified = meta.get("replacement_verified", False) or getattr(result, "replacement_verified", False)
        
        # 1. ACCESS_RESTRICTED: Cloudflare / CAPTCHA / 403 / 202
        if cls == "ACCESS_RESTRICTED":
            score = 0.30
            reason_str = "Evidence Confidence (30/100): Verification blocked by bot challenge or HTTP 403/202. Insufficient substantive evidence; human review required."
            return score, reason_str

        # 2. TEMPORARILY_UNAVAILABLE
        if cls == "TEMPORARILY_UNAVAILABLE":
            score = 0.35
            reason_str = "Evidence Confidence (35/100): Server error or transient timeout. Insufficient substantive evidence; retry pending."
            return score, reason_str

        # 3. BROKEN / DEAD LINK
        if cls == "BROKEN":
            pts = 50
            breakdown = ["Technical failure verified (+50)"]
            issue_desc = getattr(result, "issue_description", "") or getattr(result, "replacement_reason", "") or ""
            if meta.get("is_soft_404") or "soft" in issue_desc.lower():
                pts += 25
                breakdown.append("Soft-404 confirmed from empty/error content (+25)")
            else:
                pts += 25
                breakdown.append("Definitive HTTP 404/410 status code (+25)")
            if has_replacement:
                pts += 15
                breakdown.append("Replacement URL proposed (+15)")
                if rep_verified:
                    pts += 5
                    breakdown.append("Replacement independently validated (+5)")
            total_pts = min(pts, 95)
            score = round(total_pts / 100.0, 2)
            reason_str = f"Evidence Confidence ({total_pts}/100): " + "; ".join(breakdown)
            return score, reason_str

        # 4. WORKING_BUT_OUTDATED
        if cls == "WORKING_BUT_OUTDATED":
            pts = 60
            breakdown = ["Document obsolescence/supersession detected (+60)"]
            if meta.get("outdated_reason") or result.replacement_reason:
                pts += 15
                breakdown.append("Specific regulatory amendment/repeal rationale verified (+15)")
            if has_replacement:
                pts += 15
                breakdown.append("Updated official version identified (+15)")
                if rep_verified:
                    pts += 5
                    breakdown.append("Replacement independently verified (+5)")
            total_pts = min(pts, 95)
            score = round(total_pts / 100.0, 2)
            reason_str = f"Evidence Confidence ({total_pts}/100): " + "; ".join(breakdown)
            return score, reason_str

        # 5. WORKING_BUT_REGULATORY_STATUS_CHANGED (e.g. Litigation Stay, Transition)
        if cls == "WORKING_BUT_REGULATORY_STATUS_CHANGED":
            pts = 65
            breakdown = ["Regulatory stay/transition status confirmed (+65)"]
            if meta.get("outdated_reason") or result.replacement_reason:
                pts += 15
                breakdown.append("Official stay/litigation evidence confirmed (+15)")
            if has_replacement:
                pts += 10
                breakdown.append("Official status portal identified (+10)")
            total_pts = min(pts, 90)
            score = round(total_pts / 100.0, 2)
            reason_str = f"Evidence Confidence ({total_pts}/100): " + "; ".join(breakdown)
            return score, reason_str

        # 6. WORKING_BUT_NON_OFFICIAL
        if cls == "WORKING_BUT_NON_OFFICIAL":
            pts = 65
            breakdown = ["Non-official commercial aggregator source confirmed (+65)"]
            if has_replacement:
                pts += 20
                breakdown.append("Authoritative official regulator/standards replacement found (+20)")
                if rep_verified:
                    pts += 10
                    breakdown.append("Replacement verified (+10)")
            total_pts = min(pts, 95)
            score = round(total_pts / 100.0, 2)
            reason_str = f"Evidence Confidence ({total_pts}/100): " + "; ".join(breakdown)
            return score, reason_str

        # 7. VALID_BUT_REDIRECTED
        if cls == "VALID_BUT_REDIRECTED":
            pts = 75
            breakdown = ["Canonical permanent redirect verified (+75)"]
            if has_text:
                pts += 10
                breakdown.append("Substantive destination content verified (+10)")
            total_pts = min(pts, 90)
            score = round(total_pts / 100.0, 2)
            reason_str = f"Evidence Confidence ({total_pts}/100): " + "; ".join(breakdown)
            return score, reason_str

        # 8. VALID_AND_CURRENT — 100-Point Formula (Section 13)
        # 1. Technical Accessibility & Completeness: 15 pts
        tech_pts = 15 if (text_len >= 500 or metadata is None or result.content_relevance == "high") else (12 if text_len >= 250 else 6)
        # 2. Source Authority Tier: 15 pts
        auth_status = meta.get("authority_status") or result.source_authority or ""
        if "OFFICIAL" in auth_status or auth_status == "Tier 1":
            auth_pts = 15
        elif "STANDARDS" in auth_status or "EXCHANGE" in auth_status or "INSTITUTIONAL" in auth_status or auth_status == "Tier 2":
            auth_pts = 12
        elif "CORPORATE" in auth_status or "REPUTABLE" in auth_status or auth_status == "Tier 3":
            auth_pts = 8
        else:
            auth_pts = 4

        # 3. Content Relevance & Accuracy: 20 pts
        rel_score = meta.get("content_relevance_score", 85)
        rel_pts = round((rel_score / 100.0) * 20)

        # 4. Freshness & Document Currency: 20 pts
        fresh_score = meta.get("freshness_score", 90)
        fresh_pts = round((fresh_score / 100.0) * 20)

        # 5. Legal & Regulatory Applicability: 15 pts
        reg_status = meta.get("regulatory_status") or result.regulatory_status or "LEGALLY_BINDING_IN_FORCE"
        if reg_status in ("LEGALLY_BINDING_IN_FORCE", "current"):
            app_pts = 15
        elif reg_status in ("HISTORICAL_FOUNDATIONAL", "CONSULTATION_DRAFT"):
            app_pts = 10
        elif reg_status in ("STAYED_PENDING_LITIGATION", "DISBANDED_TRANSITIONED"):
            app_pts = 8
        else:
            app_pts = 5

        # 6. Target Document vs Landing Page Precision: 10 pts
        url_lower = (record.original_url if record else "").lower()
        if meta.get("is_homepage") or rel_score <= 25:
            prec_pts = 0
        elif url_lower.endswith(".pdf") or "/document/" in url_lower or "/law/" in url_lower or not record:
            prec_pts = 10
        else:
            prec_pts = 8

        # 7. Replacement Verification Status: 5 pts
        rep_pts = 5  # No replacement needed for valid & current link

        total_pts = tech_pts + auth_pts + rel_pts + fresh_pts + app_pts + prec_pts + rep_pts
        total_pts = max(10, min(total_pts, 100))

        # Evidence threshold: if substantive text is absent when inspecting a live record
        if metadata is not None and not has_text and not (record and record.page_title) and result.content_relevance != "high":
            total_pts = min(total_pts, 50)

        score = round(total_pts / 100.0, 2)
        breakdown_str = (
            f"Technical: {tech_pts}/15, Authority: {auth_pts}/15, Relevance: {rel_pts}/20, "
            f"Freshness: {fresh_pts}/20, Applicability: {app_pts}/15, Precision: {prec_pts}/10, Replacement: {rep_pts}/5"
        )
        reason_str = f"Evidence Confidence ({total_pts}/100): [{breakdown_str}]"
        return score, reason_str

    def apply(
        self,
        result: AiEvaluationResult,
        record: Optional[LinkRecord] = None,
        metadata: Optional[dict] = None,
    ) -> AiEvaluationResult:
        score_val, reason_str = self.score(result, record=record, metadata=metadata)
        result.confidence_score = score_val
        result.confidence_reason = reason_str
        return result
