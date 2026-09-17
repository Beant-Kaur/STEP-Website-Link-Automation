import json

new_replacements = {
    "https://www.greenfinanceplatform.org/policies-and-regulations/chinas-administrative-measures-legal-disclosure-enterprise-environmental": "https://www.mee.gov.cn/xxgk2018/xxgk/xxgk02/202112/t20211221_964720.html",
    "http://www.mee.gov.cn/gkml/hbb/bwj/202104/t20210427_837497.html": "https://www.mee.gov.cn/xxgk2018/xxgk/xxgk02/202112/t20211221_964720.html",
    "https://ieefa.org/resources/chinas-emissions-trading-system-ets-reforms-track-needs-robust-enforcement#:~:text=Evolving%20from%20pilot%20programs%20across,20%25%20of%20total%20global%20emissions.": "https://www.mee.gov.cn/ywgz/ydqhbh/qhgjyhxyyqyzcjgz/",
    "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023DC0012https://eur-lex.europa.eu/eli/reg_del/2023/2772/oj/eng": "https://eur-lex.europa.eu/eli/reg_del/2023/2772/oj",
    "https://www.mas.gov.sg/-/media/MAS/News-and-Publications/Consultation-Papers/CP13-Guidelines-on-Environmental-Risk-Management/Guidelines_on_Environmental_Risk_Management.pdf": "https://www.mas.gov.sg/regulation/guidelines/guidelines-on-environmental-risk-management-for-banks",
    "https://adxservices.adx.ae/WebServices/DataServices/contentDownload.aspx?doc=1704806": "https://www.adx.ae/english/pages/productsandservices/adxesg.aspx",
    "https://www.ecgi.global/sites/default/files/codes/documents/chairman_of_authoritys_board_of_directors_decision_no._3_chairman_of_2020_concerning_approval_of_joint_stock_companies_governance_guide_3.pdf": "https://www.sca.gov.ae/en/regulations/regulations-listing.aspx",
    "https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202120220SB253": "https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240SB253",
    "https://www.policyvault.africa/policy/environmental-impact-assessment-act-2/": "https://gazettes.africa/archive/ng/1992/ng-government-gazette-dated-1992-12-31-no-73.pdf",
    "https://unfccc.int/sites/default/files/NDC/2022-06/NDC%20INTERIM%20REPORT%20SUBMISSION%20-%20NIGERIA.pdf": "https://unfccc.int/sites/default/files/NDC/2022-06/Nigeria_Updated_NDC_2021.pdf",
    "https://www.sca.gov.ae/services/AjaxHandler.asmx/LoadRegulationByIdAsPdf?id=198&lang=en&title=Chairman+of+Authority%E2%80%99s+Board+of+Directors%E2%80%99+Decision+no.+%283%2FChairman%29+of+2020+concerning+Approval+of+Joint+Stock+Companies+Governance+Guide": "https://www.sca.gov.ae/en/regulations/regulations-listing.aspx",
    "https://rulebook.centralbank.ae/en/rulebook/principles-sustainability-related-disclosures": "https://www.centralbank.ae/en/our-operations/sustainable-finance/",
    "https://www.sec.gov/files/rules/final/2024/33-11275.pdf": "https://www.sec.gov/newsroom/press-releases/2024-31",
    "https://step.mykajabi.com/resource_redirect/landing_pages/2151313663": "https://www.ifrs.org/issued-standards/ifrs-sustainability-standards-navigator/"
}

with open("step_esg_pipeline/pipeline/canonical_replacements.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for k, v in new_replacements.items():
    data[k] = v

with open("step_esg_pipeline/pipeline/canonical_replacements.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4)
print("Updated canonical_replacements.json")
