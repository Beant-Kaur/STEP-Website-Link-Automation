import json
import os
from typing import Any, Optional

from ai.evaluator import AiEvaluationResult, AiProvider

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    # Prefer the new google-genai SDK (google.genai)
    from google import genai as google_genai
    from google.genai import types as genai_types
    GEMINI_AVAILABLE = True
    GEMINI_SDK_VERSION = "new"
except ImportError:
    try:
        # Fallback to legacy google-generativeai SDK
        import google.generativeai as google_genai
        GEMINI_AVAILABLE = True
        GEMINI_SDK_VERSION = "legacy"
        genai_types = None
    except ImportError:
        GEMINI_AVAILABLE = False
        GEMINI_SDK_VERSION = None
        google_genai = None
        genai_types = None


# ------------------------------------------------------------------
# Section 18 System Prompt — full 20-field output schema
# Instructs AI to perform deep semantic analysis of the document text
# ------------------------------------------------------------------
SYSTEM_PROMPT = """You are an expert ESG regulatory link intelligence analyst. Your role is NOT just to check if a URL works — it is to deeply understand what the linked document contains, whether the content is current and authoritative, and whether a better official source exists.

You will be given:
1. The URL and its technical status
2. Up to 4,000 characters of the ACTUAL DOCUMENT TEXT extracted from the page
3. Metadata: title, dates, authority, section context, anchor text

Your task is to:
A. Understand what this document is about (intended_subject, original_content_summary)
B. Assess whether this is still the current, applicable, in-force version of the regulation/standard
C. Identify if it has been superseded, repealed, stayed, amended, or expired
D. If outdated, suggest the most authoritative current official replacement URL (must be real, verifiable)
E. If a candidate replacement is provided, compare both documents and explain differences

CRITICAL RULES:
- HTTP 200 does NOT mean the content is current or relevant
- Do NOT invent or guess replacement URLs; only suggest if highly confident
- Do NOT accept a generic homepage (e.g. sec.gov or sebi.gov.in root) as a valid replacement
- A newer secondary article is NOT better than an older official regulation still in force
- If evidence is insufficient, set confidence_score below 0.50 and use NEEDS_HUMAN_REVIEW

Return ONLY valid JSON (no markdown, no explanation text outside JSON) matching this exact schema:
{
  "intended_subject": "Short phrase: what regulation/framework/topic this link is supposed to represent",
  "original_content_summary": "2-3 sentence plain-English summary of what the document actually contains",
  "freshness_assessment": "Plain explanation: is this document current, superseded, stayed, expired?",
  "classification": "One of: VALID_AND_CURRENT|CURRENT_WITH_AMENDMENTS|WORKING_BUT_OUTDATED|WORKING_BUT_REGULATORY_STATUS_CHANGED|WORKING_BUT_NON_OFFICIAL|VALID_BUT_REDIRECTED|BROKEN|BROKEN_SOFT_404|ACCESS_RESTRICTED|WRONG_DESTINATION|NON_OFFICIAL|TEMPORARILY_UNAVAILABLE|NEEDS_HUMAN_REVIEW",
  "regulatory_status": "One of: LEGALLY_BINDING_IN_FORCE|CURRENT_WITH_AMENDMENTS|STAYED_PENDING_LITIGATION|DISBANDED_TRANSITIONED|CONSULTATION_DRAFT|PARTIALLY_SUPERSEDED|COMPLETELY_SUPERSEDED|HISTORICAL_FOUNDATIONAL|REPEALED_WITHDRAWN|EXPIRED|UNKNOWN",
  "freshness_status": "One of: CURRENT_IN_FORCE|CURRENT_WITH_AMENDMENTS|PARTIALLY_SUPERSEDED|COMPLETELY_SUPERSEDED|STAYED_PENDING_LITIGATION|DISBANDED_TRANSITIONED|CONSULTATION_DRAFT|HISTORICAL_FOUNDATIONAL|REPEALED_WITHDRAWN|UNKNOWN",
  "content_relevance": "high|medium|low|unknown",
  "content_accuracy_score": 0,
  "updated_source_found": false,
  "recommended_url": "Only include if highly confident this is the current official source; empty string otherwise",
  "recommended_source_title": "Title of the recommended source",
  "recommended_source_authority": "Authority/organisation of the recommended source",
  "comparison_summary": "If candidate replacement text provided: explain key differences between old and new. Otherwise empty string.",
  "confidence_score": 0.0,
  "technical_status": "ACCESSIBLE|ACCESS_RESTRICTED|BROKEN|TIMEOUT|SERVER_ERROR|REDIRECTED|UNKNOWN",
  "source_authority": "Tier 1|Tier 2|Tier 3|Tier 4",
  "source_organisation": "Name of issuing organisation",
  "replacement_required": false,
  "replacement_reason": "Plain explanation of why a replacement is needed, or empty string",
  "recommended_action": "One of: KEEP|RECOMMEND_CANONICAL_UPDATE|RECOMMEND_REPLACEMENT|RETRY_AND_MONITOR|HUMAN_REVIEW|HUMAN_REVIEW_AND_REPLACE",
  "evidence": ["Array of concise evidence strings supporting the decision"]
}"""


