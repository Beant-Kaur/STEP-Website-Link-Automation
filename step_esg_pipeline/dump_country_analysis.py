import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
data = json.load(open('report.json', encoding='utf-8'))
from collections import defaultdict
by_country = defaultdict(list)
for r in data:
    by_country[r.get('jurisdiction') or 'Unspecified'].append(r)

for c, items in by_country.items():
    print(f"\n================================================================================")
    print(f"JURISDICTION: {c.upper()} ({len(items)} Links)")
    print(f"================================================================================")
    for i, it in enumerate(items, 1):
        desc = it.get('step_description', '') or it.get('anchor_text', '') or it.get('page_title', '')
        print(f"{i}. Title: {desc}")
        print(f"   URL: {it.get('original_url')}")
        print(f"   Technical: HTTP {it.get('http_status')} ({it.get('technical_status')}) | Access: {it.get('access_status')}")
        print(f"   Classification: {it.get('classification')} | Action: {it.get('recommended_action')}")
        if it.get('replacement_url'):
            print(f"   --> Recommended Replacement: {it.get('replacement_url')}")
            print(f"   --> Reason: {it.get('replacement_reason')}")
        else:
            print(f"   --> Recommended Replacement: None needed (or pending review)")
