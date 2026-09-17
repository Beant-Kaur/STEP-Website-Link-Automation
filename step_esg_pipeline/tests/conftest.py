import re
from typing import Optional

import requests
from bs4 import BeautifulSoup


class FakeResponse:
    def __init__(self, status_code: int, content: str = "", headers: Optional[dict] = None, url: str = ""):
        self.status_code = status_code
        self.content = content.encode("utf-8")
        self.text = content
        self.headers = headers or {}
        self.url = url
        self.history = []

    def iter_content(self, chunk_size=1024):
        yield self.content

    def raise_for_status(self):
        if 400 <= self.status_code < 600:
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.requests_made = []

    def get(self, url, **kwargs):
        self.requests_made.append({"url": url, "kwargs": kwargs})
        response = self.responses.get(url)
        if response is None:
            raise requests.exceptions.ConnectionError("No fake response configured")
        return response
