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
    return AiEvaluationResult(
        # Core fields
        classification=data.get("classification", "NEEDS_HUMAN_REVIEW"),
        technical_status=data.get("technical_status", "UNKNOWN"),
        source_authority=data.get("source_authority", "Tier 4"),
        source_organisation=data.get("source_organisation", ""),
        content_relevance=data.get("content_relevance", "unknown"),
        regulatory_status=data.get("regulatory_status", "UNKNOWN"),
        freshness_status=data.get("freshness_status", "UNKNOWN"),
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
        freshness_score=_freshness_status_to_score(data.get("freshness_status", "UNKNOWN")),
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


class OpenAIProvider(_BaseAiProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        if not OPENAI_AVAILABLE:
            raise RuntimeError("openai package is not installed")
        self.client = openai.OpenAI(api_key=api_key)
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
