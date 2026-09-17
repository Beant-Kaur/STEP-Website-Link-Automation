# MASTER PROMPT — STEP ESG LINK MONITORING, VALIDATION & AUTOMATED REPLACEMENT PIPELINE

## 1. ROLE

You are an expert **AI software engineer, web automation engineer, information-retrieval engineer, and ESG regulatory-content monitoring specialist**.

Your task is to design and build a production-quality pipeline for monitoring the external links used in the **STEP website's “ESG Legislative Landscape (Binding & Non-binding Rules, Standards, and Regulations)” section**.

Do not treat this as a simple broken-link checker.

The system must determine whether each link is:

1. Technically accessible
2. Redirecting correctly
3. Pointing to the intended content
4. From an authoritative source
5. Still current
6. Still legally/regulatorily relevant
7. Using the latest available version where applicable
8. Suitable to remain published on STEP

The ultimate objective is to create an **AI-assisted link intelligence and maintenance pipeline** that can detect problems, identify better replacement links, explain why a change is required, assign a confidence score, and eventually support safe automated updates.

---

# 2. BUSINESS PROBLEM

STEP contains educational content related to ESG legislation, regulations, standards, frameworks, reporting requirements, and sustainability guidance across multiple jurisdictions.

External sources can change over time.

A link may:

- stop working completely,
- return a 404,
- redirect to another page,
- move to a new government/regulator URL,
- remain accessible but contain an outdated regulation,
- point to an old version of a standard,
- be replaced by a new official publication,
- lead to a different document,
- remain technically valid but no longer be the best official source,
- temporarily become unavailable,
- or remain valid but require human review because its regulatory status is unclear.

Therefore:

> HTTP link validation alone is not sufficient.

The system must combine **technical web validation + webpage/document analysis + source authority analysis + regulatory freshness analysis + AI reasoning**.

---

# 3. PRIMARY OBJECTIVE

Build a pipeline that follows this overall process:

```text
STEP Website
      ↓
Extract Links
      ↓
Create Link Inventory
      ↓
Technical URL Check
      ↓
Redirect Analysis
      ↓
Destination/Page Analysis
      ↓
Source Authority Analysis
      ↓
Regulatory & Content Freshness Analysis
      ↓
AI Classification
      ↓
Find Replacement if Required
      ↓
Validate Replacement
      ↓
Assign Confidence Score
      ↓
Generate Recommended Action
      ↓
Human Approval / Safe Automation
      ↓
Update STEP
      ↓
Create Audit Log
      ↓
Continuous Monitoring
```

Build the architecture so that the system can initially operate in **read-only/reporting mode**, and later be extended to automatically update STEP when the required technical access and confidence level are available.

---

# 4. IMPORTANT PRINCIPLE

Do NOT assume:

```text
HTTP 200 = Good Link
HTTP 404 = Only Problem
```

Instead use:

```text
Link Health =
Technical Accessibility
+
Correct Destination
+
Content Relevance
+
Source Authority
+
Regulatory Freshness
+
Version Validity
```

A link should only be considered fully healthy when the available evidence supports all relevant dimensions.

---

# 5. PHASE 1 — DISCOVER AND INVENTORY STEP LINKS

Build a crawler/extractor that can identify all links within the target STEP section.

For every link, create a structured record containing at minimum:

```text
link_id
jurisdiction
topic
STEP_section
STEP_description
original_url
link_text
source_position
discovered_at
```

The system should preserve the original URL exactly as found.

Do not overwrite the original URL when a replacement is discovered.

---

# 6. PHASE 2 — TECHNICAL URL VALIDATION

For every URL, perform a technical validation.

Check:

- DNS resolution
- SSL/TLS validity
- connection success
- HTTP status code
- response headers
- response content type
- timeout
- redirects
- redirect chain
- final destination
- final HTTP status
- whether the response is HTML/PDF/other document
- whether the destination is accessible to a normal user

Handle common statuses including:

```text
200
301
302
307
308
400
401
403
404
410
408
429
500
502
503
504
```

Also handle:

```text
DNS failure
SSL failure
connection timeout
connection refused
network error
robots/access restrictions
JavaScript-only pages
authentication-required pages
```

Do not automatically classify every non-200 response as "broken."

For example:

