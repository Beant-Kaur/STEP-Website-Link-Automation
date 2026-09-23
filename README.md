# STEP ESG Link Monitoring & Kajabi Automation Platform

A clean, production-ready compliance platform designed for Sustainability Managers and ESG Analysts. Continuously monitors, verifies, and audits ESG regulations across 13 sovereign jurisdictions, and enables 1-click live updates to the STEP Kajabi portal with a tamper-evident audit ledger.

---

## Architecture Overview

```
step_esg_agent/
│
├── dashboard/
│   ├── index.html            # Executive UI (collapsible country cards, review modals, manual override, audit ledger)
│   └── server.py             # High-performance dashboard server & live update API
│
├── kajabi/
│   ├── login.py              # Interactive 1-time MFA browser helper (captures persistent session)
│   ├── updater.py            # Playwright automation: TinyMCE DOM link replacement & live Save
│   └── audit_log.json        # Permanent audit ledger tracking all updates, reviewer notes, and timestamps
│
├── agent/
│   └── step_agent.py         # AI Audit Agent (scans gazettes, verifies links, finds official replacements)
│
├── data/
│   ├── report.json           # Active compliance database (48 regulations with clean English titles & summaries)
│   └── kajabi_blocks.json    # Kajabi FAQ block & link hierarchy mapping
│
├── kajabi_session/           # Persistent Chromium user profile with authenticated MFA tokens (git-ignored)
├── .env                      # Portal credentials & API keys (git-ignored)
├── .env.example              # Credentials configuration template
├── requirements.txt          # Python dependencies
├── start_dashboard.bat       # 1-click Windows launcher for Dashboard
├── run_agent.bat             # 1-click Windows launcher for AI Scanner
└── login_kajabi.bat          # 1-click launcher for Kajabi MFA Login Helper
```

---

## Quick Start (3 Steps)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Verify Kajabi Authentication
Your persistent session is pre-authenticated in `kajabi_session/`. If you ever need to re-authenticate (e.g. session expires after weeks):
* Double-click `login_kajabi.bat` (or run `python kajabi/login.py`).
* Enter your MFA code in the browser window once; it will save session cookies and exit automatically.

### 3. Launch the Dashboard
Double-click `start_dashboard.bat` (or run):
```bash
python dashboard/server.py --port 8080 --open
```
The dashboard opens at **http://localhost:8080/dashboard/**.

---

## Core Features & Workflows

### 1. Executive Compliance Dashboard
* **Sovereign Card Grid**: Regulations grouped by jurisdiction with clean English titles and zero technical crawler jargon.
* **Collapsible State**: Country cards start collapsed by default. Expanding or collapsing cards maintains strict grid stability.
* **Filter Bar**: Filter by *Needs Action*, *Up to Date*, or *In Review*, with quick search and an *Expand All / Collapse All* toggle.

### 2. Review Modal & Kajabi Live Sync
Clicking **Review & Update** on any regulation opens the review modal:
* **Source Comparison**: Compares the current link against the verified official sovereign publication.
* **Executive Summary**: Clear *Finding* and *Recommendation* tags explaining the legal status.
* **Manual Link Override**: Check *Override with custom manual link* to enter any custom URL.
* **Reviewer Audit Note**: Enter mandatory or optional reviewer justification notes.
* **Approve & Update Kajabi**: Commits the change, updates the local database, directly navigates Kajabi's editor, replaces the link in the corresponding country block, clicks **Save**, and records the action into `kajabi/audit_log.json`.

### 3. Audit Trail
* Click **Audit Trail** in the top navigation bar to inspect every link update with before/after URLs, reviewer identity, timestamp, custom notes, and Kajabi live sync status.

### 4. Automated AI Audit Agent (`step_agent.py`)
To run an automated audit of the live STEP site against official government gazettes:
```bash
python agent/step_agent.py --all
```
* Crawls the live Kajabi page.
* Runs pre-flight deterministic checks (200 OK, redirects, 404, bot protections).
* Uses grounded search on official sovereign registers (`.gov`, `.gov.uk`, `eur-lex.europa.eu`, `sse.com.cn`, `mas.gov.sg`, etc.) to find latest replacements.
* Syncs verified findings into `data/report.json`.

---

## Configuration (`.env`)

```ini
# Kajabi Credentials & Theme Settings
KAJABI_EMAIL=beant@innovabeyond.digital
KAJABI_PASSWORD=your_password
KAJABI_THEME_ID=2161766380
KAJABI_EDIT_URL=https://app.kajabi.com/admin/themes/2161766380/settings/edit#/

# AI Search & Verification (for agent scanner)
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## Jurisdiction to Kajabi Block Mapping

| Dashboard Jurisdiction | Kajabi Editor FAQ Block |
| :--- | :--- |
| **Bahrain** | `BARHEIN` |
| **China** | `CHINA` |
| **European Union** | `EUROPEAN UNION` |
| **India** | `INDIA` |
| **Kingdom of Saudi Arabia** | `KSA` |
| **Kuwait** | `KUWAIT` |
| **Nigeria** | `Accordion` (labeled Nigeria inside) |
| **Oman** | `OMAN` |
| **Qatar** | `QATAR` |
| **Singapore** | `SINGAPORE` |
| **United Arab Emirates** | `UAE` |
| **United Kingdom** | `UK` |
| **United States** | `USA` |
