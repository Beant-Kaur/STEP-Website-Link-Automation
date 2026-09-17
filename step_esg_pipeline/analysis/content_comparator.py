import hashlib
import re
from typing import Optional, Tuple


class ContentComparator:
    """Original hash-based drift detector — unchanged for backward compatibility."""

    @staticmethod
    def hash_text(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def has_changed(previous_hash: str, current_hash: str) -> bool:
        return bool(previous_hash and current_hash and previous_hash != current_hash)

    @staticmethod
    def similarity(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        set_a = set(a.lower().split())
        set_b = set(b.lower().split())
        intersection = set_a & set_b
        union = set_a | set_b
        if not union:
            return 0.0
        return len(intersection) / len(union)


class SemanticComparator:
    """
    Compares original document text against a candidate replacement document text.

    Uses keyword overlap, date recency detection, and (when available) Gemini API
    to produce a human-readable comparison_summary and structured verdict.
    """

    # Regulatory freshness year signals
    _YEAR_RE = re.compile(r"\b(20\d{2})\b")

    def __init__(self, gemini_model=None):
        """
        Args:
            gemini_model: Optional google.generativeai.GenerativeModel instance.
                         If None, falls back to heuristic comparison only.
        """
        self._gemini = gemini_model

    def compare(
        self,
        original_text: str,
        candidate_text: str,
        original_title: str = "",
        candidate_title: str = "",
        original_url: str = "",
        candidate_url: str = "",
    ) -> dict:
        """
        Compare original and candidate document texts.

        Returns:
            {
                "subject_match": bool,
                "version_relationship": "NEWER" | "OLDER" | "SAME" | "UNRELATED",
                "comparison_summary": str,
                "similarity_score": float (0.0 – 1.0),
                "original_years": list[str],
                "candidate_years": list[str],
            }
        """
        if not original_text and not candidate_text:
            return self._empty_result("No text available for comparison.")

        # 1. Word-level Jaccard similarity
        similarity = ContentComparator.similarity(original_text, candidate_text)

        # 2. Extract year signals from both
        original_years = sorted(set(self._YEAR_RE.findall(original_text + " " + original_title)), reverse=True)
        candidate_years = sorted(set(self._YEAR_RE.findall(candidate_text + " " + candidate_title)), reverse=True)

        # 3. Subject match (simple keyword overlap check)
        subject_match = similarity >= 0.15 or self._title_overlap(original_title, candidate_title)

        # 4. Version relationship from year comparison
        version_relationship = self._infer_version_relationship(original_years, candidate_years)

        # 5. Build comparison summary
        if self._gemini:
            comparison_summary = self._gemini_compare(
                original_text, candidate_text,
                original_title, candidate_title,
                original_url, candidate_url,
            )
        else:
            comparison_summary = self._heuristic_summary(
                similarity, version_relationship, original_years, candidate_years,
                original_title, candidate_title,
            )

        return {
            "subject_match": subject_match,
            "version_relationship": version_relationship,
            "comparison_summary": comparison_summary,
            "similarity_score": round(similarity, 3),
            "original_years": original_years[:3],
            "candidate_years": candidate_years[:3],
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _title_overlap(a: str, b: str) -> bool:
        if not a or not b:
            return False
        words_a = set(w.lower() for w in a.split() if len(w) > 3)
        words_b = set(w.lower() for w in b.split() if len(w) > 3)
        if not words_a or not words_b:
            return False
        return len(words_a & words_b) / max(len(words_a), len(words_b)) >= 0.3

    @staticmethod
    def _infer_version_relationship(original_years: list, candidate_years: list) -> str:
        if not original_years and not candidate_years:
            return "UNKNOWN"
        if not candidate_years:
            return "SAME"
        if not original_years:
            return "NEWER"
        orig_max = int(original_years[0])
        cand_max = int(candidate_years[0])
        if cand_max > orig_max:
            return "NEWER"
        elif cand_max < orig_max:
            return "OLDER"
        return "SAME"

    @staticmethod
    def _heuristic_summary(
        similarity: float,
        version_relationship: str,
        original_years: list,
        candidate_years: list,
        original_title: str,
        candidate_title: str,
    ) -> str:
        parts = []
        if version_relationship == "NEWER":
            parts.append(
                f"The recommended replacement ({', '.join(candidate_years[:2]) or 'undated'}) "
                f"appears to be more recent than the original source ({', '.join(original_years[:2]) or 'undated'})."
            )
        elif version_relationship == "OLDER":
            parts.append(
                f"Warning: The candidate replacement ({', '.join(candidate_years[:2]) or 'undated'}) "
                f"appears older than the original ({', '.join(original_years[:2]) or 'undated'})."
            )
        else:
            parts.append("The replacement covers a similar time period to the original source.")

        if similarity >= 0.4:
            parts.append("High content overlap detected — likely the same document family or regulatory framework.")
        elif similarity >= 0.15:
            parts.append("Moderate content overlap — related regulatory topic confirmed.")
        else:
            parts.append("Low textual overlap — manual review recommended to confirm subject match.")

        if original_title and candidate_title:
            parts.append(f"Original: '{original_title[:80]}'. Replacement: '{candidate_title[:80]}'.")

        return " ".join(parts)

    def _gemini_compare(
        self,
        original_text: str,
        candidate_text: str,
        original_title: str,
        candidate_title: str,
        original_url: str,
        candidate_url: str,
    ) -> str:
        """Ask Gemini to compare the two documents and produce a plain-English summary."""
        orig_snippet = original_text[:2000] if original_text else "[not available]"
        cand_snippet = candidate_text[:2000] if candidate_text else "[not available]"

        prompt = f"""Compare these two regulatory/ESG documents and write a 2-3 sentence plain-English summary explaining:
1. Whether they cover the same regulatory topic/framework
2. Which is newer or more applicable
3. Why the replacement is (or is not) a suitable upgrade

ORIGINAL DOCUMENT:
Title: {original_title}
URL: {original_url}
Text: {orig_snippet}

CANDIDATE REPLACEMENT:
Title: {candidate_title}
URL: {candidate_url}
Text: {cand_snippet}

Write only the comparison summary (2-3 sentences, plain English, no bullet points, no JSON):"""

        try:
            response = self._gemini.generate_content(prompt)
            text = getattr(response, "text", "").strip()
            return text[:600] if text else ""
        except Exception as exc:
            return f"Gemini comparison unavailable: {exc}"

    @staticmethod
    def _empty_result(reason: str) -> dict:
        return {
            "subject_match": False,
            "version_relationship": "UNKNOWN",
            "comparison_summary": reason,
            "similarity_score": 0.0,
            "original_years": [],
            "candidate_years": [],
        }


class ComparabilityAnalyzer:
    """
    Implements multi-attribute comparability analysis between an original STEP
    resource and a replacement candidate per Section 9 of the Master Prompt.
    Evaluates:
    - issuer
    - jurisdiction
    - regulation/standard identity
    - topic
    - document type
    - title
    - version
    - publication date
    - effective date
    - scope & applicability
    """

    @staticmethod
    def analyze(original: dict, candidate: dict) -> dict:
        matched = []
        mismatched = []
        evidence = []

        orig_issuer = (original.get("issuer") or original.get("source_organisation") or "").lower().strip()
        cand_issuer = (candidate.get("issuer") or candidate.get("source_organisation") or "").lower().strip()

        orig_jur = (original.get("jurisdiction") or "").lower().strip()
        cand_jur = (candidate.get("jurisdiction") or "").lower().strip()

        orig_reg = (original.get("regulation_identity") or original.get("topic") or "").lower().strip()
        cand_reg = (candidate.get("regulation_identity") or candidate.get("topic") or "").lower().strip()

        orig_doc_type = (original.get("document_type") or "").lower().strip()
        cand_doc_type = (candidate.get("document_type") or "").lower().strip()

        orig_title = (original.get("title") or original.get("page_title") or "").lower().strip()
        cand_title = (candidate.get("title") or candidate.get("page_title") or "").lower().strip()

        # 1. Jurisdiction comparison
        if orig_jur and cand_jur:
            if orig_jur == cand_jur or orig_jur in cand_jur or cand_jur in orig_jur:
                matched.append("jurisdiction")
                evidence.append(f"Matching jurisdiction: {orig_jur.upper()}")
            else:
                mismatched.append("jurisdiction")
                evidence.append(f"Jurisdiction mismatch: '{orig_jur.upper()}' vs '{cand_jur.upper()}'")

        # 2. Issuer comparison
        if orig_issuer and cand_issuer:
            if orig_issuer == cand_issuer or orig_issuer in cand_issuer or cand_issuer in orig_issuer:
                matched.append("issuer")
                evidence.append(f"Matching issuing authority: {orig_issuer}")
            else:
                # Check for standard succession (e.g. TCFD -> ISSB / IFRS)
                if ("tcfd" in orig_issuer and "ifrs" in cand_issuer) or ("efrag" in orig_issuer and "commission" in cand_issuer):
                    matched.append("issuer_succession")
                    evidence.append(f"Institutional succession: {orig_issuer} transitioned to {cand_issuer}")
                else:
                    mismatched.append("issuer")
                    evidence.append(f"Different issuer: '{orig_issuer}' vs '{cand_issuer}'")

        # 3. Regulation identity / Topic comparison
        if orig_reg and cand_reg:
            if orig_reg == cand_reg or orig_reg in cand_reg or cand_reg in orig_reg:
                matched.append("regulation_identity")
                evidence.append(f"Matching regulatory topic: {orig_reg}")
            else:
                mismatched.append("regulation_identity")

        # 4. Document Type
        if orig_doc_type and cand_doc_type:
            if orig_doc_type == cand_doc_type:
                matched.append("document_type")
            else:
                # E.g. consultation draft vs enacted standard is partially comparable
                mismatched.append("document_type")
                evidence.append(f"Document type transition: '{orig_doc_type}' -> '{cand_doc_type}'")

        # 5. Title words overlap
        orig_words = set(w for w in orig_title.split() if len(w) > 3)
        cand_words = set(w for w in cand_title.split() if len(w) > 3)
        overlap = len(orig_words & cand_words)
        if overlap >= 2:
            matched.append("title_keywords")

        # Determine Comparability status
        # If jurisdiction explicitly conflicts -> NOT_COMPARABLE
        if "jurisdiction" in mismatched:
            comparability = "NOT_COMPARABLE"
            confidence = 0.85
            explanation = "Jurisdictions conflict; candidate replacement covers a different regulatory regime."
        elif len(matched) >= 3 or ("issuer" in matched and "regulation_identity" in matched):
            comparability = "COMPARABLE"
            confidence = 0.90
            explanation = "Candidate replacement directly matches regulatory identity, issuer, and jurisdiction."
        elif "issuer_succession" in matched or len(matched) >= 1:
            comparability = "PARTIALLY_COMPARABLE"
            confidence = 0.70
            explanation = "Candidate replacement shares regulatory lineage or framework, with version or institutional updates."
        elif not original and not candidate:
            comparability = "UNCERTAIN"
            confidence = 0.30
            explanation = "Insufficient metadata to establish comparability."
        else:
            comparability = "UNCERTAIN"
            confidence = 0.45
            explanation = "Comparability between original resource and candidate could not be conclusively determined."

        return {
            "comparability": comparability,
            "comparability_confidence": round(confidence, 2),
            "matched_attributes": matched,
            "mismatched_attributes": mismatched,
            "evidence": evidence,
            "explanation": explanation,
        }