RESEARCH_PROMPT = """You are a regulatory intelligence researcher for statutory, securities, and ESG frameworks.

Locate the CURRENT, AUTHORITATIVE, OFFICIAL source for a regulatory document that is broken, outdated, moved, or access-restricted. Use web search to ground your answer in real current results — do NOT rely on memory alone.

Prefer primary regulatory authority portals and direct official PDFs. Do NOT suggest generic homepages (e.g. sec.gov root). Do NOT suggest commercial aggregators (Mondaq, Lexology, LinkedIn) when the official regulator exists.

ORIGINAL SOURCE CONTEXT:
- Original URL: {url}
- Title: {title}
- Document/Circular Number: {doc_number}
- Issuing Authority: {authority}
- Jurisdiction: {jurisdiction}
- Description: {description}
- Relevant Dates: {dates}
- References: {references}
- Page Text Excerpt: {text_sample}

Return ONLY a valid JSON object (no markdown) matching this schema:
{{
  "candidate_url": "Direct official URL to the current document or official page",
  "candidate_pdf_url": "Direct official PDF URL if known, else empty string",
  "candidate_title": "Official title of the document or updated framework",
  "issuing_authority": "Name of the official regulatory body",
  "regulatory_relationship": "One of: SAME_DOCUMENT_MOVED | AMENDED_VERSION | REPLACED_BY_NEWER_CIRCULAR | CURRENT_ENACTED_VERSION | OFFICIAL_REPOSITORY",
  "reasoning": "Concise justification citing the search results",
  "search_queries": ["1-3 queries you used"]
}}"""


def _build_research_prompt(context: dict) -> str:
    refs = context.get("references") or []
    return RESEARCH_PROMPT.format(
        url=context.get("url", ""),
        title=context.get("title", "") or "Unknown",
        doc_number=context.get("doc_number", "") or "None specified",
        authority=context.get("authority", "") or "Official Regulator",
        jurisdiction=context.get("jurisdiction", "") or "Global / National",
        description=context.get("description", "") or "",
        dates=context.get("dates", "") or "",
        references=", ".join(refs) if refs else "None detected",
        text_sample=(context.get("text_sample", "") or "")[:2500],
    )


def _is_quota_error(exc: Exception) -> bool:
    """True for 429 / RESOURCE_EXHAUSTED (e.g. Search grounding not on the key's tier)."""
    s = str(exc)
    return "429" in s or "RESOURCE_EXHAUSTED" in s or "quota" in s.lower()


def _empty_candidate(context: dict) -> dict:
    return {
        "candidate_url": "",
        "candidate_pdf_url": "",
        "candidate_title": "",
        "issuing_authority": context.get("authority", ""),
        "regulatory_relationship": "",
        "reasoning": "",
        "search_queries": [],
    }


def _extract_json(text: str) -> dict:
    """Extract JSON from AI response text, handling markdown code fences."""
    # Try stripping markdown code fences
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last fence lines
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start: end + 1])
        except json.JSONDecodeError:
            pass
    return {}


