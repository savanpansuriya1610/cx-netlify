import os
import glob
import re
import json
import html
import csv

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_faqs(text):
    faqs = []
    # 1. JSON-LD
    json_ld_blocks = re.findall(r'<script\s+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', text, re.I | re.S)
    for block in json_ld_blocks:
        try:
            data = json.loads(block)
            items = []
            if isinstance(data, dict):
                if data.get('@type') == 'FAQPage' and 'mainEntity' in data:
                    items = data['mainEntity']
                elif '@graph' in data and isinstance(data['@graph'], list):
                    for g in data['@graph']:
                        if isinstance(g, dict) and g.get('@type') == 'FAQPage' and 'mainEntity' in g:
                            items = g['mainEntity']
                            break
            elif isinstance(data, list):
                for d in data:
                    if isinstance(d, dict) and d.get('@type') == 'FAQPage' and 'mainEntity' in d:
                        items = d['mainEntity']
                        break
            
            for it in items:
                if isinstance(it, dict) and it.get('@type') == 'Question':
                    q = clean_text(it.get('name', ''))
                    ans = it.get('acceptedAnswer', {})
                    a = clean_text(ans.get('text', '')) if isinstance(ans, dict) else clean_text(str(ans))
                    if q:
                        faqs.append((q, a))
        except Exception:
            pass

    # HTML fallbacks for FAQs
    if not faqs:
        landing_items = re.findall(r'<div class="landing-faq-item".*?<h3>(.*?)</h3>.*?<div class="answer.*?<p>(.*?)</p>', text, re.I | re.S)
        for q_html, a_html in landing_items:
            faqs.append((clean_text(q_html), clean_text(a_html)))
            
    if not faqs:
        area_items = re.findall(r'<div class="faq-area-block-top".*?<h3[^>]*>(.*?)</h3>.*?<p class="[^"]*at-tab">(.*?)</p>', text, re.I | re.S)
        for q_html, a_html in area_items:
            faqs.append((clean_text(q_html), clean_text(a_html)))

    faq_string = ""
    if faqs:
        faq_lines = []
        for i, (q, a) in enumerate(faqs, 1):
            faq_lines.append(f"Q{i}: {q}\nA{i}: {a}")
        faq_string = "\n\n".join(faq_lines)

    return faq_string, len(faqs)

def extract_breadcrumbs(text, rel_path):
    breadcrumbs = []
    json_ld_blocks = re.findall(r'<script\s+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', text, re.I | re.S)
    for block in json_ld_blocks:
        try:
            data = json.loads(block)
            items = []
            if isinstance(data, dict):
                if data.get('@type') == 'BreadcrumbList' and 'itemListElement' in data:
                    items = data['itemListElement']
                elif '@graph' in data and isinstance(data['@graph'], list):
                    for g in data['@graph']:
                        if isinstance(g, dict) and g.get('@type') == 'BreadcrumbList' and 'itemListElement' in g:
                            items = g['itemListElement']
                            break
            elif isinstance(data, list):
                for d in data:
                    if isinstance(d, dict) and d.get('@type') == 'BreadcrumbList' and 'itemListElement' in d:
                        items = d['itemListElement']
                        break
                        
            sorted_items = sorted(items, key=lambda x: x.get('position', 0)) if items else []
            for it in sorted_items:
                name = clean_text(it.get('name', ''))
                if name:
                    breadcrumbs.append(name)
            if breadcrumbs:
                break
        except Exception:
            pass

    if not breadcrumbs:
        bc_match = re.search(r'<ol\s+class=["\'][^"\']*breadcrumb[^"\']*["\'][^>]*>(.*?)</ol>', text, re.I | re.S)
        if bc_match:
            li_items = re.findall(r'<li[^>]*>(.*?)</li>', bc_match.group(1), re.I | re.S)
            for li in li_items:
                name = clean_text(li)
                if name:
                    breadcrumbs.append(name)

    if not breadcrumbs:
        if rel_path == 'index.html':
            breadcrumbs = ['Home']
        else:
            parts = rel_path.split('/')
            crumbs = ['Home']
            for p in parts:
                p_name = p.replace('.html', '').replace('-', ' ').title()
                if p_name and p_name != 'Index':
                    crumbs.append(p_name)
            breadcrumbs = crumbs

    return " > ".join(breadcrumbs)

