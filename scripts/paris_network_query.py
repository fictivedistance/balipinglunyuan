#!/usr/bin/env python3
"""Read-only queries for Paris Network - 100% aligned with frontend search logic.

This module replicates the JavaScript search behavior from the public HTML page:
- searchWriter() function: handles graph node search with cross-language support
- v237FindCatalogRecord() function: handles catalog fallback search

Usage:
  python3 paris_network_query.py search <writer_name>
  python3 paris_network_query.py interview-status <writer_name>
  python3 paris_network_query.py stats

All results match what users would see when searching on the website.
"""
from __future__ import annotations
import argparse, json, re, sys, unicodedata
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / 'data' / 'paris_network_v1_data.json'


def normalize_name_key(s):
    """Same as v237NormalizeNameKey in frontend.
    
    Remove dots, spaces, interpuncts, then lowercase.
    Also strips diacritics for cross-script matching.
    """
    if not s:
        return ''
    s = str(s).strip()
    # Strip diacritics (NFKD decomposes accented chars, then drop combining marks)
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    # Remove: . · ．  spaces (same as v237)
    s = re.sub(r'[\s·.．]+', '', s)
    return s.lower()


def has_cjk(s):
    """Check if string contains CJK characters."""
    if not s:
        return False
    return any('\u4e00' <= ch <= '\u9fff' for ch in str(s))


def find_node_in_graph(data, keyword, search_keyword):
    """Replicate searchWriter's main node-finding logic.
    
    Mirrors the exact steps in the frontend:
    1. Look up via name_map.en_to_zh (exact then partial match)
    2. For Chinese input: reverse lookup via name_map.zh_to_en
    3. Final fallback: filter GRAPH.nodes by inclusion match
    4. If multiple matches: pick the one with most edges
    """
    graph = data['graph']
    name_map = data['catalog']['name_map']
    
    final_search_keyword = search_keyword
    clean_keyword = re.sub(r'[\s·.．]', '', search_keyword).lower()
    
    # Step 1: English input -> look up via name_map.en_to_zh
    if re.match(r'^[a-z0-9]', clean_keyword):
        en_to_zh = name_map.get('en_to_zh', {})
        zh_name = en_to_zh.get(clean_keyword)
        
        if not zh_name:
            # Partial match
            matched_keys = [k for k in en_to_zh if clean_keyword in k]
            if len(matched_keys) == 1:
                zh_name = en_to_zh[matched_keys[0]]
        
        if zh_name:
            # Verify this Chinese name exists in graph
            for n in graph['nodes']:
                if n.get('id') == zh_name:
                    return n
                    break
    
    # Step 2: Chinese input -> reverse lookup
    if has_cjk(search_keyword):
        zh_to_en = name_map.get('zh_to_en', {})
        zh_norm = normalize_name_key(search_keyword)
        candidates = zh_to_en.get(zh_norm, [])
        if not candidates:
            # Try without dots/center dots
            no_dot = re.sub(r'[·．.]', '', search_keyword)
            if no_dot != search_keyword:
                candidates = zh_to_en.get(normalize_name_key(no_dot), [])
        
        for en in candidates:
            # Use each English name to look up canonical Chinese
            en_norm = normalize_name_key(en)
            zh = name_map.get('en_to_zh', {}).get(en_norm)
            if zh:
                for n in graph['nodes']:
                    if n.get('id') == zh:
                        return n
                        break
    
    # Step 3: Direct node filter (case-insensitive substring match)
    keyword_lower = final_search_keyword.lower()
    all_matches = []
    for n in graph['nodes']:
        nid = n.get('id', '')
        if not nid:
            continue
        nid_lower = nid.lower()
        if keyword_lower in nid_lower:
            all_matches.append(n)
            continue
        # Normalized comparison
        nid_norm = re.sub(r'[\s·．]', '', nid).lower()
        kw_norm = re.sub(r'[\s·．]', '', keyword_lower)
        if kw_norm in nid_norm or nid_norm in kw_norm:
            all_matches.append(n)
    
    if len(all_matches) == 0:
        return None
    if len(all_matches) == 1:
        return all_matches[0]
    
    # Step 4: Multiple matches - pick one with most edges
    def edges_of(node):
        nid = node.get('id')
        count = 0
        for e in graph['links']:
            src = e.get('source')
            tgt = e.get('target')
            # In the frontend, links can have source/target as either id string or object
            if isinstance(src, dict):
                src = src.get('id')
            if isinstance(tgt, dict):
                tgt = tgt.get('id')
            if src == nid or tgt == nid:
                count += 1
        return count
    
    return max(all_matches, key=edges_of)


