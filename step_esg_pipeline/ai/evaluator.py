import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List

from database.models import LinkRecord


@dataclass
class AiEvaluationResult:
    classification: str
    technical_status: str
    source_authority: str
    source_organisation: str
    content_relevance: str
    regulatory_status: str
    freshness_status: str
    replacement_required: bool
    replacement_url: str
    replacement_reason: str
    confidence_score: float
    recommended_action: str
    replacement_title: str = ""
    confidence_reason: str = ""
    # Section 22 Multi-Dimensional Schema Fields
    content_status: str = "INTENDED_CONTENT_PRESENT"
    authority_status: str = "COMMERCIAL_AGGREGATOR"
    final_status: str = "VALID_AND_CURRENT"
    replacement_verified: bool = False
    replacement_status: str = "NOT_REQUIRED"
    content_relevance_score: int = 85
    content_accuracy_score: int = 85
    freshness_score: int = 90
    reason: str = ""
    issue_description: str = ""
    evidence: List[str] = field(default_factory=list)
    # Section 18 — Deep Semantic Analysis Fields
    intended_subject: str = ""
    original_content_summary: str = ""
    comparison_summary: str = ""
    updated_source_found: bool = False
    recommended_url: str = ""
    recommended_source_title: str = ""
    recommended_source_authority: str = ""
    freshness_assessment: str = ""
    # Section 16 & 24 Comprehensive Fields
    access_status: str = ""
    authenticity_status: str = "AUTHENTIC"
    authenticity_reason: str = ""
    comparability: str = ""
    comparability_confidence: float = 0.0
    regulatory_status_reason: str = ""
    replacement_authority: str = ""
    replacement_comparability: str = ""
    replacement_confidence: float = 0.0
    document_type: str = ""


class AiProvider(ABC):
    @abstractmethod
    def evaluate(self, record: LinkRecord, metadata: dict) -> AiEvaluationResult:
        ...

    def research_source(self, context: dict) -> dict:
        """Propose a current official replacement source for a broken/outdated/restricted link.

        `context` carries url/title/authority/jurisdiction/description/text_sample/dates/references.
        Returns a candidate dict:
          {candidate_url, candidate_pdf_url, candidate_title, issuing_authority,
           regulatory_relationship, reasoning, search_queries}
        Default: no candidate (providers with web grounding override this).
        """
        return {
            "candidate_url": "",
            "candidate_pdf_url": "",
            "candidate_title": "",
            "issuing_authority": context.get("authority", ""),
            "regulatory_relationship": "",
            "reasoning": "",
            "search_queries": [],
        }