def extract_page_data(file_path):
    rel_path = file_path.replace('\\', '/')
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as fp:
        text = fp.read()

    # 7. Canonical URL
    can_match = re.search(r'<link\s+[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']', text, re.I)
    if not can_match:
        can_match = re.search(r'<link\s+[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\']canonical["\']', text, re.I)
    canonical_url = can_match.group(1).strip() if can_match else ""

    # 1. URL
    if canonical_url:
        page_url = canonical_url
    else:
        p = rel_path
        if p.endswith('.html'):
            p = p[:-5]
        if p == 'index':
            page_url = 'https://www.cypherox.com/'
        else:
            page_url = f"https://www.cypherox.com/{p}"

    # 2. Meta Title
    title_match = re.search(r'<title>(.*?)</title>', text, re.I | re.S)
    meta_title = clean_text(title_match.group(1)) if title_match else ""
    if not meta_title:
        og_title = re.search(r'<meta\s+[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']*)["\']', text, re.I)
        meta_title = clean_text(og_title.group(1)) if og_title else ""

    # 3. Meta Description
    desc_match = re.search(r'<meta\s+[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', text, re.I)
    if not desc_match:
        desc_match = re.search(r'<meta\s+[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']description["\']', text, re.I)
    if not desc_match:
        desc_match = re.search(r'<meta\s+[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']*)["\']', text, re.I)
    meta_description = clean_text(desc_match.group(1)) if desc_match else ""

    # 4. Featured Image (First Image URL)
    og_img_match = re.search(r'<meta\s+[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', text, re.I)
    if not og_img_match:
        og_img_match = re.search(r'<meta\s+[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']', text, re.I)
    if not og_img_match:
        og_img_match = re.search(r'<meta\s+[^>]*name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)["\']', text, re.I)

    featured_image = ""
    if og_img_match:
        featured_image = og_img_match.group(1).strip()
    else:
        body_match = re.search(r'<body[^>]*>(.*?)</body>', text, re.I | re.S)
        body = body_match.group(1) if body_match else text
        imgs = re.findall(r'<img\s+[^>]*src=["\']([^"\']+)["\']', body, re.I)
        for img in imgs:
            if not img.endswith('.svg') and 'pixel' not in img.lower() and '1x1' not in img:
                featured_image = img
                break
        if not featured_image and imgs:
            featured_image = imgs[0]
            
    if featured_image:
        if featured_image.startswith('//'):
            featured_image = 'https:' + featured_image
        elif featured_image.startswith('/'):
            featured_image = 'https://www.cypherox.com' + featured_image
        elif featured_image.startswith('../'):
            cleaned_path = re.sub(r'^(?:\.\./)+', '', featured_image)
            featured_image = f"https://www.cypherox.com/{cleaned_path}"
        elif not featured_image.startswith('http'):
            featured_image = f"https://www.cypherox.com/{featured_image}"

    # 5. FAQs
    faqs_str, faq_count = extract_faqs(text)

    # 6. Breadcrumbs
    breadcrumbs_str = extract_breadcrumbs(text, rel_path)

    # 8. H1 (Main Heading)
    h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.I | re.S)
    if h1_match:
        h1 = clean_text(h1_match.group(1))
    else:
        h2_match = re.search(r'<h2[^>]*>(.*?)</h2>', text, re.I | re.S)
        h1 = clean_text(h2_match.group(1)) if h2_match else ""

    return [
        page_url,
        meta_title,
        meta_description,
        featured_image,
        faqs_str,
        breadcrumbs_str,
        canonical_url,
        h1
    ]

def main():
    files = glob.glob('**/*.html', recursive=True)
    files = [f.replace('\\', '/') for f in files]
    files = [f for f in files if 'node_modules' not in f and '.git' not in f and not f.endswith('assets/img/index.html')]
    # sort files alphabetically
    files = sorted(files)

    headers = [
        "URL",
        "Meta Title",
        "Meta Description",
        "Featured Image (First Image URL)",
        "FAQs",
        "Breadcrumbs",
        "Canonical URL",
        "H1 (Main Heading)"
    ]

    rows = []
    for f in files:
        row = extract_page_data(f)
        rows.append(row)

    output_csv_path = "website_pages_data.csv"
    with open(output_csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"Generated {output_csv_path} with {len(rows)} pages and {len(headers)} columns.")

if __name__ == "__main__":
    main()
