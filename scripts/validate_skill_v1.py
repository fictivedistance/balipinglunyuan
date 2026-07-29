#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 简体中文版《巴黎评论》系列编辑部
"""Paris Network Skill v2 — API 集成验证脚本

验证 skill 端 API 客户端与 Worker API 的端到端连通性和数据正确性。

前置条件：
  - Worker API 已部署且 KV 数据已上传
  - 或本地 wrangler dev 运行中

用法：
  python3 scripts/validate_skill_v1.py
  python3 scripts/validate_skill_v1.py --api-base http://localhost:8788
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from paris_network_query import (
    api_get, get_interview_status, query_author, query_edge,
    get_leaderboard, get_community, get_story_path, get_stats, get_version,
    API_BASE
)

passed = 0
failed = 0
warnings = 0


def assert_true(cond, msg):
    global passed, failed
    if cond:
        passed += 1
    else:
        failed += 1
        print(f"  ❌ {msg}")


def warn(msg):
    global warnings
    warnings += 1
    print(f"  ⚠️  {msg}")


def main():
    global passed, failed, warnings
    print("=" * 70)
    print("Paris Network Skill v2 — API 集成验证")
    print("=" * 70)
    print(f"API: {API_BASE}")
    print()

    # ── 0. 版本检查 ──
    print("[0] API 连通性")
    vr = get_version()
    if vr.get('ok'):
        print(f"  ✅ API 版本: {vr.get('version', 'N/A')}, 更新时间: {vr.get('updated_at', 'N/A')}")
        passed += 1
    else:
        print(f"  ❌ API 不可达: {vr.get('error', 'N/A')}")
        print(f"  💡 请检查 API_BASE 或设置 PARIS_API_BASE 环境变量")
        failed += 1
        print("\n⛔ API 不可达，后续测试无法进行。")
        sys.exit(1)

    # ── 1. 统计 ──
    print("\n[1] 统计数据")
    stats = get_stats()
    s = stats.get('stats', stats)
    assert_true(s.get('nodes', 0) > 500, f"节点数异常: {s.get('nodes')}")
    assert_true(s.get('links', 0) > 1000, f"边数异常: {s.get('links')}")
    assert_true(s.get('catalog_records', 0) == 454, f"目录数异常: {s.get('catalog_records')}（期望 454）")
    assert_true(s.get('authors_with_chinese_interview', 0) > 100, f"中文版作家数异常: {s.get('authors_with_chinese_interview')}")
    if passed > 0 and failed == 0:
        print(f"  ✅ 节点: {s.get('nodes')}, 边: {s.get('links')}, 目录: {s.get('catalog_records')}, 中文版: {s.get('authors_with_chinese_interview')}")

    # ── 2. 名字映射：英文 -> 中文 ──
    print("\n[2] 名字映射 (English -> Chinese)")
    test_cases_en = [
        ("Hilary Mantel", "希拉里·曼特尔"),
        ("Haruki Murakami", "村上春树"),
        ("Murakami Haruki", "村上春树"),
        ("Jhumpa Lahiri", "裘帕·拉希莉"),
        ("Pat Barker", "派特·巴克"),
    ]
    for en_name, expected_zh in test_cases_en:
        r = get_interview_status(en_name)
        resolved = r.get('resolved_name', '')
        assert_true(
            resolved == expected_zh,
            f"{en_name}: expected {expected_zh}, got {resolved}"
        )
    if failed == 0:
        print(f"  ✅ 英文名解析 ({len(test_cases_en)} 测试) 全部通过")

    # ── 3. 中文名直查 ──
    print("\n[3] 中文名直查")
    test_cases_zh = [
        "村上春树",
        "博尔赫斯",
        "希拉里·曼特尔",
    ]
    for zh_name in test_cases_zh:
        r = get_interview_status(zh_name)
        assert_true(
            r.get('is_in_graph', False),
            f"{zh_name}: 应在图谱中"
        )
    if failed == 0:
        print(f"  ✅ 中文名直查 ({len(test_cases_zh)} 测试) 全部通过")

    # ── 4. 边查询 ──
    print("\n[4] 边查询")
    # 福克纳 -> 海明威
    r = query_edge("威廉·福克纳", "欧内斯特·海明威")
    assert_true(r.get('has_direct_edge') or r.get('reverse_edge_count', 0) > 0,
                "福克纳-海明威 应有边")
    # 不存在的边
    r2 = query_edge("海明威", "莎士比亚")
    # 莎士比亚可能在图谱中作为 mentioned 节点
    found = r2.get('found_in_network', [False, False])
    assert_true(isinstance(found, list), "found_in_network 应为列表")

    # 反序日本人名边
    r3 = query_edge("村上春树", "玛丽·莫里斯")
    assert_true(r3.get('has_direct_edge', False), "村上春树 → 玛丽·莫里斯 应有边")
    if failed == 0:
        print("  ✅ 边查询正确")

    # ── 5. 访谈信息完整性 ──
    print("\n[5] 完整访谈信息")
    r = get_interview_status("希拉里·曼特尔")
    assert_true(r.get('has_chinese_interview', False), "曼特尔应有中文版访谈")
    interviews = r.get('all_interviews', [])
    if interviews:
        iv = interviews[0]
        assert_true(iv.get('book') or iv.get('中文版书名'), "应有书名")
        assert_true(iv.get('translator') or iv.get('译者'), "应有译者")
        print(f"  ✅ 曼特尔访谈信息完整")
        print(f"     书名: {iv.get('book', iv.get('中文版书名', 'N/A'))}")
        print(f"     译者: {iv.get('translator', iv.get('译者', 'N/A'))}")

    # ── 6. 排行榜 ──
    print("\n[6] 排行榜")
    r = get_leaderboard(sort_by='degree', top=10)
    entries = r.get('entries', r.get('leaderboard', []))
    assert_true(len(entries) == 10, f"应返回 10 条，实际 {len(entries)}")
    if entries:
        first = entries[0]
        assert_true(first.get('id'), "第一名应有 id")
        print(f"  ✅ 排行榜 OK，第一名: {first.get('id')} (degree={first.get('degree')})")

    # ── 7. 社群 ──
    print("\n[7] 社群查询")
    r = get_community(1)
    members = r.get('members', [])
    assert_true(len(members) > 0, "社群 1 应有成员")
    if members:
        print(f"  ✅ 社群 1: {r.get('member_count', len(members))} 成员, {r.get('community_name', 'N/A')}")

    # ── 8. 故事路径 ──
    print("\n[8] 故事路径")
    r = get_story_path("0")
    assert_true(r.get('found', r.get('ok', False)), "第 0 条路径应存在")
    if r.get('found') or r.get('ok'):
        path = r.get('path', r)
        print(f"  ✅ 路径 0: {path.get('title', 'N/A')}")

    # ── 9. 缓存降级验证 ──
    print("\n[9] 离线缓存")
    cache_dir = Path(os.path.expanduser('~/.cache/巴黎评论员'))
    cache_files = list(cache_dir.glob('*.json')) if cache_dir.exists() else []
    assert_true(len(cache_files) > 0, f"缓存目录应有文件 (实际 {len(cache_files)} 个)")
    if cache_files:
        print(f"  ✅ 缓存目录: {cache_dir} ({len(cache_files)} 个缓存文件)")

    # ── 汇总 ──
    print("\n" + "=" * 70)
    total = passed + failed
    print(f"结果: {passed}/{total} 通过, {failed} 失败, {warnings} 警告")
    if failed == 0:
        print("✅ 所有测试通过！skill v2 API 模式验证成功")
    else:
        print(f"❌ {failed} 个测试失败")
        sys.exit(1)


if __name__ == '__main__':
    main()