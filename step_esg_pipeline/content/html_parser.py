import re
from typing import Optional
from bs4 import BeautifulSoup


TECHNICAL_TITLE_PATTERNS = [
    r"\baccess\s*denied\b",
    r"\b403\s*forbidden\b",
    r"^\s*forbidden\s*$",
    r"\bcloudflare\b",
    r"just\s*a\s*moment",
    r"\bpage\s*not\s*found\b",
    r"\b404\s*not\s*found\b",
    r"^\s*404\s*$",
    r"^\s*error\s*$",
    r"^\s*login\s*$",
    r"\baws\s*waf\b",
    r"\bakamai\b",
    r"security\s*check",
    r"verify\s*you\s*are\s*human",
    r"\bjavascript\s*(?:is\s*)?(?:disabled|required)\b",
    r"\brate\s*(?:threshold\s*)?exceeded\b",
    r"\battention\s*required\b",
]


class HtmlParser:
    @staticmethod
    def is_technical_title(title: str) -> bool:
        if not title:
            return True
        t = title.strip().lower()
        return any(re.search(pat, t, re.I) for pat in TECHNICAL_TITLE_PATTERNS)

    @staticmethod
    def parse(html: str, base_url: str = "") -> dict:
        soup = BeautifulSoup(html, "html.parser")
        doc_title, tech_title = HtmlParser._extract_title(soup)
        headings = HtmlParser._extract_headings(soup)
        organisation = HtmlParser._extract_organisation(soup)
        publication_date = HtmlParser._extract_meta_date(soup)
        text_sample = HtmlParser._extract_text_sample(soup)
        keywords = HtmlParser._extract_keywords(soup)

        # Soft 404 / Maintenance / Challenge detection per Sections 4 & 5
        is_soft_404 = HtmlParser._check_soft_404(doc_title or tech_title, soup, text_sample)
        is_maintenance = HtmlParser._check_maintenance(doc_title or tech_title, soup, text_sample)
        is_challenge_page = HtmlParser._check_challenge(doc_title or tech_title, soup, text_sample)

        # Fallback date extraction from body if meta was empty
        if not publication_date and text_sample:
            publication_date = HtmlParser._extract_body_date(text_sample)

        effective_date = HtmlParser._extract_effective_date(text_sample)
        amendment_date = HtmlParser._extract_amendment_date(text_sample)
        version = HtmlParser._extract_version(text_sample)
        document_number = HtmlParser._extract_document_number(doc_title, headings, text_sample)
        repeal_signals = HtmlParser._extract_repeal_signals(text_sample)

        return {
            "title": doc_title,
            "technical_page_title": tech_title,
            "headings": headings,
            "organisation": organisation,
            "publication_date": publication_date,
            "effective_date": effective_date,
            "amendment_date": amendment_date,
            "version": version,
            "document_number": document_number,
            "text_sample": text_sample,
            "keywords": keywords,
            "repeal_signals": repeal_signals,
            "is_soft_404": is_soft_404,
            "is_maintenance": is_maintenance,
            "is_challenge_page": is_challenge_page,
            "is_javascript_page": bool(soup.find("script", string=re.compile(r"require\(|window\.__NUXT__|__NEXT_DATA__", re.I))),
        }

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> tuple[str, str]:
        """Hierarchy: 1. h1 -> 2. og:title -> 3. title tag.
        Rejects technical titles. Returns: (document_title, technical_page_title)
        """
        raw_page_title = ""
        if soup.title and soup.title.string:
            raw_page_title = soup.title.string.strip()

        # 1. HTML h1
        h1 = soup.find("h1")
        if h1:
            h1_text = h1.get_text(strip=True)
            if h1_text and not HtmlParser.is_technical_title(h1_text):
                return h1_text, (raw_page_title if HtmlParser.is_technical_title(raw_page_title) else "")

        # 2. HTML OpenGraph title
        og_tag = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "twitter:title"})
        if og_tag and og_tag.get("content"):
            og_text = og_tag.get("content", "").strip()
            if og_text and not HtmlParser.is_technical_title(og_text):
                return og_text, (raw_page_title if HtmlParser.is_technical_title(raw_page_title) else "")

        # 3. HTML <title>
        if raw_page_title:
            if not HtmlParser.is_technical_title(raw_page_title):
                return raw_page_title, ""
            return "UNKNOWN", raw_page_title

        return "UNKNOWN", ""

    @staticmethod
    def _extract_headings(soup: BeautifulSoup) -> list[str]:
        headings = []
        for tag in soup.find_all(["h1", "h2", "h3"]):
            text = tag.get_text(strip=True)
            if text and len(text) > 3 and text not in headings:
                headings.append(text[:120])
            if len(headings) >= 6:
                break
        return headings

    @staticmethod
    def _check_soft_404(title: str, soup: BeautifulSoup, text_sample: str = "") -> bool:
        t_lower = (title or "").lower()
        body_start = (text_sample or "")[:1200].lower()

        soft_404_patterns = (
            r"\b(404\s*-\s*page\s*not\s*found|page\s*not\s*found|document\s*(?:not\s*found|unavailable)|content\s*unavailable)\b",
            r"\b(this\s*page\s*(?:no\s*longer\s*exists|cannot\s*be\s*found|is\s*unavailable)|file\s*not\s*found|resource\s*not\s*found)\b",
            r"\b(error\s*404|404\s*error|404\s*not\s*found|invalid\s*document|document\s*does\s*not\s*exist)\b",
            r"\b(the\s*requested\s*(?:page|document|file|url)\s*(?:was\s*not\s*found|could\s*not\s*be\s*found|does\s*not\s*exist|has\s*been\s*(?:removed|deleted)))\b",
            r"\b(page\s*does\s*not\s*exist|page\s*doesn'?t\s*exist|no\s*longer\s*available|content\s*not\s*available)\b",
            r"\b(sorry,?\s*we\s*can'?t\s*find\s*that\s*page|the\s*page\s*you'?re\s*looking\s*for\s*doesn'?t\s*exist)\b",
        )

        for pat in soft_404_patterns:
            if re.search(pat, t_lower, re.I):
                return True
            if re.search(pat, body_start, re.I):
                return True

        # Check all heading tags (h1, h2, h3)
        for h in soup.find_all(["h1", "h2", "h3"]):
            h_text = h.get_text(strip=True).lower()
            for pat in soft_404_patterns:
                if re.search(pat, h_text, re.I):
                    return True

        # Empty body or generic portal landing with missing requested doc
        clean_body = text_sample.strip()
        if len(clean_body) < 120 and any(w in clean_body.lower() for w in ("not found", "error", "unavailable", "missing", "does not exist")):
            return True

        return False

    @staticmethod
    def _check_maintenance(title: str, soup: BeautifulSoup, text_sample: str = "") -> bool:
        combined = f"{title} {text_sample[:400]}".lower()
        if any(pat in combined for pat in ("site maintenance", "scheduled maintenance", "under maintenance", "system maintenance")):
            return True
        if "temporarily unavailable" in combined or "temporarily down" in combined:
            return True
        return False

    @staticmethod
    def _check_challenge(title: str, soup: BeautifulSoup, text_sample: str = "") -> bool:
        combined = f"{title} {text_sample[:500]}".lower()
        challenge_markers = (
            "just a moment...", "attention required! | cloudflare", "access denied", "security check",
            "bot detection", "verify you are human", "captcha", "cf-turnstile", "ddos protection by cloudflare",
            "request blocked", "please enable javascript", "incapsula", "akamai"
        )
        if any(m in combined for m in challenge_markers):
            return True
        if soup.find(attrs={"id": re.compile(r"challenge-running|cf-turnstile|captcha|px-captcha", re.I)}):
            return True
        if soup.find(attrs={"class": re.compile(r"challenge-form|cf-error-details|captcha-container", re.I)}):
            return True
        return False

    @staticmethod
    def _extract_organisation(soup: BeautifulSoup) -> str:
        meta_author = soup.find("meta", attrs={"name": re.compile("author|publisher|creator", re.I)})
        if meta_author:
            val = (meta_author.get("content", "") or "").strip()
            if val:
                return val
        org = soup.find(attrs={"class": re.compile("organisation|author|publisher|institution|agency-name", re.I)})
        if org:
            return org.get_text(strip=True)
        return ""

    @staticmethod
    def _extract_meta_date(soup: BeautifulSoup) -> str:
        for attr in ("date", "pubdate", "modified_time", "article:published_time", "article:modified_time", "dc.date", "dc.date.issued", "webtrends.dcsvms"):
            tag = soup.find("meta", attrs={"name": re.compile(f"^{attr}$", re.I)}) or soup.find("meta", attrs={"property": re.compile(f"^{attr}$", re.I)})
            if tag:
                return (tag.get("content", "") or "").strip()
        time_tag = soup.find("time")
        if time_tag:
            return (time_tag.get("datetime") or time_tag.get_text(strip=True) or "").strip()
        return ""

    @staticmethod
    def _extract_body_date(text: str) -> str:
        patterns = [
            r"\b(?:published|adopted|issued|date)\s*[:\-]?\s*([0-9]{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(?:19|20)\d{2})\b",
            r"\b(?:published|adopted|issued|date)\s*[:\-]?\s*((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+[0-9]{1,2},?\s+(?:19|20)\d{2})\b",
            r"\b([0-9]{4}-[0-9]{2}-[0-9]{2})\b",
        ]
        for pat in patterns:
            match = re.search(pat, text[:2500], re.I)
            if match:
                return match.group(1).strip()
        return ""

    @staticmethod
    def _extract_effective_date(text: str) -> str:
        patterns = [
            r"\b(?:effective from|applicable from|entry into force|in force from)\s*[:\-]?\s*([0-9]{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(?:19|20)\d{2})\b",
            r"\b(?:effective from|applicable from|entry into force|in force from)\s*[:\-]?\s*((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+[0-9]{1,2},?\s+(?:19|20)\d{2})\b",
            r"\b(?:effective from|applicable from)\s*[:\-]?\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\b",
        ]
        for pat in patterns:
            match = re.search(pat, text[:3000], re.I)
            if match:
                return match.group(1).strip()
        return ""

    @staticmethod
    def _extract_amendment_date(text: str) -> str:
        patterns = [
            r"\b(?:amended on|last amended|modified on|revision date)\s*[:\-]?\s*([0-9]{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(?:19|20)\d{2})\b",
            r"\b(?:amended on|last amended)\s*[:\-]?\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\b",
        ]
        for pat in patterns:
            match = re.search(pat, text[:3000], re.I)
            if match:
                return match.group(1).strip()
        return ""

    @staticmethod
    def _extract_version(text: str) -> str:
        match = re.search(r"\b(?:version|v\.|ver\.)\s*([0-9]+(?:\.[0-9]+)*)\b", text[:2000], re.I)
        return match.group(0).strip() if match else ""

    @staticmethod
    def _extract_document_number(title: str, headings: list[str], text: str) -> str:
        sample = f"{title} {' '.join(headings)} {text[:1500]}"
        patterns = [
            r"\b(?:Circular\s*No\.?\s*)([A-Z0-9\/\-_]+)\b",
            r"\b(SEBI\/HO\/[A-Z0-9\/\-_]+)\b",
            r"\b(?:Release\s*No\.?\s*)(33-[0-9]+|34-[0-9]+)\b",
            r"\b(?:Directive\s*(?:\(EU\))?\s*)([0-9]{4}\/[0-9]+)\b",
            r"\b(?:Regulation\s*(?:\(EU\))?\s*)([0-9]{4}\/[0-9]+)\b",
            r"\b(?:Bill\s*ID\s*[:=]\s*|\b)([0-9]{9}[A-Z]{1,2}[0-9]+)\b",
            r"\b(SB-253|SB-261|AB-1305)\b",
        ]
        for pat in patterns:
            match = re.search(pat, sample, re.I)
            if match:
                return match.group(0).strip()
        return ""

    @staticmethod
    def _extract_repeal_signals(text: str) -> list[str]:
        signals = [
            r"\b(repealed by|superseded by|withdrawn by|replaced by directive|replaced by regulation)\b",
            r"\b(no longer in force|ceased to have effect|this standard has been replaced)\b",
        ]
        matches = []
        for s in signals:
            found = re.findall(s, text[:3000], re.I)
            matches.extend(found)
        return list(set(matches))

    @staticmethod
    def _extract_text_sample(soup: BeautifulSoup, max_chars: int = 5000) -> str:
        soup_copy = BeautifulSoup(str(soup), "html.parser")
        for tag in soup_copy(["script", "style", "noscript", "nav", "footer", "header", "aside", "svg", "form"]):
            tag.decompose()

        main = (
            soup_copy.find(["main", "article"])
            or soup_copy.find(attrs={"id": re.compile(r"content|main|article|document", re.I)})
            or soup_copy.find(attrs={"class": re.compile(r"content|main|article|document|body-text", re.I)})
        )
        target = main if main else (soup_copy.body or soup_copy)
        text = target.get_text(separator=" ", strip=True)
        return text[:max_chars]

    @staticmethod
    def _extract_keywords(soup: BeautifulSoup) -> list[str]:
        keywords = []
        meta_keywords = soup.find("meta", attrs={"name": re.compile("keywords", re.I)})
        if meta_keywords:
            raw = (meta_keywords.get("content", "") or "").strip()
            keywords = [k.strip() for k in raw.split(",") if k.strip()]
        return keywords