def find_catalog_record(data, keyword, search_keyword):
    """Replicate v237FindCatalogRecord from frontend.
    
    Searches the catalog for a matching record, used as fallback when
    the writer isn't in the graph but has a Paris Review interview.
    """
    catalog = data['catalog']
    records = catalog.get('records', [])
    zh_to_en = catalog['name_map'].get('zh_to_en', {})
    
    # Build pool of candidate names
    raw_names = []
    for x in [keyword, search_keyword]:
        if x:
            raw_names.append(x)
    
    # Add English names found via zh_to_en reverse lookup
    en_pool = []
    for x in raw_names:
        if x in zh_to_en:
            en_pool.extend(zh_to_en[x])
        no_dot = re.sub(r'[·．.]', '', str(x))
        if no_dot and no_dot != x and no_dot in zh_to_en:
            en_pool.extend(zh_to_en[no_dot])
    
    # Dedupe
    en_pool = list(set(filter(bool, en_pool)))
    pool = raw_names + en_pool
    
    norms = [normalize_name_key(n) for n in pool]
    norms = [n for n in norms if n]
    
    # First pass: direct Chinese name match
    for user_in in raw_names:
        if not user_in or not has_cjk(user_in):
            continue
        user_norm = normalize_name_key(user_in)
        for rec in records:
            rec_zh = rec.get('name_zh', '')
            if rec_zh and normalize_name_key(rec_zh) == user_norm:
                return rec
    
    # Second pass: match by English name
    for rec in records:
        rk = normalize_name_key(rec.get('name_en', ''))
        if rk and rk in norms:
            return rec
    
    # Third pass: partial English match (len >= 6, no CJK)
    for key in norms:
        if len(key) < 6 or has_cjk(key):
            continue
        for rec in records:
            rk = normalize_name_key(rec.get('name_en', ''))
            if rk and (key in rk or rk in key):
                return rec
    
    return None


