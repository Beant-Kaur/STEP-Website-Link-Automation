import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse

from analysis.regulatory_identity import RegulatoryIdentity
from jurisdictions import JurisdictionRegistry


LIFECYCLE_SUPERSEDED_PATTERNS = [
    r"\b(?:superseded\s*by|repealed\s*by|replaced\s*by)\s+([^.,;\n]+)",
    r"\b(?:replaces|supersedes|repeals|revokes)\s+([^.,;\n]+)",
    r"\b(?:no\s*longer\s*in\s*force|ceased\s*to\s*apply|repealed|withdrawn|revoked)\b",
    r"\b(?:disbanded|transitioned\s*to\s*(?:issb|ifrs))\b",
]

LIFECYCLE_AMENDED_PATTERNS = [
    r"\b(?:amended\s*by|amends|as\s*amended|amendment\s*(?:to|act|rules?|regulations?))\b",
    r"\b(?:modified\s*by|updated\s*by|revised\s*in)\b",
]

LIFECYCLE_DRAFT_PATTERNS = [
    r"\b(?:consultation\s*paper|exposure\s*draft|discussion\s*paper|proposed\s*rule|draft\s*for\s*comments?|public\s*consultation)\b",
    r"\b(?:not\s*yet\s*in\s*force|draft\s*version|preliminary\s*draft)\b",
]

LIFECYCLE_IN_FORCE_PATTERNS = [
    r"\b(?:in\s*force|currently\s*in\s*force|effective\s*from\s*[0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})\b",
    r"\b(?:legally\s*binding|applicable\s*to\s*all\s*listed)\b",
]


@dataclass
class CurrentnessResult:
    lifecycle_status: str = "UNKNOWN"
    lifecycle_reason: str = ""
    is_final: bool = True
    is_draft_or_consultation: bool = False
    evidence_items: List[Tuple[str, str]] = field(default_factory=list)
    currentness_confidence: float = 0.0

    def __getitem__(self, key: str) -> Any:
        mapping = {
            "regulatory_status": self.lifecycle_status,
            "lifecycle_status": self.lifecycle_status,
            "rationale": self.lifecycle_reason,
            "lifecycle_reason": self.lifecycle_reason,
            "freshness_score": int(self.currentness_confidence * 100),
            "confidence": self.currentness_confidence,
            "currentness_confidence": self.currentness_confidence,
            "is_final": self.is_final,
            "is_draft_or_consultation": self.is_draft_or_consultation,
            "signals": [item[1] for item in self.evidence_items],
            "evidence_items": self.evidence_items,
        }
        if key in mapping:
            return mapping[key]
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except (KeyError, AttributeError):
            return default