def _parse_common(data: dict) -> AiEvaluationResult:
    """Convert a parsed AI JSON response into AiEvaluationResult with all Section 18 fields."""
    classification = data.get("classification", "NEEDS_HUMAN_REVIEW")
    reg_status = data.get("regulatory_status", "UNKNOWN")
    fresh_status = data.get("freshness_status", "UNKNOWN")
    # A VALID_AND_CURRENT verdict inherently means current & in-force. Models often give
    # the top-line classification without filling the granular reg/freshness sub-fields,
    # leaving them UNKNOWN — which downstream caps confidence at 0.55 and forces every
    # current link into MANUAL_REVIEW. Make the sub-fields consistent with the verdict.
    if classification in ("VALID_AND_CURRENT", "CURRENT_IN_FORCE"):
        if reg_status == "UNKNOWN" or not reg_status:
            reg_status = "CURRENT_IN_FORCE"
        if fresh_status == "UNKNOWN" or not fresh_status:
            fresh_status = "CURRENT_IN_FORCE"
    return AiEvaluationResult(
        # Core fields
        classification=classification,
        technical_status=data.get("technical_status", "UNKNOWN"),
        source_authority=data.get("source_authority", "Tier 4"),
        source_organisation=data.get("source_organisation", ""),
        content_relevance=data.get("content_relevance", "unknown"),
        regulatory_status=reg_status,
        freshness_status=fresh_status,
        replacement_required=bool(data.get("replacement_required", False)),
        replacement_url=data.get("recommended_url", "") or data.get("replacement_url", ""),
        replacement_reason=data.get("replacement_reason", ""),
        confidence_score=min(1.0, max(0.0, float(data.get("confidence_score", 0.0) or 0.0))),
        recommended_action=data.get("recommended_action", "HUMAN_REVIEW"),
        # Section 22 fields
        content_status="SOFT_404" if data.get("classification") == "BROKEN_SOFT_404" else "INTENDED_CONTENT_PRESENT",
        authority_status=_tier_to_authority_status(data.get("source_authority", "Tier 4")),
        final_status=data.get("classification", "NEEDS_HUMAN_REVIEW"),
        replacement_verified=False,
        replacement_status="NONE_FOUND" if data.get("replacement_required") else "NOT_REQUIRED",
        content_relevance_score=int(data.get("content_accuracy_score", 0) or 0),
        content_accuracy_score=int(data.get("content_accuracy_score", 0) or 0),
        freshness_score=_freshness_status_to_score(fresh_status),
        reason=data.get("replacement_reason", "") or data.get("freshness_assessment", ""),
        evidence=list(data.get("evidence", [])),
        # Section 18 — Deep Semantic Analysis Fields
        intended_subject=data.get("intended_subject", ""),
        original_content_summary=data.get("original_content_summary", ""),
        comparison_summary=data.get("comparison_summary", ""),
        updated_source_found=bool(data.get("updated_source_found", False)),
        recommended_url=data.get("recommended_url", ""),
        recommended_source_title=data.get("recommended_source_title", ""),
        recommended_source_authority=data.get("recommended_source_authority", ""),
        freshness_assessment=data.get("freshness_assessment", ""),
        replacement_title=data.get("recommended_source_title", ""),
        # Section 16 & 24 Comprehensive Fields
        access_status=data.get("access_status", ""),
        authenticity_status=data.get("authenticity_status", "AUTHENTIC"),
        authenticity_reason=data.get("authenticity_reason", ""),
        comparability=data.get("comparability", ""),
        comparability_confidence=float(data.get("comparability_confidence", 0.0) or 0.0),
        regulatory_status_reason=data.get("regulatory_status_reason", "") or data.get("freshness_assessment", ""),
        replacement_authority=data.get("recommended_source_authority", ""),
        replacement_comparability=data.get("replacement_comparability", ""),
        replacement_confidence=float(data.get("replacement_confidence", 0.0) or 0.0),
        document_type=data.get("document_type", ""),
    )


def _tier_to_authority_status(tier: str) -> str:
    mapping = {
        "Tier 1": "OFFICIAL_REGULATOR",
        "Tier 2": "STANDARDS_BODY",
        "Tier 3": "INSTITUTIONAL",
        "Tier 4": "COMMERCIAL_AGGREGATOR",
    }
    return mapping.get(tier, "COMMERCIAL_AGGREGATOR")