def unified_search(data, writer_name):
    """Master search function - replicates searchWriter().
    
    Returns a dict with:
    - matched_node: the graph node if found
    - catalog_record: catalog entry if writer has interview but not in graph
    - resolved_name: the canonical name
    - search_keyword: the normalized search keyword after mapping
    """
    graph = data['graph']
    name_map = data['catalog']['name_map']
    
    keyword = writer_name.strip()
    if not keyword:
        return None
    
    # 0. Sanitize: convert smart quotes
    search_keyword = keyword.replace('\u2018', "'").replace('\u2019', "'")
    
    # 1. Look up via name_map (the modern v283+ approach)
    clean_input = re.sub(r'[\s·.．]', '', search_keyword).lower()
    
    # English -> Chinese via name_map
    en_to_zh = name_map.get('en_to_zh', {})
    zh_name = en_to_zh.get(clean_input)
    if not zh_name:
        matched_keys = [k for k in en_to_zh if clean_input in k]
        if len(matched_keys) == 1:
            zh_name = en_to_zh[matched_keys[0]]
    
    if zh_name:
        for n in graph['nodes']:
            if n.get('id') == zh_name:
                return {
                    'matched_node': n,
                    'catalog_record': None,
                    'resolved_name': zh_name,
                    'search_keyword': zh_name,
                    'is_in_graph': True,
                }
    
    # 2. Chinese reverse lookup
    if has_cjk(search_keyword):
        zh_to_en = name_map.get('zh_to_en', {})
        zh_norm = normalize_name_key(search_keyword)
        candidates = zh_to_en.get(zh_norm, [])
        if not candidates:
            no_dot = re.sub(r'[·．.]', '', search_keyword)
            if no_dot != search_keyword:
                candidates = zh_to_en.get(normalize_name_key(no_dot), [])
        
        for en in candidates:
            en_norm = normalize_name_key(en)
            zh = en_to_zh.get(en_norm)
            if zh:
                for n in graph['nodes']:
                    if n.get('id') == zh:
                        return {
                            'matched_node': n,
                            'catalog_record': None,
                            'resolved_name': zh,
                            'search_keyword': zh,
                            'is_in_graph': True,
                        }
    
    # 3. Direct node search (substring match)
    matched_node = find_node_in_graph(data, keyword, search_keyword)
    if matched_node:
        return {
            'matched_node': matched_node,
            'catalog_record': None,
            'resolved_name': matched_node.get('id'),
            'search_keyword': search_keyword,
            'is_in_graph': True,
        }
    
    # 4. Catalog fallback
    catalog_record = find_catalog_record(data, keyword, search_keyword)
    if catalog_record:
        return {
            'matched_node': None,
            'catalog_record': catalog_record,
            'resolved_name': catalog_record.get('name_en') or catalog_record.get('name_zh'),
            'search_keyword': search_keyword,
            'is_in_graph': False,
        }
    
    # 5. Not found
    return {
        'matched_node': None,
        'catalog_record': None,
        'resolved_name': None,
        'search_keyword': search_keyword,
        'is_in_graph': False,
    }


def search_writer(data, writer_name):
    """Search for a writer in the network + catalog."""
    return unified_search(data, writer_name)


def get_interview_status(data, writer_name):
    """Get interview status for a writer.
    
    Returns Chinese interview info if writer has been published in Chinese.
    """
    result = unified_search(data, writer_name)
    
    chinese_interviews = []
    chinese_book_name = None
    translator = None
    interviewer = None
    year = None
    
    # Get Chinese interview info via name_map reverse lookup
    if result['is_in_graph'] and result['resolved_name']:
        zh_to_en = data['catalog']['name_map'].get('zh_to_en', {})
        # Try the resolved name directly
        resolved_norm = normalize_name_key(result['resolved_name'])
        
        # Look up author_info by the resolved Chinese name
        author_info = data.get('author_info', {})
        for cn_name, details_list in author_info.items():
            if normalize_name_key(cn_name) == resolved_norm:
                chinese_interviews = details_list
                break
    
    if chinese_interviews:
        first = chinese_interviews[0]
        chinese_book_name = first.get('book')
        translator = first.get('translator')
        interviewer = first.get('interviewer')
        year = first.get('year')
    
    # Catalog info (from catalog records)
    catalog_info = result.get('catalog_record')
    if not catalog_info and result['is_in_graph'] and result['matched_node']:
        # Get catalog info via the resolved Chinese name
        resolved = result['resolved_name']
        for rec in data['catalog']['records']:
            if rec.get('name_zh') == resolved:
                catalog_info = rec
                break
    
    return {
        'query': writer_name,
        'resolved_name': result['resolved_name'],
        'is_in_graph': result['is_in_graph'],
        'node': result['matched_node'],
        'has_chinese_interview': bool(chinese_interviews),
        'interview_count': len(chinese_interviews),
        'chinese_book': chinese_book_name,
        'translator': translator,
        'interviewer': interviewer,
        'year': year,
        'catalog_info': catalog_info,
    }


def brief_edge(e):
    return {
        'source': e.get('source') if isinstance(e.get('source'), str) else (e.get('source') or {}).get('id'),
        'target': e.get('target') if isinstance(e.get('target'), str) else (e.get('target') or {}).get('id'),
        'type': e.get('type'),
        'influence': e.get('influence'),
        'borrowed': e.get('borrowed'),
        'id': e.get('id'),
        'reason': e.get('reason'),
    }


