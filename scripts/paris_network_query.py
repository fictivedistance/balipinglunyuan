#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 简体中文版《巴黎评论》系列编辑部
"""Paris Network query client — API mode.

All queries go through the Cloudflare Worker query API.
No local data file required.

Offline fallback: recent query results are cached in ~/.cache/巴黎评论员/
and used when the API is unreachable.

Usage:
  python3 paris_network_query.py search <writer_name>
  python3 paris_network_query.py interview-status <writer_name>
  python3 paris_network_query.py stats
  python3 paris_network_query.py author <name>
  python3 paris_network_query.py edge <name1> <name2>
  python3 paris_network_query.py leaderboard --sort-by degree --top 10
  python3 paris_network_query.py community --community-id 6
  python3 paris_network_query.py story-path --key 拉美

Environment variables:
  PARIS_API_BASE — override API base URL (default: https://api2.fictivedistance.com)
  PARIS_API_TIMEOUT — request timeout in seconds (default: 15)
  PARIS_CACHE_DIR — override cache directory
"""
from __future__ import annotations
import argparse, json, os, sys, time, hashlib
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ── 配置 ──
API_BASE = os.environ.get(
    'PARIS_API_BASE',
    'https://api2.fictivedistance.com'
)
API_TIMEOUT = int(os.environ.get('PARIS_API_TIMEOUT', '15'))
CACHE_DIR = Path(os.environ.get(
    'PARIS_CACHE_DIR',
    os.path.expanduser('~/.cache/巴黎评论员')
))
CACHE_TTL_SECONDS = 3600  # 离线缓存有效期 1 小时


# ── API 调用 ──
def api_get(action: str, **params) -> dict:
    """Call the query API and return JSON response."""
    query_parts = [f'action={action}']
    for k, v in params.items():
        if v is not None:
            query_parts.append(f'{k}={urllib_quote(str(v))}')
    url = f'{API_BASE}/api/query?{"&".join(query_parts)}'

    try:
        req = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'paris-network-skill/2.0'})
        with urlopen(req, timeout=API_TIMEOUT) as resp:
            data = json.loads(resp.read())
            # 缓存成功响应
            if data.get('ok', True):
                _cache_save(action, params, data)
            return data
    except (URLError, HTTPError, TimeoutError, OSError) as e:
        # 尝试离线缓存降级
        cached = _cache_load(action, params)
        if cached is not None:
            return cached
        return {
            'ok': False,
            'error': f'api_unreachable: {e}',
            'hint': 'API 不可达，且无本地缓存。请检查网络连接。'
        }


def urllib_quote(s: str) -> str:
    """URL-encode a string."""
    from urllib.parse import quote
    return quote(s, safe='')


