#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 简体中文版《巴黎评论》系列编辑部
"""
巴黎评论员 Skill — CLI 烟雾测试 (v2.1.3)

目的：
  - 验证 nl_interface.py 命令识别在每次 SKILL 改动后仍正常
  - 不调 API，纯本地命令检测层断言（比字段完整性快）
  - 跨 agent 一致性：CI 必须过

用例设计（20 条）：
  - 6 interview-status 触发短语
  - 3 edge 关系查询触发
  - 2 leaderboard 排序触发
  - 2 shortest-path 触发
  - 2 cross-query 触发
  - 2 community 触发
  - 1 story-path 触发
  - 2 边界/兜底（空 query / 多余标点）

运行：
  python3 tests/test_cli_smoke.py
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
from nl_interface import detect_command  # noqa: E402


# (输入 query, 期望 cmd, 期望关键参数)
CASES = [
    # interview-status (6)
    ('海明威被《巴黎评论》访谈过吗', 'interview-status', '海明威'),
    ('查一下卡佛的访谈状态', 'interview-status', '卡佛'),
    ('纳博科夫有没有中文版', 'interview-status', '纳博科夫'),
    ('W.H.奥登访谈过没', 'interview-status', 'W.H.奥登'),
    ('《巴黎评论》访谈过博尔赫斯吗', 'interview-status', '博尔赫斯'),
    ('菲茨杰拉德被收录过吗', 'interview-status', '菲茨杰拉德'),

    # edge (3)
    ('海明威和福克纳有什么关系', 'edge', ('海明威', '福克纳')),
    ('博尔赫斯怎么评价卡尔维诺', 'edge', ('博尔赫斯', '卡尔维诺')),
    ('纳博科夫提到过陀思妥耶夫斯基吗', 'edge', ('纳博科夫', '陀思妥耶夫斯基')),

    # leaderboard (2)
    ('最受欢迎的作家排行榜', 'leaderboard', 'positiveIn'),
    ('最受访谈者提及的作家前 5', 'leaderboard', 'inDegree'),

    # shortest-path (2)
    ('海明威和卡夫卡之间隔着谁', 'shortest-path', ('海明威', '卡夫卡')),
    ('博尔赫斯怎么连到福克纳', 'shortest-path', ('博尔赫斯', '福克纳')),

    # cross-query (2)
    ('从未被访谈但被提及最多的作家', 'cross-query', 'uninterviewed_most_mentioned'),
    ('跨社群桥接的作家', 'cross-query', 'cross_community_bridges'),

    # community (2)
    ('社群 6 的成员', 'community', 6),
    ('博尔赫斯在哪个社群', '_author_first_then_community', None),

    # story-path (1)
    ('第 0 条故事路径', 'story-path', '0'),

    # 边界 (2)
    ('？？？', 'search', '？？？'),  # 兜底 search
    (' 海明威 ', 'search', '海明威'),  # 多余空格归一
]


def main():
    print("=" * 70)
    print("巴黎评论员 Skill v2.1.3 — CLI 烟雾测试")
    print("=" * 70)

    passed = 0
    failed = []

    for query, expected_cmd, expected_param in CASES:
        info = detect_command(query)
        actual_cmd = info.get('cmd')

        if actual_cmd != expected_cmd:
            failed.append(f"❌ [{query!r}] cmd 期望={expected_cmd} 实际={actual_cmd}")
            continue

        # 参数校验
        ok = True
        if expected_cmd == 'interview-status':
            ok = info.get('name') == expected_param
            if not ok:
                failed.append(f"❌ [{query!r}] name 期望={expected_param} 实际={info.get('name')}")
        elif expected_cmd == 'edge':
            ok = info.get('name1') == expected_param[0] and info.get('name2') == expected_param[1]
            if not ok:
                failed.append(f"❌ [{query!r}] names 期望={expected_param} 实际={(info.get('name1'), info.get('name2'))}")
        elif expected_cmd == 'leaderboard':
            ok = info.get('sort_by') == expected_param
            if not ok:
                failed.append(f"❌ [{query!r}] sort_by 期望={expected_param} 实际={info.get('sort_by')}")
        elif expected_cmd == 'shortest-path':
            ok = info.get('name1') == expected_param[0] and info.get('name2') == expected_param[1]
            if not ok:
                failed.append(f"❌ [{query!r}] names 期望={expected_param}")
        elif expected_cmd == 'cross-query':
            ok = info.get('query_type') == expected_param
            if not ok:
                failed.append(f"❌ [{query!r}] query_type 期望={expected_param}")
        elif expected_cmd == 'community':
            ok = info.get('community_id') == expected_param
            if not ok:
                failed.append(f"❌ [{query!r}] community_id 期望={expected_param}")

        if ok:
            passed += 1
            print(f"  ✅ [{query[:30]:30s}] → {actual_cmd}")

    print()
    print("=" * 70)
    print(f"通过：{passed}/{len(CASES)}")
    if failed:
        print()
        print("失败详情：")
        for f in failed:
            print(f"  {f}")
        sys.exit(1)
    else:
        print("✅ 所有 CLI 命令识别测试通过")
        sys.exit(0)


if __name__ == '__main__':
    main()