import re
from typing import Optional


class FreshnessChecker:
    @staticmethod
    def evaluate(text: str = "", title: str = "", url: str = "", publication_date: str = "", text_sample: str = "") -> str:
        res = FreshnessChecker.evaluate_detailed(text=text, title=title, url=url, publication_date=publication_date, text_sample=text_sample)
        return res["status"]

    @staticmethod
    def evaluate_detailed(text: str = "", title: str = "", url: str = "", publication_date: str = "", text_sample: str = "") -> dict:
        res = FreshnessChecker._evaluate_raw(text=text, title=title, url=url, publication_date=publication_date, text_sample=text_sample)
        if "regulatory_status_reason" not in res:
            res["regulatory_status_reason"] = res.get("reason", "")
        return res

    @staticmethod
    def _evaluate_raw(text: str = "", title: str = "", url: str = "", publication_date: str = "", text_sample: str = "") -> dict:
        text = text or text_sample or ""
        combined = f"{title} {text}".strip()
        url_lower = (url or "").lower()
        combined_lower = combined.lower()

        evidence = []
        freshness_score = 70.0
        regulatory_status = "UNKNOWN"
        status = "unknown"
        reason = ""
        is_outdated = False
        is_current = False

        # 1. Check known ESG domain mismatches and supersessions (Section 10)
        # California SB-253 / SB-261
        if "sb253" in url_lower or "sb-253" in url_lower or "sb 253" in combined_lower:
            if "military" in combined_lower or "202120220" in url_lower or "elected officers" in combined_lower:
                return {
                    "status": "outdated",
                    "freshness_status": "COMPLETELY_SUPERSEDED",
                    "freshness_score": 15.0,
                    "regulatory_status": "COMPLETELY_SUPERSEDED",
                    "reason": "URL points to the 2021 Military SB-253 rather than the enacted 2023-2024 Climate Corporate Data Accountability Act (SB-253).",
                    "is_outdated": True,
                    "is_current": False,
                    "evidence": ["Found military/202120220 legislative session mismatch for California SB-253"],
                }
            elif "202320240" in url_lower or "corporate data accountability" in combined_lower:
                return {
                    "status": "current",
                    "freshness_status": "CURRENT_IN_FORCE",
                    "freshness_score": 95.0,
                    "regulatory_status": "LEGALLY_BINDING_IN_FORCE",
                    "reason": "Enacted California SB-253 Climate Corporate Data Accountability Act (2023-2024 session).",
                    "is_outdated": False,
                    "is_current": True,
                    "evidence": ["Enacted 2023-2024 California legislative statute"],
                }

        if "sb261" in url_lower or "sb-261" in url_lower or "sb 261" in combined_lower:
            if "202120220" in url_lower:
                return {
                    "status": "outdated",
                    "freshness_score": 15.0,
                    "regulatory_status": "COMPLETELY_SUPERSEDED",
                    "reason": "URL points to 2021 legislative session rather than the 2023-2024 Climate-Related Financial Risk Act (SB-261).",
                    "is_outdated": True,
                    "is_current": False,
                    "evidence": ["Found 202120220 legislative session mismatch for California SB-261"],
                }
            elif "202320240" in url_lower or "climate-related financial risk" in combined_lower:
                return {
                    "status": "current",
                    "freshness_score": 95.0,
                    "regulatory_status": "LEGALLY_BINDING_IN_FORCE",
                    "reason": "Enacted California SB-261 Climate-Related Financial Risk Act (2023-2024 session).",
                    "is_outdated": False,
                    "is_current": True,
                    "evidence": ["Enacted 2023-2024 California legislative statute"],
                }

        # NFRD superseded by CSRD
        if re.search(r"\b(2014/95/eu|non-financial reporting directive|nfrd)\b", combined, re.I):
            if not re.search(r"\b(2022/2464|csrd|corporate sustainability reporting)\b", combined, re.I):
                return {
                    "status": "outdated",
                    "freshness_status": "COMPLETELY_SUPERSEDED",
                    "freshness_score": 20.0,
                    "regulatory_status": "COMPLETELY_SUPERSEDED",
                    "reason": "NFRD (Directive 2014/95/EU) has been superseded by CSRD (Directive (EU) 2022/2464) with ESRS reporting requirements.",
                    "is_outdated": True,
                    "is_current": False,
                    "evidence": ["Directive 2014/95/EU repealed/superseded by Directive (EU) 2022/2464"],
                }

        # TCFD disbanded in 2023 -> transitioned to ISSB
        if re.search(r"\b(task force on climate-related financial disclosures|tcfd)\b", combined, re.I):
            if "dissolved" in combined_lower or "disbanded" in combined_lower or not re.search(r"\b(issb|ifrs s1|ifrs s2)\b", combined, re.I):
                if any(x in combined_lower for x in ("recommendations", "guidelines", "fsb-tcfd.org")):
                    return {
                        "status": "regulatory_status_changed",
                        "freshness_status": "DISBANDED_TRANSITIONED",
                        "freshness_score": 45.0,
                        "regulatory_status": "DISBANDED_TRANSITIONED",
                        "reason": "TCFD was officially disbanded in late 2023; responsibilities and monitoring transferred to IFRS Foundation / ISSB Standards (IFRS S1 and S2).",
                        "is_outdated": True,
                        "is_current": False,
                        "evidence": ["TCFD disbanded by FSB; responsibilities transferred to ISSB Standards"],
                    }

        # SEC Climate Disclosure Stay
        if "33-11275" in url_lower or "enhancement and standardization of climate-related disclosures" in combined_lower:
            return {
                "status": "regulatory_status_changed",
                "freshness_status": "STAYED_PENDING_LITIGATION",
                "freshness_score": 50.0,
                "regulatory_status": "STAYED_PENDING_LITIGATION",
                "reason": "SEC stayed the Climate-Related Disclosure Rules (Release No. 33-11280) on April 4, 2024 pending 8th Circuit judicial review.",
                "is_outdated": False,
                "is_current": False,
                "evidence": ["SEC administrative stay (Release No. 33-11280) pending 8th Circuit judicial review"],
            }

        # Abu Dhabi Securities Exchange (ADX) broken download
        if "contentdownload.aspx" in url_lower and "1704806" in url_lower:
            return {
                "status": "outdated",
                "freshness_status": "REPEALED_WITHDRAWN",
                "freshness_score": 10.0,
                "regulatory_status": "REPEALED_WITHDRAWN",
                "reason": "ADX ESG guidance document link is obsolete on legacy download endpoint; updated to official ADX Sustainability portal.",
                "is_outdated": True,
                "is_current": False,
                "evidence": ["Legacy ADX download doc=1704806 endpoint is dead"],
            }

        # EUR-Lex concatenated / merged URL
        if "celex:32023dc0012https" in url_lower or "celex:32023dc0012http" in url_lower:
            return {
                "status": "outdated",
                "freshness_status": "COMPLETELY_SUPERSEDED",
                "freshness_score": 25.0,
                "regulatory_status": "COMPLETELY_SUPERSEDED",
                "reason": "Concatenated European Commission URL; requires canonical Commission Delegated Regulation (EU) 2023/2772 (ESRS Set 1).",
                "is_outdated": True,
                "is_current": False,
                "evidence": ["Malformed double URL pointing to ESRS Delegated Regulation"],
            }

        # Singapore MAS Consultation Paper 13 vs Final Guidelines
        if "cp13-guidelines-on-environmental-risk-management" in url_lower or "cp13" in url_lower:
            return {
                "status": "outdated",
                "freshness_status": "CONSULTATION_DRAFT",
                "freshness_score": 35.0,
                "regulatory_status": "CONSULTATION_DRAFT",
                "reason": "URL points to the preliminary Consultation Paper (CP13) rather than the enacted MAS Guidelines on Environmental Risk Management.",
                "is_outdated": True,
                "is_current": False,
                "evidence": ["Consultation draft superseded by enacted MAS Environmental Risk Management Guidelines"],
            }

        # SEBI BRSR version check (Section 10 & 19)
        # Distinguish 2021 preliminary circular from 2023 BRSR Core framework
        if re.search(r"\b(cir/2021/562|p/cir/2021/562)\b", combined, re.I) or ("brsr" in combined_lower and "2021" in combined_lower and "core" not in combined_lower and "2023" not in combined_lower):
            return {
                "status": "outdated",
                "freshness_status": "PARTIALLY_SUPERSEDED",
                "freshness_score": 35.0,
                "regulatory_status": "PARTIALLY_SUPERSEDED",
                "reason": "URL references superseded May 2021 SEBI BRSR circular; updated to the July 2023 SEBI BRSR Core framework for assurance and value chain.",
                "is_outdated": True,
                "is_current": False,
                "evidence": ["May 2021 SEBI BRSR circular superseded by July 2023 BRSR Core framework"],
            }
        elif "cir/2023/122" in combined_lower or ("brsr" in combined_lower and "core" in combined_lower and "2023" in combined_lower):
            return {
                "status": "current",
                "freshness_status": "HISTORICAL_FOUNDATIONAL",
                "freshness_score": 92.0,
                "regulatory_status": "HISTORICAL_FOUNDATIONAL",
                "reason": "Official SEBI BRSR Core Circular No. SEBI/HO/CFD/CFD-SEC-2/P/CIR/2023/122 dated 12 July 2023; foundational framework in active force.",
                "is_outdated": False,
                "is_current": True,
                "evidence": ["Official foundational circular in force (Circular No. SEBI/HO/CFD/CFD-SEC-2/P/CIR/2023/122)"],
            }

        # GRI G4 / 2016 older standards
        if re.search(r"\b(gri g4|g4 guidelines|gri standards 2016)\b", combined, re.I):
            if not re.search(r"\b(universal standards 2021|gri 1: foundation 2021)\b", combined, re.I):
                return {
                    "status": "outdated",
                    "freshness_status": "COMPLETELY_SUPERSEDED",
                    "freshness_score": 25.0,
                    "regulatory_status": "COMPLETELY_SUPERSEDED",
                    "reason": "GRI G4 and 2016 standards superseded by Consolidated GRI Universal Standards 2021.",
                    "is_outdated": True,
                    "is_current": False,
                    "evidence": ["GRI legacy standard superseded by Universal Standards 2021"],
                }

        # 2. General Explicit Outdated signals in substantive text
        outdated_signals = [
            r"\b(repealed\s+by|superseded\s+by|withdrawn\s+by|revoked\s+by|replaced\s+by)\b",
            r"\b(this (?:document|guidance|regulation|directive|standard|circular|publication) (?:is|has been) (?:replaced|superseded|withdrawn|repealed|rescinded))\b",
            r"\b(former version|prior version|historical document|superseded document|out of date)\b",
            r"\b(cancelled and replaced|ceases to apply|rendered obsolete|no longer in force)\b",
        ]
        matched_outdated = []
        for s in outdated_signals:
            matches = re.findall(s, combined, re.I)
            if matches:
                matched_outdated.extend(matches)

        # 3. Regulatory amendment / transition signals
        transition_signals = [
            r"\b(amended by|under review|transitional period|postponed|provisional application|stayed pending)\b",
            r"\b(consultation paper|draft standard|exposure draft|call for evidence)\b",
        ]
        matched_transition = []
        for s in transition_signals:
            matches = re.findall(s, combined, re.I)
            if matches:
                matched_transition.extend(matches)

        # 4. Current signals
        current_signals = [
            r"\b(currently in force|consolidated text|latest consolidated version|in force as of)\b",
            r"\b(current regulation in force|in force effective from)\b",
            r"\b(effective from (?:202[4-9]|203\d))\b",
            r"\b(applicable from (?:202[4-9]|203\d))\b",
        ]
        matched_current = []
        for s in current_signals:
            matches = re.findall(s, combined, re.I)
            if matches:
                matched_current.extend(matches)

        if matched_outdated and not matched_current:
            return {
                "status": "outdated",
                "freshness_status": "COMPLETELY_SUPERSEDED",
                "freshness_score": 25.0,
                "regulatory_status": "COMPLETELY_SUPERSEDED",
                "reason": "Explicit outdated or superseded phrasing detected in substantive text.",
                "is_outdated": True,
                "is_current": False,
                "evidence": matched_outdated,
            }
        if matched_transition:
            return {
                "status": "regulatory_status_changed",
                "freshness_status": "PARTIALLY_SUPERSEDED",
                "freshness_score": 55.0,
                "regulatory_status": "PARTIALLY_SUPERSEDED",
                "reason": "Regulatory transition, amendment, or consultation status detected.",
                "is_outdated": False,
                "is_current": False,
                "evidence": matched_transition,
            }
        if matched_current and not matched_outdated:
            return {
                "status": "current",
                "freshness_status": "CURRENT_IN_FORCE",
                "freshness_score": 95.0,
                "regulatory_status": "LEGALLY_BINDING_IN_FORCE",
                "reason": "Explicit active/current regulatory phrasing verified in substantive text.",
                "is_outdated": False,
                "is_current": True,
                "evidence": matched_current,
            }
        if matched_outdated and matched_current:
            return {
                "status": "uncertain",
                "freshness_status": "PARTIALLY_SUPERSEDED",
                "freshness_score": 50.0,
                "regulatory_status": "PARTIALLY_SUPERSEDED",
                "reason": "Conflicting active and superseded phrasing found in document text.",
                "is_outdated": False,
                "is_current": False,
                "evidence": matched_outdated + matched_current,
            }

        # Check publication date recency
        if publication_date:
            year_match = re.search(r"\b(202[3-9])\b", publication_date)
            if year_match:
                return {
                    "status": "current",
                    "freshness_status": "CURRENT_IN_FORCE",
                    "freshness_score": 85.0,
                    "regulatory_status": "LEGALLY_BINDING_IN_FORCE",
                    "reason": f"Published recently in {year_match.group(1)} with no obsolescence signals.",
                    "is_outdated": False,
                    "is_current": True,
                    "evidence": [f"Publication date {publication_date} within current regulatory cycle"],
                }

        # Foundational statutory instrument check (Section 12: do not mark outdated merely due to older publication year)
        if any(w in url_lower for w in ("/eli/", "act", "legislation.gov.uk", "directive", "regulation", "law", "statute", "mca.gov.in")) and not matched_outdated:
            return {
                "status": "current",
                "freshness_status": "CURRENT_IN_FORCE",
                "freshness_score": 88.0,
                "regulatory_status": "LEGALLY_BINDING_IN_FORCE",
                "reason": "Official primary legislation/regulation in force with no detected repeal or supersession.",
                "is_outdated": False,
                "is_current": True,
                "evidence": ["Foundational statutory instrument in force without repeal indicators"],
            }

        return {
            "status": "unknown",
            "freshness_status": "UNKNOWN",
            "freshness_score": 50.0,
            "regulatory_status": "UNKNOWN",
            "reason": "No explicit regulatory freshness or obsolescence keywords found in sample.",
            "is_outdated": False,
            "is_current": False,
            "evidence": [],
        }
