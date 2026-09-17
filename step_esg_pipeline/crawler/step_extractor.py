import re
from typing import Optional
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from crawler.url_checker import UrlChecker
from crawler.redirect_checker import RedirectChecker
from database.models import LinkRecord


class StepExtractor:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.url_checker = UrlChecker(timeout=timeout)
        self.redirect_checker = RedirectChecker()

    def extract_from_html(self, html: str, base_url: str = "", section: str = "") -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        if section:
            soup = self._extract_section(soup, section)

        links = []
        seen = set()

        # Check for Kajabi-style accordions first
        accordions = soup.find_all("div", class_=lambda c: c and "accordion" in c)
        if accordions:
            for card in accordions:
                title_div = card.find("div", class_=lambda c: c and "accordion-title" in c)
                collapse_div = card.find("div", class_=lambda c: c and "accordion-collapse" in c)
                if not collapse_div:
                    collapse_div = card

                country = ""
                if title_div:
                    country = title_div.get_text(strip=True)

                current_title = ""
                for el in collapse_div.find_all(["p", "div", "li", "a"]):
                    if el.name in ("p", "div", "li"):
                        bold = el.find(["b", "strong"])
                        if bold and bold.parent.name != "a":
                            t = bold.get_text(strip=True)
                            if t and not t.lower().startswith("link") and len(t) > 3 and t.lower() != "disclaimer:":
                                current_title = t
                    elif el.name == "a" and el.get("href"):
                        href = el.get("href", "").strip()
                        if not href or href.startswith(("javascript:", "mailto:", "#")):
                            continue
                        full_url = urljoin(base_url, href)
                        cleaned = self._clean_url(full_url)
                        if cleaned in seen:
                            continue
                        seen.add(cleaned)

                        anchor_text = el.get_text(strip=True)
                        parent_p = el.find_parent(["p", "li", "div"])
                        p_text = parent_p.get_text(strip=True) if parent_p else ""
                        reg_title = current_title or p_text[:80]
                        if reg_title.lower().startswith("link") or len(reg_title) < 4:
                            reg_title = p_text[:80] or anchor_text or cleaned

                        links.append({
                            "url": cleaned,
                            "text": reg_title,
                            "anchor_text": anchor_text,
                            "title": el.get("title", "") or reg_title,
                            "jurisdiction": country,
                            "section_heading": country,
                            "step_description": reg_title,
                        })

        if not links:
            # Fallback for flat HTML (e.g. sample files, unit test fixtures)
            current_heading = ""
            for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "a"]):
                if el.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                    current_heading = el.get_text(strip=True)
                elif el.name == "a" and el.get("href"):
                    href = el.get("href", "").strip()
                    if not href or href.startswith(("javascript:", "mailto:", "#")):
                        continue
                    full_url = urljoin(base_url, href)
                    cleaned = self._clean_url(full_url)
                    if cleaned in seen:
                        continue
                    seen.add(cleaned)
                    text = el.get_text(strip=True)
                    if not text or text.lower() == "link":
                        text = el.get("title", "") or current_heading or cleaned
                    
                    # Try to infer jurisdiction from current heading
                    jurisdiction = ""
                    for c in ("Bahrain", "China", "European Union", "EU", "India", "Kingdom of Saudi Arabia", "Saudi Arabia", "Kuwait", "Oman", "Qatar", "Singapore", "United Arab Emirates", "UAE", "United Kingdom", "UK", "United States", "USA", "Nigeria"):
                        if c.lower() in current_heading.lower():
                            jurisdiction = c
                            break

                    links.append({
                        "url": cleaned,
                        "text": text,
                        "anchor_text": el.get_text(strip=True),
                        "title": el.get("title", ""),
                        "jurisdiction": jurisdiction,
                        "section_heading": current_heading,
                        "step_description": text,
                    })
        return links

    @staticmethod
    def _clean_url(url: str) -> str:
        parsed = urlparse(url)
        # Remove common tracking params
        if parsed.netloc.endswith("mykajabi.com") or parsed.path.startswith("/resource_redirect"):
            return url
        params = [p for p in parsed.query.split("&") if not p.lower().startswith("utm_")]
        return parsed._replace(query="&".join(params)).geturl()

    def _extract_section(self, soup: BeautifulSoup, section: str) -> BeautifulSoup:
        lower = section.lower()
        for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            if lower in heading.get_text(strip=True).lower():
                container = heading.find_parent("section") or heading.find_parent("div")
                if container:
                    new_soup = BeautifulSoup("<div></div>", "html.parser")
                    new_soup.div.append(container)
                    return new_soup
                break
        return soup

    def check_links(self, links: list[dict]) -> list[dict]:
        results = []
        for item in links:
            url = item["url"]
            check = self.url_checker.check(url)
            redirect = self.redirect_checker.analyze(check)
            merged = {**item, **check, **redirect}
            results.append(merged)
        return results
