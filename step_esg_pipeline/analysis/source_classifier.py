from urllib.parse import urlparse
from typing import Tuple

# Authority Status Categories (Section 11)
OFFICIAL_REGULATOR = "OFFICIAL_REGULATOR"
OFFICIAL_LEGISLATION = "OFFICIAL_LEGISLATION"
STANDARDS_BODY = "STANDARDS_BODY"
EXCHANGE_FILING = "EXCHANGE_FILING"
CORPORATE_OFFICIAL = "CORPORATE_OFFICIAL"
INSTITUTIONAL = "INSTITUTIONAL"
REPUTABLE_SECONDARY = "REPUTABLE_SECONDARY"
COMMERCIAL_AGGREGATOR = "COMMERCIAL_AGGREGATOR"

OFFICIAL_LEGISLATION_DOMAINS = {
    "eur-lex.europa.eu", "legislation.gov.uk", "parliament.uk", "congress.gov",
    "legifrance.gouv.fr", "gesetze-im-internet.de", "fedlex.admin.ch",
    "austlii.edu.au", "elaws.gov.on.ca", "overheid.nl"
}

OFFICIAL_REGULATOR_DOMAINS = {
    "sec.gov", "fca.org.uk", "eba.europa.eu", "esma.europa.eu", "eiopa.europa.eu",
    "mas.gov.sg", "sebi.gov.in", "rbi.org.in", "bafin.de", "amf-france.org",
    "finma.ch", "asic.gov.au", "hkma.gov.hk", "sfc.hk", "fsb.org", "ecb.europa.eu"
}

GOV_TLDS = {
    ".gov", ".gov.uk", ".gov.au", ".gov.ca", ".gov.in", ".gov.za", ".gov.sg",
    ".gov.ng", ".gob.es", ".gouv.fr", ".admin.ch", ".europa.eu"
}

STANDARDS_BODY_DOMAINS = {
    "ifrs.org", "iasb.org", "iasc.org", "efrag.org", "globalreporting.org",
    "gri.org", "ghgprotocol.org", "iso.org", "sasb.org", "cdp.net",
    "fsb-tcfd.org", "tnfd.global", "wipo.int"
}

EXCHANGE_FILING_DOMAINS = {
    "sseinitiative.org", "nseindia.com", "bseindia.com", "londonstockexchange.com",
    "nyse.com", "nasdaq.com", "sgx.com", "hkex.com.hk", "jpx.co.jp",
    "bahrainbourse.com", "sse.com.cn", "adx.ae", "boursakuwait.com.kw",
    "msx.om", "qe.com.qa"
}

INSTITUTIONAL_DOMAINS = {
    "un.org", "unglobalcompact.org", "unep.org", "unepfi.org", "unpri.org",
    "oecd.org", "worldbank.org", "imf.org", "bis.org", "who.int", "ilo.org", "wto.org"
}

REPUTABLE_SECONDARY_DOMAINS = {
    "reuters.com", "bloomberg.com", "ft.com", "wsj.com", "economist.com",
    "harvard.edu", "stanford.edu", "ox.ac.uk", "cam.ac.uk", "ssrn.com", "nber.org"
}

COMMERCIAL_AGGREGATOR_DOMAINS = {
    "mondaq.com", "lexology.com", "jdsupra.com", "natlawreview.com",
    "esgtoday.com", "policyvault.africa", "investopedia.com", "wikipedia.org"
}


