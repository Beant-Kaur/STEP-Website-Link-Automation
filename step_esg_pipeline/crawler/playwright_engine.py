import logging
import re
import time
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urljoin, urlparse

from content.html_parser import TECHNICAL_TITLE_PATTERNS
from crawler.url_normalizer import UrlNormalizer

logger = logging.getLogger("playwright_engine")


class PlaywrightEngine:
    """Advanced Browser Automation & Crawler Engine powered by Playwright.

    Features:
    - Launch with local Chrome / Edge for immediate availability.
    - Dynamic SPA rendering (Nuxt, Next, React, Angular).
    - Intelligent link extraction from <a>, <button>, onclick, forms, iframes, embed, object.
    - PDF viewer detection (PDF.js, Google Docs Viewer, custom embedded readers).
    - Network response inspection to detect underlying PDF requests.
    - Download event interception for JS-generated PDFs.
    - Official website internal search execution.
    - Modal / notice dismissal ("Accept cookies", "Agree & Proceed", "Disclaimer").
    - 403 / anti-bot challenge bypass attempt with real browser context.
    """

    def __init__(self, headless: bool = True, timeout: int = 25000):
        self.headless = headless
        self.timeout = timeout
        self._playwright = None
        self._browser = None
        self._browser_type = "chrome"

    def _ensure_browser(self):
        if self._browser is not None:
            return self._browser

        from playwright.sync_api import sync_playwright
        self._playwright = sync_playwright().start()

        # Try local Chrome first, then Edge, then default Chromium
        for channel in ("chrome", "msedge", None):
            try:
                launch_args = {
                    "headless": self.headless,
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-infobars",
                    ]
                }
                if channel:
                    launch_args["channel"] = channel
                self._browser = self._playwright.chromium.launch(**launch_args)
                self._browser_type = channel or "chromium"
                break
            except Exception as e:
                logger.debug(f"Failed to launch with channel {channel}: {e}")

        if self._browser is None:
            raise RuntimeError("Could not launch Playwright browser (Chrome, Edge, or Chromium).")
        return self._browser

    def close(self):
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    def __enter__(self):
        self._ensure_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def inspect_url(
        self,
        url: str,
        click_download_buttons: bool = True,
        search_query: str = "",
        max_scrolls: int = 2,
    ) -> Dict[str, Any]:
        """Deep inspection of a URL via Playwright.

        Returns comprehensive information:
        - final_url, title, status_code, html
        - discovered_links (categorized)
        - discovered_pdf_urls (direct, viewer, iframe, intercepted)
        - viewer_detected (PDF.js, Google, etc.)
        - search_results (if search_query was provided)
        - network_pdf_urls (PDF URLs intercepted during network activity)
        - downloaded_pdf_data (bytes if download was triggered)
        """
        browser = self._ensure_browser()
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            accept_downloads=True,
            ignore_https_errors=True,
        )
        page = context.new_page()
        try:
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        except Exception:
            pass

        result: Dict[str, Any] = {
            "initial_url": url,
            "final_url": url,
            "title": "",
            "http_status": 200,
            "html": "",
            "text": "",
            "is_access_denied": False,
            "is_challenge_page": False,
            "is_challenge_resolved": False,
            "viewer_detected": "",
            "discovered_pdf_urls": [],
            "discovered_links": [],
            "network_pdf_urls": [],
            "downloaded_pdf": None,
            "search_results": [],
            "error": None,
        }

        # Intercept network responses for PDFs
        def on_response(resp):
            try:
                ct = resp.headers.get("content-type", "").lower()
                r_url = resp.url
                if "application/pdf" in ct or r_url.lower().endswith(".pdf") or ".pdf?" in r_url.lower():
                    if r_url not in result["network_pdf_urls"]:
                        result["network_pdf_urls"].append(r_url)
            except Exception:
                pass

        page.on("response", on_response)

        # Track download events
        download_holder = []
        def on_download(download):
            try:
                download_holder.append(download)
            except Exception:
                pass
        page.on("download", on_download)

        try:
            # Navigate
            response = page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")
            if response:
                result["http_status"] = response.status
                result["final_url"] = page.url

            # Small wait for dynamic hydration
            page.wait_for_timeout(1500)

            # Check if page is facing AWS WAF, Cloudflare, or JS challenge
            page_content_pre = ""
            try:
                page_content_pre = (page.content() or "").lower()
            except Exception:
                page_content_pre = ""

            is_bot_challenge = (
                result["http_status"] in (202, 403)
                or "awswaf" in page_content_pre
                or "challenge.js" in page_content_pre
                or page.query_selector("#challenge-container") is not None
                or "cf-chl-" in page_content_pre
                or "just a moment" in (page.title() or "").lower()
            )
            if is_bot_challenge:
                # Wait up to 10 seconds for token acquisition and page reload
                for _ in range(10):
                    page.wait_for_timeout(1000)
                    try:
                        cur_title = page.title() or ""
                        cur_body = page.inner_text("body") if page.query_selector("body") else ""
                        is_tech_title = any(re.search(pat, cur_title, re.I) for pat in TECHNICAL_TITLE_PATTERNS)
                        if len(cur_body) > 300 and not page.query_selector("#challenge-container") and not is_tech_title:
                            result["http_status"] = 200
                            result["is_challenge_resolved"] = True
                            result["final_url"] = page.url
                            break
                    except Exception:
                        continue

            # Check if this is a direct PDF URL or PDF extension loaded in browser
            is_pdf_endpoint = (
                (response and "application/pdf" in (response.headers.get("content-type", "").lower()))
                or url.lower().endswith(".pdf")
                or "/download" in url.lower()
                or "chrome-extension://" in (page.url or "")
            )
            if is_pdf_endpoint and (response is None or response.status == 200):
                result["http_status"] = 200
                result["is_access_denied"] = False
                result["is_challenge_resolved"] = True
                if url not in result["discovered_pdf_urls"]:
                    result["discovered_pdf_urls"].append(url)

            # Check for cookie/disclaimer popups and dismiss them
            self._dismiss_modals(page)

            # Check if page is access denied / challenge
            body_text = ""
            try:
                body_text = page.inner_text("body") if page.query_selector("body") else ""
            except Exception:
                body_text = ""
            title = ""
            try:
                title = page.title() or ""
            except Exception:
                title = ""
            result["title"] = title
            result["text"] = body_text[:6000]

            low_text = body_text.lower()
            if any(x in low_text for x in ("access denied", "403 forbidden", "cf-chl-", "verify you are human", "checking your browser")):
                result["is_access_denied"] = True
                if "cf-chl-" in low_text or "verify you are human" in low_text or "checking your browser" in low_text or "just a moment" in low_text:
                    result["is_challenge_page"] = True
            elif len(body_text) > 300:
                result["is_access_denied"] = False
                result["is_challenge_page"] = False
            elif is_pdf_endpoint and result["http_status"] == 200:
                result["is_access_denied"] = False
                result["is_challenge_page"] = False

            # Scroll down to trigger lazy loading
            for _ in range(max_scrolls):
                try:
                    page.evaluate("window.scrollBy(0, 600)")
                    page.wait_for_timeout(400)
                except Exception:
                    pass

            # Inspect HTML safely
            html = ""
            try:
                html = page.content()
            except Exception:
                html = ""
            result["html"] = html

            # 1. Detect PDF Viewers
            viewer_type, viewer_pdf = self._detect_pdf_viewer(page, html, result["final_url"])
            if viewer_type:
                result["viewer_detected"] = viewer_type
                if viewer_pdf and viewer_pdf not in result["discovered_pdf_urls"]:
                    result["discovered_pdf_urls"].append(viewer_pdf)

            # 2. Extract links and buttons from DOM
            extracted_links = self._extract_dom_links(page, result["final_url"])
            result["discovered_links"] = extracted_links

            # Pull all discovered PDF links into discovered_pdf_urls
            for item in extracted_links:
                href = item.get("url", "")
                if self._is_pdf_candidate(href, item.get("text", ""), item.get("tag", "")):
                    if href not in result["discovered_pdf_urls"]:
                        result["discovered_pdf_urls"].append(href)

            # Add network intercepted PDFs
            for net_url in result["network_pdf_urls"]:
                if net_url not in result["discovered_pdf_urls"]:
                    result["discovered_pdf_urls"].append(net_url)

            # 3. If requested and download buttons exist, attempt click if no PDF URL found yet
            if click_download_buttons and not result["discovered_pdf_urls"]:
                clicked_pdf = self._try_click_download_controls(page, result["final_url"])
                if clicked_pdf and clicked_pdf not in result["discovered_pdf_urls"]:
                    result["discovered_pdf_urls"].append(clicked_pdf)

            # 4. If search query provided, execute on-site search
            if search_query:
                search_results = self._execute_site_search(page, search_query, result["final_url"])
                result["search_results"] = search_results

            # Check intercepted downloads
            if download_holder:
                dl = download_holder[0]
                result["downloaded_pdf"] = {
                    "suggested_filename": dl.suggested_filename,
                    "url": dl.url,
                }
                if dl.url and dl.url not in result["discovered_pdf_urls"]:
                    result["discovered_pdf_urls"].append(dl.url)

        except Exception as exc:
            result["error"] = str(exc)
            logger.debug(f"Playwright inspection error for {url}: {exc}")
        finally:
            try:
                context.close()
            except Exception:
                pass

        return result

    def _dismiss_modals(self, page):
        """Attempts to click common consent / modal buttons."""
        selectors = [
            "button:has-text('Accept')",
            "button:has-text('I Agree')",
            "button:has-text('Agree')",
            "button:has-text('Accept All')",
            "button:has-text('Allow All')",
            "button:has-text('Continue')",
            "button:has-text('Close')",
            "button:has-text('Dismiss')",
            ".cookie-accept",
            "#accept-cookies",
        ]
        for sel in selectors:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click(timeout=1000)
                    page.wait_for_timeout(300)
                    break
            except Exception:
                continue

    def _detect_pdf_viewer(self, page, html: str, base_url: str) -> Tuple[str, str]:
        """Detects whether page embeds a PDF viewer and identifies underlying PDF."""
        # A. PDF.js viewer pattern (viewer.html?file=...)
        pdfjs_match = re.search(r'viewer\.html\?file=([^"\'#&>]+)', html, re.I)
        if pdfjs_match:
            raw_file = urllib.parse.unquote(pdfjs_match.group(1))
            full_pdf = urljoin(base_url, raw_file)
            return "PDF.js Viewer", full_pdf

        # B. Google Docs viewer (viewer?url=... or /view?url=...)
        google_match = re.search(r'docs\.google\.com/viewer\?(?:[^"\'>]*&)?url=([^"\'&>]+)', html, re.I)
        if google_match:
            raw_file = urllib.parse.unquote(google_match.group(1))
            return "Google Docs Viewer", raw_file

        # C. Embedded PDF tags: <embed>, <object>, <iframe> with type=application/pdf or .pdf src
        try:
            embed_elements = page.query_selector_all("iframe, embed, object")
            for el in embed_elements:
                src = el.get_attribute("src") or el.get_attribute("data") or ""
                el_type = el.get_attribute("type") or ""
                if "application/pdf" in el_type.lower() or src.lower().endswith(".pdf") or ".pdf?" in src.lower():
                    full_pdf = urljoin(base_url, src)
                    return "Embedded PDF Viewer", full_pdf
        except Exception:
            pass

        # D. Generic PDF Viewer / Reader wrapper
        if "/pdf-viewer" in base_url.lower() or "/viewer" in base_url.lower() or "/document-viewer" in base_url.lower():
            # Look for iframe or download link inside viewer
            try:
                iframe = page.query_selector("iframe")
                if iframe:
                    iframe_src = iframe.get_attribute("src") or ""
                    if iframe_src:
                        return "Document Viewer (IFrame)", urljoin(base_url, iframe_src)
            except Exception:
                pass
            return "Document Viewer Page", ""

        return "", ""

    def _is_pdf_candidate(self, url: str, text: str = "", tag: str = "") -> bool:
        if not url:
            return False
        url_low = url.lower()
        text_low = text.lower()
        if url_low.endswith(".pdf") or ".pdf?" in url_low or "/pdf/" in url_low:
            return True
        if "download" in url_low and any(q in url_low for q in ("id=", "doc=", "file=", "pdf", "circular")):
            return True
        if any(w in text_low for w in ("download pdf", "view pdf", "download circular", "view document", "official pdf")):
            return True
        return False

    def _extract_dom_links(self, page, base_url: str) -> List[Dict[str, Any]]:
        """Extracts all clickable elements: <a>, <button>, <form>, cards, and links."""
        links = []
        seen = set()

        # Fast in-browser DOM extraction via single page.evaluate call
        try:
            raw_items = page.evaluate("""() => {
                const results = [];
                const links = document.querySelectorAll('a[href]');
                for (let i = 0; i < links.length && i < 300; i++) {
                    const a = links[i];
                    const href = a.getAttribute('href') || '';
                    if (!href || href.startsWith('javascript:') || href.startsWith('mailto:') || href.startsWith('#')) continue;
                    results.push({
                        tag: 'a',
                        href: href,
                        text: (a.innerText || a.textContent || '').trim(),
                        title: a.getAttribute('title') || '',
                        aria: a.getAttribute('aria-label') || ''
                    });
                }
                const btns = document.querySelectorAll("button, .btn, [role='button'], input[type='button']");
                for (let i = 0; i < btns.length && i < 50; i++) {
                    const btn = btns[i];
                    results.push({
                        tag: 'button',
                        href: btn.getAttribute('data-url') || btn.getAttribute('data-href') || btn.getAttribute('data-file') || '',
                        text: (btn.innerText || btn.textContent || '').trim(),
                        title: btn.getAttribute('title') || '',
                        aria: btn.getAttribute('aria-label') || ''
                    });
                }
                return results;
            }""")
            for item in raw_items:
                href = item.get("href", "")
                if not href:
                    continue
                full_url = urljoin(base_url, href)
                norm_url = UrlNormalizer.normalize(full_url)
                if norm_url in seen:
                    continue
                seen.add(norm_url)
                text = item.get("text", "")
                combined_label = f"{text} {item.get('title', '')} {item.get('aria', '')}".strip()
                links.append({
                    "tag": item.get("tag", "a"),
                    "url": full_url,
                    "normalized_url": norm_url,
                    "text": text,
                    "label": combined_label,
                    "is_pdf_hint": self._is_pdf_candidate(full_url, combined_label, item.get("tag", "a")),
                })
        except Exception:
            pass

        return links

    def _try_click_download_controls(self, page, base_url: str) -> Optional[str]:
        """Looks for 'Download' or 'View Document' buttons and triggers them to find PDF."""
        download_selectors = [
            "a:has-text('Download PDF')",
            "button:has-text('Download PDF')",
            "a:has-text('Download')",
            "button:has-text('Download')",
            "a:has-text('View PDF')",
            "button:has-text('View PDF')",
            "a:has-text('Full Document')",
            ".download-btn",
            ".pdf-download",
        ]
        for sel in download_selectors:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    href = el.get_attribute("href")
                    if href:
                        return urljoin(base_url, href)
            except Exception:
                continue
        return None

    def _execute_site_search(self, page, query: str, base_url: str) -> List[Dict[str, str]]:
        """Finds search boxes on the official site, inputs query, submits, and scrapes results."""
        results = []
        search_input_selectors = [
            "input[type='search']",
            "input[name*='search']",
            "input[id*='search']",
            "input[placeholder*='search' i]",
            "input[placeholder*='find' i]",
            ".search-input",
        ]
        found_input = None
        for sel in search_input_selectors:
            try:
                inp = page.query_selector(sel)
                if inp and inp.is_visible():
                    found_input = inp
                    break
            except Exception:
                continue

        if not found_input:
            return results

        try:
            found_input.fill(query)
            page.wait_for_timeout(300)
            # Submit via Enter
            found_input.press("Enter")
            page.wait_for_timeout(2500)

            # Extract result links
            result_links = page.query_selector_all("a[href]")
            for a in result_links[:15]:
                href = a.get_attribute("href") or ""
                text = (a.inner_text() or "").strip()
                if href and not href.startswith(("javascript:", "#")):
                    full = urljoin(page.url, href)
                    results.append({
                        "url": full,
                        "title": text or href,
                    })
        except Exception as e:
            logger.debug(f"Site search execution error: {e}")

        return results