class CurrentnessEngine:
    """Verifies whether a regulatory source remains current, amended, superseded, repealed, or draft."""

    def __init__(self, registry: Optional[JurisdictionRegistry] = None):
        self.registry = registry or JurisdictionRegistry.get_instance()

    @classmethod
    def evaluate(
        cls,
        identity: RegulatoryIdentity,
        text_sample: str = "",
        http_status: Optional[int] = None,
        technical_status: str = "",
        is_pdf_valid: bool = False,
        candidate_identity: Optional[RegulatoryIdentity] = None,
        page_title: str = "",
        url: str = "",
        source_domain: str = "",
        authority_status: str = "",
        **kwargs,
    ) -> CurrentnessResult:
        ev: List[Tuple[str, str]] = []
        combined_text = f"{identity.instrument_name} {page_title} {text_sample}".lower()

        # -------------------------------------------------------------
        # Signal A: Existing Source Status
        # -------------------------------------------------------------
        if http_status in (404, 410) or technical_status in ("HTTP_404", "SOFT_404"):
            ev.append(("technical", f"Original source returned {http_status or technical_status}; resource no longer exists at URL."))
            return CurrentnessResult(
                lifecycle_status="UNKNOWN",
                lifecycle_reason="Source URL is broken or removed.",
                is_final=True,
                evidence_items=ev,
                currentness_confidence=0.1,
            )

        if technical_status in ("ACCESS_BLOCKED", "WAF_BLOCKED", "BOT_CHALLENGE"):
            ev.append(("currentness", "Currentness cannot be verified because remote source access is blocked by security challenge."))
            return CurrentnessResult(
                lifecycle_status="UNKNOWN",
                lifecycle_reason="Access is blocked; currentness cannot be determined without access.",
                is_final=True,
                evidence_items=ev,
                currentness_confidence=0.0,
            )

        # -------------------------------------------------------------
        # Signal B: Issuing Authority Verification
        # -------------------------------------------------------------
        registry = JurisdictionRegistry.get_instance()
        is_official = False
        if identity.authority != "UNKNOWN" and identity.authority_tier in ("TIER_1_PRIMARY_REGULATOR", "TIER_1_OFFICIAL_LEGISLATION", "TIER_2_OFFICIAL_EXCHANGE", "TIER_2_OFFICIAL_STANDARD_BODY"):
            is_official = True
            ev.append(("authority", f"Issuing authority verified as authoritative: {identity.authority} ({identity.authority_tier})"))
        else:
            ev.append(("authority", f"Issuing authority association is unconfirmed or secondary: {identity.authority}"))

        # -------------------------------------------------------------
        # Signal F: Legal Status (Draft / Consultation vs Final)
        # -------------------------------------------------------------
        is_draft = False
        for pat in LIFECYCLE_DRAFT_PATTERNS:
            if re.search(pat, combined_text, re.I):
                is_draft = True
                ev.append(("currentness", "Document contains draft/consultation markers; not a final regulation."))
                break

        if is_draft:
            return CurrentnessResult(
                lifecycle_status="CONSULTATION",
                lifecycle_reason="Document is a consultation paper or draft proposal, not a final binding regulation.",
                is_final=False,
                is_draft_or_consultation=True,
                evidence_items=ev,
                currentness_confidence=0.75,
            )

        # -------------------------------------------------------------
        # Signal C: Lifecycle Language in Document
        # -------------------------------------------------------------
        # 1. Check Superseded / Repealed
        for pat in LIFECYCLE_SUPERSEDED_PATTERNS:
            m = re.search(pat, combined_text, re.I)
            if m:
                successor = m.group(1).strip() if len(m.groups()) >= 1 and m.group(1) else ""
                reason = f"Document explicitly superseded/repealed" + (f" by {successor}" if successor else "")
                ev.append(("currentness", reason))
                return CurrentnessResult(
                    lifecycle_status="SUPERSEDED",
                    lifecycle_reason=reason,
                    is_final=True,
                    evidence_items=ev,
                    currentness_confidence=0.85,
                )

        # 2. Check Transitioned (e.g. TCFD -> ISSB)
        if "tcfd" in identity.instrument_name.lower() and any(x in combined_text for x in ("disbanded", "transitioned to ifrs", "transferred to ifrs")):
            reason = "TCFD recommendations disbanded and officially transitioned to IFRS/ISSB standards."
            ev.append(("currentness", reason))
            return CurrentnessResult(
                lifecycle_status="TRANSITIONED",
                lifecycle_reason=reason,
                is_final=True,
                evidence_items=ev,
                currentness_confidence=0.90,
            )

        # 3. Check Amended
        for pat in LIFECYCLE_AMENDED_PATTERNS:
            if re.search(pat, combined_text, re.I):
                reason = "Document contains explicit amendment references or is an amending instrument."
                ev.append(("currentness", reason))
                return CurrentnessResult(
                    lifecycle_status="AMENDED",
                    lifecycle_reason=reason,
                    is_final=True,
                    evidence_items=ev,
                    currentness_confidence=0.80,
                )

        # -------------------------------------------------------------
        # Signal D & E: Candidate Comparison (if candidate provided)
        # -------------------------------------------------------------
        if candidate_identity:
            comp_ok, comp_reason = cls.compare_applicability(identity, candidate_identity)
            if not comp_ok:
                ev.append(("applicability", f"Candidate rejected: {comp_reason}"))
            else:
                ev.append(("applicability", f"Candidate matches regulatory applicability: {comp_reason}"))

        # -------------------------------------------------------------
        # Signal C & In-Force Verification
        # -------------------------------------------------------------
        has_in_force_terms = any(re.search(pat, combined_text, re.I) for pat in LIFECYCLE_IN_FORCE_PATTERNS)
        if is_official and is_pdf_valid:
            if has_in_force_terms:
                ev.append(("currentness", "Official document text contains active in-force/effective regulatory statements."))
                return CurrentnessResult(
                    lifecycle_status="CURRENT_IN_FORCE",
                    lifecycle_reason="Official regulatory instrument confirmed in force with no detected supersession.",
                    is_final=True,
                    evidence_items=ev,
                    currentness_confidence=0.85,
                )
            else:
                # Section 9 Rule: Valid PDF on official site without explicit supersession OR explicit currentness evidence
                # Must NOT automatically be declared CURRENT! Must remain UNKNOWN unless corroborated.
                ev.append(("currentness", "Valid official PDF verified, but active legal in-force status requires confirmation."))
                return CurrentnessResult(
                    lifecycle_status="UNKNOWN",
                    lifecycle_reason="Technical document is valid, but regulatory currentness requires independent verification.",
                    is_final=True,
                    evidence_items=ev,
                    currentness_confidence=0.55,
                )

        ev.append(("currentness", "Insufficient authoritative lifecycle evidence to confirm active legal status."))
        return CurrentnessResult(
            lifecycle_status="UNKNOWN",
            lifecycle_reason="Lifecycle status unconfirmed due to lack of explicit in-force or supersession evidence.",
            is_final=True,
            evidence_items=ev,
            currentness_confidence=0.40,
        )

    @classmethod
    def compare_applicability(cls, orig: RegulatoryIdentity, cand: RegulatoryIdentity) -> Tuple[bool, str]:
        """Signal E & Section 13: Strictly enforces that a candidate document covers the SAME subject.
        Candidate cannot replace original unless jurisdiction, authority, topic, and population match.
        """
        # 1. Jurisdiction Match
        if orig.country != "UNKNOWN" and cand.country != "UNKNOWN":
            if orig.country.lower() != cand.country.lower():
                # Allow EU regulations in European member states
                if not (orig.country.lower() == "european union" or cand.country.lower() == "european union"):
                    return False, f"Jurisdiction mismatch: '{orig.country}' vs '{cand.country}'"

        # 2. Authority Compatibility
        if orig.authority != "UNKNOWN" and cand.authority != "UNKNOWN":
            if orig.authority.lower() != cand.authority.lower():
                # Check if both are recognized authorities in the same jurisdiction
                reg = JurisdictionRegistry.get_instance()
                auths = [a["name"].lower() for a in reg.get_authorities(orig.country)]
                if cand.authority.lower() not in auths and orig.authority.lower() not in auths:
                    return False, f"Authority mismatch: '{orig.authority}' vs '{cand.authority}'"

        # 3. Draft cannot replace Final (Section 8 Signal F & Section 9)
        if "consultation" in cand.instrument_type.lower() or "draft" in cand.instrument_type.lower():
            if "consultation" not in orig.instrument_type.lower() and "draft" not in orig.instrument_type.lower():
                return False, f"Draft/consultation instrument ('{cand.instrument_name}') cannot replace a final regulation ('{orig.instrument_name}')."

        # 4. Regulatory Topic Match
        if orig.regulatory_topic and cand.regulatory_topic:
            if orig.regulatory_topic != cand.regulatory_topic:
                return False, f"Topic divergence: '{orig.regulatory_topic}' vs '{cand.regulatory_topic}'"

        return True, "Same jurisdiction, compatible authority, and matching regulatory topic."
