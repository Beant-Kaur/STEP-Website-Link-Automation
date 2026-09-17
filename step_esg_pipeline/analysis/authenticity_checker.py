import re
from urllib.parse import urlparse
from typing import Optional, Dict, Any, List

from analysis.source_classifier import SourceClassifier, OFFICIAL_REGULATOR, OFFICIAL_LEGISLATION, STANDARDS_BODY, EXCHANGE_FILING, INSTITUTIONAL, COMMERCIAL_AGGREGATOR


class AuthenticityChecker:
    """
    Evaluates whether a document/link is authentic, authoritative, uncertain,
    suspicious, or a mismatch according to Section 6 of the Master Prompt.
    """

    OFFICIAL_CITATIONS = [
        r"\b(?:directive|regulation|decision)\s+\(eu\)\s+\d+/\d+",
        r"\b(?:public law|pub\.l\.)\s+\d+-\d+",
        r"\bsec\s+release\s+no\.\s+\d+-\d+",
        r"\bsebi/ho/[a-z0-9/_-]+",
        r"\bstatutory\s+instrument\s+\d{4}\s+no\.\s+\d+",
        r"\b(?:sb|ab)\s*[- ]?\d{1,4}\b",
        r"\bifrs\s+[sS]\d+\b",
        r"\bgri\s+\d{1,3}\b",
    ]

    @staticmethod
    def evaluate(
        url: str = "",
        final_url: str = "",
        title: str = "",
        text_sample: str = "",
        organisation: str = "",
        access_status: str = "",
        http_status: Optional[int] = None,
        technical_status: str = "",
        is_challenge_page: bool = False,
    ) -> Dict[str, Any]:
        target_url = final_url or url
        domain = urlparse(target_url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        auth_type = SourceClassifier.classify_authority(domain)
        text_lower = (text_sample or "").lower()
        title_lower = (title or "").lower()
        combined = f"{title_lower} {text_lower}"

        evidence: List[str] = []
        status = "UNCERTAIN"
        confidence = 0.50
        explanation = ""

        # 1. Check for suspicious redirects across unrelated domains
        orig_domain = urlparse(url).netloc.lower()
        if orig_domain.startswith("www."):
            orig_domain = orig_domain[4:]
        if orig_domain and domain and orig_domain != domain:
            # Check if domain changed to a commercial or ad network
            if any(ad in domain for ad in ("parking", "domain", "adnetwork", "track", "click")):
                return {
                    "authenticity_status": "SUSPICIOUS",
                    "confidence": 0.85,
                    "explanation": f"Suspicious redirect: Original domain '{orig_domain}' redirected to unrelated commercial/parking domain '{domain}'.",
                    "evidence": [f"Unrelated domain redirect from {orig_domain} to {domain}"],
                }

        # 2. Official statutory and regulatory domains
        if auth_type in (OFFICIAL_REGULATOR, OFFICIAL_LEGISLATION):
            evidence.append(f"Domain '{domain}' is an officially verified regulator/legislation publisher ({auth_type}).")
            
            # Check for official citations or document patterns
            has_citation = any(re.search(pat, combined, re.I) for pat in AuthenticityChecker.OFFICIAL_CITATIONS)
            if has_citation:
                evidence.append("Document text contains authentic statutory/regulatory citations.")
                status = "AUTHENTIC"
                confidence = 0.95
                explanation = "Document is published on an official regulatory portal and contains matching statutory citations."
            elif is_challenge_page or access_status in ("ACCESS_DENIED", "CLOUDFLARE_CHALLENGE", "BOT_PROTECTION"):
                status = "LIKELY_AUTHENTIC"
                confidence = 0.70
                explanation = "Published on official regulatory domain, but automated inspection was restricted by access challenge."
                evidence.append("Automated text extraction was limited by access challenge/restriction.")
            elif len(text_sample) >= 200:
                status = "AUTHENTIC"
                confidence = 0.90
                explanation = "Published on official regulatory portal with substantive matching content."
            else:
                status = "LIKELY_AUTHENTIC"
                confidence = 0.75
                explanation = "Published on official domain with minimal extracted text."

        # 3. Recognized Standards Bodies & Exchanges
        elif auth_type in (STANDARDS_BODY, EXCHANGE_FILING, INSTITUTIONAL):
            evidence.append(f"Domain '{domain}' is a recognized institutional standard setter or exchange ({auth_type}).")
            if len(text_sample) >= 150:
                status = "AUTHENTIC"
                confidence = 0.90
                explanation = "Official document from a recognized standards body or international institution."
            else:
                status = "LIKELY_AUTHENTIC"
                confidence = 0.75
                explanation = "Institutional domain verified; limited text extracted."

        # 4. Third-Party Commercial Aggregators, Consultancies & Blogs
        else:
            evidence.append(f"Domain '{domain}' is a third-party commercial website, consultancy, or aggregator.")
            # Check if third party claims to be an official statute or has obvious mismatch
            if any(term in title_lower for term in ("act", "directive", "regulation", "statute")) and "policyvault" in domain:
                status = "LIKELY_AUTHENTIC"
                confidence = 0.60
                explanation = "Third-party aggregator hosting a secondary copy of a regulatory document; official primary source preferred."
                evidence.append("Third-party host of regulatory document.")
            elif any(blog_term in domain for blog_term in ("blog", "news", "review", "consulting", "lawfirm", "lexology", "mondaq")):
                status = "LIKELY_AUTHENTIC"
                confidence = 0.55
                explanation = "Authoritative secondary commentary/analysis rather than primary regulatory text."
                evidence.append("Secondary commentary source.")
            elif not text_sample or len(text_sample) < 50:
                status = "UNCERTAIN"
                confidence = 0.35
                explanation = "Third-party domain with insufficient substantive content to verify authenticity."
                evidence.append("Insufficient textual evidence to establish authenticity.")
            else:
                status = "UNCERTAIN"
                confidence = 0.45
                explanation = "Non-official domain; authenticity and currentness require verification against primary source."
                evidence.append("Non-official source.")

        return {
            "authenticity_status": status,
            "confidence": confidence,
            "explanation": explanation,
            "evidence": evidence,
        }
