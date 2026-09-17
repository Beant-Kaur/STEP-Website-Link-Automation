import json

with open('step_esg_pipeline/report.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

for idx, x in enumerate(items, 1):
    orig = x.get('original_url', '')
    final = x.get('final_url', '') or orig
    http = x.get('http_status')
    fs = x.get('final_status')
    fresh = x.get('freshness_status')
    tech = x.get('technical_status')
    auth = x.get('authority_status')
    repl = x.get('replacement_url', '')
    conf = x.get('final_confidence') or x.get('initial_confidence')
    jur = x.get('jurisdiction')
    anchor = x.get('anchor_text')
    print(f"#{idx:02d} [{jur}] {anchor} | HTTP: {http} | FinalStatus: {fs} | Repl: {repl[:40] if repl else 'None'}")