def _freshness_status_to_score(status: str) -> int:
    mapping = {
        "CURRENT_IN_FORCE": 90,
        "CURRENT_WITH_AMENDMENTS": 75,
        "HISTORICAL_FOUNDATIONAL": 70,
        "STAYED_PENDING_LITIGATION": 50,
        "DISBANDED_TRANSITIONED": 45,
        "CONSULTATION_DRAFT": 40,
        "PARTIALLY_SUPERSEDED": 35,
        "COMPLETELY_SUPERSEDED": 15,
        "REPEALED_WITHDRAWN": 10,
        "EXPIRED": 5,
        "UNKNOWN": 60,
    }
    return mapping.get(status, 60)


class _BaseAiProvider(AiProvider):
    def _build_user_prompt(self, record: Any, metadata: dict) -> str:
        text_sample = (metadata.get("text_sample") or "").strip()
        # Cap to 4,000 chars to avoid token overflow
        if len(text_sample) > 4000:
            text_sample = text_sample[:4000] + "\n[... truncated for token limit ...]"

        # Gather candidate replacement text if available
        candidate_text = (metadata.get("candidate_text") or "").strip()
        candidate_section = ""
        if candidate_text:
            if len(candidate_text) > 2000:
                candidate_text = candidate_text[:2000] + "\n[... candidate truncated ...]"
            candidate_section = f"\n\n=== CANDIDATE REPLACEMENT DOCUMENT TEXT ===\n{candidate_text}"

        prompt = f"""=== LINK RECORD ===
Link ID: {getattr(record, 'link_id', '')}
Course Section / Anchor Text: {getattr(record, 'step_description', '') or getattr(record, 'anchor_text', '')}
Section Heading: {getattr(record, 'section_heading', '')}

=== TECHNICAL STATUS ===
Original URL: {getattr(record, 'original_url', '')}
Final URL: {getattr(record, 'final_url', '')}
HTTP Status: {getattr(record, 'http_status', None)}
Technical Status: {getattr(record, 'technical_status', '')}
Redirect Status: {getattr(record, 'redirect_status', '')}
Content Type: {metadata.get('content_type', '')}

=== DOCUMENT IDENTITY ===
Page Title: {getattr(record, 'page_title', '')}
Source Organisation: {getattr(record, 'source_organisation', '')}
Source Domain: {getattr(record, 'source_domain', '')}
Authority Tier: {getattr(record, 'source_authority_tier', '')}
Publication Date: {getattr(record, 'publication_date', '')}
Effective Date: {metadata.get('effective_date', '')}
Amendment Date: {metadata.get('amendment_date', '')}
Version: {getattr(record, 'version', '')}
Document Number: {metadata.get('document_number', '')}
Headings Found: {'; '.join(metadata.get('headings', [])[:5])}
Repeal Signals: {'; '.join(metadata.get('repeal_signals', [])[:5])}

=== PRELIMINARY ANALYSIS ===
Pre-computed Freshness Status: {getattr(record, 'freshness_status', '') or metadata.get('freshness_status', '')}
Pre-computed Regulatory Status: {getattr(record, 'regulatory_status', '') or metadata.get('regulatory_status', '')}
Pre-computed Relevance Score: {metadata.get('content_relevance_score', '')}
Is Challenge Page: {metadata.get('is_challenge_page', False)}
Is Soft 404: {metadata.get('is_soft_404', False)}
Is Non-Official: {metadata.get('is_non_official', False)}

=== EXTRACTED DOCUMENT TEXT (up to 4,000 chars) ===
{text_sample if text_sample else '[No substantive text could be extracted — access restricted, empty page, or bot challenge]'}
{candidate_section}"""
        return prompt.strip()


class AnthropicProvider(_BaseAiProvider):
    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-20241022") -> None:
        if not ANTHROPIC_AVAILABLE:
            raise RuntimeError("anthropic package is not installed")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def evaluate(self, record: Any, metadata: dict) -> AiEvaluationResult:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": self._build_user_prompt(record, metadata)}],
        )
        text = response.content[0].text
        data = _extract_json(text)
        return _parse_common(data)

    def research_source(self, context: dict) -> dict:
        """Propose a replacement source using Claude's server-side web_search tool.

        Requires an anthropic SDK new enough to support the web_search_20250305 tool.
        Falls back to an empty candidate (→ heuristic queries downstream) on older SDKs.
        """
        prompt = _build_research_prompt(context)
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
                tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
            )
            # Concatenate any text blocks from the (tool-augmented) response
            text = "".join(
                getattr(block, "text", "") for block in response.content
                if getattr(block, "type", "") == "text"
            )
        except Exception as exc:
            cand = _empty_candidate(context)
            cand["reasoning"] = f"Claude web_search unavailable (SDK/tool): {exc}"
            return cand

        data = _extract_json(text)
        if not data:
            return _empty_candidate(context)
        base = _empty_candidate(context)
        base.update({k: data[k] for k in base if k in data})
        return base