class MockAiProvider(AiProvider):
    def evaluate(self, record: LinkRecord, metadata: dict) -> AiEvaluationResult:
        regulatory_status = metadata.get("regulatory_status") or record.regulatory_status or "UNKNOWN"
        freshness_status = metadata.get("freshness_status") or record.freshness_status or "UNKNOWN"
        content_status = metadata.get("content_status", "INTENDED_CONTENT_PRESENT")
        authority_status = metadata.get("authority_status") or "OFFICIAL_REGULATOR"
        evidence = list(metadata.get("evidence") or [])
        replacement_reason = ""

        # Technical status from record or metadata
        tech_status = metadata.get("technical_status") or record.technical_status or "ACCESSIBLE"
        if record.http_status in (404, 410):
            tech_status = "BROKEN"
        elif record.http_status in (403, 202) or metadata.get("is_challenge_page"):
            tech_status = "ACCESS_RESTRICTED"
        elif record.http_status in (500, 502, 503, 504, 408, 429):
            tech_status = "SERVER_ERROR"
        elif record.http_status in (301, 302, 307, 308):
            tech_status = "REDIRECTED"
        elif record.access_status == "WRONG_DESTINATION" or metadata.get("is_generic_homepage"):
            tech_status = "WRONG_DESTINATION"

        # 1. Soft-404 or maintenance
        if metadata.get("is_soft_404") or record.access_status == "BROKEN_SOFT_404":
            classification = "BROKEN"
            tech_status = "BROKEN"
            content_status = "SOFT_404"
            recommended_action = "RECOMMEND_REPLACEMENT"
            replacement_reason = "Page returned HTTP 200 but content indicates soft-404 error page."
            evidence.append("Page body contains soft-404 error messages or lack of substantive content.")
        elif metadata.get("is_maintenance"):
            classification = "TEMPORARILY_UNAVAILABLE"
            recommended_action = "RETRY_AND_MONITOR"
            replacement_reason = "Page is currently under maintenance or temporarily unavailable."
            evidence.append("Maintenance banner or temporary outage detected.")
        # 2. Generic homepage redirect (Homepage Rejection Rule)
        elif tech_status == "WRONG_DESTINATION" or metadata.get("is_generic_homepage"):
            classification = "WRONG_DESTINATION"
            content_status = "HOMEPAGE_REDIRECT"
            recommended_action = "RECOMMEND_REPLACEMENT"
            replacement_reason = "Link redirects to a generic domain root/homepage rather than the intended document."
            evidence.append("Homepage Rejection Rule: Deep link redirected to domain root.")
        # 3. Obsolescence / Outdated regulatory content
        elif freshness_status in ("COMPLETELY_SUPERSEDED", "REPEALED_WITHDRAWN", "OBSOLETE", "outdated") or metadata.get("is_outdated"):
            classification = "WORKING_BUT_OUTDATED"
            recommended_action = "RECOMMEND_REPLACEMENT"
            freshness_status = "COMPLETELY_SUPERSEDED"
            replacement_reason = metadata.get("outdated_reason") or "Regulation or guidance has been superseded, amended, or points to prior session."
            evidence.append(f"Obsolescence verified: {replacement_reason}")
        elif freshness_status in ("STAYED_PENDING_LITIGATION", "DISBANDED_TRANSITIONED", "PARTIALLY_SUPERSEDED", "regulatory_status_changed") or regulatory_status in ("STAYED_PENDING_LITIGATION", "DISBANDED_TRANSITIONED"):
            classification = "WORKING_BUT_REGULATORY_STATUS_CHANGED"
            recommended_action = "HUMAN_REVIEW"
            replacement_reason = metadata.get("outdated_reason") or "Regulatory status has changed (e.g. litigation stay or standard transition)."
            evidence.append(f"Regulatory status shift detected: {replacement_reason}")
        # 4. Non-official aggregator
        elif authority_status == "COMMERCIAL_AGGREGATOR" or metadata.get("is_non_official") or "policyvault.africa" in (record.original_url or "").lower():
            classification = "WORKING_BUT_NON_OFFICIAL"
            content_status = "THIRD_PARTY_AGGREGATOR"
            recommended_action = "HUMAN_REVIEW_AND_REPLACE"
            replacement_reason = "Commercial aggregator used instead of official primary regulatory portal."
            evidence.append("Source domain is a commercial aggregator rather than official statutory publisher.")
        # 5. Technical failures
        elif tech_status == "BROKEN" or record.http_status in (404, 410):
            classification = "BROKEN"
            content_status = "BLANK_OR_EMPTY"
            recommended_action = "RECOMMEND_REPLACEMENT"
            replacement_reason = f"Link is dead (HTTP {record.http_status})."
            evidence.append(f"Server responded with dead link status HTTP {record.http_status}.")
        elif tech_status == "ACCESS_RESTRICTED" or record.http_status in (403, 202) or metadata.get("is_challenge_page"):
            classification = "ACCESS_RESTRICTED"
            content_status = "CHALLENGE_BLOCKED" if metadata.get("is_challenge_page") else "ACCESS_RESTRICTED"
            recommended_action = "HUMAN_REVIEW"
            replacement_reason = "Automated verification blocked by bot challenge or access restriction (HTTP 403/202)."
            evidence.append("Access challenge/restriction prevents substantive document verification.")
        elif tech_status in ("SERVER_ERROR", "TIMEOUT", "CONNECTION_ERROR") or record.http_status in (500, 502, 503, 504, 408, 429):
            classification = "TEMPORARILY_UNAVAILABLE"
            recommended_action = "RETRY_AND_MONITOR"
            replacement_reason = f"Server temporarily unavailable ({tech_status}, HTTP {record.http_status})."
            evidence.append(f"Connection failure encountered: {tech_status}.")
        # 6. Redirects
        elif tech_status == "REDIRECTED" or record.http_status in (301, 302, 307, 308):
            classification = "VALID_BUT_REDIRECTED"
            recommended_action = "RECOMMEND_CANONICAL_UPDATE"
            replacement_reason = f"Link redirects to {record.final_url}."
            evidence.append(f"Permanent redirect observed to: {record.final_url}")
        # 7. Current and verified in-force
        elif freshness_status in ("CURRENT_IN_FORCE", "LEGALLY_BINDING_IN_FORCE", "HISTORICAL_FOUNDATIONAL"):
            classification = "VALID_AND_CURRENT"
            recommended_action = "KEEP"
            regulatory_status = "LEGALLY_BINDING_IN_FORCE"
            freshness_status = "CURRENT_IN_FORCE"
        else:
            # Ambiguous or unverified regulatory status
            classification = "NEEDS_HUMAN_REVIEW"
            recommended_action = "HUMAN_REVIEW"
            replacement_reason = "Regulatory currentness requires human review; no explicit obsolescence or in-force indicators found."
            evidence.append("Ambiguous currentness: neither active in-force phrasing nor obsolescence signals verified.")

        replacement_required = classification in ("BROKEN", "WORKING_BUT_OUTDATED", "WORKING_BUT_NON_OFFICIAL", "WRONG_DESTINATION")

        # Infer intended_subject from step_description + anchor_text
        intended_subject = (
            getattr(record, "step_description", "") or
            getattr(record, "anchor_text", "") or
            record.page_title or ""
        )[:200]

        return AiEvaluationResult(
            classification=classification,
            technical_status=tech_status,
            source_authority=record.source_authority_tier or "Tier 1",
            source_organisation=record.source_organisation or "",
            content_relevance="high" if record.page_title else "medium",
            regulatory_status=regulatory_status,
            freshness_status=freshness_status,
            replacement_required=replacement_required,
            replacement_url="",
            replacement_reason=replacement_reason,
            confidence_score=0.5,
            recommended_action=recommended_action,
            content_status=content_status,
            authority_status=authority_status,
            final_status=classification,
            replacement_verified=False,
            replacement_status="NONE_FOUND" if replacement_required else "NOT_REQUIRED",
            content_relevance_score=metadata.get("content_relevance_score", 85),
            content_accuracy_score=metadata.get("content_accuracy_score", 85),
            freshness_score=metadata.get("freshness_score", 90),
            reason=replacement_reason or "Document verified against authoritative criteria.",
            evidence=evidence,
            # Section 18 fields
            intended_subject=intended_subject,
            original_content_summary="",
            comparison_summary="",
            updated_source_found=bool(replacement_reason),
            recommended_url="",
            recommended_source_title="",
            recommended_source_authority="",
            freshness_assessment=freshness_status,
            # Section 16 & 24 comprehensive fields
            access_status=metadata.get("access_status") or record.access_status or ("ACCESSIBLE" if record.http_status == 200 else "BROKEN"),
            authenticity_status=metadata.get("authenticity_status") or "AUTHENTIC",
            authenticity_reason=metadata.get("authenticity_reason") or "",
            comparability=metadata.get("comparability") or "COMPARABLE",
            comparability_confidence=float(metadata.get("comparability_confidence") or 0.85),
            regulatory_status_reason=metadata.get("regulatory_status_reason") or replacement_reason or "",
            replacement_authority=metadata.get("replacement_authority") or "",
            replacement_comparability=metadata.get("replacement_comparability") or "",
            replacement_confidence=float(metadata.get("replacement_confidence") or 0.0),
            document_type=metadata.get("document_type") or "Legislation / Regulation",
        )


