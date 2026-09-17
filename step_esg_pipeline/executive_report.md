# STEP ESG Legislative Landscape: Link Integrity & Freshness Report
*Generated: 2026-09-15 06:09:02 UTC*

> **Operational Notice**: In accordance with the Master Prompt constraints, every finding carries verified on-page evidence. Absence of evidence is classified as `INDETERMINATE`. Replaced URLs undergo a strict 4-part verification gate.

## Section A — Executive Summary & System Health Metrics

| Metric | Count | Description |
|---|---|---|
| **Total Tracked Instruments** | **48** | Full inventory of legal instruments in STEP ESG section |
| Reachability: **OK** | 23 | Technically accessible, substantive content, verified type |
| Reachability: **BROKEN** | 4 | Hard 4xx/5xx, soft-404, or root redirect |
| Reachability: **INDETERMINATE** | 21 | WAF challenge, CAPTCHA, 403 Forbidden, Cloudflare, timeout |
| Freshness: **FRESH_LIKELY** | 0 | Asserted date within jurisdiction amendment cadence |
| Freshness: **STALE_SUSPECTED** | 0 | Exceeds expected cadence; register verification triggered |
| Freshness: **STALE_HIGH_PRIORITY** | 1 | Exceeds 2x cadence or dated <= 2023 for active jurisdiction |
| Freshness: **DATE_UNKNOWN** | 47 | No explicit date extractable from page/PDF |
| Missing Canonical Identifier | 0 | Flagged `NEEDS_IDENTIFIER` for manual review |
| Action: **AUTO_APPLY** | 0 | Safe updates meeting all criteria on same official domain |
| Action: **REVIEW_REQUIRED** | 47 | Cross-domain moves, amendments, indeterminate access |
| Action: **ESCALATE** | 1 | Repealed/superseded rules or broken issuer pointers |
| Action: **NO_ACTION** | 0 | Healthy, verified in force, content fresh |

## Section B — Urgent: Working Links Carrying Outdated Law

> [!IMPORTANT]
> **Highest Priority Risk**: These links return HTTP 200 and pass basic reachability checks, but serve superseded, repealed, or outdated legal instruments. They actively mislead STEP users evaluating disclosure compliance.

