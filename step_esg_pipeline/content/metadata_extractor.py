import hashlib
import re
from datetime import datetime
from typing import Any, Optional

from analysis.date_engine import UniversalDateEngine


class MetadataExtractor:
    @staticmethod
    def extract(content_type: str, text_or_source: Any, url: str = "", jurisdiction: str = "") -> dict:
        content_type = (content_type or "").lower()
        if content_type.startswith("application/pdf") or content_type.endswith("pdf") or (isinstance(text_or_source, bytes) and text_or_source.startswith(b"%PDF")):
            from content.pdf_parser import PdfParser
            result = PdfParser.parse(text_or_source, url=url)
        else:
            from content.html_parser import HtmlParser
            text = text_or_source.decode("utf-8", errors="replace") if isinstance(text_or_source, bytes) else str(text_or_source)
            result = HtmlParser.parse(text)

        from content.html_parser import HtmlParser
        doc_title = result.get("title", "") or ""
        tech_title = result.get("technical_page_title", "") or ""
        if HtmlParser.is_technical_title(doc_title):
            tech_title = tech_title or doc_title
            doc_title = "UNKNOWN"
        result["title"] = doc_title
        result["technical_page_title"] = tech_title

        text_sample = result.get("text_sample", "") or ""
        combined_text = f"{doc_title} {text_sample}"

        # Generate content hash for historical change comparison (Section 20)
        if text_sample:
            result["content_hash"] = hashlib.sha256(text_sample.encode("utf-8", errors="replace")).hexdigest()
        else:
            result["content_hash"] = ""

        result["is_outdated"] = MetadataExtractor.is_outdated(combined_text)

        # Universal Date Extraction (Sections 19, 20, 21, 22)
        extracted_dates = UniversalDateEngine.extract_dates(combined_text, url=url, jurisdiction=jurisdiction)
        result["extracted_dates"] = extracted_dates

        best_date = UniversalDateEngine.select_best_regulatory_date(extracted_dates)
        if best_date:
            result["publication_date"] = best_date["original_date"]
            result["publication_date_iso"] = best_date["normalized_date"]
            result["date_context"] = best_date["context"]
        else:
            if result.get("publication_date"):
                result["publication_date_iso"] = MetadataExtractor.parse_date(result["publication_date"])
            else:
                result["publication_date_iso"] = ""

        # Extract effective date if explicitly found
        eff_dates = [d for d in extracted_dates if d.get("context") == "EFFECTIVE_DATE"]
        if eff_dates:
            result["effective_date"] = eff_dates[0]["original_date"]
            result["effective_date_iso"] = eff_dates[0]["normalized_date"]
        elif result.get("effective_date"):
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