class OpenAIProvider(_BaseAiProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str = "",
                 default_headers: Optional[dict] = None) -> None:
        if not OPENAI_AVAILABLE:
            raise RuntimeError("openai package is not installed")
        # base_url lets this class target any OpenAI-compatible gateway (e.g. AgentRouter).
        # default_headers lets a gateway that does client-fingerprint validation
        # (e.g. AgentRouter) recognise us as an allowed client — key auth alone isn't enough.
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        if default_headers:
            client_kwargs["default_headers"] = default_headers
        self.client = openai.OpenAI(**client_kwargs)
        self.model = model

    def evaluate(self, record: Any, metadata: dict) -> AiEvaluationResult:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self._build_user_prompt(record, metadata)},
            ],
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content or "{}"
        data = _extract_json(text)
        return _parse_common(data)

    # Tool the model can call to ground its answer in real search results. OpenAI-compatible
    # gateways (AgentRouter/DeepSeek) have no server-side browsing, but they DO support
    # function calling — so we expose web_search and execute it ourselves.
    _SEARCH_TOOL = [{
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for the current official source of a regulation. "
                           "Returns a list of {title, url, snippet}. Call this before answering.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"],
            },
        },
    }]

    def research_source(self, context: dict) -> dict:
        """Propose a replacement source, GROUNDED via a web_search tool the model calls.

        DeepSeek/OpenAI-compatible models can't browse but support function calling: the
        model requests web_search, we run it (DuckDuckGo, no key), feed results back, and
        it returns a candidate grounded in real results. Falls back to ungrounded answering
        if the search backend is unavailable. Every candidate still passes validate_candidate().
        """
        import json as _json
        from ai.web_search import web_search
        messages = [{"role": "user", "content": _build_research_prompt(context)}]
        text = ""
        grounded = False
        try:
            # Bounded tool-calling loop: allow several rounds of search. The model is
            # non-deterministic about how many searches it runs, so if it's still calling
            # tools when the budget runs out, force a final answer with tools disabled.
            MAX_ROUNDS = 6
            for round_i in range(MAX_ROUNDS):
                last_round = round_i == MAX_ROUNDS - 1
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self._SEARCH_TOOL,
                    tool_choice="none" if last_round else "auto",
                )
                msg = resp.choices[0].message
                tool_calls = getattr(msg, "tool_calls", None)
                if not tool_calls:
                    text = msg.content or ""
                    break
                # Record the assistant's tool request, then answer each call.
                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {"id": tc.id, "type": "function",
                         "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                        for tc in tool_calls
                    ],
                })
                for tc in tool_calls:
                    try:
                        args = _json.loads(tc.function.arguments or "{}")
                    except Exception:
                        args = {}
                    results = web_search(args.get("query", ""))
                    if results:
                        grounded = True
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": _json.dumps(results)[:4000],
                    })
        except Exception as exc:
            cand = _empty_candidate(context)
            cand["reasoning"] = f"OpenAI-compatible research unavailable: {exc}"
            return cand

        data = _extract_json(text)
        if not data:
            return _empty_candidate(context)
        base = _empty_candidate(context)
        base.update({k: data[k] for k in base if k in data})
        if not grounded and base.get("reasoning"):
            base["reasoning"] = "[UNGROUNDED — search returned nothing] " + base["reasoning"]
        return base


