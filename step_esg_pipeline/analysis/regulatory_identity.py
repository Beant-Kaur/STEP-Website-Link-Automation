import re
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

from jurisdictions import JurisdictionRegistry


INSTRUMENT_TYPE_PATTERNS = [
    (r"\b(?:consultation\s*paper|discussion\s*paper|exposure\s*draft|proposed\s*rule|draft\s*guidelines?|draft)\b", "Consultation / Draft"),
    (r"\b(?:directive)\b", "Directive"),
    (r"\b(?:delegated\s*regulation)\b", "Delegated Regulation"),
    (r"\b(?:regulation|statutory\s*instrument)\b", "Regulation"),
    (r"\b(?:act\s*of\s*(?:parliament|the\s*national\s*assembly)|companies\s*act|environment\s*act|bill)\b", "Act / Legislation"),
    (r"\b(?:circular|master\s*circular|notification)\b", "Circular"),
    (r"\b(?:guidelines?|guidance|code|practice\s*note|framework|standards?)\b", "Guideline / Standard"),
    (r"\b(?:measures|provisions|rules?|rulebook)\b", "Rules / Measures"),
    (r"\b(?:decree-law|decree|executive\s*bylaws?|resolution)\b", "Decree / Bylaws"),
    (r"\b(?:policy\s*statement|recommendation)\b", "Policy / Recommendation"),
]

REGULATED_POPULATION_PATTERNS = [
    (r"\b(?:listed\s*(?:companies|issuers|entities)|publicly\s*traded\s*companies|issuers)\b", "Listed Companies / Issuers"),
    (r"\b(?:asset\s*managers|insurers|banks|financial\s*institutions|credit\s*institutions)\b", "Financial Institutions / Asset Managers"),
    (r"\b(?:large\s*undertakings|public-interest\s*entities|large\s*companies)\b", "Large Enterprises / PIEs"),
    (r"\b(?:smes|small\s*and\s*medium(?:-sized)?\s*enterprises)\b", "SMEs"),
    (r"\b(?:all\s*(?:companies|enterprises|commercial\s*entities))\b", "All Commercial Enterprises"),
]

TOPIC_PATTERNS = [
    (r"\b(?:climate(?:\s*change|\s*risk|\s*disclosure)?|carbon|ghg|greenhouse\s*gas|emissions?\s*trading|net\s*zero)\b", "Climate & Emissions Disclosure"),
    (r"\b(?:brsr|business\s*responsibility\s*and\s*sustainability|csrd|esrs|vsme|sfdr|taxonomy|tcfd|issb)\b", "Sustainability & ESG Reporting"),
    (r"\b(?:green\s*bonds?|sustainable\s*finance|green\s*finance)\b", "Sustainable Finance & Green Bonds"),
    (r"\b(?:due\s*diligence|supply\s*chain|deforestation|eudr|csddd)\b", "Due Diligence & Supply Chain"),
    (r"\b(?:corporate\s*governance|csr|corporate\s*social\s*responsibility)\b", "Corporate Governance & CSR"),
]


