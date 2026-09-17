import json

with open('step_esg_pipeline/report.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

# Let's inspect each link's:
# 1. Original URL
# 2. Status Code
# 3. Final URL
# 4. Verdict
# 5. Evidence Snippet
# 6. Recommended Replacement
# 7. Confidence

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
    
    # Filter out API error messages from evidence
    clean_ev = [str(e) for e in x.get('evidence', []) if 'RESOURCE_EXHAUSTED' not in str(e) and 'Gemini analysis' not in str(e)]
    
    print(f"[{i}] {jurisdiction} | {anchor}")
    print(f"    Orig: {orig}")
    print(f"    HTTP: {http} | Final: {final}")
    print(f"    Title: {page_title}")
    print(f"    CleanEv: {clean_ev}")
    print(f"    Repl: {repl} (verified={rep_verified}, status={rep_status})")
    print(f"    Issue: {issue}")
    print("-" * 50)
