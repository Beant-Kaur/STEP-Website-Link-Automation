import json

with open("report.json", encoding="utf-8") as f:
    data = json.load(f)

# Print keys of first record
print("=== FIELDS IN REPORT ===")
print(list(data[0].keys()))
print()

# Count by classification
from collections import Counter
classifications = Counter(r.get("ai_classification") or r.get("classification", "UNKNOWN") for r in data)
decisions = Counter(r.get("decision", "UNKNOWN") for r in data)

print("=== CLASSIFICATIONS ===")
for k, v in sorted(classifications.items(), key=lambda x: -x[1]):
    print(f"  {v:3d}  {k}")

print()
print("=== DECISIONS ===")
for r in data:
    url = r.get("original_url", "")
    decision = r.get("recommended_action", "?")
    classification = r.get("classification", "?")
    status = r.get("http_status", "?")
    replacement = r.get("replacement_url", "")
    replacement_str = f" => {replacement}" if replacement else ""
    print(f"[{decision:24s}] [{status}] {url}")
    if classification:
        print(f"  Classification: {classification}")
    if replacement_str:
        print(f"  Replacement: {replacement_str}")
    print()

print("=== SAMPLE RECORD KEYS ===")
print(data[0])
