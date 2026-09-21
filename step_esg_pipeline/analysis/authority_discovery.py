from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

from jurisdictions import JurisdictionRegistry
from analysis.regulatory_identity import RegulatoryIdentity


@dataclass
class DiscoveredCandidate:
    candidate_url: str
    candidate_title: str
    authority: str
    authority_tier: str
    domain: str
    document_type: str = "Guideline / Standard"
    publication_date: str = ""
    effective_date: str = ""
    regulatory_status: str = "UNKNOWN"
    applicability: str = ""
    discovery_level: str = "LEVEL_1_OFFICIAL_AUTHORITY"  # LEVEL_1, LEVEL_2, LEVEL_3, LEVEL_4_AI
    discovery_method: str = ""
    evidence: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OfficialSourceDiscovery:
    """Prioritizes Level 1 (Official Authority) -> Level 2 (Legislation/Gazette) -> Level 3 (Exchange) -> Level 4 (AI Research)."""

    @classmethod
    def discover_candidate(
        cls,
        identity: RegulatoryIdentity,
        discovered_links: List[Dict[str, Any]],
        ai_researcher: Optional[Any] = None,
    ) -> Optional[DiscoveredCandidate]:
        registry = JurisdictionRegistry.get_instance()
        country = identity.country

        # -------------------------------------------------------------
        # Level 1, 2, 3: Scan Discovered On-Site / Crawled Links First
        # -------------------------------------------------------------
        if discovered_links:
            # Sort high relevance first
            sorted_links = sorted(
                discovered_links,
                key=lambda l: (
                    1 if l.get("relevance") == "HIGH RELEVANCE" else 2,
                    0 if l.get("is_pdf_hint") else 1,
                )
            )

            for l in sorted_links:
                url = l.get("url", "")
                if not url or "http" not in url:
                    continue
                domain = urlparse(url).netloc.lower()
                auth_info = registry.find_authority_by_domain(domain)

                # Prioritize Level 1 (Primary Regulator) or Level 2 (Legislation)
                if auth_info:
                    tier = auth_info.get("tier", "")
                    level = "LEVEL_1_OFFICIAL_AUTHORITY"
                    if "LEGISLATION" in tier:
                        level = "LEVEL_2_OFFICIAL_GAZETTE"
                    elif "EXCHANGE" in tier:
                        level = "LEVEL_3_OFFICIAL_EXCHANGE"

                    title = l.get("text") or identity.instrument_name
                    return DiscoveredCandidate(
                        candidate_url=url,
                        candidate_title=title,
                        authority=auth_info["authority"],
                        authority_tier=tier,
                        domain=domain,
                        document_type=identity.instrument_type,
                        discovery_level=level,
                        discovery_method=f"Discovered via authoritative site crawling ({level})",
                        evidence=f"Discovered on official domain '{domain}' with high relevance.",
                    )

        # -------------------------------------------------------------
        # Level 4: AI-Assisted Web Research Hypothesis (Fallback)
        # -------------------------------------------------------------
        if ai_researcher:
            try:
                res = ai_researcher.research_official_source(
                    url="",
                    title=identity.instrument_name,
                    authority=identity.authority,
                    jurisdiction=identity.country,
                    description=f"{identity.instrument_name} {identity.regulatory_topic}",
                    text_sample=f"Jurisdiction: {identity.country}. Regulatory subject: {identity.instrument_name}.",
                )
                cand_url = res.get("candidate_pdf_url") or res.get("candidate_url")
                if cand_url:
                    cand_domain = urlparse(cand_url).netloc.lower()
                    auth_info = registry.find_authority_by_domain(cand_domain)
                    auth_name = auth_info["authority"] if auth_info else identity.authority
                    auth_tier = auth_info["tier"] if auth_info else "TIER_3_SECONDARY"

                    return DiscoveredCandidate(
                        candidate_url=cand_url,
                        candidate_title=res.get("candidate_title", identity.instrument_name),
                        authority=auth_name,
                        authority_tier=auth_tier,
                        domain=cand_domain,
                        document_type=identity.instrument_type,
                        discovery_level="LEVEL_4_AI_RESEARCH",
                        discovery_method="AI-Assisted Web Research Hypothesis",
                        evidence=res.get("reasoning", "Hypothesized official successor via AI web research."),
                    )
            except Exception:
                pass

        return None
