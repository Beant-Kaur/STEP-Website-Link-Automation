import json

with open('step_esg_pipeline/report.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

# Let's inspect the 48 links and design the precise mapping
results = []
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
    ev_list = [e for e in x.get('evidence', []) if 'RESOURCE_EXHAUSTED' not in str(e)]
    
    # Determine Verdict:
    # Allowed: OK / BROKEN / REDIRECTED / OUTDATED / NON-AUTHORITATIVE / NEEDS HUMAN REVIEW
    verdict = None
    confidence = "Medium"
    if conf_val >= 0.8:
        confidence = "High"
    elif conf_val < 0.5:
        confidence = "Low"
        
    # Check conditions
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

    results.append({
        "num": i,
        "jurisdiction": jurisdiction,
        "anchor": anchor,
        "orig": orig,
        "status_code": http,
        "final_url": final,
        "verdict": verdict,
        "clean_ev": ev_list,
        "repl": repl,
        "rep_verified": rep_verified,
        "confidence": confidence,
        "raw_fs": fs
    })

print(f"Total processed: {len(results)}")
for r in results:
    print(f"#{r['num']:02d} [{r['jurisdiction']}] {r['verdict']} | Conf: {r['confidence']} | HTTP: {r['status_code']} | Repl: {r['repl'][:35] if r['repl'] else 'None'}")
