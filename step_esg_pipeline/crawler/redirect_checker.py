import re
from typing import Optional
import requests
from urllib.parse import urljoin, urlparse

from database.models import LinkRecord


class RedirectChecker:
    def analyze(self, check_result: dict) -> dict:
        redirect_chain = check_result.get("redirect_chain", [])
        redirect_count = len(redirect_chain)
        final_url = check_result.get("final_url", "")
        final_status = check_result.get("http_status")

        if redirect_count == 0:
            redirect_status = "no_redirect"
        elif redirect_count <= 2:
            redirect_status = "healthy_redirect"
        elif redirect_count <= 5:
            redirect_status = "moderate_redirect"
        else:
            redirect_status = "long_redirect_chain"

        return {
            "redirect_chain": redirect_chain,
            "redirect_count": redirect_count,
            "final_url": final_url,
            "final_status": final_status,
            "final_domain": urlparse(final_url).netloc.lower(),
            "redirect_status": redirect_status,
        }
