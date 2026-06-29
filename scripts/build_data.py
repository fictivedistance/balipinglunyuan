#!/usr/bin/env python3
"""Build read-only Paris Network skill data from public HTML.

All data extracted directly from the single public HTML file.
No external dependencies: no JSON catalog, no SQLite database.

100% aligned with frontend search logic (pseudo B2).
"""
from __future__ import annotations
import argparse, json, re, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / 'projects' / 'paris_network'
DEFAULT_HTML = PROJECT / 'v13_public.html'
DATA_DIR = Path(__file__).resolve().parents[1] / 'data'


def extract_js_const(html: str, name: str) -> dict:
    """Extract a JavaScript const object from HTML."""
    pattern = r'const\s+' + re.escape(name) + r'\s*=\s*(\{.*?\});'
    m = re.search(pattern, html, re.S)
    if not m:
        raise SystemExit(f'missing JS const {name}')
    return json.loads(m.group(1))


def extract_catalog_array(html: str) -> list:
    """Extract PARIS_REVIEW_CATALOG records from HTML inline array.
    
    Each record looks like:
    {"year":"1953","series":"...","id":"prcat-0001","url":"...","name_en":"...","name_zh":"..."}
    
    Uses single-pass scan for performance (O(n) total).
    """
    records = []
    n = len(html)
    
    # Stack of { start positions for currently-open objects
    # When we see }, the top of stack tells us where this object started.
    open_stack = []
    
    in_string = False
    escape_next = False
    i = 0
    
    while i < n:
        ch = html[i]
        
        if escape_next:
            escape_next = False
            i += 1
            continue
        
        if ch == '\\':
            escape_next = True
            i += 1
            continue
        
        if ch == '"':
            in_string = not in_string
            i += 1
            continue
        
        if in_string:
            i += 1
            continue
        
        if ch == '{':
            open_stack.append(i)
            i += 1
            continue
        
        if ch == '}':
            if open_stack:
                start = open_stack.pop()
                # Try to parse this object
                try:
                    rec = json.loads(html[start:i+1])
                    if isinstance(rec, dict) and (rec.get('name_en') or rec.get('name_zh')):
                        records.append(rec)
                except:
                    pass
            i += 1
            continue
        
        i += 1
    
    return records


def normalize_name_key(s: str) -> str:
    """Normalize name key for fuzzy matching.
    
    Same logic as v237NormalizeNameKey in frontend + diacritics strip.
    - Strip diacritics (NFKD + drop combining marks)
    - Remove dots, spaces, interpuncts
    - Lowercase
    """
    if not s:
        return ''
    s = str(s).strip()
    # Strip diacritics
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    # Remove: . · . . spaces
    s = re.sub(r'[\s·.．]+', '', s)
    return s.lower()

def build_name_maps(catalog_records: list) -> dict:
    """Build en->zh and zh->en name maps from catalog.
    
    Same as PARIS_REVIEW_CATALOG.name_map in frontend.
    Also adds reversed-order keys for Japanese names (e.g., Murakami Haruki -> Haruki Murakami).
    """
    en_to_zh = {}
    zh_to_en = {}
    
    for rec in catalog_records:
        name_en = rec.get('name_en', '')
        name_zh = rec.get('name_zh', '')
        
        if name_en and name_zh:
            norm_en = normalize_name_key(name_en)
            norm_zh = normalize_name_key(name_zh)
            
            # English -> Chinese (may have multiple, pick first non-empty)
            if norm_en and norm_en not in en_to_zh:
                en_to_zh[norm_en] = name_zh
            
            # Also add reversed-order key (for Japanese names like Murakami Haruki)
            en_parts = name_en.split()
            if len(en_parts) == 2:
                reversed_en = en_parts[1] + ' ' + en_parts[0]
                norm_reversed = normalize_name_key(reversed_en)
                if norm_reversed and norm_reversed not in en_to_zh:
                    en_to_zh[norm_reversed] = name_zh
            
            # Chinese -> list of English names
            if norm_zh:
                zh_to_en.setdefault(norm_zh, []).append(name_en)
    
    return {
        'en_to_zh': en_to_zh,
        'zh_to_en': zh_to_en,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--html', default=str(DEFAULT_HTML))
    ap.add_argument('--out', default=str(DATA_DIR))
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    html_path = Path(args.html)
    html = html_path.read_text()
    
    # === Extract core data (same as frontend) ===
    graph = extract_js_const(html, 'GRAPH')
    leaderboard = extract_js_const(html, 'LEADERBOARD_BUBBLES')
    story = extract_js_const(html, 'STORY_PATHS_V1')
    author_info = extract_js_const(html, 'authorInfo')
    
    # Extract catalog
    catalog_records = extract_catalog_array(html)
    name_map = build_name_maps(catalog_records)
    
    # Build interviews lookup (Chinese published interviews)
    # from authorInfo
    interviews_by_name_norm = {}
    interviews_by_name = {}
    for author, details_list in author_info.items():
        norm = normalize_name_key(author)
        interviews_by_name_norm[norm] = {
            'author': author,
            'interviews': details_list,
        }
        interviews_by_name[author] = details_list
    
    # Build bundle
    bundle = {
        'version': 'v13-skill-v1-pseudo-b2',
        'source_html': str(html_path),
        'counts': {
            'nodes': len(graph.get('nodes', [])),
            'links': len(graph.get('links', [])),
            'catalog_records': len(catalog_records),
            'authors_with_chinese_interview': len(author_info),
        },
        # Core data (same as frontend)
        'graph': graph,
        'leaderboard': leaderboard,
        'story_paths': story,
        'author_info': author_info,
        # Catalog for search
        'catalog': {
            'records': catalog_records,
            'name_map': name_map,
        },
        # Lookup indexes
        'indexes': {
            'interviews_by_name_norm': interviews_by_name_norm,
            'interviews_by_name': interviews_by_name,
        },
    }
    
    # Save
    (out / 'paris_network_v1_data.json').write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2)
    )
    
    print(f'✅ Data built successfully!')
    print(f'   - Graph nodes: {len(graph.get("nodes", []))}')
    print(f'   - Graph links: {len(graph.get("links", []))}')
    print(f'   - Catalog records: {len(catalog_records)}')
    print(f'   - English names mapped: {len(name_map["en_to_zh"])}')
    print(f'   - Chinese names mapped: {len(name_map["zh_to_en"])}')
    print(f'   - Authors with Chinese interview: {len(author_info)}')


if __name__ == '__main__':
    main()
