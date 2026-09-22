import json
import logging
import os
import re
from typing import Dict, Any, Optional, List

logger = logging.getLogger("web_researcher")


class WebResearcher:
    """AI + Web Research Engine for Regulatory Sources.

    Invoked when local crawling and internal link discovery do not yield
    a current, valid official source. Leverages Gemini / configured LLM
    to suggest candidate authoritative locations and document links.

    CRITICAL RULE (Section 26):
    Outputs from this class are CANDIDATE HYPOTHESES ONLY.
    No candidate is EVER accepted without independent multi-stage verification
    (HTTP + Playwright + PDF signature + Date & Authority check).
    """

    RESEARCH_PROMPT_TEMPLATE = """You are a specialized regulatory intelligence researcher for statutory, securities, and ESG frameworks.

The user needs to locate the official current source or current official PDF for a regulatory document that is either broken, outdated, moved, or access-restricted.

ORIGINAL SOURCE CONTEXT:
- Original URL: {url}
- Page/Doc Title: {title}
- Document / Circular Number: {doc_number}
- Issuing Authority: {authority}
- Jurisdiction: {jurisdiction}
- Context / Description: {description}
- Relevant Extracted Dates: {dates}
- Extracted References: {references}
- Page Text Excerpt: {text_sample}

TASK:
Identify the CURRENT, AUTHORITATIVE, OFFICIAL location of this regulation/standard.
Prefer primary regulatory authority portals (e.g. SEBI, MCA, RBI, EUR-Lex, SEC, FCA, MEE, Gov ministries) and direct official PDFs.
Do NOT suggest generic homepages (e.g. sec.gov root).
Do NOT suggest commercial aggregators (Mondaq, Lexology, LinkedIn, etc.) when the official regulator exists.

Return ONLY a valid JSON object matching this schema:
{{
  "candidate_url": "Direct official URL to current document or official circular page",
  "candidate_pdf_url": "Direct official PDF URL if known, else empty string",
  "candidate_title": "Official title of the document or updated framework",
  "issuing_authority": "Name of the official regulatory body",
  "regulatory_relationship": "One of: SAME_DOCUMENT_MOVED | AMENDED_VERSION | REPLACED_BY_NEWER_CIRCULAR | CURRENT_ENACTED_VERSION | OFFICIAL_REPOSITORY",
  "reasoning": "Concise justification explaining why this is the current official location",
  "search_queries": ["1-3 exact queries that can be used on Google or official site search to find this document"]
}}"""

    def __init__(self, ai_provider: Optional[Any] = None):
        self.ai_provider = ai_provider

    def research_official_source(
        self,
        url: str,
        title: str = "",
        doc_number: str = "",
        authority: str = "",
        jurisdiction: str = "",
        description: str = "",
        dates: str = "",
        references: List[str] = None,
        text_sample: str = "",
    ) -> Dict[str, Any]:
        """Conducts AI-assisted research to formulate official replacement hypotheses.

        Delegates to the configured provider's grounded `research_source`. The provider
        is the single source of truth for which model/key/grounding is used, so test
        (Gemini) and production (Claude) route through the same path.
        """
        context = {
            "url": url,
            "title": title,
            "doc_number": doc_number,
            "authority": authority,
            "jurisdiction": jurisdiction,
            "description": description,
            "dates": dates,
            "references": references or [],
            "text_sample": text_sample,
        }

        # Grounded research via the configured provider (Gemini/Claude/OpenAI).
        if self.ai_provider is not None:
            try:
                res = self.ai_provider.research_source(context)
                if res and res.get("candidate_url"):
                    return res
                # Provider returned no candidate; keep its search_queries for the fallback below.
                if res:
                    return self._with_heuristic_queries(res, title, description, doc_number, authority)
            except Exception as exc:
                logger.debug(f"Provider research_source error: {exc}")

        # No provider (mock/unconfigured): heuristic search-query hints only.
        return self._with_heuristic_queries(
            {
                "candidate_url": "",
                "candidate_pdf_url": "",
                "candidate_title": "",
                "issuing_authority": authority,
                "regulatory_relationship": "",
                "reasoning": "",
                "search_queries": [],
            },
            title, description, doc_number, authority,
        )

    @staticmethod
    def _with_heuristic_queries(result: Dict[str, Any], title: str, description: str,
                                doc_number: str, authority: str) -> Dict[str, Any]:
        """Populate search_queries heuristically only if the provider didn't supply any."""
        if not result.get("search_queries"):
            clean_title = re.sub(r"[^\w\s]", " ", title or description).strip()
            queries = []
            if doc_number:
                queries.append(f"{authority} {doc_number} circular pdf")
            if clean_title:
                queries.append(f"{authority} {clean_title} official")
            result["search_queries"] = queries[:2]
        return result

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end + 1])
            except Exception:
                pass
        return None
