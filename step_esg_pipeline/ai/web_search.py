"""No-key web search executor (DuckDuckGo) used to ground LLM replacement research.

Models like DeepSeek can't browse; they request a `web_search` function call, and this
executor actually performs the search so candidate URLs come from real current results
instead of the model's memory. Degrades to an empty list if the backend is unavailable,
in which case the model simply answers ungrounded.
"""
import logging
from typing import List, Dict

logger = logging.getLogger("web_search")


def web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    if not query or not query.strip():
        return []
    try:
        from ddgs import DDGS
    except Exception:
        try:
            from duckduckgo_search import DDGS  # older package name
        except Exception:
            logger.debug("No DuckDuckGo search package installed; grounding disabled.")
            return []
    try:
        with DDGS() as d:
            rows = d.text(query, max_results=max_results)
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("href") or r.get("url", ""),
                "snippet": r.get("body", ""),
            }
            for r in rows
        ]
    except Exception as e:
        logger.debug(f"web_search failed for {query!r}: {e}")
        return []