- 301/302 → potentially healthy if final destination is correct
- 403 → may indicate access restrictions rather than a dead link
- 429 → rate limiting
- 503 → potentially temporary outage
- timeout → uncertain until retried
- 200 → technically working but may still be outdated

Implement retry logic for transient failures.

Use sensible:

- timeout limits
- retry limits
- exponential backoff
- rate limiting
- concurrency limits

Avoid aggressive crawling.

---

# 7. PHASE 3 — REDIRECT ANALYSIS

If a URL redirects, record the complete redirect chain.

Example:

```text
Original URL
    ↓
301
    ↓
Intermediate URL
    ↓
302
    ↓
Final URL
```

Store:

```text
original_url
redirect_chain
final_url
redirect_count
final_status
final_domain
```

Determine whether:

### A. Healthy Redirect

The redirect leads to the correct current official source.

### B. Suspicious Redirect

The redirect works but leads somewhere unexpected.

### C. Incorrect Redirect

The destination no longer corresponds to the original STEP topic.

### D. Redirect Chain Too Long

Flag unnecessarily long or potentially unstable redirect chains.

---

# 8. PHASE 4 — DESTINATION CONTENT ANALYSIS

Do not stop at HTTP validation.

Retrieve and analyse the destination content where technically possible.

For HTML pages identify:

- page title
- organisation
- regulator/government body
- publication title
- relevant headings
- publication date
- updated date
- effective date
- version
- amendment information
- repeal/withdrawal information
- replacement information
- document links
- relevant ESG/legal keywords

For PDFs/documents identify:

- document title
- issuing organisation
- document date
- effective date
- version
- revision number
- publication status
- relevant regulation/standard name
- whether it references an earlier or newer version

Do not rely exclusively on metadata.

Use the actual page/document content when possible.

---

# 9. PHASE 5 — LINK CLASSIFICATION SYSTEM

Every link must be assigned one primary status.

Implement at least these categories:

## CATEGORY A — VALID & CURRENT

The link works, points to the intended content, comes from an appropriate source, and appears current.

Action:

```text
KEEP
```

---

## CATEGORY B — VALID BUT REDIRECTED

The original URL redirects to the correct current destination.

Action:

```text
KEEP / UPDATE URL
```

Depending on the redirect stability, recommend replacing the old URL with the final canonical URL.

---

## CATEGORY C — BROKEN / NOT FOUND

Examples:

```text
404
410
dead domain
invalid URL
DNS failure
```

Action:

```text
FIND REPLACEMENT
```

---

## CATEGORY D — TEMPORARILY UNAVAILABLE

Examples:

```text
503
timeout
429
temporary server error
maintenance
```

Action:

```text
RETRY + MONITOR
```

Do not immediately replace the source.

---

## CATEGORY E — ACCESS RESTRICTED / UNCERTAIN

Examples:

```text
403
authentication required
bot protection
JavaScript-only access
```

Action:

```text
VERIFY BEFORE CLASSIFICATION
```

Do not automatically declare the link broken.

---

## CATEGORY F — WORKING BUT OUTDATED

The URL works, but the content has been replaced, updated, amended, or superseded.

Action:

```text
FIND CURRENT VERSION
```

---

## CATEGORY G — WORKING BUT REGULATORY STATUS CHANGED

The page works but the underlying law/regulation/framework may have been:

- amended
- repealed
- withdrawn
- replaced
- superseded
- postponed
- extended
- made effective
- made applicable
- transitioned to a new framework

Action:

```text
REGULATORY REVIEW
```

---

## CATEGORY H — WORKING BUT OLD VERSION

The document is validly accessible but an updated version exists.

Action:

```text
REPLACE WITH LATEST VERSION
```

---

## CATEGORY I — WORKING BUT NON-OFFICIAL

The URL works but is hosted by:

- consultancy
- law firm
- news site
- blog
- aggregator
- third-party database

while a suitable official source exists.

Action:

```text
SEARCH FOR PRIMARY SOURCE
```

Do not automatically replace if the third-party source provides unique context that STEP intentionally requires.

---

## CATEGORY J — WRONG DESTINATION

The URL works but does not contain the content described by STEP.

Action:

```text
FIND CORRECT SOURCE
```

---

## CATEGORY K — CONTENT MISMATCH

The page is related to the general subject but does not correspond to the specific regulation, standard, guideline, or framework referenced by STEP.

Action:

```text
REVIEW / REPLACE
```

---