def query_author(data, writer_name, limit=20):
    """Query author info with their edges."""
    result = unified_search(data, writer_name)
    if not result['matched_node']:
        return {'query': writer_name, 'found_in_network': False}
    
    node_id = result['matched_node']['id']
    ins, outs = [], []
    for e in data['graph']['links']:
        src = e.get('source') if isinstance(e.get('source'), str) else (e.get('source') or {}).get('id')
        tgt = e.get('target') if isinstance(e.get('target'), str) else (e.get('target') or {}).get('id')
        if tgt == node_id:
            ins.append(e)
        elif src == node_id:
            outs.append(e)
    
    return {
        'query': writer_name,
        'found_in_network': True,
        'node': result['matched_node'],
        'resolved_chinese_name': node_id,
        'in_degree_edges_count': len(ins),
        'out_degree_edges_count': len(outs),
        'incoming_edges': [brief_edge(e) for e in ins[:limit]],
        'outgoing_edges': [brief_edge(e) for e in outs[:limit]],
    }


def get_leaderboard(data, sort_by='degree', top=10):
    """Get writer leaderboard sorted by various metrics.
    
    sort_by options: degree, inDegree, outDegree, pageRank, betweenness,
                      positiveIn, negativeIn, influenceIn
    """
    nodes = data['graph']['nodes']
    valid_sort_keys = ['degree', 'inDegree', 'outDegree', 'pageRank', 
                       'betweenness', 'positiveIn', 'negativeIn', 'influenceIn']
    if sort_by not in valid_sort_keys:
        sort_by = 'degree'
    
    sorted_nodes = sorted(nodes, key=lambda n: n.get(sort_by, 0), reverse=True)
    
    result = []
    for rank, node in enumerate(sorted_nodes[:top], 1):
        result.append({
            'rank': rank,
            'id': node['id'],
            'degree': node.get('degree', 0),
            'inDegree': node.get('inDegree', 0),
            'outDegree': node.get('outDegree', 0),
            'pageRank': node.get('pageRank', 0),
            'betweenness': node.get('betweenness', 0),
            'group': node.get('group', ''),
            'community_id': node.get('community_id', 0),
        })
    
    return {
        'sort_by': sort_by,
        'top_n': top,
        'total_writers': len(nodes),
        'leaderboard': result
    }


def query_edge(data, name1, name2):
    """Query direct relationship(s) between two writers."""
    result1 = unified_search(data, name1)
    result2 = unified_search(data, name2)
    
    node1 = result1.get('matched_node')
    node2 = result2.get('matched_node')
    
    if not node1 or not node2:
        return {
            'query': [name1, name2],
            'resolved_names': [
                node1['id'] if node1 else result1.get('resolved_name', name1),
                node2['id'] if node2 else result2.get('resolved_name', name2)
            ],
            'found_in_network': [node1 is not None, node2 is not None],
            'has_direct_edge': False,
            'edges': []
        }
    
    id1, id2 = node1['id'], node2['id']
    edges = []
    
    for e in data['graph']['links']:
        src = e.get('source') if isinstance(e.get('source'), str) else (e.get('source') or {}).get('id')
        tgt = e.get('target') if isinstance(e.get('target'), str) else (e.get('target') or {}).get('id')
        
        if (src == id1 and tgt == id2) or (src == id2 and tgt == id1):
            edges.append(brief_edge(e))
    
    return {
        'query': [name1, name2],
        'resolved_names': [id1, id2],
        'found_in_network': [True, True],
        'has_direct_edge': len(edges) > 0,
        'edge_count': len(edges),
        'edges': edges
    }


