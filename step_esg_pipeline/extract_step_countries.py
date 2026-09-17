import sys
import io
import requests
import bs4

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
r = requests.get('https://step.mykajabi.com/free-digital-content', timeout=20)
soup = bs4.BeautifulSoup(r.text, 'html.parser')
landscape_sec = None
for el in soup.find_all(string=lambda t: t and 'ESG Legislative Landscape' in t):
    sec = el.find_parent('section')
    if sec:
        landscape_sec = sec
        break

current_country = 'General'
current_title = ''
records = []
seen_urls = set()
for child in landscape_sec.descendants:
    if child.name == 'h5':
        current_country = child.get_text(strip=True)
    elif child.name in ('b', 'strong') and child.parent.name != 'a':
        t = child.get_text(strip=True)
        if t and not t.lower().startswith('link') and len(t) > 3 and t.lower() != 'disclaimer:':
            current_title = t
    elif child.name == 'a' and child.get('href'):
        href = child.get('href').strip()
        if href and not href.startswith(('javascript:', 'mailto:', '#')):
            if href in seen_urls:
                continue
            seen_urls.add(href)
            records.append({
                'country': current_country,
                'title': current_title,
                'anchor': child.get_text(strip=True),
                'url': href
            })

print(f'Total unique links in Landscape section: {len(records)}')
by_country = {}
for rec in records:
    by_country.setdefault(rec['country'], []).append(rec)

for c, items in by_country.items():
    print(f'\n=== {c} ({len(items)} links) ===')
    for it in items:
        print(f"  [{it['title']}] -> {it['url']}")
