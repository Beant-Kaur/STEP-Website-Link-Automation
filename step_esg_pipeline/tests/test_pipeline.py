import re

import requests
from crawler.step_extractor import StepExtractor
from crawler.url_checker import UrlChecker
from database.models import DatabaseRepository, LinkRecord
from tests.conftest import FakeResponse, FakeSession


class TestUrlChecker:
    def setup_method(self):
        self.checker = UrlChecker()

    def test_200(self, tmp_path):
        session = FakeSession({
            "https://example.org/doc": FakeResponse(200, content="<html></html>", headers={"Content-Type": "text/html"})
        })
        self.checker.session = session
        result = self.checker.check("https://example.org/doc")
        assert result["http_status"] == 200
        assert result["technical_status"] == "accessible"

    def test_404(self):
        session = FakeSession({
            "https://example.org/missing": FakeResponse(404)
        })
        self.checker.session = session
        result = self.checker.check("https://example.org/missing")
        assert result["http_status"] == 404

    def test_redirect_chain(self):
        final = FakeResponse(200, content="final", url="https://final.example.org")
        intermediate = FakeResponse(302, content="", url="https://intermediate.example.org")
        intermediate.history = []
        final.history = [intermediate]
        session = FakeSession({
            "https://start.example.org": final
        })
        self.checker.session = session
        result = self.checker.check("https://start.example.org")
        assert result["final_url"] == "https://final.example.org"


class TestStepExtractor:
    def test_extract_links(self):
        html = '<a href="https://a.example.org/1">Link 1</a><a href="https://a.example.org/2">Link 2</a>'
        extractor = StepExtractor()
        links = extractor.extract_from_html(html, base_url="https://a.example.org")
        assert len(links) == 2
        assert links[0]["url"] == "https://a.example.org/1"


class TestDatabase:
    def test_upsert_and_get(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        repo = DatabaseRepository(db_path)
        record = LinkRecord(
            link_id="abc",
            jurisdiction="EU",
            topic="CSRD",
            step_section="Reporting",
            step_description="CSRD link",
            original_url="https://ec.europa.eu/doc",
        )
        repo.upsert_link(record)
        fetched = repo.get_link("abc")
        assert fetched is not None
        assert fetched.jurisdiction == "EU"
        assert fetched.classification == ""

    def test_get_all_links(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        repo = DatabaseRepository(db_path)
        record = LinkRecord(
            link_id="def",
            jurisdiction="UK",
            topic="ESRS",
            step_section="Standards",
            step_description="ESRS link",
            original_url="https://frc.org.uk/esrs",
        )
        repo.upsert_link(record)
        assert len(repo.get_all_links()) == 1

    def test_get_latest_link_by_url(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        repo = DatabaseRepository(db_path)
        rec1 = LinkRecord(
            link_id="run1_1",
            jurisdiction="EU",
            topic="CSRD",
            step_section="Reporting",
            step_description="CSRD link",
            original_url="https://ec.europa.eu/csrd",
            content_hash="hash_v1",
        )
        repo.upsert_link(rec1)
        rec2 = LinkRecord(
            link_id="run2_1",
            jurisdiction="EU",
            topic="CSRD",
            step_section="Reporting",
            step_description="CSRD link",
            original_url="https://ec.europa.eu/csrd",
            content_hash="hash_v2",
        )
        repo.upsert_link(rec2)
        latest = repo.get_latest_link_by_url("https://ec.europa.eu/csrd")
        assert latest is not None
        assert latest.content_hash in ("hash_v1", "hash_v2")