class SourceClassifier:
    @staticmethod
    def classify_authority(domain: str) -> str:
        domain = domain.lower().strip()
        if domain.startswith("www."):
            domain = domain[4:]

        # 1. Official Legislation
        if any(domain == d or domain.endswith("." + d) for d in OFFICIAL_LEGISLATION_DOMAINS):
            return OFFICIAL_LEGISLATION

        # 2. Official Regulator & Government
        if any(domain == d or domain.endswith("." + d) for d in OFFICIAL_REGULATOR_DOMAINS):
            return OFFICIAL_REGULATOR
        if any(domain == tld.lstrip(".") or domain.endswith(tld) or domain.endswith("." + tld.lstrip(".")) for tld in GOV_TLDS):
            return OFFICIAL_REGULATOR

        # 3. Standards Body
        if any(domain == d or domain.endswith("." + d) for d in STANDARDS_BODY_DOMAINS):
            return STANDARDS_BODY

        # 4. Exchange Filing
        if any(domain == d or domain.endswith("." + d) for d in EXCHANGE_FILING_DOMAINS):
            return EXCHANGE_FILING

        # 5. Institutional
        if any(domain == d or domain.endswith("." + d) for d in INSTITUTIONAL_DOMAINS):
            return INSTITUTIONAL

        # 6. Reputable Secondary
        if any(domain == d or domain.endswith("." + d) for d in REPUTABLE_SECONDARY_DOMAINS):
            return REPUTABLE_SECONDARY

        # 7. Commercial Aggregator
        if any(domain == d or domain.endswith("." + d) for d in COMMERCIAL_AGGREGATOR_DOMAINS):
            return COMMERCIAL_AGGREGATOR

        # Default fallback
        return COMMERCIAL_AGGREGATOR

    @staticmethod
    def classify(domain: str) -> str:
        """Backward compatible mapping to Tier 1 - Tier 4."""
        auth = SourceClassifier.classify_authority(domain)
        if auth in (OFFICIAL_REGULATOR, OFFICIAL_LEGISLATION):
            return "Tier 1"
        if auth in (STANDARDS_BODY, EXCHANGE_FILING, INSTITUTIONAL):
            return "Tier 2"
        if auth in (CORPORATE_OFFICIAL, REPUTABLE_SECONDARY):
            return "Tier 3"
        return "Tier 4"

    @staticmethod
    def get_authority_score(authority_status: str) -> int:
        """Scores authority from 0 to 100 based on tier."""
        scores = {
            OFFICIAL_REGULATOR: 100,
            OFFICIAL_LEGISLATION: 100,
            STANDARDS_BODY: 90,
            EXCHANGE_FILING: 85,
            INSTITUTIONAL: 85,
            CORPORATE_OFFICIAL: 70,
            REPUTABLE_SECONDARY: 60,
            COMMERCIAL_AGGREGATOR: 35,
        }
        return scores.get(authority_status, 30)

    @staticmethod
    def assess_authority(domain: str) -> str:
        """
        Master Prompt Section 5 Authority Assessment:
        - Official
        - Authoritative secondary
        - Non-official but useful
        - Weak/non-authoritative
        - Unknown
        """
        auth = SourceClassifier.classify_authority(domain)
        if auth in (OFFICIAL_REGULATOR, OFFICIAL_LEGISLATION, STANDARDS_BODY, EXCHANGE_FILING, INSTITUTIONAL):
            return "Official"
        if auth in (REPUTABLE_SECONDARY, CORPORATE_OFFICIAL):
            return "Authoritative secondary"
        
        domain = domain.lower().strip()
        if any(c in domain for c in ("pwc.", "deloitte.", "ey.com", "kpmg.", "mckinsey.", "lexology.", "mondaq.", "natlawreview.", "esgtoday.")):
            return "Non-official but useful"
        if any(b in domain for b in ("blog", "wordpress", "medium.com", "blogspot", "tumblr")):
            return "Weak/non-authoritative"
        if auth == COMMERCIAL_AGGREGATOR:
            return "Non-official but useful"
        return "Unknown"

    @staticmethod
    def is_official(domain: str) -> bool:
        auth = SourceClassifier.classify_authority(domain)
        return auth in (OFFICIAL_REGULATOR, OFFICIAL_LEGISLATION, STANDARDS_BODY, EXCHANGE_FILING, INSTITUTIONAL)

    @staticmethod
    def is_non_official_aggregator(domain: str) -> bool:
        auth = SourceClassifier.classify_authority(domain)
        return auth == COMMERCIAL_AGGREGATOR or SourceClassifier.assess_authority(domain) in ("Non-official but useful", "Weak/non-authoritative")
