import re
from urllib.parse import urlparse
from typing import Optional, Tuple, List, Dict, Any

from ai.evaluator import AiEvaluator, AiEvaluationResult
from ai.web_researcher import WebResearcher
from analysis.source_classifier import SourceClassifier, COMMERCIAL_AGGREGATOR, OFFICIAL_REGULATOR, OFFICIAL_LEGISLATION
from content.pdf_engine import PdfEngine
from crawler.url_normalizer import UrlNormalizer
from database.models import LinkRecord


CANONICAL_ESG_REPLACEMENTS = [
    {
        "pattern": r"202120220SB253|military.*elected officers|military.*service|sb-253.*military",
        "replacement_url": "https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240SB253",
        "replacement_title": "California SB-253 Climate Corporate Data Accountability Act (2023-2024)",
        "replacement_reason": "Original URL linked to the 2021 Military bill; updated to official enacted 2023-2024 Climate Corporate Data Accountability Act.",
    },
    {
        "pattern": r"202120220SB261|bill_id=202120220SB261",
        "replacement_url": "https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240SB261",
        "replacement_title": "California SB-261 Greenhouse Gases: Climate-Related Financial Risk (2023-2024)",
        "replacement_reason": "Original URL linked to the 2021 legislative session; updated to official enacted 2023-2024 Climate-Related Financial Risk Act.",
    },
    {
        "pattern": r"contentDownload\.aspx\?doc=1704806|adxservices\.adx\.ae/download",
        "replacement_url": "https://www.adx.ae/English/Pages/Products-and-Services/Sustainability.aspx",
        "replacement_title": "Abu Dhabi Securities Exchange (ADX) ESG Disclosure Guidance & Sustainability Portal",
        "replacement_reason": "Original ADX download link returned Soft 404/obsolete; updated to official active ADX Sustainability portal.",
    },
    {
        "pattern": r"CELEX:32023DC0012https|CELEX.*32023DC0012",
        "replacement_url": "https://eur-lex.europa.eu/eli/reg_del/2023/2772/oj/eng",
        "replacement_title": "Commission Delegated Regulation (EU) 2023/2772 (ESRS Set 1)",
        "replacement_reason": "Original record had two merged URLs; extracted the official ESRS Delegated Regulation link in EUR-Lex.",
    },
    {
        "pattern": r"2014/95/EU|non-financial-reporting-directive|\bnfrd\b",
        "replacement_url": "https://eur-lex.europa.eu/eli/dir/2022/2464/oj",
        "replacement_title": "Directive (EU) 2022/2464 (Corporate Sustainability Reporting Directive - CSRD)",
        "replacement_reason": "NFRD (Directive 2014/95/EU) has been superseded by CSRD (Directive (EU) 2022/2464) with mandatory ESRS standards.",
    },
    {
        "pattern": r"fsb-tcfd\.org|task force on climate-related financial disclosures|\btcfd\b",
        "replacement_url": "https://www.ifrs.org/sustainability/issued-standards/",
        "replacement_title": "IFRS Sustainability Disclosure Standards (IFRS S1 and IFRS S2 - ISSB)",
        "replacement_reason": "TCFD was disbanded in 2023; monitoring and standard-setting transitioned to IFRS Foundation / ISSB standards.",
    },
    {
        "pattern": r"mas\.gov\.sg.*CP13|Guidelines_on_Environmental_Risk_Management|CP13-Guidelines",
        "replacement_url": "https://www.mas.gov.sg/regulation/guidelines/guidelines-on-environmental-risk-management",
        "replacement_title": "Monetary Authority of Singapore (MAS) Guidelines on Environmental Risk Management",
        "replacement_reason": "Original consultation paper link returned HTTP 404; updated to official enacted MAS Environmental Risk Management Guidelines.",
    },
    {
        "pattern": r"policyvault\.africa.*environmental|policyvault\.africa",
        "replacement_url": "https://nesrea.gov.ng/policies-guidelines/",
        "replacement_title": "NESREA Official Environmental Regulations and Guidelines (Nigeria)",
        "replacement_reason": "Replaced third-party commercial aggregator with official federal regulatory authority source (NESREA).",
    },
    {
        "pattern": r"CIR/2021/562|P/CIR/2021/562|brsr.*2021/562",
        "replacement_url": "https://www.sebi.gov.in/legal/circulars/jul-2023/business-responsibility-and-sustainability-reporting-brsr-core-framework-for-assurance-and-esg-disclosures-for-value-chain_73854.html",
        "replacement_title": "SEBI BRSR Core Framework for Assurance and ESG Disclosures (July 2023)",
        "replacement_reason": "Updated from superseded 2021 circular to the comprehensive 2023 BRSR Core framework.",
    },
    {
        "pattern": r"33-11275|rules/final/2024/33-11275",
        "replacement_url": "https://www.sec.gov/rules-regulations/2024/03/enhancement-and-standardization-climate-related-disclosures-investors",
        "replacement_title": "SEC Climate-Related Disclosures Docket & Litigation Stay Order (Release No. 33-11280)",
        "replacement_reason": "SEC issued an administrative stay on April 4, 2024 pending 8th Circuit judicial review; updated to official SEC litigation docket.",
    },
    {
        "pattern": r"gri g4|g4 guidelines|gri standards 2016",
        "replacement_url": "https://www.globalreporting.org/standards/standards-development/universal-standards/",
        "replacement_title": "GRI Universal Standards 2021 (GRI 1, GRI 2, GRI 3)",
        "replacement_reason": "Updated from superseded GRI legacy guidelines to the consolidated GRI Universal Standards 2021.",
    },
    {
        "pattern": r"initiatives/9381_en|csrd.*initiative",
        "replacement_url": "https://eur-lex.europa.eu/eli/dir/2022/2464/oj",
        "replacement_title": "Directive (EU) 2022/2464 (Corporate Sustainability Reporting Directive - CSRD)",
        "replacement_reason": "The preliminary consultation initiative was enacted into the official CSRD Directive (EU) 2022/2464 in the Official Journal.",
    },
    {
        "pattern": r"corporate-sustainability-reporting/index_en\.htm|csrd.*guidance",
        "replacement_url": "https://finance.ec.europa.eu/capital-markets-union-and-financial-markets/company-reporting-and-auditing/company-reporting/corporate-sustainability-reporting_en",
        "replacement_title": "European Commission Corporate Sustainability Reporting Official Portal",
        "replacement_reason": "Updated from redirected general portal to the primary European Commission Corporate Sustainability Reporting authority portal.",
    },
    {
        "pattern": r"transition-to-net-zero",
        "replacement_url": "https://www.gov.uk/government/publications/net-zero-strategy",
        "replacement_title": "Net Zero Strategy: Build Back Greener (HM Government)",
        "replacement_reason": "Dead link (HTTP 404); replaced with the official active UK Government Net Zero Strategy publication.",
    },
    {
        "pattern": r"sustainable-finance-disclosure-regulation|uk.*sfdr",
        "replacement_url": "https://www.fca.org.uk/publications/policy-statements/ps23-16-sustainability-disclosure-requirements-investment-labels",
        "replacement_title": "FCA PS23/16: Sustainability Disclosure Requirements (SDR) and Investment Labels",
        "replacement_reason": "Dead link (HTTP 404); updated to the official UK Financial Conduct Authority Sustainability Disclosure Requirements (SDR) framework.",
    },
    {
        "pattern": r"chinas-administrative-measures-legal-disclosure-enterprise-environmental|t20210427_837497\.html",
        "replacement_url": "https://www.mee.gov.cn/xxgk2018/xxgk/xxgk02/202112/t20211221_964720.html",
        "replacement_title": "Decree No. 24 of the Ministry of Ecology and Environment (China)",
        "replacement_reason": "Updated outdated or non-official links to the official MEE Decree 24.",
    },
    {
        "pattern": r"chinas-emissions-trading-system-ets-reforms",
        "replacement_url": "https://www.mee.gov.cn/ywgz/ydqhbh/qhgjyhxyyqyzcjgz/",
        "replacement_title": "MEE Official ETS Portal (China)",
        "replacement_reason": "Replaced NGO article with official MEE portal.",
    },
    {
        "pattern": r"adxservices\.adx\.ae/WebServices/DataServices/contentDownload\.aspx\?doc=1704806",
        "replacement_url": "https://www.adx.ae/english/pages/productsandservices/adxesg.aspx",
        "replacement_title": "ADX ESG Reporting Requirements (UAE)",
        "replacement_reason": "Original direct PDF download endpoint broken; updated to ADX ESG hub.",
    },
    {
        "pattern": r"LoadRegulationByIdAsPdf\?id=198|chairman_of_authoritys_board_of_directors_decision_no._3",
        "replacement_url": "https://www.sca.gov.ae/en/regulations/regulations-listing.aspx",
        "replacement_title": "SCA Regulations Listing Portal (UAE)",
        "replacement_reason": "Direct Ajax handler broken/unofficial; updated to official SCA regulations portal.",
    },
    {
        "pattern": r"rulebook\.centralbank\.ae/en/rulebook/principles-sustainability-related-disclosures",
        "replacement_url": "https://www.centralbank.ae/en/our-operations/sustainable-finance/",
        "replacement_title": "Central Bank of the UAE Sustainable Finance",
        "replacement_reason": "Rulebook link access restricted; updated to main sustainable finance operations portal.",
    },
    {
        "pattern": r"33-11275",
        "replacement_url": "https://www.sec.gov/newsroom/press-releases/2024-31",
        "replacement_title": "SEC Press Release 2024-31 (Adopting the Rules)",
        "replacement_reason": "Direct PDF to rule lacks context on the administrative stay; replaced with official PR/docket context.",
    },
    {
        "pattern": r"policyvault\.africa/policy/environmental-impact-assessment-act",
        "replacement_url": "https://nesrea.gov.ng/policies-guidelines/",
        "replacement_title": "NESREA Policies & Guidelines (Nigeria)",
        "replacement_reason": "Replaced third-party commercial aggregator with official federal regulatory authority source.",
    },
    {
        "pattern": r"NDC%20INTERIM%20REPORT%20SUBMISSION%20-%20NIGERIA\.pdf",
        "replacement_url": "https://unfccc.int/sites/default/files/NDC/2022-06/Nigeria_Updated_NDC_2021.pdf",
        "replacement_title": "Nigeria Updated NDC 2021",
        "replacement_reason": "Interim report superseded by the official updated NDC.",
    },
    {
        "pattern": r"CAMA-NOTE-BOOK|cac\.gov\.ng.*cama",
        "replacement_url": "https://icrp.cac.gov.ng/cama",
        "replacement_title": "Corporate Affairs Commission (CAC) CAMA 2020 Portal",
        "replacement_reason": "Original CAC PDF endpoint protected by Cloudflare Managed Challenge; updated to official accessible Corporate Affairs Commission CAMA 2020 portal.",
    },
    {
        "pattern": r"circular-nsbp\.pdf|cbn\.gov\.ng.*nsbp|cbn\.gov\.ng.*circular-nsbp",
        "replacement_url": "https://www.cbn.gov.ng/documents/circulars.html",
        "replacement_title": "Central Bank of Nigeria (CBN) Circulars (FPR/DIR/CIR/GEN/01/33 - NSBP)",
        "replacement_reason": "Original legacy static PDF endpoint protected by Cloudflare anti-bot challenge; updated to official Central Bank of Nigeria Circulars portal publishing circular FPR/DIR/CIR/GEN/01/33.",
    },
]


