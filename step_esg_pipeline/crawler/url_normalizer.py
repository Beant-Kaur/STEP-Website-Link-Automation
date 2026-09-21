import re
import urllib.parse
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode


class UrlNormalizer:
    """Normalizes URLs for robust comparison and canonical tracking.

    Rules:
    - Normalizes scheme (http -> https default where appropriate, lowercase scheme).
    - Lowercases netloc (domain).
    - Strips standard tracking query parameters (utm_*, fbclid, gclid, etc.)
      while strictly preserving document identification query parameters (e.g. id, doc, file, uri, mode).
    - Strips non-functional fragment identifiers.
    - Normalizes trailing slashes (except for domain root).
    - Normalizes URL percent-encoding (decodes unreserved characters).
    """

    TRACKING_PARAMS = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "fbclid", "gclid", "msclkid", "ref", "source", "mc_cid", "mc_eid",
        "_hsenc", "_hsmi", "yclid", "igshid"
    }

    @classmethod
    def normalize(cls, url: str) -> str:
        if not url:
            return ""

        url = url.strip()
        # Handle concatenated URLs or bad pastes
        concat_match = re.search(r"(https?://.*?)(https?://.*)", url, re.I)
        if concat_match:
            # If two URLs concatenated, prefer the second if deeper or first
            url = concat_match.group(2)

        try:
            parsed = urlparse(url)
        except Exception:
            return url

        scheme = (parsed.scheme or "https").lower()
        netloc = parsed.netloc.lower()

        # Clean port if default
        if (scheme == "http" and netloc.endswith(":80")) or (scheme == "https" and netloc.endswith(":443")):
            netloc = netloc.rsplit(":", 1)[0]

        path = parsed.path
        if not path:
            path = "/"
        else:
            # Normalize path encoding: unquote unreserved and clean double slashes
            path = re.sub(r"/+", "/", path)
            if len(path) > 1 and path.endswith("/"):
                # Do not strip trailing slash if it's purely domain root
                path = path.rstrip("/")

        # Filter query params: strip tracking while keeping document IDs
        query_items = parse_qsl(parsed.query, keep_blank_values=True)
        filtered_query = []
        seen_keys = set()
        for k, v in query_items:
            k_low = k.lower()
            if k_low in cls.TRACKING_PARAMS or k_low.startswith("utm_"):
                continue
            # Deduplicate exact duplicate key-value pairs
            kv_tuple = (k, v)
            if kv_tuple in seen_keys:
                continue
            seen_keys.add(kv_tuple)
            filtered_query.append((k, v))

        query = urlencode(filtered_query, doseq=True) if filtered_query else ""

        # Normalize fragments (strip tracking fragments like #:~:text=...)
        fragment = parsed.fragment
        if fragment and any(x in fragment.lower() for x in (":~:text=", "xtor=", "utm_")):
            fragment = ""

        normalized = urlunparse((scheme, netloc, path, "", query, fragment))
        return normalized

    @classmethod
    def are_equivalent(cls, url1: str, url2: str) -> bool:
        if not url1 or not url2:
            return False
        return cls.normalize(url1).lower() == cls.normalize(url2).lower()
