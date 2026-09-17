import json

with open('step_esg_pipeline/report.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

for i in [8, 38, 46]:
    x = items[i-1]
    print(f"Item #{i}: {x.get('anchor_text')}")
    print(f"  Repl URL: {x.get('replacement_url')}")
    print(f"  Repl verified: {x.get('replacement_verified')}")
    print(f"  Repl status: {x.get('replacement_status')}")
    print(f"  Repl reason: {x.get('replacement_reason')}")
