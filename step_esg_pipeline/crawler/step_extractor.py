import re
from typing import Optional, List, Dict, Any, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from crawler.url_checker import UrlChecker
from crawler.redirect_checker import RedirectChecker


VALID_13_JURISDICTIONS = [
    "Bahrain",
    "China",
    "European Union",
    "India",
    "Kingdom of Saudi Arabia",
    "Kuwait",
    "Oman",
    "Qatar",
    "Singapore",
    "United Arab Emirates",
    "United Kingdom",
    "United States",
    "Nigeria",
]

JURISDICTION_ALIASES = {
    "eu": "European Union",
    "european union": "European Union",
    "eu reporting": "European Union",
    "uk": "United Kingdom",
    "united kingdom": "United Kingdom",
    "uk standards": "United Kingdom",
    "usa": "United States",
    "us": "United States",
    "united states": "United States",
    "ksa": "Kingdom of Saudi Arabia",
    "saudi arabia": "Kingdom of Saudi Arabia",
    "kingdom of saudi arabia": "Kingdom of Saudi Arabia",
    "uae": "United Arab Emirates",
    "united arab emirates": "United Arab Emirates",
}


class StepExtractor:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.url_checker = UrlChecker(timeout=timeout)
        self.redirect_checker = RedirectChecker()

    @staticmethod
    def match_country(raw_name: str) -> tuple[str, float, str]:
        """Matches a raw text to one of the 13 valid countries.
        Returns: (country_name, country_confidence, evidence)
        """
        if not raw_name:
            return "UNKNOWN", 0.0, "No heading text provided"

        cleaned = raw_name.strip()
        cleaned_lower = cleaned.lower()

        # Check exact valid country names
        for c in VALID_13_JURISDICTIONS:
            if c.lower() == cleaned_lower:
                return c, 1.0, f"Exact match with target jurisdiction: '{cleaned}'"

        # Check aliases
        for alias, target in JURISDICTION_ALIASES.items():
            if alias == cleaned_lower or alias in cleaned_lower:
                return target, 1.0, f"Matched target jurisdiction via alias '{alias}': '{cleaned}'"

        # Check substring
        for c in VALID_13_JURISDICTIONS:
            if c.lower() in cleaned_lower:
                return c, 1.0, f"Target jurisdiction found in heading: '{cleaned}'"

        return "UNKNOWN", 0.0, f"Heading '{cleaned}' does not match any of the 13 target jurisdictions"

    def extract_from_html(self, html: str, base_url: str = "", section: str = "") -> list[dict]:
        """Extracts regulatory links specifically from the ESG Legislative Landscape section.
        Audits only the 13 target jurisdictions and rejects general/unrelated page links.
        """
        soup = BeautifulSoup(html, "html.parser")
        target_section_name = section or "ESG Legislative Landscape"

        # 1. Try to isolate the ESG Legislative Landscape section container
        landscape_container = self._find_landscape_container(soup, target_section_name)

        target_soup = landscape_container if landscape_container is not None else soup
        links = self._extract_from_kajabi_accordions(target_soup, base_url, target_section_name)

        if not links:
            # Fallback for flat HTML (e.g. sample files, unit test fixtures)
            links = self._extract_from_flat_html(target_soup, base_url, target_section_name)

        return links

    def _find_landscape_container(self, soup: BeautifulSoup, section_name: str) -> Optional[BeautifulSoup]:
        """Locates the specific <section> or container for the ESG Legislative Landscape."""
        section_pattern = re.compile(re.escape(section_name), re.I)

        # Look for section heading in text nodes
        for el in soup.find_all(string=section_pattern):
            # Prefer parent <section>
            sec = el.find_parent("section")
            if sec:
                return sec
            # Fallback to parent container div
            div = el.find_parent("div", class_=lambda c: c and ("section" in c or "container" in c))
            if div:
                return div

        # Look in headings directly
        for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            if section_pattern.search(h.get_text()):
                sec = h.find_parent("section") or h.find_parent("div", class_=lambda c: c and "section" in c)
                if sec:
                    return sec

        return None

    def _extract_from_kajabi_accordions(self, container: BeautifulSoup, base_url: str, section_name: str) -> list[dict]:
        """Extracts links from Kajabi block-type--accordion elements belonging to the 13 jurisdictions."""
        links: List[Dict[str, Any]] = []
        seen: Set[str] = set()

        # Target top-level accordion blocks
        blocks = container.find_all("div", class_=lambda c: c and "block-type--accordion" in c)
        if not blocks:
            # Check for direct .accordion elements that are not nested
            all_accs = container.find_all("div", class_="accordion")
            blocks = [a for a in all_accs if not a.find_parent("div", class_="accordion")]

        if not blocks:
            return []

        step_pos = 0

        for block in blocks:
            # Extract Country Heading
            title_el = block.find("h5") or block.find("div", class_=lambda c: c and "accordion-title" in c)
            raw_title = title_el.get_text(strip=True) if title_el else ""

            country, country_conf, country_ev = self.match_country(raw_title)

            collapse = block.find("div", class_=lambda c: c and "accordion-collapse" in c) or block

            # Walk bold headings and links in DOCUMENT ORDER. We iterate leaf nodes
            # (<strong>/<b> and <a>) rather than container elements: sweeping a wrapper
            # <div> would grab all its descendant bolds and links at once, latching the
            # LAST heading onto every link in the block (the title-bleed bug). Streaming
            # leaf nodes means each link's title is the nearest heading that precedes it.
            current_doc_title = ""

            for node in collapse.find_all(["strong", "b", "a"]):
                if node.name in ("strong", "b"):
                    bt = node.get_text(strip=True)
                    # Filter generic labels like 'Link:' / 'Disclaimer:' so they don't
                    # overwrite the real document heading.
                    clean_bt = re.sub(r"^(Link\s*:\s*|Link\s*)", "", bt, flags=re.I).strip()
                    if len(clean_bt) > 4 and not clean_bt.lower().startswith("disclaimer"):
                        current_doc_title = clean_bt
                    continue

                # node is an <a>
                href = node.get("href", "").strip()
                if not href or href.startswith(("javascript:", "mailto:", "#")):
                    continue

                full_url = urljoin(base_url, href)
                cleaned_url = self._clean_url(full_url)
                if cleaned_url in seen:
                    continue
                seen.add(cleaned_url)

                anchor_text = node.get_text(strip=True)
                clean_anchor = re.sub(r"^(Link\s*:\s*|Link\s*)", "", anchor_text, flags=re.I).strip()

                # Prefer a SPECIFIC per-link anchor (e.g. "Regulation (EU) 2019/2088 (SFDR)");
                # otherwise use the nearest preceding heading (now reliable, no bleed);
                # otherwise fall back to the link's own paragraph text.
                generic_anchor = clean_anchor.lower() in (
                    "link", "here", "click here", "pdf", "download", "view",
                    "read more", "view document", "download pdf", "official",
                )
                is_specific_anchor = (
                    clean_anchor and len(clean_anchor) > 4
                    and not clean_anchor.lower().startswith("http")
                    and not generic_anchor
                )
                if is_specific_anchor:
                    reg_title = clean_anchor
                elif current_doc_title:
                    reg_title = current_doc_title
                else:
                    parent = node.find_parent(["p", "li", "div"])
                    parent_text = parent.get_text(strip=True) if parent else ""
                    clean_parent = re.sub(r"^(Link\s*:\s*|Link\s*)", "", parent_text, flags=re.I).strip()
                    reg_title = clean_parent[:120] if clean_parent else cleaned_url

                step_pos += 1
                links.append({
                    "section": section_name,
                    "country": country,
                    "jurisdiction": country,
                    "country_confidence": country_conf,
                    "country_evidence": country_ev,
                    "link_text": reg_title,
                    "text": reg_title,
                    "source_url": cleaned_url,
                    "url": cleaned_url,
                    "anchor_text": anchor_text,
                    "title": reg_title,
                    "step_position": step_pos,
                    "step_description": reg_title,
                    "section_heading": country,
                })

        return links

    def _extract_from_flat_html(self, soup: BeautifulSoup, base_url: str, section_name: str) -> list[dict]:
        """Fallback for flat HTML layouts (headings followed by lists or paragraphs)."""
        links: List[Dict[str, Any]] = []
        seen: Set[str] = set()

        current_country = "UNKNOWN"
        country_conf = 0.0
        country_ev = "No country heading detected in flat HTML"
        current_title = ""
        step_pos = 0

        # Traverse tags in document order
        for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "a"]):
            if el.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                h_text = el.get_text(strip=True)
                # Check if heading is the section title itself
                if "esg legislative landscape" in h_text.lower():
                    continue
                matched_c, c_conf, c_ev = self.match_country(h_text)
                if matched_c != "UNKNOWN":
                    current_country = matched_c
                    country_conf = c_conf
                    country_ev = c_ev
                    current_title = ""
                else:
                    current_title = h_text

            elif el.name == "a":
                href = el.get("href", "").strip()
                if not href or href.startswith(("javascript:", "mailto:", "#")):
                    continue
                full_url = urljoin(base_url, href)
                cleaned_url = self._clean_url(full_url)
                if cleaned_url in seen:
                    continue
                seen.add(cleaned_url)
                anchor_text = el.get_text(strip=True)
                clean_anchor = re.sub(r"^(Link\s*:\s*|Link\s*)", "", anchor_text, flags=re.I).strip()
                reg_title = current_title or clean_anchor or cleaned_url
                step_pos += 1
                links.append({
                    "section": section_name,
                    "country": current_country,
                    "jurisdiction": current_country,
                    "country_confidence": country_conf,
                    "country_evidence": country_ev,
                    "link_text": reg_title,
                    "text": reg_title,
                    "source_url": cleaned_url,
                    "url": cleaned_url,
                    "anchor_text": anchor_text,
                    "title": reg_title,
                    "step_position": step_pos,
                    "step_description": reg_title,
                    "section_heading": current_country,
                })
                current_title = ""

            elif el.name in ("p", "li"):
                bolds = el.find_all(["strong", "b"])
                for b in bolds:
                    bt = b.get_text(strip=True)
                    clean_bt = re.sub(r"^(Link\s*:\s*|Link\s*)", "", bt, flags=re.I).strip()
                    if len(clean_bt) > 3 and not clean_bt.lower().startswith("disclaimer"):
                        current_title = clean_bt

                # If element has links
                a_tags = el.find_all("a", href=True)
                for a in a_tags:
                    href = a.get("href", "").strip()
                    if not href or href.startswith(("javascript:", "mailto:", "#")):
                        continue

                    full_url = urljoin(base_url, href)
                    cleaned_url = self._clean_url(full_url)
                    if cleaned_url in seen:
                        continue
                    seen.add(cleaned_url)

                    anchor_text = a.get_text(strip=True)
                    clean_anchor = re.sub(r"^(Link\s*:\s*|Link\s*)", "", anchor_text, flags=re.I).strip()

                    reg_title = current_title or clean_anchor or cleaned_url
                    step_pos += 1

                    links.append({
                        "section": section_name,
                        "country": current_country,
                        "jurisdiction": current_country,
                        "country_confidence": country_conf,
                        "country_evidence": country_ev,
                        "link_text": reg_title,
                        "text": reg_title,
                        "source_url": cleaned_url,
                        "url": cleaned_url,
                        "anchor_text": anchor_text,
                        "title": reg_title,
                        "step_position": step_pos,
                        "step_description": reg_title,
                        "section_heading": current_country,
                    })

                    if el.name == "li":
                        current_title = ""

        return links

    @staticmethod
    def _clean_url(url: str) -> str:
        parsed = urlparse(url)
        if parsed.netloc.endswith("mykajabi.com") or parsed.path.startswith("/resource_redirect"):
            return url
        # Keep non-tracking parameters
        params = [p for p in parsed.query.split("&") if not p.lower().startswith("utm_")]
        clean_query = "&".join(params)
        return parsed._replace(query=clean_query).geturl()

    def check_links(self, links: list[dict]) -> list[dict]:
        results = []
        for item in links:
            url = item["url"]
            check = self.url_checker.check(url)
            redirect = self.redirect_checker.analyze(check)
            merged = {**item, **check, **redirect}
            results.append(merged)
        return results
