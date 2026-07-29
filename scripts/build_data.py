#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 简体中文版《巴黎评论》系列编辑部
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
DEFAULT_HTML = PROJECT / 'dist_public' / 'index.html'
DATA_DIR = Path(__file__).resolve().parents[1] / 'data'


def extract_js_const(html: str, name: str) -> dict:
    """Extract a JavaScript const object from HTML.
    
    Handles nested braces correctly, unlike the old regex-only approach
    which failed on objects containing nested } in strings.
    """
    pattern = r'const\s+' + re.escape(name) + r'\s*=\s*'
    m = re.search(pattern, html)
    if not m:
        raise SystemExit(f'missing JS const {name}')
    pos = m.end()
    while pos < len(html) and html[pos] in ' \n\t':
        pos += 1
    if pos >= len(html) or html[pos] not in '{[':
        raise SystemExit(f'{name} value is not an object or array')
    # Handle nested braces/brackets with string awareness
    open_ch = html[pos]
    close_ch = '}' if open_ch == '{' else ']'
    depth = 0
    in_str = False
    esc = False
    i = pos
    while i < len(html):
        ch = html[i]
        if esc:
            esc = False; i += 1; continue
        if ch == '\\':
            esc = True; i += 1; continue
        if ch == '"':
            in_str = not in_str; i += 1; continue
        if in_str:
            i += 1; continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return json.loads(html[pos:i+1])
        i += 1
    raise SystemExit(f'unmatched brace for {name}')


def extract_catalog(html: str) -> tuple[list, dict]:
    """Extract PARIS_REVIEW_CATALOG from HTML.
    
    Newer HTML (v14+) stores it as a structured object:
      { meta: {...}, records: [...], name_map: {zh_to_en, en_to_zh} }
    
    Returns (records, name_map) where name_map has en_to_zh and zh_to_en.
    """
    cat = extract_js_const(html, 'PARIS_REVIEW_CATALOG')
    records = cat.get('records', [])
    name_map = cat.get('name_map', {})
    
    # Validate records
    valid = [r for r in records if r.get('name_en') or r.get('name_zh')]
    if len(valid) != len(records):
        print(f'⚠️  {len(records) - len(valid)} records missing names, filtered')
    
    return valid, name_map


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


def build_name_maps_fallback(catalog_records: list) -> dict:
    """Build en->zh and zh->en name maps from catalog records.
    
    Fallback used when the HTML does not contain a pre-built name_map
    inside PARIS_REVIEW_CATALOG.
    """
    en_to_zh = {}
    zh_to_en = {}
    
    for rec in catalog_records:
        name_en = rec.get('name_en', '')
        name_zh = rec.get('name_zh', '')
        
        if name_en and name_zh:
            norm_en = normalize_name_key(name_en)
            norm_zh = normalize_name_key(name_zh)
            
            if norm_en and norm_en not in en_to_zh:
                en_to_zh[norm_en] = name_zh
            
            # Also add reversed-order key (for Japanese names like Murakami Haruki)
            en_parts = name_en.split()
            if len(en_parts) == 2:
                reversed_en = en_parts[1] + ' ' + en_parts[0]
                norm_reversed = normalize_name_key(reversed_en)
                if norm_reversed and norm_reversed not in en_to_zh:
                    en_to_zh[norm_reversed] = name_zh
            
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
    
    # Extract catalog (structured object in newer HTML)
    catalog_records, _cat_name_map = extract_catalog(html)
    # Always build name_map from records using our normalize_name_key,
    # because the HTML's built-in name_map uses name_key slugs (e.g. 'achebe')
    # which don't match the query script's normalize_name_key output.
    name_map = build_name_maps_fallback(catalog_records)
    
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
        'version': 'v15.1-skill-v1',
        'source_html': 'projects/paris_network/dist_public/index.html',
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