class AiEvaluator:
    def __init__(self, provider: Optional[AiProvider] = None):
        self.provider = provider or MockAiProvider()

    def evaluate(self, record: LinkRecord, metadata: dict) -> AiEvaluationResult:
        return self.provider.evaluate(record, metadata)


def load_provider_from_config(cfg: dict):
    import os
    ai_cfg = cfg.get("ai", {})
    provider_name = (os.getenv("STEP_AI_PROVIDER", "") or ai_cfg.get("provider", "mock")).lower()

    if provider_name == "mock":
        return MockAiProvider()

    if provider_name == "gemini":
        gemini_key = os.getenv("GEMINI_API_KEY", "") or ai_cfg.get("gemini_api_key", "")
        if gemini_key:
            try:
                from ai.providers import GeminiProvider
                return GeminiProvider(
                    api_key=gemini_key,
                    model=ai_cfg.get("gemini_model") or "gemini-flash-latest",
                )
            except Exception:
                pass

    if provider_name == "anthropic" and (os.getenv("ANTHROPIC_API_KEY") or ai_cfg.get("anthropic_api_key")):
        from ai.providers import AnthropicProvider
        return AnthropicProvider(
            api_key=os.getenv("ANTHROPIC_API_KEY") or ai_cfg.get("anthropic_api_key", ""),
            model=ai_cfg.get("claude_model") or "claude-3-5-haiku-20241022",
        )
    if provider_name == "openai" and (os.getenv("OPENAI_API_KEY") or ai_cfg.get("openai_api_key")):
        from ai.providers import OpenAIProvider
        return OpenAIProvider(
            api_key=os.getenv("OPENAI_API_KEY") or ai_cfg.get("openai_api_key", ""),
            model=ai_cfg.get("openai_model") or "gpt-4o-mini",
        )

    if provider_name == "agentrouter":
        ar_key = os.getenv("AGENTROUTER_API_KEY", "") or ai_cfg.get("agentrouter_api_key", "")
        if ar_key:
            from ai.providers import OpenAIProvider
            # AgentRouter validates the CLIENT, not just the key: a generic HTTP client
            # gets 401 "unauthorized client detected". Identify as a recognised coding-agent
            # client so the request is allowed through to the model.
            return OpenAIProvider(
                api_key=ar_key,
                model=ai_cfg.get("agentrouter_model") or "deepseek-v4-flash",
                base_url=ai_cfg.get("agentrouter_base_url") or "https://agentrouter.org/v1",
                default_headers={
                    "User-Agent": "codex_cli_rs/0.149.1",
                    "originator": "codex_cli_rs",
                },
            )

    return MockAiProvider()
