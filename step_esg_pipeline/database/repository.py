import hashlib
from urllib.parse import urlparse

from database.models import DatabaseRepository, LinkRecord


def generate_link_id(url: str, step_section: str, topic: str) -> str:
    raw = f"{step_section}|{topic}|{url}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower()


class LinkInventory:
    def __init__(self, repository: DatabaseRepository):
        self.repository = repository

    def add_link(self, link_id: str, jurisdiction: str, topic: str,
                 step_section: str, step_description: str,
                 original_url: str, link_text: str = "",
                 source_position: str = "") -> LinkRecord:
        record = LinkRecord(
            link_id=link_id,
            jurisdiction=jurisdiction,
            topic=topic,
            step_section=step_section,
            step_description=step_description,
            original_url=original_url,
            current_url=original_url,
            final_url=original_url,
        )
        self.repository.upsert_link(record)
        return record

    def get_all(self) -> list[LinkRecord]:
        return self.repository.get_all_links()

    def get(self, link_id: str) -> LinkRecord | None:
        return self.repository.get_link(link_id)
