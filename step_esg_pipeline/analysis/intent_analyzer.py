import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IntentProfile:
    expected_subject: str
    expected_authority: str
    expected_jurisdiction: str
    expected_framework: str
    expected_document_type: str
    expected_document_number: str
    mandatory_keywords: list[str] = field(default_factory=list)
    context_summary: str = ""


class IntentAnalyzer:
    @staticmethod
    def infer_intent(
        original_url: str,
        link_text: str = "",
        step_description: str = "",
        step_section: str = "",
        jurisdiction: str = "",
        topic: str = "",
        page_title: str = "",
        metadata: Optional[dict] = None,
    ) -> IntentProfile:
        meta = metadata or {}
        combined_context = f"{original_url} {link_text} {step_description} {step_section} {page_title} {meta.get('document_number', '')}".strip()
        context_lower = combined_context.lower()

        expected_authority = ""
        expected_jurisdiction = jurisdiction or ""
        expected_framework = ""
        expected_document_type = "Regulatory Document"
        expected_document_number = meta.get("document_number", "")
        mandatory_keywords = []

        # 1. Authority and Jurisdiction Inference
        if "sebi.gov.in" in context_lower or "sebi" in context_lower:
            expected_authority = "SEBI (Securities and Exchange Board of India)"
            expected_jurisdiction = expected_jurisdiction or "India"
        elif "rbi.org.in" in context_lower or "rbi" in context_lower:
            expected_authority = "Reserve Bank of India (RBI)"
            expected_jurisdiction = expected_jurisdiction or "India"
        elif "mca.gov.in" in context_lower:
            expected_authority = "Ministry of Corporate Affairs (India)"
            expected_jurisdiction = expected_jurisdiction or "India"
        elif "eur-lex.europa.eu" in context_lower or "ec.europa.eu" in context_lower or "europa.eu" in context_lower:
            expected_authority = "European Commission / European Union"
            expected_jurisdiction = expected_jurisdiction or "European Union"
        elif "sec.gov" in context_lower:
            expected_authority = "US Securities and Exchange Commission (SEC)"
            expected_jurisdiction = expected_jurisdiction or "United States"
        elif "legislature.ca.gov" in context_lower or "sb-253" in context_lower or "sb 253" in context_lower or "sb253" in context_lower:
            expected_authority = "California State Legislature"
            expected_jurisdiction = expected_jurisdiction or "California, United States"
        elif "legislation.gov.uk" in context_lower or "gov.uk" in context_lower:
            expected_authority = "UK Government / Parliament"
            expected_jurisdiction = expected_jurisdiction or "United Kingdom"
        elif "mas.gov.sg" in context_lower:
            expected_authority = "Monetary Authority of Singapore (MAS)"
            expected_jurisdiction = expected_jurisdiction or "Singapore"
        elif "adx.ae" in context_lower or "adxservices" in context_lower:
            expected_authority = "Abu Dhabi Securities Exchange (ADX)"
            expected_jurisdiction = expected_jurisdiction or "United Arab Emirates"
        elif "nesrea.gov.ng" in context_lower or "policyvault.africa" in context_lower:
            expected_authority = "NESREA (Nigeria)"
            expected_jurisdiction = expected_jurisdiction or "Nigeria"
        elif "fsb-tcfd.org" in context_lower or "tcfd" in context_lower:
            expected_authority = "FSB / TCFD (now IFRS / ISSB)"
            expected_jurisdiction = expected_jurisdiction or "Global"

        # 2. Framework & Subject Inference
        if "brsr" in context_lower:
            expected_framework = "SEBI BRSR Core Framework"
            expected_document_type = "Circular / Framework"
            mandatory_keywords = ["brsr", "sustainability", "assurance", "disclosures"]
            if "core" in context_lower:
                mandatory_keywords.append("core")
            expected_subject = "SEBI BRSR Core framework for assurance and ESG disclosures for value chain"
            if not expected_document_number:
                expected_document_number = "SEBI/HO/CFD/CFD-SEC-2/P/CIR/2023/122"

        elif "sb253" in context_lower or "sb-253" in context_lower or "sb 253" in context_lower or "climate corporate data accountability" in context_lower:
            expected_framework = "California SB-253"
            expected_document_type = "Enacted Statute / Legislation"
            expected_subject = "California SB-253 Climate Corporate Data Accountability Act"
            expected_document_number = "202320240SB253"
            mandatory_keywords = ["climate", "corporate", "data", "accountability", "greenhouse gas", "emissions"]

        elif "sb261" in context_lower or "sb-261" in context_lower or "sb 261" in context_lower or "climate-related financial risk" in context_lower:
            expected_framework = "California SB-261"
            expected_document_type = "Enacted Statute / Legislation"
            expected_subject = "California SB-261 Greenhouse Gases: Climate-Related Financial Risk"
            expected_document_number = "202320240SB261"
            mandatory_keywords = ["climate", "financial risk", "tcfd", "greenhouse gases"]

        elif "esrs" in context_lower or "2023/2772" in context_lower:
            expected_framework = "European Sustainability Reporting Standards (ESRS Set 1)"
            expected_document_type = "Commission Delegated Regulation"
            expected_subject = "Commission Delegated Regulation (EU) 2023/2772 supplementing Directive 2013/34/EU (ESRS Set 1)"
            expected_document_number = "2023/2772"
            mandatory_keywords = ["esrs", "sustainability", "reporting", "standards", "delegated regulation"]

        elif "csrd" in context_lower or "2022/2464" in context_lower:
            expected_framework = "Corporate Sustainability Reporting Directive (CSRD)"
            expected_document_type = "Directive"
            expected_subject = "Directive (EU) 2022/2464 Corporate Sustainability Reporting Directive"
            expected_document_number = "2022/2464"
            mandatory_keywords = ["csrd", "corporate sustainability", "reporting", "directive"]

        elif "nfrd" in context_lower or "2014/95" in context_lower:
            expected_framework = "Non-Financial Reporting Directive (NFRD -> superseded by CSRD)"
            expected_document_type = "Directive"
            expected_subject = "EU Non-Financial Reporting Directive (Directive 2014/95/EU - superseded by CSRD)"
            mandatory_keywords = ["non-financial", "reporting", "directive"]

        elif "tcfd" in context_lower:
            expected_framework = "TCFD Recommendations (transitioned to IFRS ISSB)"
            expected_document_type = "Disclosure Standard / Recommendations"
            expected_subject = "TCFD Recommendations for Climate-Related Financial Disclosures (ISSB IFRS S1/S2)"
            mandatory_keywords = ["climate", "financial disclosures", "recommendations", "tcfd"]

        elif "33-11275" in context_lower or ("sec" in context_lower and "climate" in context_lower):
            expected_framework = "SEC Climate-Related Disclosures Rule"
            expected_document_type = "Final Rule / Release"
            expected_subject = "SEC The Enhancement and Standardization of Climate-Related Disclosures for Investors"
            expected_document_number = "Release No. 33-11275 / 33-11280"
            mandatory_keywords = ["climate-related disclosures", "enhancement", "standardization", "sec"]

        elif "environmental risk management" in context_lower or "cp13" in context_lower:
            expected_framework = "MAS Guidelines on Environmental Risk Management"
            expected_document_type = "Regulatory Guidelines"
            expected_subject = "Monetary Authority of Singapore (MAS) Guidelines on Environmental Risk Management"
            mandatory_keywords = ["environmental risk", "management", "guidelines", "mas"]

        elif "adx" in context_lower and ("sustainability" in context_lower or "esg" in context_lower):
            expected_framework = "ADX ESG Disclosure Guidance"
            expected_document_type = "Exchange Guidance"
            expected_subject = "Abu Dhabi Securities Exchange (ADX) ESG Disclosure Guidance for Listed Companies"
            mandatory_keywords = ["adx", "esg", "disclosure", "sustainability", "guidance"]

        else:
            # General fallback using page title or link text
            expected_subject = page_title or step_description or link_text or "ESG Regulatory Document"
            expected_framework = topic or step_section or "ESG Regulatory Framework"
            mandatory_keywords = [w.lower() for w in re.findall(r"\b[A-Za-z]{4,}\b", expected_subject) if w.lower() not in ("about", "http", "https", "page", "file", "download")]

        context_summary = f"Authority: {expected_authority} | Subject: {expected_subject} | Framework: {expected_framework}"

        return IntentProfile(
            expected_subject=expected_subject,
            expected_authority=expected_authority,
            expected_jurisdiction=expected_jurisdiction,
            expected_framework=expected_framework,
            expected_document_type=expected_document_type,
            expected_document_number=expected_document_number,
            mandatory_keywords=mandatory_keywords[:8],
            context_summary=context_summary,
        )
