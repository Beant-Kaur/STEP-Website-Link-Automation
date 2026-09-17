import sys
import io
import bs4
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
r = requests.get('https://step.mykajabi.com/free-digital-content', timeout=20)
soup = bs4.BeautifulSoup(r.text, 'html.parser')

landscape_sec = None
for el in soup.find_all(string=lambda t: t and 'ESG Legislative Landscape' in t):
    sec = el.find_parent('section')
    if sec:
        landscape_sec = sec
        break

if not landscape_sec:
    print("ESG Legislative Landscape section not found!")
    sys.exit(1)

accordions = landscape_sec.find_all('div', class_=lambda c: c and 'accordion' in c)
print(f"Total accordions found: {len(accordions)}")

seen_urls = set()
country_data = []

for card in accordions:
    title_div = card.find('div', class_=lambda c: c and 'accordion-title' in c)
    collapse_div = card.find('div', class_=lambda c: c and 'accordion-collapse' in c)
    if title_div and collapse_div:
        country = title_div.get_text(strip=True)
        # Check if this accordion title is a country
        # Clean country name (e.g. remove trailing arrows or numbers)
        links = collapse_div.find_all('a', href=True)
        for a in links:
            href = a.get('href', '').strip()
            if not href or href.startswith(('javascript:', 'mailto:', '#')):
                continue
            if href in seen_urls:
                continue
            seen_urls.add(href)
            
            # Find specific regulation title
            # In Kajabi, usually the previous sibling paragraph or the bold text in current paragraph
            parent_p = a.find_parent(['p', 'li', 'div'])
            p_text = parent_p.get_text(strip=True) if parent_p else ""
            
            # Try to find bold tag
            bold = None
            if parent_p:
                bold = parent_p.find(['b', 'strong'])
            if not bold and parent_p:
                prev = parent_p.find_previous_sibling(['p', 'div', 'h4', 'h5', 'h6'])
                if prev:
                    bold = prev.find(['b', 'strong']) or prev
            
            reg_title = bold.get_text(strip=True) if bold else p_text[:60]
            if reg_title.lower().startswith('link') or len(reg_title) < 4:
                reg_title = p_text[:80]
                
            country_data.append({
                'country': country,
                'regulation_title': reg_title,
                'anchor_text': a.get_text(strip=True),
                'url': href
            })

print(f"Total unique links extracted: {len(country_data)}")
from collections import defaultdict
grouped = defaultdict(list)
for item in country_data:
    grouped[item['country']].append(item)

for c, items in grouped.items():
    print(f"\n========================================================")
    print(f"COUNTRY / JURISDICTION: {c} ({len(items)} links)")
    print(f"========================================================")
    for i, it in enumerate(items, 1):
        print(f"{i}. [{it['regulation_title']}]")
        print(f"   URL: {it['url']}")
        print(f"   Anchor: '{it['anchor_text']}'")
