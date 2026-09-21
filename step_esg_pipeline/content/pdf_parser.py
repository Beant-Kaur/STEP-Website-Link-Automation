import io
from typing import Any, Optional

from content.pdf_engine import PdfEngine
from analysis.date_engine import UniversalDateEngine


class PdfParser:
    @staticmethod
    def parse(source: Any, url: str = "") -> dict:
        raw_bytes = b""
        if isinstance(source, bytes):
            raw_bytes = source
        elif hasattr(source, "read"):
            raw_bytes = source.read()

        result = {
            "title": "",
            "organisation": "",
            "document_number": "",
            "publication_date": "",
            "effective_date": "",
            "version": "",
            "text_sample": "",
            "page_count": 0,
            "repeal_signals": [],
            "amendment_references": [],
            "document_references": [],
            "is_pdf": True,
            "is_valid_pdf": False,
            "magic_signature_verified": False,
            "is_scanned_pdf": False,
            "ocr_applied": False,
        }

        if not raw_bytes:
            return result

        result["magic_signature_verified"] = PdfEngine.verify_magic_bytes(raw_bytes)
        result["is_valid_pdf"] = result["magic_signature_verified"] or raw_bytes.startswith(b"%PDF")

        # Parse content using PdfEngine
        parsed_holder = {
            "url": url,
            "final_url": url,
            "title": "",
            "document_number": "",
            "organisation": "",
            "text_sample": "",
            "page_count": 0,
            "document_references": [],
            "is_scanned_pdf": False,
            "ocr_applied": False,
            "metadata": {},
        }
        PdfEngine._parse_pdf_content(raw_bytes, parsed_holder)

        result["title"] = parsed_holder["title"]
        result["document_number"] = parsed_holder["document_number"]
        result["organisation"] = parsed_holder["organisation"]
        result["text_sample"] = parsed_holder["text_sample"]
        result["page_count"] = parsed_holder["page_count"]
        result["document_references"] = parsed_holder["document_references"]
        result["is_scanned_pdf"] = parsed_holder["is_scanned_pdf"]
        result["ocr_applied"] = parsed_holder["ocr_applied"]

        # Universal Date Extraction on PDF text and URL
        dates = UniversalDateEngine.extract_dates(result["text_sample"], url=url)
        best_date = UniversalDateEngine.select_best_regulatory_date(dates)
        if best_date:
            result["publication_date"] = best_date["original_date"]

        eff_dates = [d for d in dates if d.get("context") == "EFFECTIVE_DATE"]
        if eff_dates:
            result["effective_date"] = eff_dates[0]["original_date"]

        return result
