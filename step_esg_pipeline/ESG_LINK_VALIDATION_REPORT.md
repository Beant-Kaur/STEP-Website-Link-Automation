# STEP ESG Link Validation & Regulatory Freshness Report

**Crawl Run ID:** `b1d71ff4a8664332816d88ec843b2344`  
**Target Course Section:** STEP Kajabi *ESG Legislative Landscape — Binding & Non-binding Rules, Standards, and Regulations*  
**Scope:** 49 Course Reference Links  
**Execution Timestamp:** 2026-09-15  
**Pipeline Status:** Complete (100% Link Coverage, 0 Unhandled Failures)  

---

## 1. Executive Summary

The **STEP ESG Link Monitoring & Replacement Pipeline** performed a deep audit of all **49 course links** referenced in the *ESG Legislative Landscape* module.

Unlike basic link checkers that only confirm HTTP 200 responses, this system performs deep validation:
- **Substantive Text Inspection**: Extracts and parses up to 5,000 characters from HTML and PDF documents.
- **Intent Profiling**: Matches actual document substance against STEP course curriculum objectives.
- **100-Point Evidence Scoring**: Measures technical status, authority tier, relevance, regulatory freshness, and comparability.
- **Homepage Rejection Rule**: Rejects root homepages (e.g., `sec.gov`, `sebi.gov.in`) as replacements for specific regulatory guidance.
- **Two-Stage Replacement Engine**: Discovers, validates, and recommends authoritative replacement sources with side-by-side comparability.

---

## 2. Link Health & Classification Breakdown

| Classification | Count | % of Total | Operational Significance | Final Action |
|---|:---:|:---:|---|:---:|
| **VALID_AND_CURRENT** | **17** | 34.7% | Authoritative, in-force regulatory text from recognized issuers. | `KEEP` |
| **ACCESS_RESTRICTED** | **16** | 32.7% | HTTP 403, 202, or bot challenges (Cloudflare, Akamai, Turnstile). | `HUMAN_REVIEW_REQUIRED` |
| **WORKING_BUT_NON_OFFICIAL** | **10** | 20.4% | Third-party commercial aggregators, law firm summaries, or portals. | `HUMAN_REVIEW_REQUIRED` / `REPLACE` |
| **WORKING_BUT_OUTDATED** | **2** | 4.1% | Superseded regulatory drafts, consultation versions, or old legislative bills. | `REPLACE` |
| **BROKEN** | **2** | 4.1% | HTTP 404 dead link or corrupted download service endpoint. | `REPLACE` |
| **WORKING_BUT_REGULATORY_STATUS_CHANGED** | **1** | 2.0% | Active document whose legal force is stayed pending judicial review. | `HUMAN_REVIEW_REQUIRED` |
| **TEMPORARILY_UNAVAILABLE** | **1** | 2.0% | Gateway timeout or transient connection drop. | `HUMAN_REVIEW_REQUIRED` |
| **Total Links Audited** | **49** | **100%** | Comprehensive coverage across all curriculum references. | — |

---

## 3. Discovered & Verified Replacements

The pipeline identified and verified authoritative replacement sources for outdated, broken, or secondary links:

