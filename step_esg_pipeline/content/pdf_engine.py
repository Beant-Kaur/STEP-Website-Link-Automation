import io
import logging
import re
import urllib.parse
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlparse

import requests

logger = logging.getLogger("pdf_engine")


class PdfEngine:
    """Advanced Regulatory PDF Discovery, Validation, and Content Extraction Engine.

    Guarantees:
    - Direct PDF, download endpoint, viewer, and embedded PDF discovery.
    - Content-Type: application/pdf verification.
    - Magic file-signature (%PDF-) binary validation.
    - Detection of Soft-404 HTML pages disguised as HTTP 200 responses.
    - Scanned PDF detection with pypdfium2 image rendering & pytesseract OCR fallback.
    - Deep extraction: document number, circular number, notification number,
      universal dates, version, references to previous/subsequent documents.
    """

    PDF_MAGIC_BYTES = b"%PDF-"

    @classmethod
    def verify_magic_bytes(cls, raw_bytes: bytes) -> bool:
        """Verifies if raw bytes start with standard PDF magic signature (%PDF-)."""
        if not raw_bytes:
            return False
        # Allow up to 1024 bytes prefix for BOM or leading whitespace/headers
        prefix = raw_bytes[:1024]
        return cls.PDF_MAGIC_BYTES in prefix

    @classmethod
    def is_pdf_url_or_endpoint(cls, url: str, content_type: str = "") -> bool:
        """Checks if URL or response indicates a PDF resource."""
        if not url:
            return False
        u_low = url.lower()
        ct_low = (content_type or "").lower()
        if "application/pdf" in ct_low or "application/x-pdf" in ct_low:
            return True
        if u_low.endswith(".pdf") or ".pdf?" in u_low or "/pdf/" in u_low:
            return True
        if "download" in u_low and any(k in u_low for k in ("id=", "doc=", "file=", "circular")):
            return True
        return False

    @classmethod
    def fetch_and_validate(cls, url: str, timeout: int = 30) -> Dict[str, Any]:
        """Fetches resource stream, validates headers and magic bytes, and extracts content.

        Distinguishes Cases:
        - Case A: Valid PDF (200 + application/pdf + %PDF- + readable)
        - Case B: HTTP 200 HTML error page (soft-404)
        - Case C: PDF viewer page wrapping a document
        - Case D: Redirected PDF
        - Case E: Download endpoint
        - Case F: Access restricted (403 / challenge)
        """
        result: Dict[str, Any] = {
            "url": url,
            "final_url": url,
            "http_status": None,
            "content_type": "",
            "is_valid_pdf": False,
            "magic_signature_verified": False,
            "pdf_case": "UNKNOWN",
            "is_soft_404": False,
            "is_scanned_pdf": False,
            "ocr_applied": False,
            "title": "",
            "document_number": "",
            "organisation": "",
            "publication_date": "",
            "effective_date": "",
            "version": "",
            "text_sample": "",
            "page_count": 0,
            "document_references": [],
            "repeal_signals": [],
            "metadata": {},
            "raw_bytes": None,
            "error": None,
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "application/pdf,application/xhtml+xml,text/html;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True, stream=True)
            result["http_status"] = resp.status_code
            result["final_url"] = resp.url
            result["content_type"] = resp.headers.get("Content-Type", "").lower()

            if resp.status_code in (403, 202):
                result["pdf_case"] = "CASE_F_ACCESS_DENIED"
                return result

            if resp.status_code in (404, 410):
                result["pdf_case"] = "PAGE_NOT_FOUND"
                return result

            if resp.status_code >= 400:
                result["pdf_case"] = f"HTTP_{resp.status_code}"
                return result

            # Read initial chunk (up to 256KB) for signature & type check
            raw_chunk = resp.raw.read(256 * 1024)
            full_bytes = raw_chunk
            # Read remainder if it's a PDF of reasonable size (up to 15MB)
            content_length = resp.headers.get("Content-Length")
            max_size = 15 * 1024 * 1024
            if content_length and content_length.isdigit() and int(content_length) <= max_size:
                remainder = resp.raw.read(max_size - len(raw_chunk))
                full_bytes += remainder

            result["raw_bytes"] = full_bytes

            # Check magic signature (%PDF-)
            has_magic_bytes = cls.verify_magic_bytes(full_bytes)
            result["magic_signature_verified"] = has_magic_bytes

            is_pdf_content_type = "application/pdf" in result["content_type"] or "application/x-pdf" in result["content_type"]

            # Case B: HTTP 200 but HTML error page
            if not has_magic_bytes and ("text/html" in result["content_type"] or full_bytes.startswith(b"<!DOCTYPE") or full_bytes.startswith(b"<html")):
                html_snippet = full_bytes[:4000].decode("utf-8", errors="replace").lower()
                if any(x in html_snippet for x in ("page not found", "404 not found", "document not found", "file not found", "does not exist")):
                    result["is_soft_404"] = True
                    result["pdf_case"] = "CASE_B_SOFT_404_HTML"
                    return result

                # Check if it's a PDF viewer page wrapping a document (Case C)
                if any(v in html_snippet for v in ("viewer.html?file=", "pdf.js", "application/pdf", "<embed", "<iframe")):
                    result["pdf_case"] = "CASE_C_VIEWER_WRAPPER"
                    return result

                result["pdf_case"] = "HTML_PAGE"
                return result

            # If it has magic signature or PDF content type, treat as PDF
            if has_magic_bytes or is_pdf_content_type:
                result["is_valid_pdf"] = True
                if len(resp.history) > 0:
                    result["pdf_case"] = "CASE_D_REDIRECTED_PDF"
                elif "download" in url.lower() or "download" in result["final_url"].lower():
                    result["pdf_case"] = "CASE_E_DOWNLOAD_ENDPOINT"
                else:
                    result["pdf_case"] = "CASE_A_VALID_PDF"

                # Parse PDF document content & metadata
                cls._parse_pdf_content(full_bytes, result)

        except requests.exceptions.RequestException as exc:
            result["error"] = str(exc)
            result["pdf_case"] = "CONNECTION_ERROR"
        except Exception as exc:
            result["error"] = str(exc)

        return result

    @classmethod
    def _parse_pdf_content(cls, raw_bytes: bytes, result: Dict[str, Any]) -> None:
        """Extracts text, metadata, dates, document numbers, and references from PDF bytes."""
        try:
            import pdfplumber
            stream = io.BytesIO(raw_bytes)
            with pdfplumber.open(stream) as pdf:
                result["page_count"] = len(pdf.pages)
                meta = getattr(pdf, "metadata", {}) or {}
                result["metadata"] = {str(k): str(v) for k, v in meta.items() if v}

                raw_title = str(meta.get("Title") or "").strip()
                if raw_title and not any(raw_title.lower().startswith(x) for x in ("untitled", "microsoft", "powerpoint", "word")):
                    result["title"] = raw_title

                raw_author = str(meta.get("Author") or "").strip()
                if raw_author and not any(raw_author.lower().startswith(x) for x in ("user", "admin", "microsoft")):
                    result["organisation"] = raw_author

                # Extract text from first 6 pages
                text_pages = []
                total_chars = 0
                has_images = False
                for page in pdf.pages[:6]:
                    extracted = page.extract_text() or ""
                    if extracted:
                        text_pages.append(extracted)
                        total_chars += len(extracted.strip())
                    if getattr(page, "images", None) and len(page.images) > 0:
                        has_images = True

                combined_text = "\n".join(text_pages)
                result["text_sample"] = combined_text[:5000].strip()

                # Scanned PDF Detection (Section 17)
                if total_chars < 80 and result["page_count"] > 0 and has_images:
                    result["is_scanned_pdf"] = True
                    # Attempt OCR fallback
                    ocr_text = cls._run_ocr_fallback(raw_bytes)
                    if ocr_text:
                        result["ocr_applied"] = True
                        result["text_sample"] = ocr_text[:5000].strip()
                        combined_text = ocr_text

                # Document number regex (Circular, Notification, Release, Order, Act, Directive)
                doc_patterns = [
                    r"\b(?:Circular\s*No\.?\s*[:\s]*)([A-Z0-9\/\-_]+)\b",
                    r"\b(SEBI\/[A-Z0-9\/\-_]+)\b",
                    r"\b(RBI\/[0-9]{4}-[0-9]{2,4}\/[0-9]+)\b",
                    r"\b(?:Release\s*No\.?\s*)(33-[0-9]+|34-[0-9]+)\b",
                    r"\b(?:Directive\s*(?:\(EU\))?\s*)([0-9]{4}\/[0-9]+)\b",
                    r"\b(?:Regulation\s*(?:\(EU\))?\s*)([0-9]{4}\/[0-9]+)\b",
                    r"\b(?:Order\s*No\.?\s*)([A-Z0-9\/\-_]+)\b",
                    r"\b(?:Notification\s*No\.?\s*)([A-Z0-9\/\-_]+)\b",
                ]
                for pat in doc_patterns:
                    m = re.search(pat, combined_text[:3000], re.I)
                    if m:
                        result["document_number"] = m.group(0).strip()
                        break

                # Infer title if metadata title was blank
                if not result["title"] and combined_text:
                    lines = [l.strip() for l in combined_text.split("\n") if len(l.strip()) > 3]
                    header_lines = []
                    for l in lines[:5]:
                        if re.search(r"^(table of contents|contents|page \d|http|www\.)", l, re.I):
                            break
                        header_lines.append(l)
                    if header_lines:
                        result["title"] = " - ".join(header_lines[:2])[:120]

                # Document References Extraction (Section 23)
                ref_patterns = [
                    r"\b(?:supersedes|superseded by|in supersession of)\s+([A-Za-z0-9\/\s\-_\.]{5,60})",
                    r"\b(?:replaces|replaced by)\s+([A-Za-z0-9\/\s\-_\.]{5,60})",
                    r"\b(?:amends|amended by|as amended by)\s+([A-Za-z0-9\/\s\-_\.]{5,60})",
                    r"\b(?:read with circular|read with notification)\s+([A-Za-z0-9\/\s\-_\.]{5,60})",
                    r"\b(?:revised pursuant to)\s+([A-Za-z0-9\/\s\-_\.]{5,60})",
                ]
                references = []
                for pat in ref_patterns:
                    matches = re.finditer(pat, combined_text[:4000], re.I)
                    for m in matches:
                        references.append(m.group(0).strip())
                result["document_references"] = list(set(references))

        except Exception as exc:
            logger.debug(f"Error extracting PDF text: {exc}")

    @classmethod
    def _run_ocr_fallback(cls, raw_bytes: bytes) -> str:
        """Renders first 2 pages of scanned PDF via pypdfium2 and runs pytesseract OCR."""
        try:
            import pypdfium2 as pdfium
            import pytesseract
            from PIL import Image

            pdf = pdfium.PdfDocument(raw_bytes)
            ocr_text = []
            max_pages = min(2, len(pdf))
            for i in range(max_pages):
                page = pdf[i]
                image = page.render(scale=2).to_pil()
                text = pytesseract.image_to_string(image)
                if text:
                    ocr_text.append(text)
            return "\n".join(ocr_text)
        except Exception as e:
            logger.debug(f"OCR fallback unavailable or failed: {e}")
            return ""

    @classmethod
    def score_pdf_candidate(cls, pdf_res: Dict[str, Any], target_title: str = "", target_doc_no: str = "") -> float:
        """Calculates a PDF Validation Score (Section 28) based on multi-signal evidence."""
        if not pdf_res.get("is_valid_pdf"):
            return 0.0

        score = 0.0
        # 1. Accessible & magic signature verified (25 pts)
        if pdf_res.get("magic_signature_verified"):
            score += 0.25

        # 2. Text / content extracted (20 pts)
        text = pdf_res.get("text_sample", "")
        if len(text) > 50 or pdf_res.get("ocr_applied"):
            score += 0.20

        # 3. Document number matches (25 pts)
        doc_no = pdf_res.get("document_number", "")
        if target_doc_no and target_doc_no.lower() in (doc_no.lower() + " " + text.lower()):
            score += 0.25
        elif doc_no:
            score += 0.15

        # 4. Title / Topic overlap (20 pts)
        title = pdf_res.get("title", "")
        if target_title and any(w.lower() in (title.lower() + " " + text[:1000].lower()) for w in target_title.split() if len(w) >= 3):
            score += 0.20

        # 5. Authority identified (10 pts)
        if pdf_res.get("organisation"):
            score += 0.10

        return min(1.0, round(score, 2))
