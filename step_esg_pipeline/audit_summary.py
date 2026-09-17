import json

with open('step_esg_pipeline/report.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

for i in range(0, len(items), 10):
    chunk = items[i:i+10]
    print(f"=== CHUNK {i+1} to {i+len(chunk)} ===")
    for idx, x in enumerate(chunk, start=i+1):
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
        ev = x.get('evidence', [])
        # filter out the raw gemini 429 string to see the real domain/textual evidence
        real_ev = [e for e in ev if 'RESOURCE_EXHAUSTED' not in str(e)]
        print(f"[{idx}] {jur} | {anchor}")
        print(f"  Orig: {orig}")
        print(f"  HTTP: {http} -> Final: {final}")
        print(f"  Status: {fs} | Fresh: {fresh} | Tech: {tech} | Auth: {auth} | Conf: {conf}")
        print(f"  Repl: {repl}")
        print(f"  Ev: {real_ev}")
