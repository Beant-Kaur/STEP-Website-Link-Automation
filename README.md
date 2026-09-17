# STEP ESG Link Monitor

## What this project does

This tool checks the ESG regulation links on the STEP website to make sure they are still working, point to the right source, and reflect the latest official rules. Instead of manually visiting every link, it automatically inspects each one and produces a simple report that tells you:

- Is the link still working?
- Does it lead to the correct regulation?
- Is there a better official source available?
- Does it need human review before changing anything?

The system never edits the website automatically. It only recommends changes and assigns a confidence score so a person can approve updates safely.

## How to run it

1. Double-click `start.bat` in the project folder.
2. The dashboard opens automatically in your browser.
3. If the browser does not open, copy this address into your browser:

   http://localhost:8080/dashboard/

4. To close the tool, close the command windows that open when you run `start.bat`.

## Features

### Link inventory
- Extracts every regulation link from the ESG Legislative Landscape section on the STEP website.
- Stores each link with its original URL, section, topic, and source.

### Technical checks
- Verifies DNS resolution.
- Checks SSL/TLS security.
- Follows redirects and records the full chain.
- Detects HTTP status including 200, 301, 302, 404, 410, 403, 503, and timeouts.
- Retries temporary failures before classifying them as broken.

### Content and authority analysis
- Reads page titles, organizations, and publication dates where possible.
- Classifies sources as Tier 1 official, Tier 2 recognized institutional, or lower tiers.
- Flags non-official sources when an official version exists.

### AI evaluation
- Uses Claude, OpenAI, or Google Gemini to decide whether a link is:
  - Valid and current
  - Redirected
  - Broken
  - Outdated
  - Access restricted
  - Requiring human review
- Returns a structured decision with a confidence score between 0 and 1.
- You can change the AI provider and model from the Settings page.

### Confidence scoring
- Every recommendation includes a numeric confidence score.
- Low-confidence results always route to human review.
- High-confidence results with official sources can be approved faster.

### Decision engine
- Broken or outdated links are marked as replacement candidates.
- Temporary issues like 503 or timeout are marked for retry.
- Access-restricted links are flagged for verification before replacement.
- All actions are recorded for audit.

### Scheduled monitoring
- Runs automatically on the schedule you set: daily, weekly, or monthly.
- Choose the day of week, hour, and minute from the Settings page.
- No need to remember to run it manually.

### Dashboard
- Shows total links, valid links, restricted links, replacement candidates, and average confidence.
- Search by URL, title, or organization.
- Filter by status, authority tier, and confidence.
- Click any link to open the original or proposed replacement.

### Reports
- Exports CSV and JSON reports.
- JSON report feeds the dashboard automatically.
- CSV report can be opened in Excel for offline review.

### Safety rules
- Never replaces a link solely because it returned a non-200 status.
- Never treats 403 as automatically broken.
- Never replaces a low-confidence recommendation automatically.
- Never edits the STEP website without authorization.
- Never exposes API keys in reports.
- Preserves the original URL in all records.

## Where to find things

| Item | Location |
|------|----------|
| Start script | `start.bat` |
| Dashboard | http://localhost:8080/dashboard/ |
| Settings | http://localhost:8080/dashboard/settings.html |
| JSON report | `step_esg_pipeline/report.json` |
| CSV report | `step_esg_pipeline/report.csv` |
| Database | `step_esg_pipeline/step_esg_links.db` |
| Configuration | `step_esg_pipeline/config.json` |
| API keys | `step_esg_pipeline/.env` |

## Requirements for AI features

To use real AI evaluation instead of the built-in mock mode, add your API key to the Settings page or to the `.env` file:

- Anthropic Claude: add `ANTHROPIC_API_KEY`
- OpenAI: add `OPENAI_API_KEY`
- Google Gemini: add `GEMINI_API_KEY`

The default mode is Mock, which does not make external API calls.

## Support

If the dashboard shows Failed to load report, open the command window from `start.bat` and check for errors. If the server is not running, close all command windows and double-click `start.bat` again.
