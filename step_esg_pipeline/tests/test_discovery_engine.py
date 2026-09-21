import io
import json
import pytest

from analysis.date_engine import UniversalDateEngine
from analysis.version_chain import VersionChainEngine
from content.pdf_engine import PdfEngine
from crawler.link_discovery import LinkDiscoveryEngine, LinkRelevance
from crawler.url_normalizer import UrlNormalizer
from database.models import DatabaseRepository, LinkRecord
from pipeline.orchestrator import PipelineOrchestrator


# ----------------------------------------------------------------------
# 1. UNIVERSAL DATE EXTRACTION TESTS (Sections 19, 20, 21, 22)
# ----------------------------------------------------------------------
class TestUniversalDateEngine:
    def test_universal_date_formats(self):
        test_cases = [
            ("15 March 2025", "2025-03-15"),
            ("15 Mar 2025", "2025-03-15"),
            ("15 MAR 2025", "2025-03-15"),
            ("15/03/2025", "2025-03-15"),
            ("15-03-2025", "2025-03-15"),
            ("15.03.2025", "2025-03-15"),
            ("2025-03-15", "2025-03-15"),
            ("2025/03/15", "2025-03-15"),
            ("March 15, 2025", "2025-03-15"),
            ("Mar 15, 2025", "2025-03-15"),
            ("15th March 2025", "2025-03-15"),
            ("1st January 2025", "2025-01-01"),
            ("2nd February 2025", "2025-02-02"),
            ("3rd March 2025", "2025-03-03"),
            ("15/3/2025", "2025-03-15"),
            ("15-03-25", "2025-03-15"),
            ("03/15/2025", "2025-03-15"),
            ("March 2025", "2025-03"),
            ("2025-03-15T10:30:00Z", "2025-03-15"),
        ]

        for raw_str, expected_iso in test_cases:
            dates = UniversalDateEngine.extract_dates(f"Document notification date: {raw_str}")
            assert len(dates) > 0, f"Failed to extract: {raw_str}"
            assert any(d["normalized_date"] == expected_iso for d in dates), f"Expected {expected_iso} for {raw_str}, got {[d['normalized_date'] for d in dates]}"

    def test_date_in_filename(self):
        url = "https://bahrainbourse.com/resources/files/Sustainability/ESG_11%20June%202020.pdf"
        dates = UniversalDateEngine.extract_dates("", url=url)
        assert len(dates) >= 1
        assert dates[0]["normalized_date"] == "2020-06-11"
        assert dates[0]["location"] == "url_path"

    def test_dynamic_context_understanding(self):
        sample = """
        SEBI Circular dated 12 July 2023.
        This framework shall be effective from 1 April 2024.
        Supersedes previous circular published on 10 May 2021.
        """
        dates = UniversalDateEngine.extract_dates(sample)
        contexts = {d["normalized_date"]: d["context"] for d in dates}
        assert contexts.get("2024-04-01") == "EFFECTIVE_DATE"
        assert contexts.get("2021-05-10") == "PUBLICATION_DATE"

    def test_ambiguous_date_handling(self):
        # 03/04/2025 could be March 4 or April 3
        # In UK/India convention -> 3 April 2025
        dates_uk = UniversalDateEngine.extract_dates("Notice date: 03/04/2025", jurisdiction="India")
        assert len(dates_uk) >= 1
        assert dates_uk[0]["normalized_date"] == "2025-04-03"

        # In US convention -> 4 March 2025
        dates_us = UniversalDateEngine.extract_dates("Notice date: 03/04/2025", jurisdiction="United States")
        assert len(dates_us) >= 1
        assert dates_us[0]["normalized_date"] == "2025-03-04"

    def test_multi_date_comparison_rejects_cms_footer(self):
        sample = """
        Official Directive issued on 15 March 2021.
        All rights reserved © 2026 Government Portal.
        """
        dates = UniversalDateEngine.extract_dates(sample)
        best = UniversalDateEngine.select_best_regulatory_date(dates)
        assert best is not None
        assert best["normalized_date"] == "2021-03-15"
        assert best["context"] == "ISSUE_DATE"


