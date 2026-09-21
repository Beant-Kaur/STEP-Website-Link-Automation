import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import unquote


MONTH_NAMES = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

CONTEXT_KEYWORDS = {
    "EFFECTIVE_DATE": ["effective from", "effective date", "comes into force", "entry into force", "applicable from", "in force as of"],
    "ISSUE_DATE": ["issued on", "date of issue", "issuance date", "issued by", "dated"],
    "PUBLICATION_DATE": ["published on", "publication date", "published in the official journal", "date of publication", "promulgated on"],
    "NOTIFICATION_DATE": ["notification date", "notified on", "gazette notification dated"],
    "AMENDMENT_DATE": ["amended on", "amendment dated", "last amended", "as amended on"],
    "REVISION_DATE": ["revised on", "revision date", "version dated"],
    "EXPIRY_DATE": ["expiry date", "valid until", "expires on", "sunset date", "ceases to have effect"],
    "COMMENCEMENT_DATE": ["commencement date", "commencing on", "enacted on"],
    "FILING_DATE": ["filed on", "filing date", "lodged on"],
    "UPDATE_DATE": ["updated on", "last updated", "page modified", "site updated"],
    "CMS_FOOTER_DATE": ["all rights reserved", "copyright", "©", "terms of use"],
}


class UniversalDateEngine:
    """Universal Regulatory Date Extraction, Context Inference, and Ambiguity Resolution Engine."""

    # 1. Day Month Year (e.g. 15 March 2025, 15th Mar 2025, 15-Mar-2025)
    DMY_TEXT_PAT = re.compile(
        r"\b([0-3]?[0-9])(?:st|nd|rd|th)?[\s\-_]+([A-Za-z]{3,9})[\s\-_]+(19\d{2}|20\d{2})\b",
        re.I
    )

    # 2. Month Day Year (e.g. March 15, 2025, Mar 15 2025, March 15th 2025)
    MDY_TEXT_PAT = re.compile(
        r"\b([A-Za-z]{3,9})[\s\-_]+([0-3]?[0-9])(?:st|nd|rd|th)?(?:,)?[\s\-_]+(19\d{2}|20\d{2})\b",
        re.I
    )

    # 3. ISO format with optional time (2025-03-15, 2025/03/15, 2025.03.15, 2025-03-15T10:30:00Z)
    ISO_DATE_PAT = re.compile(
        r"\b(19\d{2}|20\d{2})[\/\-\.](0?[1-9]|1[0-2])[\/\-\.](0?[1-9]|[12][0-9]|3[01])(?:T|\s+)?(?:\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?\b",
        re.I
    )

    # 4. Numeric Slash/Dash/Dot (e.g. 15/03/2025, 15-03-2025, 15.03.2025)
    NUMERIC_PAT = re.compile(
        r"\b(0?[1-9]|[12][0-9]|3[01])[\/\-\.](0?[1-9]|[12][0-9]|3[01])[\/\-\.](19\d{2}|20\d{2}|[0-9]{2})\b"
    )

    # 5. Month Year (e.g. March 2025, Mar 2025, 2025-03, 03/2025)
    MONTH_YEAR_PAT = re.compile(
        r"\b([A-Za-z]{3,9})[\s\-_]+(19\d{2}|20\d{2})\b",
        re.I
    )

    @classmethod
    def extract_dates(
        cls,
        text: str,
        url: str = "",
        jurisdiction: str = "",
        location_hint: str = "body",
    ) -> List[Dict[str, Any]]:
        """Extracts all dates from text or URL with dynamic context and normalized ISO values."""
        results: List[Dict[str, Any]] = []
        seen_normalized = set()

        # Check URL filename and path first
        if url:
            decoded_url = unquote(url)
            url_dates = cls._extract_from_snippet(decoded_url, "url_path", jurisdiction, url)
            for d in url_dates:
                if d["normalized_date"] not in seen_normalized:
                    seen_normalized.add(d["normalized_date"])
                    results.append(d)

        # Check text content
        if text:
            text_dates = cls._extract_from_snippet(text, location_hint, jurisdiction, url)
            for d in text_dates:
                if d["normalized_date"] not in seen_normalized:
                    seen_normalized.add(d["normalized_date"])
                    results.append(d)

        return results

    @classmethod
    def _extract_from_snippet(
        cls,
        content: str,
        location: str,
        jurisdiction: str,
        source_url: str,
    ) -> List[Dict[str, Any]]:
        extracted = []
        # Replace underscores and plus signs with space for text-based matching
        clean_text_content = re.sub(r"[_\+]+", " ", content)

        # 1. Day Month Year text
        for m in cls.DMY_TEXT_PAT.finditer(clean_text_content):
            day_s, month_s, year_s = m.group(1), m.group(2).lower(), m.group(3)
            if month_s in MONTH_NAMES:
                month_num = MONTH_NAMES[month_s]
                try:
                    norm = f"{int(year_s):04d}-{month_num:02d}-{int(day_s):02d}"
                    ctx, conf = cls._infer_context(content, m.start(), m.end(), location)
                    extracted.append({
                        "original_date": m.group(0).strip(),
                        "normalized_date": norm,
                        "context": ctx,
                        "location": location,
                        "source_url": source_url,
                        "confidence": conf,
                        "is_ambiguous": False,
                    })
                except Exception:
                    pass

        # 2. Month Day Year text
        for m in cls.MDY_TEXT_PAT.finditer(clean_text_content):
            month_s, day_s, year_s = m.group(1).lower(), m.group(2), m.group(3)
            if month_s in MONTH_NAMES:
                month_num = MONTH_NAMES[month_s]
                try:
                    norm = f"{int(year_s):04d}-{month_num:02d}-{int(day_s):02d}"
                    ctx, conf = cls._infer_context(content, m.start(), m.end(), location)
                    extracted.append({
                        "original_date": m.group(0).strip(),
                        "normalized_date": norm,
                        "context": ctx,
                        "location": location,
                        "source_url": source_url,
                        "confidence": conf,
                        "is_ambiguous": False,
                    })
                except Exception:
                    pass

        # 3. ISO Date Pattern
        for m in cls.ISO_DATE_PAT.finditer(content):
            year_s, month_s, day_s = m.group(1), m.group(2), m.group(3)
            try:
                norm = f"{int(year_s):04d}-{int(month_s):02d}-{int(day_s):02d}"
                ctx, conf = cls._infer_context(content, m.start(), m.end(), location)
                extracted.append({
                    "original_date": m.group(0).strip(),
                    "normalized_date": norm,
                    "context": ctx,
                    "location": location,
                    "source_url": source_url,
                    "confidence": conf,
                    "is_ambiguous": False,
                })
            except Exception:
                pass

        # 4. Numeric Pattern (e.g. 15/03/2025, 15-03-2025, 15.03.2025, 15_03_2025)
        for m in cls.NUMERIC_PAT.finditer(clean_text_content):
            p1, p2, p3 = int(m.group(1)), int(m.group(2)), int(m.group(3))
            year = p3 if p3 > 99 else (2000 + p3 if p3 < 70 else 1900 + p3)

            is_ambiguous = False
            confidence = 0.85
            if p1 > 12 and p2 <= 12:
                # Must be DD/MM/YYYY
                day, month = p1, p2
            elif p1 <= 12 and p2 > 12:
                # Must be MM/DD/YYYY
                month, day = p1, p2
            elif p1 <= 12 and p2 <= 12:
                # Ambiguous! Section 21
                is_ambiguous = True
                # Use regional convention
                jurisdiction_low = jurisdiction.lower()
                if any(x in jurisdiction_low for x in ("us", "usa", "united states")):
                    month, day = p1, p2
                    confidence = 0.55
                elif any(x in jurisdiction_low for x in ("india", "uk", "united kingdom", "eu", "singapore", "australia", "uae", "nigeria")):
                    day, month = p1, p2
                    confidence = 0.65
                else:
                    day, month = p1, p2
                    confidence = 0.40

            try:
                norm = f"{year:04d}-{month:02d}-{day:02d}"
                ctx, ctx_conf = cls._infer_context(content, m.start(), m.end(), location)
                extracted.append({
                    "original_date": m.group(0).strip(),
                    "normalized_date": norm,
                    "context": ctx,
                    "location": location,
                    "source_url": source_url,
                    "confidence": min(confidence, ctx_conf),
                    "is_ambiguous": is_ambiguous,
                })
            except Exception:
                pass

        # 5. Month Year Pattern (e.g. July 2023)
        for m in cls.MONTH_YEAR_PAT.finditer(clean_text_content):
            month_s, year_s = m.group(1).lower(), m.group(2)
            if month_s in MONTH_NAMES:
                month_num = MONTH_NAMES[month_s]
                norm = f"{int(year_s):04d}-{month_num:02d}"
                ctx, conf = cls._infer_context(content, m.start(), m.end(), location)
                extracted.append({
                    "original_date": m.group(0).strip(),
                    "normalized_date": norm,
                    "context": ctx,
                    "location": location,
                    "source_url": source_url,
                    "confidence": conf * 0.9,
                    "is_ambiguous": False,
                })

        return extracted

    @classmethod
    def _infer_context(cls, full_text: str, start: int, end: int, location: str) -> Tuple[str, float]:
        """Examines surrounding text window to dynamically classify date context based on closest keyword."""
        full_text_lower = full_text.lower()
        date_mid = (start + end) / 2

        closest_label = None
        min_dist = 9999

        for ctx_label, phrases in CONTEXT_KEYWORDS.items():
            for phrase in phrases:
                for m in re.finditer(re.escape(phrase), full_text_lower):
                    phrase_mid = (m.start() + m.end()) / 2
                    dist = abs(phrase_mid - date_mid)
                    # Prioritize words immediately preceding the date
                    if phrase_mid <= date_mid:
                        dist *= 0.8
                    if dist < min_dist and dist <= 120:
                        min_dist = dist
                        closest_label = ctx_label

        if closest_label:
            confidence = 0.95 if closest_label in ("EFFECTIVE_DATE", "ISSUE_DATE", "PUBLICATION_DATE") else 0.85
            return closest_label, confidence

        if location == "url_path":
            return "DOCUMENT_DATE", 0.90
        elif location in ("header", "title"):
            return "DOCUMENT_DATE", 0.85

        return "DOCUMENT_DATE", 0.70

    @classmethod
    def select_best_regulatory_date(cls, dates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Section 22: Selects the most relevant regulatory date from multiple candidates.

        Prioritizes:
        1. Explicit Effective Date
        2. Explicit Document / Issue / Publication Date
        3. Document Date from URL or Title
        4. Rejects CMS / Copyright / Footer update dates
        """
        if not dates:
            return None

        # Exclude CMS footer dates
        candidates = [d for d in dates if d.get("context") != "CMS_FOOTER_DATE"]
        if not candidates:
            candidates = dates

        # Priority order
        priority_map = {
            "EFFECTIVE_DATE": 10,
            "ISSUE_DATE": 9,
            "PUBLICATION_DATE": 8,
            "NOTIFICATION_DATE": 8,
            "COMMENCEMENT_DATE": 8,
            "DOCUMENT_DATE": 7,
            "REVISION_DATE": 6,
            "AMENDMENT_DATE": 6,
            "FILING_DATE": 5,
            "UPDATE_DATE": 3,
            "CMS_FOOTER_DATE": 1,
        }

        candidates.sort(
            key=lambda d: (
                priority_map.get(d.get("context", ""), 4),
                d.get("confidence", 0.0),
                d.get("normalized_date", "")
            ),
            reverse=True
        )

        return candidates[0] if candidates else None