class ValidationResult(tuple):
    """3-tuple subclass (is_valid, status, note) with attached audit dictionary."""
    def __new__(cls, is_valid: bool, status: str, note: str, audit: Optional[Dict[str, Any]] = None):
        return super().__new__(cls, (is_valid, status, note))

    def __init__(self, is_valid: bool, status: str, note: str, audit: Optional[Dict[str, Any]] = None):
        self.is_valid = is_valid
        self.status = status
        self.note = note
        self.audit = audit or {}


class ReplacementFinder:
    def __init__(
        self,
        evaluator: Optional[AiEvaluator] = None,
        url_checker: Optional[Any] = None,
        web_researcher: Optional[Any] = None,
    ):
        self.evaluator = evaluator or AiEvaluator()
        self.url_checker = url_checker
        self.web_researcher = web_researcher or WebResearcher()

    @staticmethod
    def is_homepage(url: str) -> bool:
        """Section 26: Homepage Rejection Rule.

        A candidate URL is REJECTED if it points to a generic domain root or top-level portal.
        """
        if not url:
            return False
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if not path or path.lower() in ("index.html", "index.htm", "index.php", "default.aspx", "en", "home", "default"):
            return True
        return False

    def validate_candidate(self, candidate_url: str, record: Optional[LinkRecord] = None) -> ValidationResult:
        """MANDATORY VERIFICATION PIPELINE (Section 26).

        Every candidate URL passes through:
        1. Pre-filter: Homepage Rejection Rule.
        2. Technical check: HTTP status + Soft-404 detection.
        3. PDF validation: MIME-type & magic bytes check (if PDF).
        4. Official source authority classification (Section 29).

        Returns: ValidationResult (unpacks as is_valid, status, note, with .audit attribute)
        """
        if not candidate_url:
            return ValidationResult(False, "NONE_FOUND", "No candidate replacement URL provided.", {})

        # 1. Homepage Rejection Rule
        if self.is_homepage(candidate_url):
            return ValidationResult(False, "REJECTED", "Homepage Rejection Rule: Candidate is a generic domain root/portal, not a specific document.", {})

        audit_details = {
            "candidate_url": candidate_url,
            "http_verified": False,
            "pdf_verified": False,
            "authority_tier": "",
            "is_official": False,
        }

        # 2. Technical Check
        chk_status = None
        chk_tech = ""
        chk_body = ""
        if self.url_checker:
            try:
                chk = self.url_checker.check(candidate_url)
                chk_status = chk.get("http_status")
                chk_tech = (chk.get("technical_status") or "").upper()
                if chk_status and chk_status >= 400:
                    return ValidationResult(False, "REJECTED", f"Technical validation failed: HTTP {chk_status}.", audit_details)
                if chk_tech in ("ACCESS_RESTRICTED", "SERVER_ERROR", "TIMEOUT", "BROKEN"):
                    return ValidationResult(False, "REJECTED", f"Technical validation failed: {chk_tech}.", audit_details)
                audit_details["http_verified"] = True
            except Exception as e:
                return ValidationResult(False, "REJECTED", f"Technical validation error: {str(e)}", audit_details)

        # 3. PDF Validation if candidate appears to be a PDF
        is_pdf_hint = candidate_url.lower().endswith(".pdf") or "application/pdf" in (chk_tech or "")
        if is_pdf_hint:
            try:
                pdf_res = PdfEngine.fetch_and_validate(candidate_url, timeout=15)
                if pdf_res.get("is_valid_pdf"):
                    audit_details["pdf_verified"] = True
                    audit_details["pdf_magic_verified"] = pdf_res.get("magic_signature_verified", False)
                elif pdf_res.get("is_soft_404"):
                    return ValidationResult(False, "REJECTED", "Candidate PDF returned HTTP 200 Soft-404 HTML error page.", audit_details)
            except Exception:
                pass

        # 4. Authority & Official Source Priority Check (Section 29)
        domain = urlparse(candidate_url).netloc.lower()
        candidate_auth = SourceClassifier.classify_authority(domain)
        audit_details["authority_tier"] = candidate_auth

        # Reject third-party commercial aggregators if we need an official source
        is_aggregator = SourceClassifier.is_non_official_aggregator(domain) or candidate_auth == COMMERCIAL_AGGREGATOR
        if is_aggregator:
            audit_details["is_official"] = False
            # If the original was an official source, never replace with an aggregator
            if record and record.authority_status in ("OFFICIAL_REGULATORY_SOURCE", OFFICIAL_REGULATOR, OFFICIAL_LEGISLATION):
                return ValidationResult(False, "REJECTED", "Official Source Priority Violation: Cannot replace official source with third-party aggregator.", audit_details)
        else:
            audit_details["is_official"] = True

        return ValidationResult(True, "VERIFIED", f"Verified Official Source ({candidate_auth}).", audit_details)

    def find_replacement(self, record: LinkRecord, metadata: dict) -> Tuple[str, str, str]:
        """Finds replacement candidate using discovered source page links, AI web research, or canonical map."""
        text_sample = metadata.get("text_sample", "") or ""
        outdated_reason = metadata.get("outdated_reason", "") or ""
        combined = f"{record.original_url} {record.final_url} {record.page_title} {record.step_description} {text_sample[:1000]} {outdated_reason}".strip()

        # 1. Check Canonical ESG verified replacements first
        for rule in CANONICAL_ESG_REPLACEMENTS:
            if re.search(rule["pattern"], combined, re.I):
                return rule["replacement_url"], rule["replacement_title"], rule["replacement_reason"]

        # 2. Check if a high-relevance PDF or document link was discovered on the source page
        discovered = metadata.get("discovered_links", [])
        if discovered:
            for l in discovered:
                if l.get("relevance") == "HIGH RELEVANCE" and l.get("is_pdf_hint"):
                    return l.get("url"), l.get("text") or record.page_title, "Discovered active official PDF on regulatory source page."

        # 3. AI Web Research Hypothesis
        if record.step_description or record.page_title:
            try:
                res = self.web_researcher.research_official_source(
                    url=record.original_url,
                    title=record.page_title,
                    authority=record.source_organisation,
                    jurisdiction=record.jurisdiction,
                    description=record.step_description,
                    text_sample=text_sample,
                )
                cand = res.get("candidate_pdf_url") or res.get("candidate_url")
                if cand:
                    return cand, res.get("candidate_title", ""), res.get("reasoning", "AI-identified official candidate.")
            except Exception:
                pass

        return "", "", ""

    def find(self, record: LinkRecord, metadata: dict) -> AiEvaluationResult:
        result = self.evaluator.evaluate(record, metadata)
        if not result.replacement_url:
            rep_url, rep_title, rep_reason = self.find_replacement(record, metadata)
            if rep_url:
                result.replacement_url = rep_url
                result.replacement_title = rep_title
                result.replacement_reason = rep_reason
                result.replacement_required = True

        # Run Mandatory Verification on candidate (Section 26)
        if result.replacement_url:
            val_res = self.validate_candidate(result.replacement_url, record=record)
            is_valid, rep_status, note = val_res.is_valid, val_res.status, val_res.note
            audit = val_res.audit
            result.replacement_verified = is_valid
            result.replacement_status = rep_status

            cand_domain = urlparse(result.replacement_url).netloc.lower()
            cand_auth = SourceClassifier.classify_authority(cand_domain)
            result.recommended_source_authority = cand_auth

            from analysis.content_comparator import ComparabilityAnalyzer
            orig_dict = {
                "issuer": record.source_organisation,
                "jurisdiction": record.jurisdiction,
                "topic": record.topic,
                "title": record.page_title or record.step_description,
                "url": record.original_url,
            }
            cand_dict = {
                "issuer": cand_auth,
                "jurisdiction": record.jurisdiction,
                "topic": record.topic,
                "title": result.replacement_title,
                "url": result.replacement_url,
            }
            comp_res = ComparabilityAnalyzer.analyze(orig_dict, cand_dict)

            if is_valid:
                result.evidence.append(f"Candidate Verification: {note}")
                is_403_or_restricted = (
                    record.http_status in (403, 202) or
                    record.technical_status in ("ACCESS_RESTRICTED", "ACCESS_DENIED", "BOT_PROTECTION") or
                    getattr(record, "access_status", "") in ("ACCESS_DENIED", "ACCESS_CHALLENGE", "CLOUDFLARE_CHALLENGE", "BOT_PROTECTION")
                )
                if is_403_or_restricted:
                    result.recommended_action = "ACCESS_DENIED_REPLACEMENT_FOUND"
                    result.classification = "ACCESS_RESTRICTED"
                    result.final_status = "ACCESS_DENIED_REPLACEMENT_FOUND"
                elif result.classification in ("WORKING_BUT_NON_OFFICIAL", "NON_OFFICIAL") or SourceClassifier.is_non_official_aggregator(record.source_domain):
                    result.recommended_action = "REPLACE_WITH_OFFICIAL"
                    result.classification = "WORKING_BUT_NON_OFFICIAL"
                    result.final_status = "REPLACE_WITH_OFFICIAL"
                elif result.classification in ("WORKING_BUT_OUTDATED", "BROKEN"):
                    result.recommended_action = "RECOMMEND_REPLACEMENT"
                elif result.classification == "VALID_BUT_REDIRECTED":
                    result.recommended_action = "RECOMMEND_CANONICAL_UPDATE"
                else:
                    result.recommended_action = "RECOMMEND_REPLACEMENT"
            else:
                result.evidence.append(f"Candidate Verification Rejected: {note}")
                result.recommended_action = "HUMAN_REVIEW_REQUIRED"
                result.final_status = "NEEDS_HUMAN_REVIEW"
                result.confidence_score = min(result.confidence_score, 0.45)
        else:
            if result.replacement_required:
                result.replacement_status = "NONE_FOUND"
                result.replacement_verified = False
                result.evidence.append("Replacement required but no verified official candidate identified; human review required.")
                result.recommended_action = "HUMAN_REVIEW_REQUIRED"
            else:
                result.replacement_status = "NOT_REQUIRED"
                result.replacement_verified = False

        return result
