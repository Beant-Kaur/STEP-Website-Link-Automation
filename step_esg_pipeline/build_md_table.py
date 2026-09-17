import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('step_esg_pipeline/audited_table_rows.json', 'r', encoding='utf-8') as f:
    rows = json.load(f)

md_lines = []
md_lines.append("| Original URL | Status Code | Final URL (after redirect) | Verdict | Evidence Snippet | Recommended Replacement (if any) | Confidence |")
md_lines.append("|---|---|---|---|---|---|---|")

for r in rows:
    orig = r['orig'].replace('|', '%7C')
    code = str(r['status_code'])
    final = r['final_url'].replace('|', '%7C')
    verdict = r['verdict']
    evidence = r['evidence'].replace('|', '-').replace('\n', ' ')
    repl = r['replacement'].replace('|', '%7C')
    conf = r['confidence']
    md_lines.append(f"| {orig} | {code} | {final} | {verdict} | {evidence} | {repl} | {conf} |")

output_md = "\n".join(md_lines)
with open('step_esg_pipeline/final_audit_table.md', 'w', encoding='utf-8') as f:
    f.write(output_md)

print("Saved to step_esg_pipeline/final_audit_table.md")
print(f"Total rows: {len(rows)}")