@dataclass
class RegulatoryIdentity:
    country: str = "UNKNOWN"
    authority: str = "UNKNOWN"
    authority_tier: str = "UNKNOWN"
    instrument_name: str = ""
    instrument_type: str = "Guideline / Standard"
    regulatory_topic: str = "Sustainability & ESG Reporting"
    regulated_population: str = "Listed Companies / Issuers"
    reference_number: str = ""
    issue_date: str = ""
    publication_date: str = ""
    effective_date: str = ""
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RegulatoryIdentityEngine:
    """Extracts a structured regulatory fingerprint for a link/document to anchor currentness & replacement checks."""

    def __init__(self, registry: Optional[JurisdictionRegistry] = None):
        self.registry = registry or JurisdictionRegistry.get_instance()

    def extract_identity(
        self,
        link_item: dict,
        text_sample: str = "",
        page_title: str = "",
        url: str = "",
    ) -> RegulatoryIdentity:
        country = link_item.get("country") or link_item.get("jurisdiction") or "UNKNOWN"
        step_title = link_item.get("step_description") or link_item.get("link_text") or link_item.get("text") or ""
        return self.identify(
            country=country,
            step_title=step_title,
            url=url or link_item.get("url", ""),
            metadata={"title": page_title, "text_sample": text_sample},
        )

    @classmethod
    def identify(
        cls,
        country: str,
        step_title: str,
        url: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RegulatoryIdentity:
        meta = metadata or {}
        doc_title = meta.get("title") or step_title or ""
        text_sample = (meta.get("text_sample") or "")[:3000]
        combined = f"{step_title} {doc_title} {text_sample} {url}".strip()

        reg_registry = JurisdictionRegistry.get_instance()
        domain = urlparse(url).netloc.lower()

        # 1. Authority resolution from JurisdictionRegistry or domain
        authority = "UNKNOWN"
        authority_tier = "UNKNOWN"
        auth_info = reg_registry.find_authority_by_domain(domain)
        if auth_info:
            authority = auth_info["authority"]
            authority_tier = auth_info["tier"]
            if not country or country == "UNKNOWN":
                country = auth_info["country"]
        else:
            # Check if domain belongs to a country authority
            authorities = reg_registry.get_authorities(country)
            for a in authorities:
                if a["name"].lower() in combined.lower():
                    authority = a["name"]
                    authority_tier = a.get("tier", "TIER_1_PRIMARY_REGULATOR")
                    break

        # 2. Instrument Type determination
        instrument_type = "Guideline / Standard"
        for pat, itype in INSTRUMENT_TYPE_PATTERNS:
            if re.search(pat, combined, re.I):
                instrument_type = itype
                break

        # 3. Regulated Population determination
        regulated_pop = "Listed Companies / Issuers"
        for pat, pop in REGULATED_POPULATION_PATTERNS:
            if re.search(pat, combined, re.I):
                regulated_pop = pop
                break

        # 4. Regulatory Topic determination
        topic = "Sustainability & ESG Reporting"
        for pat, top in TOPIC_PATTERNS:
            if re.search(pat, combined, re.I):
                topic = top
                break

        # 5. Reference Number extraction
        ref_no = meta.get("document_number", "")
        if not ref_no:
            ref_patterns = [
                r"\b(?:Directive\s*(?:\(EU\))?\s*)([0-9]{4}\/[0-9]+)\b",
                r"\b(?:Regulation\s*(?:\(EU\))?\s*)([0-9]{4}\/[0-9]+)\b",
                r"\b(?:Release\s*No\.?\s*)(33-[0-9]+|34-[0-9]+)\b",
                r"\b(SEBI\/[A-Z0-9\/\-_]+)\b",
                r"\b(RBI\/[0-9]{4}-[0-9]{2,4}\/[0-9]+)\b",
                r"\b(?:Circular\s*No\.?\s*[:\s]*)([A-Z0-9\/\-_]+)\b",
                r"\b(?:Act\s*No\.?\s*)([0-9]+(?:\s*of\s*[0-9]{4})?)\b",
            ]
            for pat in ref_patterns:
                m = re.search(pat, combined, re.I)
                if m:
                    ref_no = m.group(1) if len(m.groups()) >= 1 else m.group(0)
                    break

        # 6. Dates
        pub_date = meta.get("publication_date") or meta.get("publication_date_iso") or ""
        eff_date = meta.get("effective_date") or meta.get("effective_date_iso") or ""

        # 7. Instrument Name
        inst_name = doc_title or step_title
        # Clean generic affixes
        inst_name = re.sub(r"^(Link\s*:\s*|Link\s*)", "", inst_name, flags=re.I).strip()

        # 8. Keywords
        words = set(re.findall(r"\b[A-Za-z0-9\-]{4,}\b", inst_name.lower()))
        filtered_words = [w for w in words if w not in ("with", "from", "that", "this", "have", "been", "rule", "guidelines")]

        return RegulatoryIdentity(
            country=country,
            authority=authority,
            authority_tier=authority_tier,
            instrument_name=inst_name,
            instrument_type=instrument_type,
            regulatory_topic=topic,
            regulated_population=regulated_pop,
            reference_number=ref_no,
            issue_date=pub_date,
            publication_date=pub_date,
            effective_date=eff_date,
            keywords=filtered_words[:8],
        )
