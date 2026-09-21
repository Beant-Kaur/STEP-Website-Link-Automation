from typing import Optional, Dict, Any, Tuple

from ai.evaluator import AiEvaluationResult
from database.models import LinkRecord


class ConfidenceEngine:
    """
    Evaluates multi-dimensional confidence and computes sub-scores:
    - technical_confidence
    - authority_confidence
    - identity_confidence
    - currentness_confidence
    - replacement_confidence
    - overall_confidence

    Enforces Section 13 hard confidence caps:
    - Access blocked / challenge unresolved: capped at 0.40
    - Technical page title rejected (e.g. Access Denied): capped at 0.50
    - Regulatory lifecycle unknown: capped at 0.55
    """

    @classmethod
    def compute_sub_scores(
        cls,
        result: Optional[AiEvaluationResult] = None,
        record: Optional[LinkRecord] = None,
        metadata: Optional[dict] = None,
    ) -> Dict[str, float]:
        meta = metadata or {}
        cls_name = (getattr(result, "classification", "") or getattr(record, "classification", "") or "").upper()
        http_status = getattr(record, "http_status", None)
        tech_status = (getattr(record, "technical_status", "") or "").upper()
        access_status = (getattr(record, "access_status", "") or "").upper()
        auth_status = (getattr(record, "authority_status", "") or meta.get("authority_status") or "").upper()
        reg_status = (getattr(record, "regulatory_status", "") or meta.get("regulatory_status") or "").upper()
        fresh_status = (getattr(record, "freshness_status", "") or meta.get("freshness_status") or "").upper()
        cand_status = (getattr(record, "candidate_status", "") or "").upper()
        rep_verified = meta.get("replacement_verified", False) or getattr(record, "replacement_verified", False) or getattr(result, "replacement_verified", False)
        has_rep = bool(getattr(record, "replacement_url", "") or getattr(result, "replacement_url", ""))

        tech_title = (getattr(record, "technical_page_title", "") or "").lower()
        has_tech_title_err = any(err in tech_title for err in ["access denied", "403 forbidden", "cloudflare", "waf", "security check"])

        # 1. Technical Confidence
        if http_status in (403, 202) or access_status in ("ACCESS_DENIED", "ACCESS_CHALLENGE", "CLOUDFLARE_CHALLENGE") or cls_name == "ACCESS_RESTRICTED":
            tech_conf = 0.30
        elif http_status in (404, 410) or access_status == "BROKEN_SOFT_404" or tech_status == "BROKEN" or cls_name == "BROKEN":
            tech_conf = 0.95
        elif tech_status == "ACCESSIBLE_VIA_BROWSER" or (record and record.pdf_magic_signature_verified):
            tech_conf = 0.95
        elif http_status == 200:
            tech_conf = 0.90
        elif cls_name == "TEMPORARILY_UNAVAILABLE":
            tech_conf = 0.35
        else:
            tech_conf = 0.50

        # 2. Authority Confidence
        if "TIER_1" in auth_status or "OFFICIAL" in auth_status:
            auth_conf = 0.95
        elif "TIER_2" in auth_status or "STANDARDS" in auth_status or "EXCHANGE" in auth_status:
            auth_conf = 0.85
        elif "TIER_3" in auth_status or "COMMERCIAL" in auth_status or "LAW_FIRM" in auth_status:
            auth_conf = 0.40
        else:
            auth_conf = 0.30

        # 3. Identity Confidence
        if has_tech_title_err:
            id_conf = 0.25
        elif getattr(record, "instrument_name", "") and getattr(record, "country", ""):
            id_conf = 0.90
        elif getattr(record, "page_title", "") and len(record.page_title) > 5:
            id_conf = 0.75
        else:
            id_conf = 0.35

        # 4. Currentness Confidence
        if reg_status in ("CURRENT_IN_FORCE", "LEGALLY_BINDING_IN_FORCE"):
            cur_conf = 0.90
        elif reg_status in ("SUPERSEDED", "REPEALED", "AMENDED") or fresh_status in ("COMPLETELY_SUPERSEDED", "REPEALED_WITHDRAWN", "OBSOLETE"):
            cur_conf = 0.85
        elif reg_status in ("CONSULTATION", "CONSULTATION_DRAFT"):
            cur_conf = 0.50
        elif reg_status == "STAYED_PENDING_LITIGATION":
            cur_conf = 0.80
        elif reg_status == "UNKNOWN" or not reg_status:
            cur_conf = 0.30
        else:
            cur_conf = 0.40

        # 5. Replacement Confidence
        if not has_rep and (cls_name in ("VALID_AND_CURRENT", "CURRENT_IN_FORCE") or reg_status == "CURRENT_IN_FORCE"):
            rep_conf = 1.0  # Not needed
        elif rep_verified or cand_status in ("REPLACEMENT_VERIFIED", "CANDIDATE_VERIFIED"):
            rep_conf = 0.90
        elif has_rep:
            rep_conf = 0.40
        else:
            rep_conf = 0.20

        # Weighted calculation
        overall = (tech_conf * 0.20) + (auth_conf * 0.20) + (id_conf * 0.20) + (cur_conf * 0.25) + (rep_conf * 0.15)

        # Enforce Hard Caps
        if http_status in (403, 202) or access_status in ("ACCESS_DENIED", "ACCESS_CHALLENGE", "CLOUDFLARE_CHALLENGE") or cls_name == "ACCESS_RESTRICTED":
            overall = min(overall, 0.40)

        if has_tech_title_err:
            overall = min(overall, 0.50)

        if reg_status == "UNKNOWN" or not reg_status:
            overall = min(overall, 0.55)

        return {
            "technical_confidence": round(tech_conf, 2),
            "authority_confidence": round(auth_conf, 2),
            "identity_confidence": round(id_conf, 2),
            "currentness_confidence": round(cur_conf, 2),
            "replacement_confidence": round(rep_conf, 2),
            "overall_confidence": round(overall, 2),
        }

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
        rep_pts = 5

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

        # Also calculate and attach sub-scores to record if present
        if record:
            sub = self.compute_sub_scores(result=result, record=record, metadata=metadata)
            record.technical_confidence = sub["technical_confidence"]
            record.authority_confidence = sub["authority_confidence"]
            record.identity_confidence = sub["identity_confidence"]
            record.currentness_confidence = sub["currentness_confidence"]
            record.replacement_confidence = sub["replacement_confidence"]
            record.overall_confidence = sub["overall_confidence"]

        return result