| # | Curriculum Topic / Anchor | Original URL | Issue Identified | Verified Replacement Source | Authority Tier | Confidence |
|---|---|---|---|---|---|:---:|
| 1 | **European Union — ESRS Set 1** | `https://eur-lex.europa.eu/...CELEX:32023DC0012https://eur-lex.europa.eu/...` | **Merged URL / Error**: Two distinct URLs concatenated together into an invalid link. | [Commission Delegated Regulation (EU) 2023/2772 (OJ L 2023/2772)](https://eur-lex.europa.eu/eli/reg_del/2023/2772/oj/eng) | Tier 1 (EUR-Lex) | **95%** |
| 2 | **Singapore — MAS Environmental Risk** | `https://www.mas.gov.sg/.../Guidelines_on_Environmental_Risk_Management.pdf` | **HTTP 404 Dead Link**: Legacy consultation paper endpoint removed. | [MAS Guidelines on Environmental Risk Management (Enacted)](https://www.mas.gov.sg/regulation/guidelines/guidelines-on-environmental-risk-management) | Tier 1 (Monetary Authority of Singapore) | **95%** |
| 3 | **Abu Dhabi Securities Exchange (ADX)** | `https://adxservices.adx.ae/download/...doc=1704806` | **Broken Service Endpoint**: Download web service returns empty/dead file. | [ADX Official Sustainability Portal](https://www.adx.ae/English/Pages/Products-and-Services/Sustainability.aspx) | Tier 2 (ADX Exchange) | **95%** |
| 4 | **United States — SEC Climate Disclosure** | `https://www.sec.gov/files/rules/final/2024/33-11275.pdf` | **Regulatory Status Changed**: Administrative stay issued pending 8th Circuit litigation. | [SEC Climate-Related Disclosures Rule Portal](https://www.sec.gov/rules-regulations/2024/03/enhancement-and-standardization-climate-related-disclosures-investors) | Tier 1 (US SEC) | **92%** |
| 5 | **California — Climate Corporate Data Act** | `https://leginfo.legislature.ca.gov/...bill_id=202120220SB253` | **Outdated Legislative Bill**: Links to 2021-2022 legislative session draft instead of enacted statute. | [California Legislature SB 253 (2023-2024 Chaptered)](https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240SB253) | Tier 1 (California Legislature) | **95%** |
| 6 | **Nigeria — Environmental Standards** | `https://www.policyvault.africa/policy/environmental-impact-assessment-act-2/` | **Commercial Aggregator**: Third-party commercial blog used instead of official statutory regulator. | [NESREA Official Policies & Guidelines](https://nesrea.gov.ng/policies-guidelines/) | Tier 1 (NESREA Nigeria) | **90%** |

---

## 4. Key Regulatory Intelligence Observations

### A. Litigation Stays & Enforcement Halts
- **U.S. SEC Climate Rules (Release Nos. 33-11275 / 34-99678)**:
  Although published in March 2024, the SEC issued an administrative stay on April 4, 2024 pending consolidated litigation in the Eighth Circuit Court of Appeals (*Liberty Energy Inc. v. SEC*). Course material should annotate this link with an explanatory notice that the rule is currently stayed.

### B. Global Standards Transition (TCFD → ISSB)
- The Financial Stability Board (FSB) disbanded the TCFD at COP28 following the publication of IFRS S1 and IFRS S2. Legacy TCFD recommendations links should transition to the IFRS Sustainability Standards portal.

### C. Bot Protection & Institutional Paywalls
- 16 links returned HTTP 403 or 202 due to institutional Cloudflare/Akamai bot management (e.g., `legislation.gov.uk`, `dol.gov`, `cbn.gov.ng`, `cac.gov.ng`). These are flagged for human review or verified via trusted secondary canonical registries.

---

## 5. Artifacts & Generated Reports

| Format | File Path | Description |
|---|---|---|
| **JSON** | [`step_esg_pipeline/report.json`](file:///c:/Users/HP-PC/Desktop/STEP/step_esg_pipeline/report.json) | Complete 65-attribute audit record for all 49 links. |
| **CSV** | [`step_esg_pipeline/report.csv`](file:///c:/Users/HP-PC/Desktop/STEP/step_esg_pipeline/report.csv) | Full 32-column export matching Master Prompt specification. |
| **Excel** | [`step_esg_pipeline/report.xlsx`](file:///c:/Users/HP-PC/Desktop/STEP/step_esg_pipeline/report.xlsx) | Styled spreadsheet with summary metrics and decision columns. |
| **Dashboard** | `http://localhost:8080/dashboard/` | Interactive browser dashboard with light/white theme, filters, and export. |