class GeminiProvider(_BaseAiProvider):
    def __init__(self, api_key: str, model: str = "gemini-flash-latest") -> None:
        if not GEMINI_AVAILABLE:
            raise RuntimeError(
                "Gemini SDK is not installed. Run: pip install google-genai>=1.0.0"
            )
        self.api_key = api_key
        self.model_name = model
        self._sdk = GEMINI_SDK_VERSION

        if GEMINI_SDK_VERSION == "new":
            # google-genai >= 1.0 SDK
            self._client = google_genai.Client(api_key=api_key)
        else:
            # Legacy google-generativeai SDK (fallback)
            google_genai.configure(api_key=api_key)
            self._legacy_model = google_genai.GenerativeModel(
                model_name=model,
                system_instruction=SYSTEM_PROMPT,
            )

    def evaluate(self, record: Any, metadata: dict) -> AiEvaluationResult:
        user_prompt = self._build_user_prompt(record, metadata)
        try:
            if self._sdk == "new":
                # New google.genai SDK
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=user_prompt,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.1,
                        max_output_tokens=1500,
                        response_mime_type="application/json",
                    ),
                )
                text = response.text or ""
            else:
                # Legacy SDK
                response = self._legacy_model.generate_content(
                    user_prompt,
                    generation_config={
                        "temperature": 0.1,
                        "max_output_tokens": 1500,
                        "response_mime_type": "application/json",
                    },
                )
                text = getattr(response, "text", "") or ""
        except Exception as exc:
            return self._fallback_result(record, metadata, reason=str(exc))

        data = _extract_json(text)
        if not data:
            return self._fallback_result(record, metadata, reason="Gemini returned unparseable response")

        result = _parse_common(data)
        if result.original_content_summary:
            result.confidence_reason = (
                f"[Gemini {self.model_name}] {result.freshness_assessment or result.original_content_summary[:120]}"
            )
        return result

    def research_source(self, context: dict) -> dict:
        """Propose a replacement source, grounded in real Google Search results.

        If Search grounding is unavailable on the key's tier (429 RESOURCE_EXHAUSTED),
        degrade to an UNGROUNDED call so the pipeline still gets a candidate. Ungrounded
        candidates come from model knowledge and MUST still pass validate_candidate().
        """
        prompt = _build_research_prompt(context)
        text = ""
        grounded = True
        try:
            text = self._research_call(prompt, use_search=True)
        except Exception as exc:
            if _is_quota_error(exc):
                # Grounding quota exhausted — retry without the search tool.
                grounded = False
                try:
                    text = self._research_call(prompt, use_search=False)
                except Exception as exc2:
                    cand = _empty_candidate(context)
                    cand["reasoning"] = f"Gemini research unavailable (ungrounded retry failed): {exc2}"
                    return cand
            else:
                cand = _empty_candidate(context)
                cand["reasoning"] = f"Gemini research unavailable: {exc}"
                return cand

        data = _extract_json(text)
        if not data:
            return _empty_candidate(context)
        base = _empty_candidate(context)
        base.update({k: data[k] for k in base if k in data})
        if not grounded:
            base["reasoning"] = "[UNGROUNDED — no web search] " + (base.get("reasoning") or "")
        return base

    def _research_call(self, prompt: str, use_search: bool) -> str:
        """One research generation, optionally with Google Search grounding."""
        if self._sdk == "new":
            cfg_kwargs = {"temperature": 0.1}
            if use_search:
                cfg_kwargs["tools"] = [genai_types.Tool(google_search=genai_types.GoogleSearch())]
            response = self._client.models.generate_content(
                model=self.model_name, contents=prompt,
                config=genai_types.GenerateContentConfig(**cfg_kwargs),
            )
            return response.text or ""
        # Legacy SDK
        model = google_genai.GenerativeModel(
            model_name=self.model_name,
            tools="google_search_retrieval" if use_search else None,
        )
        response = model.generate_content(prompt)
        return getattr(response, "text", "") or ""

    @staticmethod
    def _fallback_result(record: Any, metadata: dict, reason: str) -> AiEvaluationResult:
        """Return a safe low-confidence result when Gemini call fails."""
        from ai.evaluator import MockAiProvider
        mock = MockAiProvider()
        result = mock.evaluate(record, metadata)
        result.confidence_score = min(result.confidence_score, 0.35)
        result.evidence.append(f"Gemini analysis unavailable: {reason}")
        result.confidence_reason = f"Gemini unavailable — using rule-based fallback: {reason[:120]}"
        result.final_status = result.classification
        return result