# ── 离线降级缓存 ──
def _cache_key(action: str, params: dict) -> str:
    """Generate a stable cache key from action + params."""
    raw = f'{action}:{json.dumps(params, sort_keys=True, ensure_ascii=False)}'
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _cache_save(action: str, params: dict, data: dict):
    """Save API response to local cache."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        key = _cache_key(action, params)
        path = CACHE_DIR / f'{key}.json'
        payload = {
            'action': action,
            'params': params,
            'data': data,
            'cached_at': time.time(),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False))
    except OSError:
        pass  # 缓存写入失败不影响主流程


def _cache_load(action: str, params: dict) -> dict | None:
    """Load cached response if within TTL."""
    try:
        key = _cache_key(action, params)
        path = CACHE_DIR / f'{key}.json'
        if not path.exists():
            return None
        payload = json.loads(path.read_text())
        age = time.time() - payload.get('cached_at', 0)
        if age > CACHE_TTL_SECONDS:
            return None
        # 标记为缓存数据
        result = payload['data']
        if isinstance(result, dict):
            result['_from_cache'] = True
        return result
    except (OSError, json.JSONDecodeError):
        return None


# ── 查询函数 ──
def get_interview_status(writer_name: str) -> dict:
    return api_get('interview-status', name=writer_name)


def search_writer(writer_name: str) -> dict:
    return api_get('interview-status', name=writer_name)


def query_author(writer_name: str, limit: int = 20) -> dict:
    return api_get('author', name=writer_name, limit=limit)


def query_edge(name1: str, name2: str) -> dict:
    return api_get('edge', name_a=name1, name_b=name2)


def get_leaderboard(sort_by: str = 'degree', top: int = 10) -> dict:
    return api_get('leaderboard', sort_by=sort_by, top=top)


def get_community(community_id: int) -> dict:
    return api_get('community', community_id=community_id)


def get_story_path(path_key: str) -> dict:
    return api_get('story-path', key=path_key)


def get_stats() -> dict:
    return api_get('stats')


def get_version() -> dict:
    return api_get('version')

def get_shortest_path(name_a: str, name_b: str) -> dict:
    return api_get('shortest-path', name_a=name_a, name_b=name_b)

def get_cross_query(query_type: str = 'uninterviewed_most_mentioned', top: int = 20) -> dict:
    return api_get('cross-query', type=query_type, top=top)

def get_communities() -> dict:
    return api_get('list-communities')


# ── 兼容旧接口：normalize_name_key 保留供 nl_interface 使用 ──
def normalize_name_key(s):
    import re, unicodedata
    if not s:
        return ''
    s = str(s).strip()
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r'[\s·.．]+', '', s)
    return s.lower()


# ── CLI ──
def main():
    ap = argparse.ArgumentParser(description='Paris Network query client (API mode)')
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('search')
    p.add_argument('name')

    p = sub.add_parser('interview-status')
    p.add_argument('name')

    p = sub.add_parser('author')
    p.add_argument('name')
    p.add_argument('--limit', type=int, default=20)

    p = sub.add_parser('stats')

    p = sub.add_parser('leaderboard')
    p.add_argument('--sort-by', default='degree',
                   choices=['degree', 'inDegree', 'outDegree', 'pageRank',
                            'betweenness', 'positiveIn', 'negativeIn', 'influenceIn'])
    p.add_argument('--top', type=int, default=10)

    p = sub.add_parser('edge')
    p.add_argument('name1')
    p.add_argument('name2')

    p = sub.add_parser('community')
    p.add_argument('--community-id', type=int, required=True)

    p = sub.add_parser('story-path')
    p.add_argument('--key', required=True)

    p = sub.add_parser('version', help='Check API version')

    p = sub.add_parser('shortest-path', help='Find shortest path between two writers')
    p.add_argument('name1')
    p.add_argument('name2')

    p = sub.add_parser('cross-query', help='Cross-reference queries')
    p.add_argument('--type', default='uninterviewed_most_mentioned',
                   choices=['uninterviewed_most_mentioned', 'interviewed_but_isolated',
                            'cross_community_bridges', 'positive_vs_negative'])
    p.add_argument('--top', type=int, default=20)

    p = sub.add_parser('list-communities', help='List all communities')

    args = ap.parse_args()

    if args.cmd == 'search':
        result = search_writer(args.name)
    elif args.cmd == 'interview-status':
        result = get_interview_status(args.name)
    elif args.cmd == 'author':
        result = query_author(args.name, args.limit)
    elif args.cmd == 'stats':
        result = get_stats()
    elif args.cmd == 'leaderboard':
        result = get_leaderboard(args.sort_by, args.top)
    elif args.cmd == 'edge':
        result = query_edge(args.name1, args.name2)
    elif args.cmd == 'community':
        result = get_community(args.community_id)
    elif args.cmd == 'story-path':
        result = get_story_path(args.key)
    elif args.cmd == 'version':
        result = get_version()
    elif args.cmd == 'shortest-path':
        result = get_shortest_path(args.name1, args.name2)
    elif args.cmd == 'cross-query':
        result = get_cross_query(args.type, args.top)
    elif args.cmd == 'list-communities':
        result = get_communities()
    else:
        ap.print_help()
        return

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    main()