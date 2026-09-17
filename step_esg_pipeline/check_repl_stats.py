import json

rows = json.load(open('step_esg_pipeline/audited_table_rows.json', encoding='utf-8'))
found_repl = [r for r in rows if r['replacement'] != 'No verified replacement found — manual research required.']
print(f"Total with replacement: {len(found_repl)}")
for r in found_repl:
    print(f"#{r['num']:02d} [{r['jurisdiction']}] {r['verdict']} -> Replacement: {r['replacement']}")

print("\nVerdicts summary:")
from collections import Counter
verdicts = Counter([r['verdict'] for r in rows])
for v, count in verdicts.items():
    print(f"  {v}: {count}")

no_repl = len([r for r in rows if r['verdict'] != 'OK' and r['replacement'] == 'No verified replacement found — manual research required.'])
print(f"\nLinks not OK without replacement: {no_repl}")
needs_review = len([r for r in rows if r['verdict'] == 'NEEDS HUMAN REVIEW'])
print(f"Flagged as NEEDS HUMAN REVIEW: {needs_review}")
