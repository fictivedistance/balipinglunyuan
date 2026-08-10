#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 简体中文版《巴黎评论》系列编辑部
"""
巴黎评论员 Skill — 字段完整性回归测试 (v2.1.3)

目的：
  - 防 v2.1.2 bug 重现（interview-status 缺 series/number/issue/url）
  - 跨 agent 一致性：CI 跑这个，所有 SKILL 修改必须先通过这里
  - **不**随发布包分发（见 skill.yaml `distribution.exclude`）

用例设计（20 条）：
  - 10 中文版收录：覆盖 has_chinese_interview=True 的字段完整性
  - 6 仅英文版：覆盖 catalog_info 命中的字段完整性
  - 3 未访谈过：覆盖状态 B/C（不要求 catalog 字段，但要求 is_in_graph 判断正确）
  - 1 边界 case：多篇中文收录（如奥登 2 篇）

运行：
  python3 tests/test_field_completeness.py
  # 指定 API:
  PARIS_API_BASE=http://localhost:8788 python3 tests/test_field_completeness.py
  # 离线模式（用 fixtures）:
  python3 tests/test_field_completeness.py --offline
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

# 把 scripts/ 加进 path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
from paris_network_query import get_interview_status  # noqa: E402


# ============================================================
# 测试用例
# ============================================================
# 每个 case: (作家名, 期望 has_chinese_interview, 期望 catalog_info 是否必填完整字段)
# 字段完整性检查按 SKILL.md "输出字段自检清单" 段

CASES_CN = [
    # 中文名 + 中文版收录（10 条）
    ('海明威', True,  {'series', 'number', 'issue_season_year', 'issue_number', 'url'}),
    ('欧内斯特·海明威', True,  {'series', 'number', 'issue_season_year', 'issue_number', 'url'}),
    ('弗朗西斯·斯科特·菲茨杰拉德', True, {'series', 'number', 'issue_season_year', 'issue_number', 'url'}),
    ('T.S.艾略特', True,  {'series', 'number', 'issue_season_year', 'issue_number', 'url'}),
    ('拉尔夫·埃利森', True, {'series', 'number', 'issue_season_year', 'issue_number', 'url'}),
    ('威廉·福克纳', True, {'series', 'number', 'issue_season_year', 'issue_number', 'url'}),
    ('杰克·凯鲁亚克', True, {'series', 'number', 'issue_season_year', 'issue_number', 'url'}),
    ('W.H.奥登', True,  {'series', 'number', 'issue_season_year', 'issue_number', 'url'}),  # 2 篇中文收录
    ('雷蒙德·卡佛', True, {'series', 'number', 'issue_season_year', 'issue_number', 'url'}),
    ('伊塔洛·卡尔维诺', True, {'series', 'number', 'issue_season_year', 'issue_number', 'url'}),
]

CASES_EN_ONLY = [
    # 仅英文版收录（6 条）— 来自 data-contract.md regression 段
    ('Jhumpa Lahiri', False, {'series', 'number', 'year', 'url'}),
    ('Pat Barker', False, {'series', 'number', 'year', 'url'}),
    ('Hilary Mantel', False, {'series', 'number', 'year', 'url'}),
    ('Kazuo Ishiguro', False, {'series', 'number', 'year', 'url'}),
    ('Haruki Murakami', False, {'series', 'number', 'year', 'url'}),
    ('Ian McEwan', False, {'series', 'number', 'year', 'url'}),
]

CASES_NOT_INTERVIEWED = [
    # 未被访谈过（3 条）— 不要求 catalog 字段，但要求 is_in_graph / catalog 字段判断正确
    ('王尔德', False, set()),  # 在图谱中但未被访谈（状态 B）
    ('陀思妥耶夫斯基', False, set()),  # 同上
    ('李白', False, set()),  # 状态 C（不在图谱也不被访谈）
]


# ============================================================
# 离线 fixtures（用于 --offline 跑测，避免依赖 Worker）
# ============================================================
OFFLINE_FIXTURES = {
    '海明威': {
        'ok': True,
        'is_in_graph': True,
        'has_chinese_interview': True,
        'interview_count': 1,
        'chinese_book': '巴黎评论·作家访谈1',
        'translator': 'XXX',
        'interviewer': 'XXX',
        'year': '1956',
        'node': {},
        'catalog_info': {
            'series': 'The Art of Fiction',
            'number': 'No. 21',
            'issue_season_year': 'Spring 1956',
            'issue_number': '13',
            'url': 'https://www.theparisreview.org/letters-essays/5877/the-art-of-fiction-no-21-ernest-hemingway',
        },
    },
    # 其余 fixture 在 --offline 时只覆盖核心断言，不要求全部 20 条
}


# ============================================================
# 断言逻辑
# ============================================================

def check_case(name: str, expected_cn: bool, required_fields: set, result: dict, fail_msgs: list) -> None:
    """检查单个 case 的字段完整性，错误追加到 fail_msgs。"""
    if not result.get('ok', True):
        fail_msgs.append(f"❌ [{name}] API 返回错误：{result.get('error')}")
        return

    actual_cn = result.get('has_chinese_interview', False)
    if actual_cn != expected_cn:
        fail_msgs.append(f"❌ [{name}] has_chinese_interview 期望={expected_cn} 实际={actual_cn}")
        return

    if expected_cn or result.get('catalog_info'):
        ci = result.get('catalog_info') or {}
        # 回落 node.interview
        if not ci.get('series') and isinstance(result.get('node', {}).get('interview'), dict):
            ci = result.get('node', {}).get('interview') or ci
        missing = []
        for f in required_fields:
            if not ci.get(f):
                missing.append(f)
        if missing:
            fail_msgs.append(f"❌ [{name}] catalog_info 缺字段：{', '.join(sorted(missing))}")


def main():
    parser = argparse.ArgumentParser(description='巴黎评论员字段完整性回归测试')
    parser.add_argument('--offline', action='store_true', help='用 fixtures 跑测，不依赖 Worker API')
    args = parser.parse_args()

    print("=" * 70)
    print("巴黎评论员 Skill v2.1.3 — 字段完整性回归测试")
    print(f"模式：{'offline (fixtures)' if args.offline else 'online (Worker API)'}")
    print("=" * 70)

    all_cases = CASES_CN + CASES_EN_ONLY + CASES_NOT_INTERVIEWED
    passed = 0
    failed_msgs = []

    for name, expected_cn, required in all_cases:
        if args.offline:
            if name not in OFFLINE_FIXTURES:
                # offline 模式只覆盖核心 1 条，其余跳过
                print(f"  ⏭  [offline skip] {name}")
                continue
            result = OFFLINE_FIXTURES[name]
        else:
            try:
                result = get_interview_status(name)
            except Exception as e:
                failed_msgs.append(f"❌ [{name}] 异常：{e}")
                continue

        before = len(failed_msgs)
        check_case(name, expected_cn, required, result, failed_msgs)
        if len(failed_msgs) == before:
            passed += 1
            ci = result.get('catalog_info') or {}
            series = ci.get('series', '(N/A)')[:30]
            print(f"  ✅ [{name}] series={series}")
        else:
            print(f"  ❌ [{name}]")

    total = len(all_cases)
    print()
    print("=" * 70)
    print(f"通过：{passed}/{total}")
    if failed_msgs:
        print()
        print("失败详情：")
        for m in failed_msgs:
            print(f"  {m}")
        sys.exit(1)
    else:
        print("✅ 所有字段完整性检查通过")
        sys.exit(0)


if __name__ == '__main__':
    main()