| Canonical Identifier | Jurisdiction | Current URL | Page Date | Age (Days) | Status / Register Finding | Verified Replacement | Action Gate |
|---|---|---|---|---|---|---|---|
| `CHI:National_Emissions_Trading_Scheme:2021` | China | [https://ieefa.org/resources/chinas-...](https://ieefa.org/resources/chinas-emissions-trading-system-ets-reforms-track-needs-robust-enforcement#:~:text=Evolving%20from%20pilot%20programs%20across,20%25%20of%20total%20global%20emissions.) | N/A | N/A | "replaced by revenue generation for domestic use" (supersession_repeal): ...revenue leakag | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |
| `32023R2772` | European Union | [http://ec.europa.eu/finance/docs/la...](http://ec.europa.eu/finance/docs/law/250730-recommendation-vsme_en.pdf) | 2023-01-05 | 1349 days | REGISTER_UNAVAILABLE | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |
| `IND:RBI_Guidelines_Environmental_Social` | India | [https://www.rbi.org.in/Scripts/Noti...](https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12213&Mode=0) | N/A | N/A | "Withdrawn" (supersession_repeal): ..."/scripts/NotificationUserWithdrawnCircular.aspx">Ci | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |
| `TCFD Recommendations` | United Kingdom | [https://assets.publishing.service.g...](https://assets.publishing.service.gov.uk/media/62138625d3bf7f4f05879a21/mandatory-climate-related-financial-disclosures-publicly-quoted-private-cos-llps.pdf) | February 2022 | N/A | SUPERSEDED | `NO_VERIFIED_REPLACEMENT_FOUND` | `ESCALATE` |

## Section C — Broken and Soft-404 Links

| Canonical Identifier | Jurisdiction | Broken URL | Failure Reason | Verified Replacement | Action Gate |
|---|---|---|---|---|---|
| `CHI:MEE_Measures_Environmental_Information:2021` | China | [http://www.mee.gov.cn/gkml/hbb/bwj/20210...](http://www.mee.gov.cn/gkml/hbb/bwj/202104/t20210427_837497.html) | HTTP error / soft 404 | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |
| `IND:SEBI_Business_Responsibility_Sustainability:2021` | India | [https://www.sebi.gov.in/legal/circulars/...](https://www.sebi.gov.in/legal/circulars/may-2021/business-responsibility-and-sustainability-reporting-by-listed-entities_50096.html) | HTTP error / soft 404 | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |
| `UNI:ADX_ESG_Disclosure_Guidelines` | United Arab Emirates | [https://adxservices.adx.ae/WebServices/D...](https://adxservices.adx.ae/WebServices/DataServices/contentDownload.aspx?doc=1704806) | HTTP error / soft 404 | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |
| `NIG:Nigeria:1992` | Nigeria | [https://www.policyvault.africa/policy/en...](https://www.policyvault.africa/policy/environmental-impact-assessment-act-2/) | HTTP error / soft 404 | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |

## Section D — Issuer-Declared Latest-Version Pointers Found

> Standing pointers embedded by official publishers (EUR-Lex consolidated versions, legislation.gov.uk revised texts, eCFR current rules). These represent the highest-confidence replacements.

*No standing issuer pointers detected in this run.*

## Section E — Amended Instruments (Surrounding Text May Need Rewriting)

> The instrument is currently in force but has undergone formal amendments or delegated regulations. The STEP portal description should be reviewed alongside the link.

| Canonical Identifier | Jurisdiction | Instrument Title | Register Status | Surrounding STEP Text / Note | Action Gate |
|---|---|---|---|---|---|
| `SEC 33-11275` | United States | SEC Climate-Related Disclosure Rule (Final Rule 33 | `IN_FORCE_AMENDED` | https://www.sec.gov/files/rules/final/2024/33-11275.pdf... | `REVIEW_REQUIRED` |

## Section F — Source-Authority Upgrades

> Third-party blogs, law firm commentaries, or commercial aggregators recommended for upgrade to primary official regulatory registers.

| Canonical Identifier | Jurisdiction | Non-Official Domain | Proposed Official Authority | Proposed URL | Action Gate |
|---|---|---|---|---|---|
| `CHI:Sustainability_Report_Trial_Guidelines:2024` | China | `english.sse.com.cn` | ä¸æµ·è¯å¸äº¤ææ | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |
| `CHI:Sustainability_Report_Trial_Guidelines:2024` | China | `static.sse.com.cn` | Official Register | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |
| `CHI:MEE_Measures_Environmental_Information:2021` | China | `www.greenfinanceplatform.org` | Official Register | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |
| `CHI:MEE_Measures_Environmental_Information:2021` | China | `www.mee.gov.cn` | Official Register | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |
| `CHI:National_Emissions_Trading_Scheme:2021` | China | `ieefa.org` | Shu Xuan TanShu is IEEFA's Sustainable Finance Analyst, Asia.Go to Profile | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |
| `KUW:Kuwait` | Kuwait | `www.boursakuwait.com.kw` | Official Register | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |
| `QAT:Guidance_ESG_Reporting_Qatar` | Qatar | `www.qe.com.qa` | Official Register | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |
| `SIN:Practice_Note_76_Sustainability` | Singapore | `rulebook.sgx.com` | Official Register | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |
| `UNI:ADX_ESG_Disclosure_Guidelines` | United Arab Emirates | `adxservices.adx.ae` | Official Register | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |
| `UNI:sustainability_report` | United Arab Emirates | `www.ecgi.global` | Official Register | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |
| `UNI:sustainability_report` | United Arab Emirates | `www.uaecma.gov.ae` | Future Internet | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |
| `UNI:National_Carbon_Credit_Registry:2024` | United Arab Emirates | `uaelegislation.gov.ae` | Official Register | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |
| `UNI:Principles_SustainabilityRelated_Disclosures` | United Arab Emirates | `rulebook.centralbank.ae` | Official Register | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |
| `NIG:Nigeria:1992` | Nigeria | `www.policyvault.africa` | Official Register | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |
| `NIG:Nigeria:2021` | Nigeria | `unfccc.int` | Official Register | `NO_VERIFIED_REPLACEMENT_FOUND` | `REVIEW_REQUIRED` |

## Section G — Indeterminate / Blocked Links

> [!WARNING]
> **Strict Classification**: These endpoints are neither confirmed working nor broken. They encountered WAF blocks, Cloudflare challenges, CAPTCHAs, or timeouts. They are queued for human review with exact block signatures.

| Canonical Identifier | Jurisdiction | URL | HTTP Status | Block / Challenge Reason | Action Gate |
|---|---|---|---|---|---|
| `CHI:MEE_Measures_Environmental_Information:2021` | China | [https://www.greenfinanceplatform.org/pol...](https://www.greenfinanceplatform.org/policies-and-regulations/chinas-administrative-measures-legal-disclosure-enterprise-environmental) | None | Access Restricted / WAF Challenge | `REVIEW_REQUIRED` |
| `32022L2464` | European Union | [https://eur-lex.europa.eu/eli/dir/2022/2...](https://eur-lex.europa.eu/eli/dir/2022/2464/2025-04-17/eng) | 202 | Access Restricted / WAF Challenge | `REVIEW_REQUIRED` |
| `32023R2772` | European Union | [https://eur-lex.europa.eu/legal-content/...](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023DC0012https://eur-lex.europa.eu/eli/reg_del/2023/2772/oj/eng) | 202 | Access Restricted / WAF Challenge | `REVIEW_REQUIRED` |
| `32019R2088` | European Union | [https://eur-lex.europa.eu/eli/reg/2019/2...](https://eur-lex.europa.eu/eli/reg/2019/2088) | 202 | Access Restricted / WAF Challenge | `REVIEW_REQUIRED` |
| `32020R0852` | European Union | [https://eur-lex.europa.eu/eli/reg/2020/8...](https://eur-lex.europa.eu/eli/reg/2020/852) | 202 | Access Restricted / WAF Challenge | `REVIEW_REQUIRED` |
| `32024L1760` | European Union | [https://eur-lex.europa.eu/eli/dir/2024/1...](https://eur-lex.europa.eu/eli/dir/2024/1760/oj/eng) | 202 | Access Restricted / WAF Challenge | `REVIEW_REQUIRED` |
| `EUR:Sets_capandtrade_system_CO:2003` | European Union | [https://eur-lex.europa.eu/eli/dir/2003/8...](https://eur-lex.europa.eu/eli/dir/2003/87) | 202 | Access Restricted / WAF Challenge | `REVIEW_REQUIRED` |
| `32018L2001` | European Union | [https://eur-lex.europa.eu/eli/dir/2018/2...](https://eur-lex.europa.eu/eli/dir/2018/2001) | 202 | Access Restricted / WAF Challenge | `REVIEW_REQUIRED` |
| `32018L2002` | European Union | [https://eur-lex.europa.eu/eli/dir/2018/2...](https://eur-lex.europa.eu/eli/dir/2018/2002) | 202 | Access Restricted / WAF Challenge | `REVIEW_REQUIRED` |
| `EUR:Ecodesign_Directive:2009` | European Union | [https://eur-lex.europa.eu/eli/dir/2009/1...](https://eur-lex.europa.eu/eli/dir/2009/125) | 202 | Access Restricted / WAF Challenge | `REVIEW_REQUIRED` |
| `32023R1115` | European Union | [https://eur-lex.europa.eu/eli/reg/2023/1...](https://eur-lex.europa.eu/eli/reg/2023/1115) | 202 | Access Restricted / WAF Challenge | `REVIEW_REQUIRED` |
| `IND:Companies_Act_2013_Section:2013` | India | [https://www.mca.gov.in/Ministry/pdf/Comp...](https://www.mca.gov.in/Ministry/pdf/CompaniesAct2013.pdf) | None | Access Restricted / WAF Challenge | `REVIEW_REQUIRED` |
| `KUW:Kuwait` | Kuwait | [https://www.boursakuwait.com.kw/en/resou...](https://www.boursakuwait.com.kw/en/resources/e-publications/esg-reporting-guide) | None | Access Restricted / WAF Challenge | `REVIEW_REQUIRED` |
| `SIN:MAS_Guidelines_Environmental_Risk` | Singapore | [https://www.mas.gov.sg/-/media/MAS/News-...](https://www.mas.gov.sg/-/media/MAS/News-and-Publications/Consultation-Papers/CP13-Guidelines-on-Environmental-Risk-Management/Guidelines_on_Environmental_Risk_Management.pdf) | None | Access Restricted / WAF Challenge | `REVIEW_REQUIRED` |
| `UNI:National_Carbon_Credit_Registry:2024` | United Arab Emirates | [https://uaelegislation.gov.ae/en/legisla...](https://uaelegislation.gov.ae/en/legislations/2521/download) | None | Access Restricted / WAF Challenge | `REVIEW_REQUIRED` |
| `2021 c. 30` | United Kingdom | [https://www.legislation.gov.uk/ukpga/202...](https://www.legislation.gov.uk/ukpga/2021/30/contents/enacted) | 202 | Access Restricted / WAF Challenge | `REVIEW_REQUIRED` |
| `UK SI 2022/31` | United Kingdom | [https://www.legislation.gov.uk/uksi/2022...](https://www.legislation.gov.uk/uksi/2022/31/contents/made) | 202 | Access Restricted / WAF Challenge | `REVIEW_REQUIRED` |
| `SEC 33-11275` | United States | [https://www.sec.gov/files/rules/final/20...](https://www.sec.gov/files/rules/final/2024/33-11275.pdf) | None | Access Restricted / WAF Challenge | `REVIEW_REQUIRED` |
| `UNI:Department_Labor_ESG_Rule:2022` | United States | [https://www.dol.gov/newsroom/releases/eb...](https://www.dol.gov/newsroom/releases/ebsa/ebsa20221122) | None | Access Restricted / WAF Challenge | `REVIEW_REQUIRED` |
| `NIG:Nigeria:2020` | Nigeria | [https://www.cac.gov.ng/wp-content/upload...](https://www.cac.gov.ng/wp-content/uploads/2020/12/CAMA-NOTE-BOOK-FULL-VERSION.pdf) | None | Access Restricted / WAF Challenge | `REVIEW_REQUIRED` |
| `NIG:Nigeria:2012` | Nigeria | [https://www.cbn.gov.ng/out/2012/ccd/circ...](https://www.cbn.gov.ng/out/2012/ccd/circular-nsbp.pdf) | None | Access Restricted / WAF Challenge | `REVIEW_REQUIRED` |

## Section H — Registry Diff (Field-Level Updates Ready to Apply)

| Entry ID | Canonical Identifier | Volatility Tier | Field | Current Value | Proposed Value | Confidence | Action Gate |
|---|---|---|---|---|---|---|---|
| `7c59627827154e5fbe214639604bdf2d_1` | `BAH:Bahrain` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_1` | `BAH:Bahrain` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_2` | `CHI:Sustainability_Report_Trial_Guidelines:2024` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_2` | `CHI:Sustainability_Report_Trial_Guidelines:2024` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_3` | `CHI:Sustainability_Report_Trial_Guidelines:2024` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_3` | `CHI:Sustainability_Report_Trial_Guidelines:2024` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_4` | `CHI:MEE_Measures_Environmental_Information:2021` | `Tier B` | `reachability` | `OK` | `INDETERMINATE` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_4` | `CHI:MEE_Measures_Environmental_Information:2021` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_4` | `CHI:MEE_Measures_Environmental_Information:2021` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_5` | `CHI:MEE_Measures_Environmental_Information:2021` | `Tier B` | `reachability` | `OK` | `BROKEN` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_5` | `CHI:MEE_Measures_Environmental_Information:2021` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_5` | `CHI:MEE_Measures_Environmental_Information:2021` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_6` | `CHI:National_Emissions_Trading_Scheme:2021` | `Tier A` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_6` | `CHI:National_Emissions_Trading_Scheme:2021` | `Tier A` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_7` | `32022L2464` | `Tier A` | `reachability` | `OK` | `INDETERMINATE` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_7` | `32022L2464` | `Tier A` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_7` | `32022L2464` | `Tier A` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_8` | `32023R2772` | `Tier A` | `reachability` | `OK` | `INDETERMINATE` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_8` | `32023R2772` | `Tier A` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_8` | `32023R2772` | `Tier A` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_9` | `32023R2772` | `Tier A` | `freshness` | `FRESH_LIKELY` | `STALE_HIGH_PRIORITY` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_9` | `32023R2772` | `Tier A` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_10` | `32019R2088` | `Tier A` | `reachability` | `OK` | `INDETERMINATE` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_10` | `32019R2088` | `Tier A` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_10` | `32019R2088` | `Tier A` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_11` | `32020R0852` | `Tier A` | `reachability` | `OK` | `INDETERMINATE` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_11` | `32020R0852` | `Tier A` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_11` | `32020R0852` | `Tier A` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_12` | `32024L1760` | `Tier A` | `reachability` | `OK` | `INDETERMINATE` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_12` | `32024L1760` | `Tier A` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_12` | `32024L1760` | `Tier A` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_13` | `EUR:Sets_capandtrade_system_CO:2003` | `Tier A` | `reachability` | `OK` | `INDETERMINATE` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_13` | `EUR:Sets_capandtrade_system_CO:2003` | `Tier A` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_13` | `EUR:Sets_capandtrade_system_CO:2003` | `Tier A` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_14` | `32018L2001` | `Tier A` | `reachability` | `OK` | `INDETERMINATE` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_14` | `32018L2001` | `Tier A` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_14` | `32018L2001` | `Tier A` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_15` | `32018L2002` | `Tier A` | `reachability` | `OK` | `INDETERMINATE` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_15` | `32018L2002` | `Tier A` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_15` | `32018L2002` | `Tier A` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_16` | `EUR:Ecodesign_Directive:2009` | `Tier A` | `reachability` | `OK` | `INDETERMINATE` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_16` | `EUR:Ecodesign_Directive:2009` | `Tier A` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_16` | `EUR:Ecodesign_Directive:2009` | `Tier A` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_17` | `32023R1115` | `Tier A` | `reachability` | `OK` | `INDETERMINATE` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_17` | `32023R1115` | `Tier A` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_17` | `32023R1115` | `Tier A` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_18` | `IND:SEBI_Business_Responsibility_Sustainability:2021` | `Tier B` | `reachability` | `OK` | `BROKEN` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_18` | `IND:SEBI_Business_Responsibility_Sustainability:2021` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_18` | `IND:SEBI_Business_Responsibility_Sustainability:2021` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_19` | `IND:Companies_Act_2013_Section:2013` | `Tier B` | `reachability` | `OK` | `INDETERMINATE` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_19` | `IND:Companies_Act_2013_Section:2013` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_20` | `IND:RBI_Guidelines_Environmental_Social` | `Tier A` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_20` | `IND:RBI_Guidelines_Environmental_Social` | `Tier A` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_21` | `KIN:ESG_Disclosure_Guidelines_Saudi` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_21` | `KIN:ESG_Disclosure_Guidelines_Saudi` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_22` | `KUW:Kuwait` | `Tier B` | `reachability` | `OK` | `INDETERMINATE` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_22` | `KUW:Kuwait` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_22` | `KUW:Kuwait` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_23` | `OMA:Oman` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_23` | `OMA:Oman` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_24` | `QAT:Guidance_ESG_Reporting_Qatar` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_24` | `QAT:Guidance_ESG_Reporting_Qatar` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_25` | `SIN:Practice_Note_76_Sustainability` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_25` | `SIN:Practice_Note_76_Sustainability` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_26` | `SIN:MAS_Guidelines_Environmental_Risk` | `Tier B` | `reachability` | `OK` | `INDETERMINATE` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_26` | `SIN:MAS_Guidelines_Environmental_Risk` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_26` | `SIN:MAS_Guidelines_Environmental_Risk` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_27` | `SIN:MAS_Guidelines_Environmental_Risk` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_27` | `SIN:MAS_Guidelines_Environmental_Risk` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_28` | `SIN:Singapore:2022` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_28` | `SIN:Singapore:2022` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_29` | `UNI:Federal_DecreeLaw_No_11:2024` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_29` | `UNI:Federal_DecreeLaw_No_11:2024` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_30` | `UNI:ADX_ESG_Disclosure_Guidelines` | `Tier B` | `reachability` | `OK` | `BROKEN` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_30` | `UNI:ADX_ESG_Disclosure_Guidelines` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_30` | `UNI:ADX_ESG_Disclosure_Guidelines` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_31` | `UNI:sustainability_report` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_31` | `UNI:sustainability_report` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_32` | `UNI:sustainability_report` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_32` | `UNI:sustainability_report` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_33` | `UNI:National_Carbon_Credit_Registry:2024` | `Tier B` | `reachability` | `OK` | `INDETERMINATE` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_33` | `UNI:National_Carbon_Credit_Registry:2024` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_33` | `UNI:National_Carbon_Credit_Registry:2024` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_34` | `UNI:Principles_SustainabilityRelated_Disclosures` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_34` | `UNI:Principles_SustainabilityRelated_Disclosures` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_35` | `TCFD Recommendations` | `Tier D` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `ESCALATE` |
| `7c59627827154e5fbe214639604bdf2d_35` | `TCFD Recommendations` | `Tier D` | `register_status` | `IN_FORCE_UNCHANGED` | `SUPERSEDED` | 0.95 | `ESCALATE` |
| `7c59627827154e5fbe214639604bdf2d_36` | `2021 c. 30` | `Tier B` | `reachability` | `OK` | `INDETERMINATE` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_36` | `2021 c. 30` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_36` | `2021 c. 30` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_37` | `UK SI 2022/31` | `Tier B` | `reachability` | `OK` | `INDETERMINATE` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_37` | `UK SI 2022/31` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_37` | `UK SI 2022/31` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_38` | `SEC 33-11275` | `Tier B` | `reachability` | `OK` | `INDETERMINATE` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_38` | `SEC 33-11275` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_38` | `SEC 33-11275` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `IN_FORCE_AMENDED` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_39` | `UNI:Department_Labor_ESG_Rule:2022` | `Tier B` | `reachability` | `OK` | `INDETERMINATE` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_39` | `UNI:Department_Labor_ESG_Rule:2022` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_40` | `California SB 253` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_41` | `NIG:Nigeria:2007` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_41` | `NIG:Nigeria:2007` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_42` | `NIG:Nigeria:2018` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_42` | `NIG:Nigeria:2018` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_43` | `NIG:Nigeria:1992` | `Tier B` | `reachability` | `OK` | `BROKEN` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_43` | `NIG:Nigeria:1992` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_43` | `NIG:Nigeria:1992` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_44` | `NIG:Nigeria:2020` | `Tier B` | `reachability` | `OK` | `INDETERMINATE` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_44` | `NIG:Nigeria:2020` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_44` | `NIG:Nigeria:2020` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_45` | `NIG:Nigeria` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_45` | `NIG:Nigeria` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_46` | `NIG:Nigeria:2021` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_46` | `NIG:Nigeria:2021` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_47` | `NIG:Nigeria:2012` | `Tier B` | `reachability` | `OK` | `INDETERMINATE` | 1.00 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_47` | `NIG:Nigeria:2012` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_47` | `NIG:Nigeria:2012` | `Tier B` | `register_status` | `IN_FORCE_UNCHANGED` | `REGISTER_UNAVAILABLE` | 0.95 | `REVIEW_REQUIRED` |
| `7c59627827154e5fbe214639604bdf2d_48` | `NIG:Nigeria:2018` | `Tier B` | `freshness` | `FRESH_LIKELY` | `DATE_UNKNOWN` | 0.95 | `REVIEW_REQUIRED` |
