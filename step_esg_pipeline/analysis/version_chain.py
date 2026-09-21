import re
from typing import List, Dict, Any, Optional


class VersionChainEngine:
    """Extracts regulatory cross-references and builds document version chains.

    Patterns:
    - 'supersedes Circular X'
    - 'replaces Notification Y'
    - 'amends Regulation Z'
    - 'read with Circular A'
    - 'as amended by B'
    - 'revised pursuant to C'
    - 'master circular on ...'
    """

    RELATIONSHIP_PATTERNS = [
        ("SUPERSEDES", re.compile(r"\b(?:supersedes|superseded by|in supersession of|repeals)\s+([A-Za-z0-9\/\s\-_\.]{5,80})", re.I)),
        ("REPLACES", re.compile(r"\b(?:replaces|replaced by|substituted for)\s+([A-Za-z0-9\/\s\-_\.]{5,80})", re.I)),
        ("AMENDS", re.compile(r"\b(?:amends|amended by|as amended by|in partial modification of)\s+([A-Za-z0-9\/\s\-_\.]{5,80})", re.I)),
        ("READ_WITH", re.compile(r"\b(?:read with circular|read with notification|read with direction)\s+([A-Za-z0-9\/\s\-_\.]{5,80})", re.I)),
        ("REVISED_PURSUANT_TO", re.compile(r"\b(?:revised pursuant to|issued pursuant to)\s+([A-Za-z0-9\/\s\-_\.]{5,80})", re.I)),
    ]

    @classmethod
    def extract_references(cls, text: str) -> List[Dict[str, str]]:
        """Extracts structured regulatory references from document text."""
        if not text:
            return []

        results = []
        seen = set()

        for rel_type, pat in cls.RELATIONSHIP_PATTERNS:
            for match in pat.finditer(text):
                raw_target = match.group(1).strip()
                # Clean up punctuation and line breaks
                clean_target = re.sub(r"[\r\n\t]+", " ", raw_target)
                clean_target = re.split(r"(?:and|or|\.|\;|\,)\s+(?:whereas|dated|vide)", clean_target)[0].strip(" ,;.")

                if len(clean_target) > 3 and clean_target.lower() not in seen:
                    seen.add(clean_target.lower())
                    results.append({
                        "relationship_type": rel_type,
                        "raw_snippet": match.group(0).strip(),
                        "target_document": clean_target,
                    })

        return results

    @classmethod
    def build_version_chain(
        cls,
        original_doc_title: str,
        original_doc_number: str,
        extracted_references: List[Dict[str, str]],
        candidate_title: str = "",
        candidate_doc_number: str = "",
    ) -> List[Dict[str, Any]]:
        """Constructs an indicative regulatory lifecycle chain for traceability."""
        chain = []

        # 1. Base / Previous node
        previous_refs = [r["target_document"] for r in extracted_references if r["relationship_type"] in ("SUPERSEDES", "REPLACES")]
        for p in previous_refs[:2]:
            chain.append({
                "stage": "PREVIOUS_VERSION",
                "document": p,
                "relationship": "SUPERSEDED_BY_CURRENT",
            })

        # 2. Current / Original node
        chain.append({
            "stage": "ORIGINAL_DOCUMENT",
            "document": original_doc_title or original_doc_number or "Referenced Document",
            "number": original_doc_number,
            "relationship": "MONITORED_LINK",
        })

        # 3. Amendments
        amendment_refs = [r["target_document"] for r in extracted_references if r["relationship_type"] == "AMENDS"]
        for a in amendment_refs[:2]:
            chain.append({
                "stage": "AMENDMENT",
                "document": a,
                "relationship": "AMENDS_CURRENT",
            })

        # 4. Candidate replacement (if present)
        if candidate_title or candidate_doc_number:
            chain.append({
                "stage": "CURRENT_OFFICIAL_VERSION",
                "document": candidate_title or candidate_doc_number,
                "number": candidate_doc_number,
                "relationship": "RECOMMENDED_AUTHORITATIVE_SOURCE",
            })

        return chain
