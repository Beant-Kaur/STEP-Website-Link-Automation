import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from crawler.url_normalizer import UrlNormalizer
from analysis.source_classifier import SourceClassifier


class LinkRelevance:
    HIGH = "HIGH RELEVANCE"
    MEDIUM = "MEDIUM RELEVANCE"
    LOW = "LOW RELEVANCE"
    IRRELEVANT = "IRRELEVANT"


class LinkDiscoveryEngine:
    """Intelligent Crawler & Link Relevance Classifier.

    Ensures the crawler does NOT crawl everything blindly:
    - Filters out social media, ads, tracking, login, careers, privacy policies.
    - Classifies discovered links into HIGH, MEDIUM, LOW, or IRRELEVANT.
    - Follows internal source links up to configured crawl depth.
    - Understands landing pages vs documents.
    """

    IRRELEVANT_DOMAINS = {
        "facebook.com", "twitter.com", "x.com", "linkedin.com", "instagram.com",
        "youtube.com", "t.co", "tiktok.com", "pinterest.com", "reddit.com",
        "google-analytics.com", "doubleclick.net", "googletagmanager.com",
    }

    IRRELEVANT_PATH_PATTERNS = [
        r"/(?:login|signin|logout|signup|register|auth|password|reset-password)\b",
        r"/(?:privacy-policy|terms-of-service|terms-and-conditions|terms|disclaimer|cookie-policy|legal-notice)\b",
        r"/(?:careers|jobs|work-with-us|internships|vacancies)\b",
        r"/(?:contact-us|about-us|feedback|sitemap|site-map|accessibility)\b",
        r"/(?:cart|checkout|shop|subscribe|membership)\b",
        r"/(?:advertisement|ads|sponsored)\b",
    ]

    HIGH_RELEVANCE_PATTERNS = [
        r"\b(?:circular|notification|regulation|directive|standard|guideline|framework|ordinance|act|bill|statute)\b",
        r"\b(?:download\s*pdf|full\s*text|official\s*document|view\s*document|gazette)\b",
        r"\b(?:current\s*version|updated\s*version|superseded\s*by|amendment|consolidated\s*version)\b",
        r"\b(?:brsr|csrd|esrs|tcfd|issb|sfdr|gri|eia|sdg)\b",
        r"\b(?:sebi|mca|rbi|sec|fca|mee|efrag)\b",
    ]

    def __init__(self, max_crawl_depth: int = 2):
        self.max_crawl_depth = max_crawl_depth

    def classify_link(
        self,
        url: str,
        anchor_text: str = "",
        page_title: str = "",
        target_doc_title: str = "",
        target_doc_no: str = "",
        source_domain: str = "",
    ) -> str:
        """Classifies relevance of a discovered link."""
        if not url:
            return LinkRelevance.IRRELEVANT

        norm_url = UrlNormalizer.normalize(url)
        parsed = urlparse(norm_url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()

        # 1. Filter out known social/tracking domains
        if any(domain == d or domain.endswith("." + d) for d in self.IRRELEVANT_DOMAINS):
            return LinkRelevance.IRRELEVANT

        # 2. Filter out generic homepages (domain root with empty path)
        if path in ("", "/", "/index.html", "/index.htm", "/en", "/en/", "/home", "/default.aspx"):
            # Only allow if it's the target authority domain and we're looking for doc repository
            return LinkRelevance.LOW

        # 3. Filter out irrelevant sections (careers, privacy, login)
        for pat in self.IRRELEVANT_PATH_PATTERNS:
            if re.search(pat, path, re.I):
                return LinkRelevance.IRRELEVANT

        combined_context = f"{url} {anchor_text} {page_title}".lower()

        # 4. Check for high relevance: exact doc number, title match, or direct PDF
        if target_doc_no and target_doc_no.lower() in combined_context:
            return LinkRelevance.HIGH

        if target_doc_title:
            # Word overlap check
            title_words = [w for w in re.findall(r"\b[a-zA-Z]{4,}\b", target_doc_title.lower()) if w not in ("with", "from", "that", "this", "have", "been")]
            if title_words:
                matching_words = sum(1 for w in title_words if w in combined_context)
                if matching_words >= min(3, len(title_words)):
                    return LinkRelevance.HIGH

        if norm_url.lower().endswith(".pdf") or "application/pdf" in combined_context:
            return LinkRelevance.HIGH

        for pat in self.HIGH_RELEVANCE_PATTERNS:
            if re.search(pat, combined_context, re.I):
                return LinkRelevance.HIGH

        # 5. Medium relevance: internal links on same official domain or regulatory repository
        if source_domain and (source_domain in domain or domain in source_domain):
            if any(w in path for w in ("legal", "rules", "publications", "documents", "acts", "circulars", "policies", "disclosure")):
                return LinkRelevance.MEDIUM
            return LinkRelevance.LOW

        # External domain
        return LinkRelevance.LOW

    def filter_and_rank_links(
        self,
        discovered_links: List[Dict[str, Any]],
        target_doc_title: str = "",
        target_doc_no: str = "",
        source_domain: str = "",
    ) -> List[Dict[str, Any]]:
        """Filters out irrelevant links and ranks the rest by relevance."""
        ranked = []
        seen = set()

        priority_weight = {
            LinkRelevance.HIGH: 3,
            LinkRelevance.MEDIUM: 2,
            LinkRelevance.LOW: 1,
            LinkRelevance.IRRELEVANT: 0,
        }

        for link in discovered_links:
            url = link.get("url", "")
            norm = UrlNormalizer.normalize(url)
            if not norm or norm in seen:
                continue
            seen.add(norm)

            text = link.get("text", "") or link.get("label", "")
            relevance = self.classify_link(
                url=norm,
                anchor_text=text,
                target_doc_title=target_doc_title,
                target_doc_no=target_doc_no,
                source_domain=source_domain,
            )

            if relevance == LinkRelevance.IRRELEVANT:
                continue

            ranked.append({
                **link,
                "normalized_url": norm,
                "relevance": relevance,
                "priority": priority_weight[relevance],
            })

        # Sort by priority descending
        ranked.sort(key=lambda x: x["priority"], reverse=True)
        return ranked
