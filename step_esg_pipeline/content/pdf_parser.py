import io
import re
from typing import Any, Optional


class PdfParser:
    @staticmethod
    def parse(source: Any) -> dict:
        try:
            import pdfplumber
        except ImportError:
            return {"error": "pdfplumber not installed"}

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
            "is_pdf": True,
        }

        stream: Any = source
        if isinstance(source, bytes):
            stream = io.BytesIO(source)

        try:
            with pdfplumber.open(stream) as pdf:
                result["page_count"] = len(pdf.pages)
                meta = getattr(pdf, "metadata", {}) or {}

                raw_title = str(meta.get("Title") or "").strip()
                generic_titles = ("microsoft", "untitled", "powerpoint", "word", "template", "esg template", "presentation", "slide 1")
                if raw_title and not any(raw_title.lower() == x or raw_title.lower().startswith(x) for x in generic_titles):
                    result["title"] = raw_title

                raw_author = str(meta.get("Author") or "").strip()
                if raw_author and not any(raw_author.lower().startswith(x) for x in ("microsoft", "user", "admin")):
                    result["organisation"] = raw_author

                text = ""
                for page in pdf.pages[:5]:
                    extracted = page.extract_text() or ""
                    if extracted:
                        text += extracted + "\n"

                result["text_sample"] = text[:5000].strip()

                # Infer title if metadata title was empty or poor
                if not result["title"] and text:
                    lines = [line.strip() for line in text.split("\n") if len(line.strip()) > 3]
                    heading_parts = []
                    for line in lines[:4]:
                        if re.search(r"^(table of contents|contents|page \d|http|www\.)", line, re.I):
                            break
                        heading_parts.append(line)
                    if heading_parts:
                        result["title"] = " - ".join(heading_parts[:2])[:120]

                # Document number regex (Circular / Release / Directive / Decision / Act)
                doc_patterns = [
                    r"\b(?:Circular\s*No\.?\s*)([A-Z0-9\/\-_]+)\b",
                    r"\b(SEBI\/HO\/[A-Z0-9\/\-_]+)\b",
                    r"\b(?:Release\s*No\.?\s*)(33-[0-9]+|34-[0-9]+)\b",
                    r"\b(?:Directive\s*(?:\(EU\))?\s*)([0-9]{4}\/[0-9]+)\b",
                    r"\b(?:Regulation\s*(?:\(EU\))?\s*)([0-9]{4}\/[0-9]+)\b",
                    r"\b(?:Decision\s*(?:no\.?|No\.?)\s*)([0-9\/\(\)A-Za-z\-]+)\b",
                ]
                for pat in doc_patterns:
                    match = re.search(pat, text[:2000], re.I)
                    if match:
                        result["document_number"] = match.group(0).strip()
                        break

                # Extract publication date
                date_patterns = [
                    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+(?:19|20)\d{2}\b",
                    r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(?:19|20)\d{2}\b",
                    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(?:19|20)\d{2}\b",
                    r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b",
                ]
                for pat in date_patterns:
                    match = re.search(pat, text[:2500], re.I)
                    if match:
                        result["publication_date"] = match.group(0).strip()
                        break

                # Extract effective date
                eff_patterns = [
                    r"\b(?:effective from|applicable from|entry into force|in force from)\s*[:\-]?\s*([0-9]{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(?:19|20)\d{2})\b",
                    r"\b(?:effective from|applicable from|entry into force|in force from)\s*[:\-]?\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\b",
                ]
                for pat in eff_patterns:
                    match = re.search(pat, text[:3000], re.I)
                    if match:
                        result["effective_date"] = match.group(1).strip()
                        break

                # Version regex
                ver_match = re.search(r"\b(?:version|v\.|ver\.)\s*([0-9]+(?:\.[0-9]+)*)\b", text[:2000], re.I)
                if ver_match:
                    result["version"] = ver_match.group(0).strip()

                # Repeal and amendment signals
                repeal_signals = [
                    r"\b(repealed by|superseded by|withdrawn by|replaced by directive|replaced by regulation)\b",
                    r"\b(no longer in force|ceased to have effect|this standard has been replaced)\b",
                ]
                for s in repeal_signals:
                    found = re.findall(s, text[:3000], re.I)
                    result["repeal_signals"].extend(found)
                result["repeal_signals"] = list(set(result["repeal_signals"]))

                amendment_signals = [
                    r"\b(amended by|amended on|last amended|consolidated version)\b",
                ]
                for s in amendment_signals:
                    found = re.findall(s, text[:3000], re.I)
                    result["amendment_references"].extend(found)
                result["amendment_references"] = list(set(result["amendment_references"]))

        except Exception as exc:
            result["error"] = str(exc)

        return result
