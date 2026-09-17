import sys
from reference import ExcelReferenceDatabase, RegulatoryDatabaseError


def test_india_excel_integration():
    print("=== Loading Regulatory Reference Database (Excel) ===")
    db = ExcelReferenceDatabase()
    try:
        db.load()
    except RegulatoryDatabaseError as e:
        print(f"FAILED to load database: {e}")
        return False

    print(f"Database File: {db.file_path}")
    print(f"Loaded {len(db.resources)} resources, {len(db.authorities)} authorities\n")

    print("--- 1. Authorities in India ---")
    for aid, auth in db.authorities.items():
        print(f"[{aid}] {auth.authority_name} ({auth.country})")
        print(f"       Official Domain: {auth.official_domain} | Trust: {auth.trust_level}")

    print("\n--- 2. India Pilot Resources ---")
    for rid, res in db.resources.items():
        print(f"[{rid}] {res.name}")
        print(f"       Issuing Authority: {res.issuing_authority}")
        print(f"       Official Domain  : {res.official_domain}")
        print(f"       Official URL     : {res.official_url}")
        print(f"       Topic / Type     : {res.regulatory_topic} | {res.document_type}")
        print(f"       Enactment Date   : {res.publication_date}")
        print(f"       Validator Rule   : {res.validator_rule}")
        print(f"       Versions Tracked : {len(res.versions)}")
        for v in res.versions:
            print(f"          * [{v.relationship}] {v.resource_update} ({v.date})")

    print("\n--- 3. Testing Real STEP India Link Matching ---")
    step_india_links = [
        ("India", "https://www.sebi.gov.in/legal/circulars/may-2021/business-responsibility-and-sustainability-reporting-by-listed-entities_50096.html", "SEBI BRSR Circular"),
        ("India", "https://www.mca.gov.in/Ministry/pdf/CompaniesAct2013.pdf", "Companies Act 2013 (see Section 135 & CSR Rules)"),
        ("India", "https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12213&Mode=0", "RBI Guidelines on Environmental and Social Risk Management"),
    ]

    all_matched = True
    for c, u, desc in step_india_links:
        matched = db.match_resource(jurisdiction=c, url=u, text=desc)
        if matched:
            print(f"SUCCESS: Link '{desc}'")
            print(f"         Matched to: [{matched.resource_id}] {matched.name}")
            print(f"         Authority : {matched.issuing_authority} ({matched.official_domain})")
        else:
            print(f"FAILED: Could not match {u}")
            all_matched = False

    return all_matched


if __name__ == "__main__":
    success = test_india_excel_integration()
    sys.exit(0 if success else 1)
