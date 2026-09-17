import json

with open('step_esg_pipeline/report.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

print(f"Total items loaded: {len(items)}")

# Let's map each pipeline record into the exact table structure:
# Original URL | Status Code | Final URL (after redirect) | Verdict | Evidence Snippet | Recommended Replacement (if any) | Confidence

for i, x in enumerate(items, 1):
    orig = x.get('original_url', '')
    final = x.get('final_url', '') or orig
    http = x.get('http_status')
    fs = x.get('final_status')
    fresh = x.get('freshness_status')
    tech = x.get('technical_status')
    auth = x.get('authority_status')
    repl = x.get('replacement_url', '')
    conf_score = x.get('final_confidence') or x.get('initial_confidence') or 0.5
    title = x.get('page_title', '')
    issue = x.get('issue_description', '')
    ev_list = x.get('evidence', [])
    # clean ev_list
    clean_ev = [e for e in ev_list if 'RESOURCE_EXHAUSTED' not in str(e)]
    
    print(f"Item #{i:02d}:")
    print(f"  Title: {x.get('anchor_text')} ({x.get('jurisdiction')})")
    print(f"  Orig: {orig}")
    print(f"  Status: {http} -> {final}")
    print(f"  Pipeline Status: {fs} | Freshness: {fresh} | Tech: {tech} | Auth: {auth}")
    print(f"  Repl: {repl}")
    print(f"  Clean Ev: {clean_ev}")
    print()
