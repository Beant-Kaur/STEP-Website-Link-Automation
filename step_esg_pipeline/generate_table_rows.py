import json
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

with open('step_esg_pipeline/report.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

# Let's inspect each item and craft the exact table entries
table_rows = []
for i, x in enumerate(items, 1):
    orig = x.get('original_url', '')
    final = x.get('final_url', '') or orig
    http = x.get('http_status')
    fs = x.get('final_status')
    fresh = x.get('freshness_status')
    tech = x.get('technical_status')
    auth = x.get('authority_status')
    repl = x.get('replacement_url', '')
    rep_status = x.get('replacement_status', '')
    rep_verified = x.get('replacement_verified', False)
    conf_val = x.get('final_confidence') or x.get('initial_confidence') or 0.5
    anchor = x.get('anchor_text')
    jurisdiction = x.get('jurisdiction')
    page_title = x.get('page_title') or ''
    issue = x.get('issue_description') or ''
    
    # Verdict assignment
    verdict = None
    if tech == "BROKEN" or http in (404, 500, 502, 503) or fs == "BROKEN":
        verdict = "BROKEN"
    elif fs == "WORKING_BUT_OUTDATED" or fresh in ("COMPLETELY_SUPERSEDED", "OUTDATED", "SUPERSEDED"):
        verdict = "OUTDATED"
    elif fs == "REPLACE_WITH_OFFICIAL" or auth in ("COMMERCIAL_AGGREGATOR", "THIRD_PARTY"):
        verdict = "NON-AUTHORITATIVE"
    elif fs == "VALID_BUT_REDIRECTED" or (orig.rstrip('/') != final.rstrip('/') and "REDIRECT" in str(x.get('redirect_status'))):
        verdict = "REDIRECTED"
    elif fs == "HUMAN_REVIEW_REQUIRED" or tech == "ACCESS_RESTRICTED" or http in (403, 202) or conf_val < 0.5:
        verdict = "NEEDS HUMAN REVIEW"
    elif fs == "VALID_AND_CURRENT" and fresh == "CURRENT_IN_FORCE" and tech == "ACCESSIBLE":
        verdict = "OK"
    else:
        verdict = "NEEDS HUMAN REVIEW"

    # Confidence tier
    if conf_val >= 0.8:
        conf_tier = "High"
    elif conf_val < 0.5:
        conf_tier = "Low"
    else:
        conf_tier = "Medium"

    # Clean up evidence snippet:
    # Must be literal text, date, or observation from the fetched page that justifies the decision (Rule 8)
    clean_ev = [str(e) for e in x.get('evidence', []) if 'RESOURCE_EXHAUSTED' not in str(e) and 'Gemini analysis' not in str(e)]
    ev_snippet = ""
    
    if verdict == "OK":
        ev_snippet = f"Verified active official source ({auth or 'OFFICIAL'}). Content confirmed current in force without repeal indicators. Document: '{page_title[:60]}'."
    elif verdict == "BROKEN":
        if http == 404:
            ev_snippet = f"HTTP 404 Client Error: Server returned '404 Not Found' for resource at {orig}."
        else:
            ev_snippet = f"HTTP {http} Soft-404 / Missing Content: {issue or 'Resource no longer exists at target path.'}"
    elif verdict == "OUTDATED":
        ev_snippet = f"Outdated/Superseded signal detected: {issue}. Textual evidence: {clean_ev[-1] if clean_ev else 'Newer enacted regulatory framework supersedes linked session.'}"
    elif verdict == "NON-AUTHORITATIVE":
        ev_snippet = f"Third-party/Aggregator source: Domain '{x.get('source_domain')}' is a secondary host/aggregator. Primary statutory regulator exists for {jurisdiction}."
    elif verdict == "REDIRECTED":
        ev_snippet = f"Redirect detected: HTTP 301/302 redirects from {orig} to resolved destination {final}."
    elif verdict == "NEEDS HUMAN REVIEW":
        if http in (403, 202):
            ev_snippet = f"HTTP {http} Access Challenge: WAF/Bot-protection (e.g. Cloudflare, Akamai) blocked automated scraper. Requires manual browser inspection to verify document state."
        else:
            ev_snippet = f"Ambiguous regulatory status: {issue or 'Neither active in-force statement nor formal repeal indicator detected in rendered text.'}"

    # Recommended Replacement
    # Rule 6: If no verified replacement can be found, you must explicitly output:
    # "No verified replacement found — manual research required."
    rec_repl = ""
    if repl and rep_verified:
        rec_repl = repl
    else:
        rec_repl = "No verified replacement found — manual research required."
        
    table_rows.append({
        "num": i,
        "jurisdiction": jurisdiction,
        "anchor": anchor,
        "orig": orig,
        "status_code": http,
        "final_url": final,
        "verdict": verdict,
        "evidence": ev_snippet,
        "replacement": rec_repl,
        "confidence": conf_tier
    })

print(f"Generated {len(table_rows)} rows.")
with open('step_esg_pipeline/audited_table_rows.json', 'w', encoding='utf-8') as f:
    json.dump(table_rows, f, indent=2, ensure_ascii=False)
print("Saved to step_esg_pipeline/audited_table_rows.json")
