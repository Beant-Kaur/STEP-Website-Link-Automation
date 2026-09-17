import hashlib
import re
from datetime import datetime
from typing import Any, Optional


class MetadataExtractor:
    @staticmethod
    def extract(content_type: str, text_or_source: Any) -> dict:
        content_type = (content_type or "").lower()
        if content_type.startswith("application/pdf") or content_type.endswith("pdf"):
            from content.pdf_parser import PdfParser
            result = PdfParser.parse(text_or_source)
        else:
            from content.html_parser import HtmlParser
            text = text_or_source.decode("utf-8", errors="replace") if isinstance(text_or_source, bytes) else str(text_or_source)
            result = HtmlParser.parse(text)

        text_sample = result.get("text_sample", "") or ""
        combined_text = f"{result.get('title', '')} {text_sample}"

        # Generate content hash for historical change comparison (Section 20)
        if text_sample:
            result["content_hash"] = hashlib.sha256(text_sample.encode("utf-8", errors="replace")).hexdigest()
        else:
            result["content_hash"] = ""

        result["is_outdated"] = MetadataExtractor.is_outdated(combined_text)

        if result.get("publication_date"):
            result["publication_date_iso"] = MetadataExtractor.parse_date(result["publication_date"])
        else:
            result["publication_date_iso"] = ""

        if result.get("effective_date"):
            result["effective_date_iso"] = MetadataExtractor.parse_date(result["effective_date"])
        else:
            result["effective_date_iso"] = ""

        return result

    @staticmethod
    def parse_date(raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%B %d, %Y", "%d %B %Y", "%Y/%m/%d", "%d-%b-%Y"):
            try:
                return datetime.strptime(raw.strip(), fmt).date().isoformat()
            except ValueError:
                continue
        return raw

    @staticmethod
    def is_outdated(text: str) -> bool:
        signals = [
            r"\b(replaced by|superseded by|repealed|withdrawn|revoked|no longer in force|previous version|former version)\b",
            r"\b(historical document|prior version|archived|obsolete|expired)\b",
        ]
        return any(re.search(s, text, re.I) for s in signals)
