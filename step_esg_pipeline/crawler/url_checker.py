import re
import time
from typing import Optional
from urllib.parse import urlparse

import requests


class CaseInsensitiveStatus(str):
    """String subclass that matches case-insensitively for backward compatibility with existing tests."""
    def __eq__(self, other):
        if isinstance(other, str):
            return self.lower() == other.lower()
        return super().__eq__(other)

    def __hash__(self):
        return hash(self.lower())


class UrlChecker:
    def __init__(self, timeout: int = 30, max_retries: int = 2, backoff_factor: float = 1.5):
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "STEP-ESG-Auditor/1.0 (compliance@step-monitoring.org; Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
        })

    # Some official domains block generic browser UAs and require a descriptive,
    # contactable User-Agent per their published access policy (e.g. SEC.gov).
    DOMAIN_HEADER_OVERRIDES = {
        "www.sec.gov": {"User-Agent": "STEP ESG Link Monitor admin@step.org"},
        "sec.gov": {"User-Agent": "STEP ESG Link Monitor admin@step.org"},
        "www.dol.gov": {"User-Agent": "STEP ESG Link Monitor admin@step.org"},
    }

    SOFT_404_PATTERNS = [
        r"\b(404\s*-\s*page\s*not\s*found|page\s*not\s*found|page\s*doesn'?t\s*exist|page\s*does\s*not\s*exist)\b",
        r"\b(resource\s*not\s*found|content\s*not\s*available|content\s*unavailable|this\s*page\s*is\s*unavailable)\b",
        r"\b(the\s*requested\s*(?:page|document|file|url)\s*(?:could\s*not\s*be\s*found|was\s*not\s*found|does\s*not\s*exist))\b",
        r"\b(document\s*not\s*found|file\s*not\s*found|no\s*longer\s*available|sorry,?\s*we\s*can'?t\s*find\s*that\s*page)\b",
        r"\b(error\s*404|404\s*error|404\s*not\s*found|invalid\s*document|document\s*does\s*not\s*exist)\b",
    ]

    def _classify_access(self, response: requests.Response, body_snippet: str, page_title: str = "") -> tuple[str, str]:
        """
        Classifies accessibility per Section 3 & 7:
        Returns (access_status, reason_for_failure)
        """
        status_code = response.status_code
        body_lower = (body_snippet or "").lower()
        title_lower = (page_title or "").lower()
        server_header = response.headers.get("Server", "").lower()
        cf_ray = response.headers.get("cf-ray", "")

        if status_code == 429:
            return "RATE_LIMITED", "HTTP 429 Rate limit exceeded by target server."
        if status_code in (500, 502, 503, 504):
            return "SERVER_ERROR", f"HTTP {status_code} Internal Server Error."
        if status_code in (404, 410):
            return "BROKEN", f"HTTP {status_code} Resource Not Found / Gone."

        if status_code in (403, 202):
            if "just a moment" in title_lower or cf_ray or "cloudflare" in server_header or "cf-chl-" in body_lower or "cloudflare" in body_lower:
                return "CLOUDFLARE_CHALLENGE", "Cloudflare anti-bot security challenge detected."
            if "awswaf" in body_lower or status_code == 202 or "aws" in server_header:
                return "AWS_WAF_CHALLENGE", "AWS WAF anti-bot challenge detected (HTTP 202)."
            if any(k in body_lower for k in ("turnstile", "recaptcha", "hcaptcha", "captcha", "challenge-running", "security check", "verify you are human")):
                return "BOT_PROTECTION", "Automated bot verification / CAPTCHA challenge detected."
            if any(k in body_lower for k in ("enable javascript", "javascript is required", "js challenge", "javascript is disabled")):
                return "JS_CHALLENGE", "Client-side JavaScript execution challenge required."
            if any(k in body_lower for k in ("rate threshold exceeded", "rate limit")):
                return "RATE_LIMITED", "HTTP 403 Rate limit or access policy threshold exceeded."
            if any(k in body_lower for k in ("login", "sign in", "authentication required", "unauthorized", "subscriber")):
                return "LOGIN_REQUIRED", "Access denied: authentication, login, or subscription required."
            if any(k in body_lower for k in ("geographic", "geo-block", "not available in your country", "region restricted")):
                return "GEOGRAPHIC_RESTRICTION", "Access denied: geographic or regional restriction."
            if any(k in body_lower for k in ("robots.txt", "crawler", "scraper blocked")):
                return "ROBOTS_RESTRICTION", "Access denied: crawler/bot policy restriction."
            return "ACCESS_DENIED", "HTTP 403 Forbidden: access denied by remote server."

        if 200 <= status_code < 300:
            if any(k in body_lower for k in ("cf-chl-", "security check to access", "turnstile", "verify you are human")):
                return "ACCESS_CHALLENGE", "Security challenge page served with HTTP 200."
            
            # Stage 3: Soft-404 / Page Not Found Detection
            # Strip script and style tags to prevent false positives from client-side JS error handlers
            body_clean = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", body_snippet, flags=re.DOTALL | re.I)
            body_clean_lower = body_clean.lower()
            combined_check = f"{title_lower} {body_clean_lower[:1500]}"
            for pat in self.SOFT_404_PATTERNS:
                if re.search(pat, combined_check, re.I):
                    return "BROKEN_SOFT_404", "Soft-404: Page returned HTTP 200 but content indicates page not found or unavailable."

            return "ACCESSIBLE", ""

        if 300 <= status_code < 400:
            return "REDIRECTED", f"HTTP {status_code} Redirection."

        return "BROKEN", f"HTTP {status_code} error."

    def check(self, url: str) -> dict:
        result = {
            "url": url,
            "http_status": None,
            "technical_status": CaseInsensitiveStatus("BROKEN"),
            "access_status": "BROKEN",
            "final_url": url,
            "redirect_chain": [],
            "content_type": "",
            "response_time_ms": 0.0,
            "response_size_bytes": 0,
            "domain": urlparse(url).netloc.lower(),
            "reason_for_failure": "",
            "headers": {},
            "page_title": "",
            "timestamp": time.time(),
            "error": None,
            "is_soft_404": False,
            "is_generic_homepage": False,
        }

        start_time = time.perf_counter()
        try:
            per_request_headers = self.DOMAIN_HEADER_OVERRIDES.get(urlparse(url).netloc.lower())
            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                stream=True,
                headers=per_request_headers,
            )
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            result["response_time_ms"] = elapsed_ms
            result["http_status"] = response.status_code
            result["final_url"] = response.url
            result["domain"] = urlparse(response.url).netloc.lower()
            result["content_type"] = response.headers.get("Content-Type", "")
            result["redirect_chain"] = [r.url for r in response.history]

            # Collect key headers
            for h in ("Server", "Content-Type", "Content-Length", "cf-ray", "Retry-After", "Location"):
                if h in response.headers:
                    result["headers"][h] = response.headers[h]

            # Read snippet or HTML body (up to 512KB)
            body_snippet = ""
            html_text = ""
            try:
                if "pdf" in (result["content_type"] or "").lower():
                    raw_chunk = next(response.iter_content(4096), b"")
                    body_snippet = raw_chunk.decode("utf-8", errors="replace")
                else:
                    chunks = []
                    total = 0
                    for chunk in response.iter_content(65536):
                        chunks.append(chunk)
                        total += len(chunk)
                        if total >= 524288:
                            break
                    html_text = b"".join(chunks).decode("utf-8", errors="replace")
                    body_snippet = html_text[:4096]
                    result["html"] = html_text

                title_match = re.search(r"<title[^>]*>(.*?)</title>", body_snippet or html_text, re.I | re.S)
                if title_match:
                    result["page_title"] = title_match.group(1).strip()
            except Exception:
                pass

            # Determine response size
            content_length = response.headers.get("Content-Length")
            if content_length and content_length.isdigit():
                result["response_size_bytes"] = int(content_length)

            # Classify access per Section 3 & 7
            access_status, access_reason = self._classify_access(response, body_snippet, result["page_title"])
            result["access_status"] = access_status
            if access_reason:
                result["reason_for_failure"] = access_reason

            if access_status == "BROKEN_SOFT_404":
                result["is_soft_404"] = True
                result["technical_status"] = CaseInsensitiveStatus("BROKEN")
            elif response.status_code in (202, 403):
                if access_status in ("CLOUDFLARE_CHALLENGE", "AWS_WAF_CHALLENGE", "BOT_PROTECTION", "JS_CHALLENGE"):
                    result["technical_status"] = CaseInsensitiveStatus("BOT_PROTECTION")
                elif access_status == "RATE_LIMITED":
                    result["technical_status"] = CaseInsensitiveStatus("RATE_LIMITED")
                else:
                    result["technical_status"] = CaseInsensitiveStatus("ACCESS_RESTRICTED")
            elif response.status_code in (404, 410):
                result["technical_status"] = CaseInsensitiveStatus("BROKEN")
            elif response.status_code in (500, 502, 503, 504):
                result["technical_status"] = CaseInsensitiveStatus("SERVER_ERROR")
            elif response.status_code == 429:
                result["technical_status"] = CaseInsensitiveStatus("ACCESS_RESTRICTED")
            elif 200 <= response.status_code < 300:
                if len(result["redirect_chain"]) > 0:
                    orig_p = urlparse(url)
                    final_p = urlparse(response.url)
                    # Detect generic homepage redirects
                    is_orig_deep = len(orig_p.path.strip("/").split("/")) > 0 and orig_p.path.strip("/") != ""
                    is_final_root = final_p.path.strip("/") in ("", "index.html", "index.htm", "default.aspx", "en", "home")
                    if is_orig_deep and is_final_root and orig_p.netloc.lower() == final_p.netloc.lower():
                        result["technical_status"] = CaseInsensitiveStatus("WRONG_DESTINATION")
                        result["access_status"] = "WRONG_DESTINATION"
                        result["reason_for_failure"] = "Generic Homepage Redirect: deep document link redirected to domain root."
                        result["is_generic_homepage"] = True
                    elif orig_p.netloc.lower() != final_p.netloc.lower() or orig_p.path.rstrip("/") != final_p.path.rstrip("/"):
                        result["technical_status"] = CaseInsensitiveStatus("REDIRECTED")
                    else:
                        result["technical_status"] = CaseInsensitiveStatus("ACCESSIBLE")
                else:
                    result["technical_status"] = CaseInsensitiveStatus("ACCESSIBLE")
            elif 300 <= response.status_code < 400:
                result["technical_status"] = CaseInsensitiveStatus("REDIRECTED")
            else:
                result["technical_status"] = CaseInsensitiveStatus("BROKEN")

        except requests.exceptions.Timeout:
            result["response_time_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
            result["technical_status"] = CaseInsensitiveStatus("TIMEOUT")
            result["access_status"] = "TIMEOUT"
            result["reason_for_failure"] = "Request timed out"
            result["error"] = "Request timed out"
        except requests.exceptions.SSLError as exc:
            result["response_time_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
            result["technical_status"] = CaseInsensitiveStatus("CONNECTION_ERROR")
            result["access_status"] = "CONNECTION_ERROR"
            result["reason_for_failure"] = f"SSL/TLS Handshake Error: {exc}"
            result["error"] = f"SSL/TLS Handshake Error: {exc}"
        except requests.exceptions.ConnectionError as exc:
            result["response_time_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
            result["technical_status"] = CaseInsensitiveStatus("CONNECTION_ERROR")
            result["access_status"] = "CONNECTION_ERROR"
            result["reason_for_failure"] = f"DNS / Connection Error: {exc}"
            result["error"] = f"DNS / Connection Error: {exc}"
        except requests.exceptions.TooManyRedirects:
            result["response_time_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
            result["technical_status"] = CaseInsensitiveStatus("BROKEN")
            result["access_status"] = "BROKEN"
            result["reason_for_failure"] = "Too many redirects"
            result["error"] = "Too many redirects"
        except requests.exceptions.RequestException as exc:
            result["response_time_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
            result["technical_status"] = CaseInsensitiveStatus("BROKEN")
            result["access_status"] = "BROKEN"
            result["reason_for_failure"] = str(exc)
            result["error"] = str(exc)

        return result
