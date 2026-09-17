# STEP ESG Link Monitor & Content Freshness Verification System

> **Advanced ESG Regulatory Link Audit, Deep Text Verification, and Two-Stage Replacement Pipeline**  
> Built for the STEP Curriculum: *ESG Legislative Landscape — Binding & Non-binding Rules, Standards, and Regulations*

---

## Table of Contents

1. [Executive Summary & Core Philosophy](#1-executive-summary--core-philosophy)
2. [Why Traditional Link Checkers Fail for ESG](#2-why-traditional-link-checkers-fail-for-esg)
3. [Architecture: The 14-Step Deep Verification Pipeline](#3-architecture-the-14-step-deep-verification-pipeline)
4. [Quick Start & How to Use](#4-quick-start--how-to-use)
   - [Starting the Light-Mode Interactive Dashboard](#starting-the-light-mode-interactive-dashboard)
   - [Running a Full Course Link Audit](#running-a-full-course-link-audit)
   - [Running Automated Tests](#running-automated-tests)
5. [How to Read the Reports & Status Badges](#5-how-to-read-the-reports--status-badges)
   - [Classification Statuses](#classification-statuses)
   - [Authority Hierarchy (Tiers 1–4)](#authority-hierarchy-tiers-14)
   - [Regulatory Status Lifecycle](#regulatory-status-lifecycle)
6. [The 100-Point Transparent Evidence Confidence Formula](#6-the-100-point-transparent-evidence-confidence-formula)
7. [Two-Stage Replacement Engine & Homepage Rejection Rule](#7-two-stage-replacement-engine--homepage-rejection-rule)
8. [Audited Course Findings & Key Regulatory Shifts](#8-audited-course-findings--key-regulatory-shifts)
9. [Project File Structure & Output Artifacts](#9-project-file-structure--output-artifacts)

---

## 1. Executive Summary & Core Philosophy

The **STEP ESG Link Monitor** is an enterprise-grade auditing and validation engine designed specifically for educational curricula, legal guidelines, and compliance frameworks. Unlike conventional link checkers that merely ping a server to see if it returns `HTTP 200 OK`, this system inspects the **substantive text**, determines the **underlying legal/regulatory authority**, evaluates **content freshness and obsolescence**, detects **bot challenges & soft-404s**, and automatically validates **authoritative replacements**.

### Fundamental System Invariants

- **`HTTP 200 != Valid`**: A server returning 200 can easily be an empty template, a soft-404 page ("Document not found"), an access challenge (Cloudflare, Turnstile, 403), or a generic homepage.
- **`HTTP 200 + Extracted Text != Current`**: An active, readable document can still be legally repealed, stayed by federal courts, superseded by a newer directive, or archived.
- **`Domain Match != Official Document`**: A link to `sebi.gov.in` or `sec.gov` is *not* a valid source for a specific disclosure requirement if it simply lands on the regulator's generic homepage (**Homepage Rejection Rule**).
- **`No Blind AI Hallucinations`**: Replacements must pass **Two-Stage Validation** (Stage 1: live HTTP/PDF fetchability; Stage 2: semantic relevance & regulatory intent match). Unverified candidate URLs are strictly rejected.

---

## 2. Why Traditional Link Checkers Fail for ESG

| Problem in ESG Courses | Traditional Link Checker Behavior | STEP ESG Pipeline Behavior |
|---|---|---|
| **Cloudflare / Bot Challenge (HTTP 403 / 202)** | Marks as "Dead / Error" or blindly assumes valid if `.gov`. | Flags as `ACCESS_RESTRICTED`, caps confidence at $\le 30\%$, explains the firewall rule, and queues for human review. |
| **Soft-404 Error Pages** | Sees `HTTP 200 OK` and marks as "Healthy". | Parses body text for *"page does not exist"*, *"404"*, *"file removed"*; classifies as `BROKEN`. |
| **Court Stays (e.g. SEC Climate Rule)** | URL is 100% active; marks as "Healthy". | Flags status as `STAYED_PENDING_LITIGATION` (SEC Administrative Stay 33-11280). |
| **Disbanded Bodies (e.g. TCFD to ISSB)** | Recommendations page exists; marks as "Healthy". | Identifies transition to IFRS/ISSB; classifies as `DISBANDED_TRANSITIONED` and supplies modern ISSB link. |
| **Superseded Law (e.g. EU NFRD to CSRD)** | NFRD text is permanently archived on EUR-Lex; marks as "Healthy". | Detects modern superseding directive (`CSRD Directive 2022/2464`); classifies as `COMPLETELY_SUPERSEDED`. |
| **Commercial Blog Aggregator** | URL works; marks as "Healthy". | Flags as `WORKING_BUT_NON_OFFICIAL` (`Tier 4`); replaces with official statutory regulator portal. |
| **Merged / Malformed URLs** | Crashes or reports connection error. | Unravels concatenated URLs, extracts valid sub-URLs, and tests the target document. |

---

## 3. Architecture: The 14-Step Deep Verification Pipeline

```
[Target URL / Course Link]
           │
           ▼
[Step 1: URL Normalization & Sanitization]  ──► Fixes trailing punctuation, merged URLs, schema flaws
           │
           ▼
[Step 2: Technical Retrieval & Network Check] ──► Inspects HTTP status, latencies, payloads, headers
           │
           ▼
[Step 3: Bot Challenge & Soft-404 Detection] ──► Detects Cloudflare, Turnstile, Akamai, JS-rendering blocks
           │
           ▼
[Step 4: Substantive Text Extraction]       ──► Extracts up to 5,000 characters from HTML or PDF docs
           │
           ▼
[Step 5: Document Fingerprinting]           ──► Generates SHA-256 hash, extracts titles, dates, & doc IDs
           │
           ▼
[Step 6: Source Authority Classification]   ──► 8-Tier Authority Hierarchy (Regulator vs. Aggregator)
           │
           ▼
[Step 7: Pedagogical Intent Profiling]      ──► Infers expected jurisdiction, topic, and document type
           │
           ▼
[Step 8: Semantic Relevance Scoring]        ──► Compares extracted content against curriculum intent
           │
           ▼
[Step 9: Homepage Rejection Guardrail]      ──► Rejects generic domain roots lacking specific content
           │
           ▼
[Step 10: Regulatory Freshness Check]       ──► 100-pt Freshness score; checks amendments, stays, repeals
           │
           ▼
[Step 11: Candidate Replacement Discovery]  ──► Identifies modern official replacements for failed links
           │
           ▼
[Step 12: Two-Stage Replacement Validation] ──► Validates Candidate: Stage 1 (Tech) + Stage 2 (Semantic)
           │
           ▼
[Step 13: Transparent Confidence Engine]    ──► Computes 100-point multi-factor evidence score
           │
           ▼
[Step 14: Final Classification & Routing]   ──► Multi-dimensional Section 22 record + Reporting
```

---

## 4. Quick Start & How to Use

### Starting the Light-Mode Interactive Dashboard

The dashboard features a **clean, high-contrast white/light theme** with interactive stat cards, authority badges, search & status filters, confidence progress bars, and expandable **Evidence Drawers**.

1. Start the dashboard server:
   ```bash
   python dashboard/server.py --port 8080 --report report.json
   ```
2. Open your browser and navigate to:
   ```
   http://localhost:8080/dashboard/?report=report.json
   ```
   *(Or click the direct link provided in the summary)*.

### Running a Full Course Link Audit

To run a live crawl across all 49 STEP Kajabi curriculum links and generate fresh report files (`report.json`, `report.csv`, and SQLite database records):

```bash
# Execute pipeline against Kajabi course references
python main.py --kajabi --json report.json --csv report.csv
```

Optional CLI flags:
- `--concurrency 5`: Sets maximum parallel requests.
- `--db custom_audit.db`: Directs persistence to a custom SQLite database file.
- `--urls "https://example.com/rule.pdf"`: Evaluates an ad-hoc list of URLs.

### Running Automated Tests

The test suite includes 42 comprehensive unit tests covering URL normalization, PDF/HTML text extraction, 8-tier authority classification, soft-404 detection, the Homepage Rejection Rule, and all Master Prompt validation criteria:

```bash
python -m pytest tests
```

### Scheduling Link Automation (Claude Pro & Windows Task Scheduler)

You can automate recurring link freshness audits using Claude Pro or OS-level task schedulers:

1. **Claude Pro Orchestrator:**
   - See [CLAUDE_SCHEDULING_MASTER_PROMPT.md](file:///c:/Users/HP-PC/Desktop/STEP/step_esg_pipeline/CLAUDE_SCHEDULING_MASTER_PROMPT.md) for the master instructions to paste into your Claude Pro Project.
   - Claude will autonomously interpret `report.json`, detect regulatory shifts, validate replacements, and output curriculum update patches.
2. **Windows Task Scheduler Script:**
   - Register a recurring weekly Monday 2:00 AM audit:
     ```powershell
     powershell -ExecutionPolicy Bypass -File .\schedule_task.ps1 -Action register -Frequency Weekly -DaysOfWeek Monday -At 2:00AM
     ```
   - Trigger the task immediately:
     ```powershell
     powershell -ExecutionPolicy Bypass -File .\schedule_task.ps1 -Action run
     ```
   - Check status or remove:
     ```powershell
     powershell -ExecutionPolicy Bypass -File .\schedule_task.ps1 -Action status
     powershell -ExecutionPolicy Bypass -File .\schedule_task.ps1 -Action unregister
     ```
3. **Web Dashboard Scheduler:**
   - Configure cron trigger rules directly in the browser at `http://localhost:8080/dashboard/settings.html`.

---

## 5. How to Read the Reports & Status Badges

### Classification Statuses

Every link is assigned an actionable final classification:

| Badge | Meaning | System Action |
|---|---|---|
| <span style="background:#ecfdf5;color:#047857;padding:3px 8px;border-radius:4px;font-weight:600;">VALID_AND_CURRENT</span> | Link is technically alive, official, highly relevant, and in force. | **KEEP**: No changes required. |
| <span style="background:#eff6ff;color:#1d4ed8;padding:3px 8px;border-radius:4px;font-weight:600;">VALID_BUT_REDIRECTED</span> | Link redirects permanently to a valid canonical destination. | **UPDATE_URL**: Update course URL to the canonical destination. |
| <span style="background:#fffbeb;color:#b45309;padding:3px 8px;border-radius:4px;font-weight:600;">WORKING_BUT_OUTDATED</span> | Link resolves, but references an obsolete or superseded regulatory version. | **REPLACE**: Swap with the attached verified modern link. |
| <span style="background:#faf5ff;color:#7e22ce;padding:3px 8px;border-radius:4px;font-weight:600;">WORKING_BUT_REGULATORY_STATUS_CHANGED</span> | Document is intact, but the legal state has changed (e.g. stayed by courts or transitioned). | **HUMAN_REVIEW_AND_REPLACE**: Update pedagogical notes and provide updated standard link. |
| <span style="background:#f1f5f9;color:#334155;padding:3px 8px;border-radius:4px;font-weight:600;">WORKING_BUT_NON_OFFICIAL</span> | Working link from a commercial blog or law-firm summary rather than the regulator. | **REPLACE**: Upgrade to the official statutory source. |
| <span style="background:#fffbeb;color:#b45309;padding:3px 8px;border-radius:4px;font-weight:600;">ACCESS_RESTRICTED</span> | Server presented Cloudflare, Turnstile, or HTTP 403/202 anti-bot challenges. | **HUMAN_REVIEW**: Manually verify behind firewall or white-list scraper IP. |
| <span style="background:#fef2f2;color:#b91c1c;padding:3px 8px;border-radius:4px;font-weight:600;">BROKEN</span> | HTTP 404, DNS failure, empty response, or confirmed Soft-404. | **REPLACE**: Apply verified replacement immediately. |
| <span style="background:#fef2f2;color:#b91c1c;padding:3px 8px;border-radius:4px;font-weight:600;">NEEDS_HUMAN_REVIEW</span> | Evidence is ambiguous or insufficient to make an automated determination. | **HUMAN_REVIEW**: Manual curriculum review required. |

### Authority Hierarchy (Tiers 1–4)

1. **Tier 1 — Official Statutory & Regulators**: Primary statutory legislation portals (e.g., `legislation.gov.uk`, `eur-lex.europa.eu`, `sec.gov`, `sebi.gov.in`, `mas.gov.sg`). Weight: **15 pts**.
2. **Tier 2 — Recognized Standards Bodies & Exchanges**: Standard-setters and stock exchanges (e.g., `ifrs.org`, `globalreporting.org`, `bseindia.com`, `adx.ae`). Weight: **12 pts**.
3. **Tier 3 — Institutional & Academic Repositories**: Multilateral institutions (e.g., `worldbank.org`, `oecd.org`, universities). Weight: **8 pts**.
4. **Tier 4 — Commercial Aggregators & Media**: Commercial blogs, law firm alerts, newsletters (e.g., `policyvault.africa`, `mondaq.com`). Weight: **4 pts**.

### Regulatory Status Lifecycle

- `LEGALLY_BINDING_IN_FORCE`: Enacted and active statutory law.
- `STAYED_PENDING_LITIGATION`: Enacted, but enforcement paused by judicial or administrative stay.
- `DISBANDED_TRANSITIONED`: Institution or task force concluded its work and handed mandate to a successor.
- `CONSULTATION_DRAFT`: Non-binding draft issued for public comments.
- `COMPLETELY_SUPERSEDED`: Replaced entirely by a newer legislative act.
- `HISTORICAL_FOUNDATIONAL`: Legacy milestone retained for educational/historical context.
- `PARTIALLY_SUPERSEDED`: Key provisions amended while remainder stands.

---

## 6. The 100-Point Transparent Evidence Confidence Formula

Rather than generating arbitrary percentages, the pipeline calculates confidence through an additive, verifiable 7-factor mathematical model:

$$\text{Confidence Score} = \frac{T + A + R + F + P + L + S}{100}$$

| Component | Max Points | Evaluation Criteria |
|---|:---:|---|
| **$T$: Technical Accessibility** | **15** | HTTP 200, substantive payload (> 250 characters), fast latency (< 3.0s). |
| **$A$: Authority Tier** | **15** | Tier 1 (15 pts), Tier 2 (12 pts), Tier 3 (8 pts), Tier 4 (4 pts). |
| **$R$: Content Relevance** | **20** | Proportional to keyword matches, title alignment, and jurisdictional fit. |
| **$F$: Content Freshness** | **20** | Proportional to absence of obsolescence language, recent amendment checks. |
| **$P$: Regulatory Applicability** | **15** | Legally binding (15 pts), Stayed / Transitioned (8 pts), Superseded (3 pts). |
| **$L$: Landing Page Precision** | **10** | Specific rule or PDF (10 pts), Sub-section (6 pts), Homepage (0 pts). |
| **$S$: Replacement Verification** | **5** | Verified replacement attached (5 pts), Unverified candidate (0 pts). |

> [!IMPORTANT]
> **Evidence Threshold Rule**: If substantive page content cannot be extracted (due to bot-blocking, empty payloads, or network dropouts), the confidence score is strictly capped at $\le 50\%$ and automatically flagged for manual review.

---

## 7. Two-Stage Replacement Engine & Homepage Rejection Rule

### The Homepage Rejection Rule
A common pitfall in automated curriculum maintenance is replacing a dead circular with the regulator's main landing page (e.g. replacing a repealed SEBI circular with `https://www.sebi.gov.in/`).  
The STEP pipeline **strictly rejects generic domain roots**:
- Path depth must be $> 1$ or point to a specific document (`.pdf`, `.html`, `/circulars/...`).
- Landing on a domain root yields `landing_page_precision = 0` and triggers rejection of candidate links.

### Two-Stage Replacement Validation
When an original link is broken, outdated, or commercial, the system identifies candidate replacements and subjects them to a strict two-stage filter:
1. **Stage 1 (Technical Verification)**: Live network request verifying `HTTP 200`, content size $> 500$ bytes, no bot challenges, and valid MIME type.
2. **Stage 2 (Semantic & Regulatory Verification)**: Verifies that the replacement covers the exact same topic, belongs to an authoritative source (Tier 1 or Tier 2), and represents the current or superseding version.
3. If both stages pass, the replacement is tagged `replacement_verified = True` and presented in the dashboard. If either fails, the candidate is discarded.

---

## 8. Audited Course Findings & Key Regulatory Shifts

During the full crawl of the 49 STEP Kajabi curriculum links, several critical regulatory findings were identified:

### 1. United States SEC Climate Disclosures (Release 33-11275)
- **Original URL:** `https://www.sec.gov/files/rules/final/2024/33-11275.pdf`
- **Audit Finding:** Document resolves with HTTP 200, but is **`STAYED_PENDING_LITIGATION`**.
- **Context:** On April 4, 2024, the SEC issued an administrative stay (Release No. 33-11280) pending judicial review in the 8th Circuit Court of Appeals.
- **Curriculum Recommendation:** Maintain the link for study of the rule text, but append a prominent note highlighting the administrative stay.

### 2. Task Force on Climate-Related Financial Disclosures (TCFD)
- **Original URL:** `https://www.fsb-tcfd.org/recommendations/`
- **Audit Finding:** Classifies as **`DISBANDED_TRANSITIONED`**.
- **Context:** The FSB disbanded the TCFD in late 2023. Responsibilities were handed over to the IFRS Foundation and ISSB.
- **Curriculum Recommendation:** Replace with the official [IFRS Sustainability Disclosure Standards (ISSB S1/S2)](https://www.ifrs.org/sustainability/issued-standards/).

### 3. European Union NFRD (Directive 2014/95/EU)
- **Original URL:** EUR-Lex Non-Financial Reporting Directive
- **Audit Finding:** Classifies as **`COMPLETELY_SUPERSEDED`**.
- **Context:** NFRD has been superseded by Directive (EU) 2022/2464 (CSRD).
- **Curriculum Recommendation:** Replace with [Directive (EU) 2022/2464 (CSRD)](https://eur-lex.europa.eu/eli/dir/2022/2464/oj).

### 4. Singapore Monetary Authority (MAS) Environmental Risk Management
- **Original URL:** `https://www.mas.gov.sg/.../Guidelines_on_Environmental_Risk_Management.pdf` (HTTP 404)
- **Audit Finding:** Consultation draft link was removed.
- **Verified Replacement:** [MAS Guidelines on Environmental Risk Management Portal](https://www.mas.gov.sg/regulation/guidelines/guidelines-on-environmental-risk-management) (Confidence: 95%).

### 5. Abu Dhabi Securities Exchange (ADX)
- **Original URL:** `https://adxservices.adx.ae/download/...` (Soft-404 empty document)
- **Verified Replacement:** [ADX Sustainability Portal](https://www.adx.ae/English/Pages/Products-and-Services/Sustainability.aspx) (Confidence: 95%).

---

## 9. Project File Structure & Output Artifacts

```
step_esg_pipeline/
├── README.md                      <-- This guide & technical manual
├── ESG_LINK_VALIDATION_REPORT.md  <-- Executive report with breakdown of all 49 links
├── report.json                    <-- Full 22-field JSON dataset of all links
├── report.csv                     <-- Spreadsheet export for curriculum team
├── step_esg_links.db              <-- SQLite database with historical crawl logs
├── main.py                        <-- Main CLI entry point
│
├── dashboard/                     <-- Web UI (Light / White Theme)
│   ├── index.html                 <-- Interactive dashboard with Evidence Drawers
│   ├── server.py                  <-- Local lightweight Python dashboard server
│   └── settings.html              <-- Pipeline configuration and scheduler
│
├── crawler/                       <-- Retrieval engine
│   ├── url_checker.py             <-- Network client, timeout & latency tracking
│   └── normalizer.py              <-- URL sanitation & merged URL unwrapping
│
├── content/                       <-- Parsing and extraction
│   ├── html_parser.py             <-- HTML & soft-404 / challenge detector
│   ├── pdf_parser.py              <-- PDF deep text extractor
│   └── metadata_extractor.py      <-- SHA-256 fingerprinting & date parsing
│
├── analysis/                      <-- Decision logic
│   ├── intent_analyzer.py         <-- Expected topic & jurisdiction profiler
│   ├── relevance_checker.py       <-- Semantic relevance & Homepage Rejection Rule
│   ├── freshness_checker.py       <-- 100-pt Freshness score & repeal detection
│   └── source_classifier.py       <-- 8-Tier source authority classifier
│
├── ai/                            <-- AI & replacement validation
│   ├── confidence_engine.py       <-- 100-point transparent evidence formula
│   ├── replacement_finder.py      <-- Two-stage replacement validator
│   └── evaluator.py               <-- Semantic evaluation harness & mock provider
│
├── database/                      <-- Persistence
│   └── models.py                  <-- Section 22 schema & SQLite migrations
│
├── reporting/                     <-- Serialization
│   ├── json_report.py             <-- Section 22 JSON builder
│   └── csv_report.py              <-- Section 22 CSV builder
│
└── tests/                         <-- Automated verification
    ├── test_analysis.py           <-- Logic and parser tests
    ├── test_master_prompt_cases.py<-- 12 comprehensive Master Prompt test cases
    └── test_pipeline.py           <-- End-to-end integration tests
```

---
*STEP ESG Link Monitor — Developed for rigorous, evidence-based regulatory compliance.*