def get_community(data, community_id):
    """Get all writers in a specific community."""
    nodes = data['graph']['nodes']
    community_nodes = [n for n in nodes if n.get('community_id') == community_id]
    
    if not community_nodes:
        return {
            'community_id': community_id,
            'found': False,
            'total_communities': len(set(n.get('community_id', 0) for n in nodes))
        }
    
    sorted_nodes = sorted(community_nodes, key=lambda n: n.get('community_rank', 999))
    
    return {
        'community_id': community_id,
        'found': True,
        'size': len(sorted_nodes),
        'members': [
            {
                'rank': n.get('community_rank', 0),
                'id': n['id'],
                'degree': n.get('degree', 0),
                'group': n.get('group', ''),
                'art_category': n.get('art_category_label', '')
            }
            for n in sorted_nodes
        ]
    }


def get_story_path(data, path_key):
    """Get a predefined story path by index (int) or keyword match in title."""
    story_paths = data.get('story_paths', {}).get('paths', [])
    
    if not story_paths:
        return {'error': 'No story paths available'}
    
    # Try numeric index first
    matched = None
    try:
        idx = int(path_key)
        if 0 <= idx < len(story_paths):
            matched = story_paths[idx]
    except ValueError:
        # Try keyword match in title
        key_norm = normalize_name_key(path_key)
        for p in story_paths:
            title = p.get('title', '')
            if key_norm in normalize_name_key(title):
                matched = p
                break
    
    if not matched:
        available = [f"{i}: {p.get('title', 'untitled')}" for i, p in enumerate(story_paths)]
        return {
            'query_key': path_key,
            'found': False,
            'available_paths': available
        }
    
    return {
        'query_key': path_key,
        'found': True,
        'title': matched.get('title', ''),
        'description': matched.get('description', ''),
        'node_count': len(matched.get('nodes', [])),
        'edge_count': len(matched.get('edges', [])),
        'nodes': matched.get('nodes', []),
        'edges': [brief_edge(e) for e in matched.get('edges', [])]
    }


def main():
    ap = argparse.ArgumentParser(description='Paris Network query tool - aligned with frontend search logic')
    sub = ap.add_subparsers(dest='cmd', required=True)
    
    p = sub.add_parser('search')
    p.add_argument('name')
    
    p = sub.add_parser('interview-status')
    p.add_argument('name')
    
    p = sub.add_parser('author')
    p.add_argument('name')
    p.add_argument('--limit', type=int, default=20)
    
    p = sub.add_parser('stats')
    
    p = sub.add_parser('leaderboard', help='Get writer leaderboard')
    p.add_argument('--sort-by', default='degree', 
                   choices=['degree', 'inDegree', 'outDegree', 'pageRank', 
                            'betweenness', 'positiveIn', 'negativeIn', 'influenceIn'],
                   help='Sort metric (default: degree)')
    p.add_argument('--top', type=int, default=10, help='Number of results (default: 10)')
    
    p = sub.add_parser('edge', help='Query direct relationship between two writers')
    p.add_argument('name1')
    p.add_argument('name2')
    
    p = sub.add_parser('community', help='Get members of a community')
    p.add_argument('--community-id', type=int, required=True, help='Community ID number')
    
    p = sub.add_parser('story-path', help='Get a predefined story path')
    p.add_argument('--key', required=True, help='Story path key (e.g., 女性, 海明威)')
    
    args = ap.parse_args()
    data = json.loads(DATA.read_text())
    
    if args.cmd == 'search':
        result = search_writer(data, args.name)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    elif args.cmd == 'interview-status':
        result = get_interview_status(data, args.name)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    elif args.cmd == 'author':
        result = query_author(data, args.name, args.limit)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    elif args.cmd == 'stats':
        counts = data['counts']
        print(json.dumps(counts, ensure_ascii=False, indent=2))
    elif args.cmd == 'leaderboard':
        result = get_leaderboard(data, args.sort_by, args.top)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    elif args.cmd == 'edge':
        result = query_edge(data, args.name1, args.name2)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    elif args.cmd == 'community':
        result = get_community(data, args.community_id)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    elif args.cmd == 'story-path':
        result = get_story_path(data, args.key)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    main()