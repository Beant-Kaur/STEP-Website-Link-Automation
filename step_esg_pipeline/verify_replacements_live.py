import requests

replacements = [
    ("China", "https://www.mee.gov.cn/xxgk2018/xxgk/xxgk02/202112/t20211221_964720.html"),
    ("China", "https://www.mee.gov.cn/ywgz/ydqhbh/qhgjyhxyyqyzcjgz/"),
    ("Singapore", "https://www.mas.gov.sg/regulation/guidelines/guidelines-on-environmental-risk-management"),
    ("UAE", "https://www.adx.ae/English/Pages/Products-and-Services/Sustainability.aspx"),
    ("UAE", "https://www.sca.gov.ae/en/regulations/regulations-listing.aspx"),
    ("US", "https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240SB253"),
    ("Nigeria", "https://nesrea.gov.ng/policies-guidelines/")
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

for jur, url in replacements:
    try:
        r = requests.get(url, headers=headers, timeout=10, verify=False)
        print(f"[{jur}] HTTP {r.status_code} -> {url[:60]}")
    except Exception as e:
        print(f"[{jur}] ERROR {e} -> {url[:60]}")