## CATEGORY L — SOURCE STRUCTURE CHANGED

The organisation still provides the relevant information, but its website structure has changed significantly.

Example:

```text
old government PDF
       ↓
new legislation portal
       ↓
current regulation database
```

Action:

```text
FIND CANONICAL CURRENT SOURCE
```

---

## CATEGORY M — CURRENT BUT REQUIRES HUMAN REVIEW

The system cannot confidently determine whether the source remains current or appropriate.

Action:

```text
HUMAN REVIEW
```

---

# 10. PHASE 6 — SOURCE AUTHORITY ANALYSIS

The AI must evaluate the authority of the source.

Use a hierarchy.

### Tier 1 — Primary Official Sources

Highest preference:

- government websites
- regulators
- official legislation portals
- stock exchanges
- official standard-setting organisations
- official ministries
- official environmental agencies
- official financial authorities

### Tier 2 — Recognised Institutional Sources

Examples:

- international organisations
- recognised industry bodies
- established professional institutions

### Tier 3 — Secondary Sources

Examples:

- law firms
- consulting firms
- professional publications
- research organisations

### Tier 4 — General Secondary Sources

Examples:

- blogs
- news articles
- aggregators
- generic reference websites

For regulatory/legal content, prefer Tier 1 whenever an appropriate primary source exists.

The AI must never select a replacement merely because it ranks first in search results.

---

# 11. PHASE 7 — REGULATORY FRESHNESS ANALYSIS

This is one of the most important parts of the system.

The AI should inspect the source for signals such as:

```text
updated
revised
amended
superseded
replaced
withdrawn
repealed
effective
applicable
version
revision
consultation
transition
implementation
new requirements
previous version
```

Also look for explicit statements such as:

```text
This replaces...
This supersedes...
This guidance has been updated...
The previous version is withdrawn...
Effective from...
Applicable from...
```

The AI must distinguish between:

```text
Publication Date
Effective Date
Amendment Date
Last Updated Date
Version Date
```

These are not necessarily the same.

---

# 12. PHASE 8 — REPLACEMENT SOURCE DISCOVERY

When a link requires replacement, the system should search for the correct replacement.

Use this priority order:

### Step 1

Search the original issuing organisation.

### Step 2

Search the official regulator/government/standard setter.

### Step 3

Search recognised institutional sources.

### Step 4

Use secondary sources only when necessary.

The replacement must correspond to the same:

```text
jurisdiction
topic
regulation/standard
purpose
scope
```

Do not simply replace a broken URL with a related webpage.

---

# 13. PHASE 9 — REPLACEMENT VALIDATION

Every proposed replacement must be independently validated.

Check:

### Authority

Is it from an appropriate authoritative source?

### Identity

Does it actually represent the same regulation/standard/framework?

### Currentness

Is it the latest applicable version?

### Relevance

Does it satisfy the purpose of the original STEP link?

### Accessibility

Can normal users access it?

### Stability

Is it likely to be a stable/canonical URL?

### Content Type

Does it link to the correct:

- webpage
- regulation
- PDF
- guidance
- standard
- database
- official document?

---

# 14. PHASE 10 — AI REASONING LAYER

Use an AI/LLM component only where semantic reasoning is required.

Do not use an LLM for tasks that deterministic code can handle reliably.

### Deterministic code should handle:

- HTTP requests
- status codes
- redirects
- DNS
- SSL
- timeouts
- retries
- URL parsing
- content extraction
- duplicate detection
- hashing
- scheduling
- database operations

### AI should handle:

- semantic content comparison
- identifying whether a replacement matches the original topic
- interpreting regulatory update language
- comparing old and new documents
- determining likely currentness
- explaining why a link is outdated
- identifying possible replacement sources
- assigning confidence
- generating human-readable recommendations

This separation is extremely important.

---

# 15. PHASE 11 — CONFIDENCE SCORING

Every AI classification and replacement recommendation must include a confidence score.

Use:

```text
HIGH
MEDIUM
LOW
```

or preferably a numeric score:

```text
0.00 – 1.00
```

Example:

```text
0.95 = very high confidence
0.80 = high confidence
0.65 = medium confidence
0.40 = low confidence
```

The system should also store the reason for the confidence score.

Example:

```text
Confidence: 0.94

Reason:
- Original URL returns 404
- Same regulator has published a newer document
- New document title matches original topic
- New document explicitly supersedes previous version
- Official regulator domain
```