# ----------------------------------------------------------------------
# 2. PDF ENGINE TESTS (Sections 7, 8, 9, 11, 16, 28)
# ----------------------------------------------------------------------
class TestPdfEngine:
    def test_magic_file_signature_verification(self):
        valid_pdf_stream = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj"
        assert PdfEngine.verify_magic_bytes(valid_pdf_stream) is True

        html_stream = b"<!DOCTYPE html><html><body><h1>Not a PDF</h1></body></html>"
        assert PdfEngine.verify_magic_bytes(html_stream) is False

    def test_pdf_endpoint_detection(self):
        assert PdfEngine.is_pdf_url_or_endpoint("https://example.gov/doc.pdf") is True
        assert PdfEngine.is_pdf_url_or_endpoint("https://example.gov/download?id=123", "application/pdf") is True
        assert PdfEngine.is_pdf_url_or_endpoint("https://example.gov/home", "text/html") is False

    def test_pdf_scoring(self):
        pdf_res = {
            "is_valid_pdf": True,
            "magic_signature_verified": True,
            "text_sample": "Securities and Exchange Board of India Circular SEBI/HO/CFD/CMD/CIR/P/2023/123",
            "document_number": "SEBI/HO/CFD/CMD/CIR/P/2023/123",
            "title": "BRSR Core Framework",
            "organisation": "SEBI",
        }
        score = PdfEngine.score_pdf_candidate(pdf_res, target_title="BRSR Core", target_doc_no="SEBI/HO/CFD/CMD/CIR/P/2023/123")
        assert score >= 0.85


# ----------------------------------------------------------------------
# 3. LINK DISCOVERY & URL NORMALIZER (Sections 4, 5, 31)
# ----------------------------------------------------------------------
class TestLinkDiscoveryAndNormalizer:
    def test_url_normalizer(self):
        raw = "HTTPS://WWW.SEBI.GOV.IN/legal/circulars/may-2021/brsr.html/?utm_source=twitter&utm_medium=social&doc_id=99#section1"
        norm = UrlNormalizer.normalize(raw)
        assert "utm_source" not in norm
        assert "doc_id=99" in norm
        assert norm.startswith("https://www.sebi.gov.in/legal/circulars/may-2021/brsr.html")

    def test_link_relevance_classification(self):
        engine = LinkDiscoveryEngine()

        # High relevance: direct circular or PDF
        r1 = engine.classify_link("https://sebi.gov.in/circulars/2023/brsr_core.pdf", anchor_text="Download PDF Circular")
        assert r1 == LinkRelevance.HIGH

        # Irrelevant: social media or login
        r2 = engine.classify_link("https://twitter.com/sebi_india", anchor_text="Follow on Twitter")
        assert r2 == LinkRelevance.IRRELEVANT

        r3 = engine.classify_link("https://sebi.gov.in/portal/login.jsp", anchor_text="Officer Login")
        assert r3 == LinkRelevance.IRRELEVANT


# ----------------------------------------------------------------------
# 4. VERSION CHAIN & DOCUMENT REFERENCES (Sections 23, 24)
# ----------------------------------------------------------------------
class TestVersionChainEngine:
    def test_references_extraction(self):
        text = """
        This Circular supersedes Circular No. CIR/CFD/CMD/10/2015 dated November 04, 2015
        and amends Regulation 34 of LODR Regulations.
        """
        refs = VersionChainEngine.extract_references(text)
        assert len(refs) >= 2
        types = [r["relationship_type"] for r in refs]
        assert "SUPERSEDES" in types
        assert "AMENDS" in types

    def test_version_chain_construction(self):
        refs = [{"relationship_type": "SUPERSEDES", "target_document": "Circular CIR/2015/10"}]
        chain = VersionChainEngine.build_version_chain(
            original_doc_title="BRSR Framework 2021",
            original_doc_number="CIR/2021/562",
            extracted_references=refs,
            candidate_title="BRSR Core 2023",
        )
        assert len(chain) >= 3
        stages = [c["stage"] for c in chain]
        assert "PREVIOUS_VERSION" in stages
        assert "ORIGINAL_DOCUMENT" in stages
        assert "CURRENT_OFFICIAL_VERSION" in stages


# ----------------------------------------------------------------------
# 5. PIPELINE WITHOUT EXCEL DATABASE (Section 2)
# ----------------------------------------------------------------------
class TestPipelineWithoutExcel:
    def test_pipeline_runs_without_excel_dependency(self, tmp_path):
        db_path = str(tmp_path / "test_no_excel.db")
        repo = DatabaseRepository(db_path)
        orchestrator = PipelineOrchestrator(repo)

        sample_html = """
        <html>
          <body>
            <h2>India</h2>
            <p><strong>SEBI BRSR Circular</strong></p>
            <a href="https://bahrainbourse.com/resources/files/Sustainability/ESG_11%20June%202020.pdf">Bahrain ESG Guide</a>
          </body>
        </html>
        """
        run_id = orchestrator.run(sample_html, limit=1)
        assert run_id is not None

        records = repo.get_all_links()
        assert len(records) == 1
        r = records[0]
        assert r.original_url == "https://bahrainbourse.com/resources/files/Sustainability/ESG_11%20June%202020.pdf"
        assert r.pdf_url != "" or r.pdf_validation_status != ""
        # Check that Universal Date extracted the date from the filename!
        assert r.publication_date == "11 June 2020" or "2020" in r.publication_date