---

# 16. PHASE 12 — DECISION ENGINE

Create a rule-based + AI-assisted decision engine.

Example:

```text
IF status = 200
AND source = official
AND content = correct
AND currentness = confirmed
THEN KEEP

IF status = 301/302
AND final destination = correct
THEN RECOMMEND_CANONICAL_UPDATE

IF status = 404/410
AND replacement confidence >= threshold
THEN RECOMMEND_REPLACEMENT

IF status = 503/timeout
THEN RETRY

IF status = 403
THEN HUMAN_REVIEW

IF content = outdated
AND current official replacement confidence >= threshold
THEN RECOMMEND_REPLACEMENT

IF regulatory status = uncertain
THEN HUMAN_REVIEW

IF replacement confidence < threshold
THEN DO_NOT_AUTO_UPDATE
```

Make the thresholds configurable.

Do not hard-code assumptions that cannot later be changed.

---

# 17. PHASE 13 — HUMAN-IN-THE-LOOP SAFETY

The system must support human approval.

Recommended workflow:

```text
AI detects issue
      ↓
AI proposes replacement
      ↓
AI explains reasoning
      ↓
Confidence score
      ↓
Human reviews
      ↓
Approve / Reject / Modify
      ↓
Update STEP
```

Initially, implement:

```text
DETECT → RECOMMEND → HUMAN APPROVAL
```

Do not begin with unrestricted automatic replacement.

Later, support:

```text
HIGH CONFIDENCE
+
PRIMARY OFFICIAL SOURCE
+
CLEAR REPLACEMENT
+
NO SEMANTIC AMBIGUITY
=
OPTIONAL AUTO-UPDATE
```

---

# 18. PHASE 14 — DATA MODEL

Create a structured database/table for monitored links.

At minimum include:

```text
id
jurisdiction
topic
step_section
step_description

original_url
current_url
final_url

http_status
technical_status
redirect_status

page_title
source_organisation
source_domain
source_authority_tier

publication_date
updated_date
effective_date
version

content_status
regulatory_status
freshness_status

classification
issue_description

replacement_url
replacement_title
replacement_source
replacement_reason

confidence_score
confidence_reason

recommended_action

human_review_required
human_review_status

last_checked_at
next_check_at

content_hash
previous_content_hash

created_at
updated_at
```

Design the schema so that future historical versions can be stored.

---

# 19. PHASE 15 — CHANGE DETECTION

Do not only monitor whether the URL works.

Detect changes to the source.

Where practical, store:

```text
content hash
page title
document metadata
relevant extracted text
last checked date
```

Compare previous and current versions.

If significant changes occur, flag:

```text
CONTENT_CHANGED
```

Then ask the AI to determine whether the change is relevant to STEP.

This allows the system to detect:

```text
URL still works
BUT
content has materially changed
```

---

# 20. PHASE 16 — REPORTING DASHBOARD / OUTPUT

Create a clear monitoring report.

The report should show:

| Field | Example |
|---|---|
| Link | Original STEP URL |
| Jurisdiction | India |
| Topic | BRSR |
| Technical Status | 404 |
| Source | SEBI |
| Authority | Tier 1 |
| Regulatory Status | Current |
| Freshness | Outdated |
| Classification | Broken |
| Replacement | Proposed URL |
| Confidence | 0.94 |
| Action | Replace |
| Review | Required |

Also provide summary metrics:

```text
Total Links
Healthy Links
Redirected Links
Broken Links
Temporarily Unavailable
Outdated Links
Wrong Destinations
Non-official Sources
Human Review Required
Replacement Candidates
High-confidence Replacements
```

---

# 21. PHASE 17 — AUDIT TRAIL

Every change must be traceable.

For every replacement record:

```text
old URL
new URL
date detected
date approved
reason
evidence
AI confidence
reviewer
approval status
```

Never silently overwrite historical information.

The system must answer:

> Why was this STEP link changed?

---

# 22. PHASE 18 — SCHEDULING

The system should support scheduled monitoring.

For example:

```text
Daily
Weekly
Monthly
Custom schedule
```

Do not assume every link needs the same monitoring frequency.

Potentially classify monitoring frequency based on:

```text
regulatory importance
source volatility
historical change frequency
criticality
```

Example:

```text
High-risk regulatory source → weekly
Stable standard → monthly
Low-risk informational source → quarterly
```

Make the schedule configurable.

---

# 23. PHASE 19 — TECHNOLOGY ARCHITECTURE

Choose a practical technology stack.

A reasonable initial architecture could include:

### Backend

Python

### HTTP / Web

Use an appropriate HTTP client and HTML parser.

### PDF Processing

Use appropriate PDF text extraction.

### Database

Start with SQLite if building an MVP.

Design the repository so it can later migrate to PostgreSQL.

### AI

Use an LLM through a clean abstraction layer.

Do not tightly couple the entire application to one AI provider.

### Frontend

For MVP, use a simple dashboard such as Streamlit if appropriate.

### Scheduler

Use an appropriate scheduler for local development and make the design deployable later.

### Configuration

Use environment variables for:

```text
API keys
AI credentials
database configuration
STEP credentials
monitoring settings
```

Never hard-code secrets.

---

# 24. PHASE 20 — KAJABI / STEP UPDATE LAYER

Treat STEP updating as a separate module.

Architecture:

```text
Monitoring Engine
       ↓
Decision Engine
       ↓
Approval
       ↓
STEP Update Adapter
```

Do not mix monitoring logic directly with website modification logic.

The update adapter should support:

```text
read current STEP content
identify target link
replace URL
preserve surrounding content
validate modification
record audit log
```

Before implementing automatic updates, investigate the available STEP/Kajabi access method and determine whether the required page/content modification API is actually available.

If write access is not available:

```text
DO NOT SIMULATE AN UPDATE
```

Instead generate:

```text
proposed change
old URL
new URL
exact location
reason
confidence
```

---

# 25. IMPORTANT SAFETY RULES

The system must NEVER:

1. Replace a link solely because it returns a non-200 response.
2. Treat a 403 as automatically broken.
3. Treat a 503 as permanently broken.
4. Select the first search result as the replacement.
5. Replace an official source with a third-party source without justification.
6. Assume a newer publication date automatically means the old source is invalid.
7. Assume a regulation is repealed without evidence.
8. Automatically replace low-confidence recommendations.
9. Delete the original URL from the audit history.
10. Modify STEP without authorization.
11. Expose API keys or credentials.
12. Crawl aggressively or ignore rate limits.
13. Claim a source is legally current when the evidence is insufficient.
14. Use AI-generated assumptions as regulatory facts.

---

# 26. ERROR HANDLING

The application must gracefully handle:

```text
network failures
timeouts
DNS errors
SSL errors
HTTP errors
malformed URLs
invalid HTML
PDF extraction failures
encoding issues
JavaScript pages
rate limiting
robots/access restrictions
AI API failures
AI timeouts
invalid AI responses
database errors
authentication failures
```

Failures should be logged without stopping the entire pipeline.

One problematic URL must not crash the complete monitoring run.

---

# 27. AI OUTPUT FORMAT

Whenever the AI evaluates a link, require structured output.

Example:

```json
{
  "classification": "WORKING_BUT_OUTDATED",
  "technical_status": "accessible",
  "source_authority": "Tier 1",
  "source_organisation": "Official regulator",
  "content_relevance": "high",
  "regulatory_status": "superseded",
  "freshness_status": "outdated",
  "replacement_required": true,
  "replacement_url": "candidate URL",
  "replacement_reason": "The official organisation published a newer version that supersedes the linked document.",
  "confidence_score": 0.94,
  "recommended_action": "HUMAN_REVIEW_AND_REPLACE"
}
```

Validate AI output against a schema before storing it.

Never trust free-form AI output directly for critical system actions.

---

# 28. TESTING REQUIREMENTS

Build tests for at least:

### Technical

- 200
- 301
- 302
- 404
- 410
- 403
- 429
- 500
- 503
- timeout
- malformed URL

### Content

- current page
- outdated page
- superseded document
- wrong document
- unrelated page

### Source

- official source
- third-party source
- official replacement available
- no replacement found

### AI

- valid structured response
- malformed AI response
- low-confidence response
- ambiguous replacement
- hallucinated replacement

### Safety

Verify that:

```text
low confidence ≠ automatic update
```

and:

```text
temporary failure ≠ replacement
```

---

# 29. MVP REQUIREMENTS

Do not attempt to build everything at once.

First create a working MVP with:

```text
1. STEP link extraction
2. Link inventory
3. Technical URL checker
4. Redirect detection
5. Basic webpage/PDF extraction
6. Link classification
7. Official-source identification
8. AI semantic analysis
9. Replacement discovery
10. Confidence score
11. CSV/JSON report
12. Human review status
13. Logging
```

Only after this works reliably should you implement:

```text
automated STEP updates
advanced change detection
scheduled monitoring
dashboard
historical version tracking
```

---

# 30. DEVELOPMENT APPROACH

Work incrementally.

### Step 1

Inspect the target STEP page and understand its structure.

### Step 2

Build the link extractor.

### Step 3

Create the link inventory.

### Step 4

Build the deterministic technical checker.

### Step 5

Build redirect handling.

### Step 6

Build content extraction.

### Step 7

Build source authority classification.

### Step 8

Build regulatory freshness analysis.

### Step 9

Integrate the AI reasoning layer.

### Step 10

Build replacement discovery.

### Step 11

Build confidence scoring.

### Step 12

Build the decision engine.

### Step 13

Build reporting.

### Step 14

Build tests.

### Step 15

Investigate and implement the STEP/Kajabi update adapter only after the monitoring pipeline is reliable.

---

# 31. CODE QUALITY REQUIREMENTS

Write clean, maintainable, modular code.

Use clear separation of concerns.

Suggested modules:

```text
crawler/
    step_extractor
    url_checker
    redirect_checker

content/
    html_parser
    pdf_parser
    metadata_extractor

analysis/
    source_classifier
    freshness_checker
    content_comparator

ai/
    evaluator
    replacement_finder
    confidence_engine

pipeline/
    orchestrator
    decision_engine

database/
    models
    repository

reporting/
    csv_report
    json_report
    dashboard

step/
    step_reader
    step_updater

tests/
```

Do not create one giant Python file.

---

# 32. OBSERVABILITY

Implement useful logs.

For every pipeline run record:

```text
run_id
start_time
end_time
total_links
successful_checks
failed_checks
AI_evaluations
replacement_candidates
human_review_items
errors
```

For individual links record processing stages.

Example:

```text
[1] Extracted
[2] HTTP checked
[3] Redirect analysed
[4] Content extracted
[5] Source evaluated
[6] Freshness evaluated
[7] AI classification
[8] Replacement searched
[9] Recommendation generated
```

---

# 33. EXPLAINABILITY

The system must not simply say:

```text
OUTDATED
```

It should explain:

```text
Why is it outdated?
What evidence supports this?
What changed?
What is the proposed replacement?
Why is the replacement appropriate?
How confident is the system?
```

The final output should be understandable to a non-technical ESG professional.

---

# 34. FINAL SUCCESS CRITERIA

The project will be considered successful when the system can take a STEP ESG link and produce something like:

```text
Original Link:
[URL]

Technical Status:
Accessible

Final Destination:
[URL]

Source:
Official Government / Regulator

Authority:
Tier 1

Content:
Relevant

Regulatory Status:
Superseded

Freshness:
Outdated

Issue:
The linked document has been replaced by a newer official version.

Replacement:
[NEW URL]

Replacement Validation:
Passed

Confidence:
94%

Recommended Action:
Replace after human approval
```

The system should also be able to identify:

```text
Healthy → Keep
Redirected → Canonicalize
Broken → Find replacement
Temporary failure → Retry
Outdated → Find current version
Superseded → Find replacement
Non-official → Prefer primary source
Wrong destination → Replace
Uncertain → Human review
```

---

# 35. MOST IMPORTANT DESIGN PRINCIPLE

Build this as a **Link Intelligence Pipeline**, not simply a **Broken Link Checker**.

The difference is:

```text
Broken Link Checker

"Does this URL work?"
```

versus:

```text
Link Intelligence Pipeline

"Does this STEP link still work,
lead to the correct information,
come from the right authority,
represent the current regulatory position,
and remain the best source for STEP users?"
```

The second objective is the actual goal.

Start by inspecting the STEP page structure and proposing the project architecture and implementation plan before writing large amounts of code.

Do not make assumptions about API access, Kajabi write permissions, authentication, or automatic updating.

Where information is uncertain, explicitly identify the uncertainty and determine what needs to be verified.

Build the system in small, testable stages and show the result of each major stage before proceeding to the next.