#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 简体中文版《巴黎评论》系列编辑部
"""
巴黎评论员技能 - 自然语言接口（API 模式）
把用户的自然语言提问映射到对应的 API 查询，并把 JSON 结果转换为人类可读的回答。
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

# 导入 API 客户端模块
sys.path.insert(0, str(Path(__file__).parent))
from paris_network_query import (
    get_interview_status, query_author,
    get_leaderboard, query_edge, get_community, get_story_path,
    get_stats, get_version, normalize_name_key,
    get_shortest_path, get_cross_query, get_communities,
    api_get
)


# ============================================================
# 字段自检 (v2.1.3) — 防止 SKILL 升级或 agent 截断导致字段丢失
# ============================================================

# interview-status 在 has_chinese_interview=True 时必须展示的字段
# 来源：data-contract.md "Interview status fields" + SKILL.md 状态 A1 模板
_REQUIRED_CN_FIELDS = ('series', 'number', 'issue_season_year', 'issue_number', 'url')
# 仅英文版收录（无中文版）时必须展示的字段
_REQUIRED_EN_ONLY_FIELDS = ('series', 'number', 'year', 'url')


def _self_check_interview_status(result: dict) -> list[str]:
    """检查 interview-status 结果字段完整性，返回缺失字段名列表。

    v2.1.2 bug 教训：脚本输出字段缺失时，agent 倾向于凭印象补全而不调脚本，
    于是把残缺输出当真。改在这里做硬性自检，宁可输出告警也不漏字段。
    """
    missing = []
    if not result.get('ok', True):
        return missing  # 错误结果由调用方处理

    if result.get('has_chinese_interview'):
        # 中文版收录：必须展示原刊系列/编号/期号/原文链接
        ci = result.get('catalog_info') or {}
        node = result.get('node') or {}
        # 缺失时回落 node.interview，逻辑与 format_result 一致
        if not ci.get('series') and isinstance(node.get('interview'), dict):
            ci = node.get('interview') or ci
        for f in _REQUIRED_CN_FIELDS:
            if not ci.get(f):
                missing.append(f'catalog_info.{f}')
    elif result.get('catalog_info'):
        # 仅英文版：必须展示系列/编号/年份/原文链接
        ci = result.get('catalog_info') or {}
        for f in _REQUIRED_EN_ONLY_FIELDS:
            if not ci.get(f):
                missing.append(f'catalog_info.{f}')
    return missing


# ============================================================
# 辅助函数
# ============================================================

def _clean_name(name: str) -> str:
    """归一化人名标点空格。"""
    if not name:
        return ''
    import re
    # 统一间隔号前后无空格, 去掉名字中的多余空格
    name = re.sub(r'\s*·\s*', '·', name)
    name = re.sub(r'\s+', '', name)
    return name


# ============================================================
# 命令检测（拆分为独立函数，便于维护和扩展）
# ============================================================

def _detect_leaderboard(q: str) -> dict | None:
    """检测排行榜类查询"""
    if not any(kw in q for kw in ['排行榜', '排名', '最多', '最高', '前十', 'top', 'Top', '排第几',
                                   '最伟大', '最牛', '最重要', '最受欢迎', '最受',
                                   '最讨厌', '最反感', '最喜爱', '最赞赏', '最好评', '最差']):
        return None
    
    sort_by = 'degree'
    
    if any(kw in q for kw in ['提及', '被提到', 'inDegree']):
        sort_by = 'inDegree'
    elif any(kw in q for kw in ['提到', '评价别人', 'outDegree']):
        sort_by = 'outDegree'
    elif any(kw in q for kw in ['影响力', 'pageRank', '重要', '伟大', '牛']):
        sort_by = 'pageRank'
    elif any(kw in q for kw in ['桥梁', '中介', 'betweenness']):
        sort_by = 'betweenness'
    elif any(kw in q for kw in ['正面', '好评', 'positive', '喜爱', '欢迎', '赞赏']):
        sort_by = 'positiveIn'
    elif any(kw in q for kw in ['负面', '批评', 'negative', '讨厌', '反感']):
        sort_by = 'negativeIn'
    elif any(kw in q for kw in ['影响', 'influence']):
        sort_by = 'influenceIn'
    
    # 提取数字
    top = 10
    num_match = re.search(r'前\s*(\d+)', q) or re.search(r'top\s*(\d+)', q, re.I) or re.search(r'(\d+)\s*名', q)
    if num_match:
        top = int(num_match.group(1))
    
    return {'cmd': 'leaderboard', 'sort_by': sort_by, 'top': top}


def _extract_two_names(q: str) -> tuple[str, str] | None:
    """从关系查询中提取两个作家名"""
    q_clean = q
    for suffix in ['有什么关系', '的关系', '有联系吗', '有关系吗', '有关系', '有联系',
                   '怎么看', '如何看', '的看法', '怎么评价', '如何评价',
                   '的评价', '提到过', '提到', '看法', '评价', '吗', '呢', '？', '?']:
        if q_clean.endswith(suffix):
            q_clean = q_clean[:-len(suffix)]
            break

    for sep in ['和', '与', '跟', '对']:
        if sep in q_clean:
            parts = q_clean.split(sep, 1)
            name1 = parts[0].strip()
            name2 = parts[1].strip()
            # 清理右侧噪音词：从 name2 里移除路径/关系词（不只剥前缀，因为可能出现在中段）
            # 例如「卡夫卡之间隔着谁」要变成「卡夫卡」、「福克纳怎么连」要变成「福克纳」
            noise_pattern = r'(之间隔着谁|怎么连上|怎么连|怎么联系|能联系|能连到|之间|隔着谁|中间)'
            name2 = re.sub(noise_pattern, '', name2).strip()
            # 清理尾部疑问词 / 助词
            name2 = re.sub(r'[了吗？?呢。]+$', '', name2).strip()
            name2 = re.sub(r'^[的]+', '', name2).strip()
            if name1 and name2 and len(name1) > 1 and len(name2) > 1:
                return (name1, name2)

    # 退路：含关系动词但无明确分隔词（如「博尔赫斯怎么评价卡尔维诺」「纳博科夫提到过陀思妥耶夫斯基」）
    rel_verbs = ['怎么评价', '如何评价', '提到过', '提到', '评价', '看法']
    for verb in rel_verbs:
        if verb in q_clean:
            idx = q_clean.find(verb)
            left = q_clean[:idx].strip()
            right = q_clean[idx + len(verb):].strip()
            # 左侧清理：「怎么」「怎么评价」的反向
            for prefix in ['怎么', '如何']:
                if left.endswith(prefix):
                    left = left[:-len(prefix)].strip()
            # 右侧清理：「了」「过」「吗」「？」等
            right = re.sub(r'[了吗？?呢。]+$', '', right)
            if left and right and len(left) > 1 and len(right) > 1:
                return (left, right)

    return None


def _detect_edge(q: str) -> dict | None:
    """检测双边关系查询"""
    relation_markers = ['和', '与', '跟', '对', '怎么评价', '如何评价', '评价', '提到', '看法']
    if not any(m in q for m in relation_markers):
        return None
    
    names = _extract_two_names(q)
    if names:
        return {'cmd': 'edge', 'name1': names[0], 'name2': names[1]}
    
    return None


def _detect_community(q: str) -> dict | None:
    """检测社群查询"""
    if not any(kw in q for kw in ['社群', '社区', 'community', '同一个群', '同属', '成员']):
        return None
    
    id_match = re.search(r'社群\s*(\d+)', q) or re.search(r'community\s*(\d+)', q, re.I)
    if id_match:
        return {'cmd': 'community', 'community_id': int(id_match.group(1))}
    
    if any(kw in q for kw in ['哪个社群', '哪个社区', '在哪个群']):
        return {'cmd': '_author_first_then_community', 'question': q}
    
    return None


def _detect_story_path(q: str) -> dict | None:
    """检测故事路径查询"""
    if not any(kw in q for kw in ['故事路径', '故事线', '路径', '主题', 'story']):
        return None
    
    # 提取数字索引
    key_match = re.search(r'第\s*(\d+)\s*条', q) or re.search(r'(\d+)', q)
    if key_match:
        return {'cmd': 'story-path', 'key': key_match.group(1)}
    
    # 静态退路关键词
    for kw in ['拉美', '女性', '现代主义', '美国', '诗歌', '四种', '立场', '美学',
               '乔伊斯', '卡夫卡', '庞德', '福克纳', '詹姆斯', '阅读']:
        if kw in q:
            return {'cmd': 'story-path', 'key': kw}
    
    return {'cmd': 'story-path_list'}


def _detect_path(q: str) -> dict | None:
    """检测关系路径发现查询"""
    if not any(kw in q for kw in ['路径', '隔着谁', '怎么连上', '怎么连', '连通', '最短路径',
                                   '能联系到吗', '能连到吗', '几步']):
        return None

    # 优先用标准分隔词提取两个名字
    names = _extract_two_names(q)
    if names:
        return {'cmd': 'shortest-path', 'name1': names[0], 'name2': names[1]}

    # 退路：「X 怎么连到/连上 Y」模式（如「博尔赫斯怎么连到福克纳」）
    for verb in ['怎么连到', '怎么连上', '怎么联系', '能联系', '能连到']:
        if verb in q:
            parts = q.split(verb, 1)
            left = parts[0].strip()
            right = parts[1].strip()
            right = re.sub(r'[了吗？?呢。]+$', '', right)
            if left and right and len(left) > 1 and len(right) > 1:
                return {'cmd': 'shortest-path', 'name1': left, 'name2': right}

    return None


def _detect_cross_query(q: str) -> dict | None:
    """检测交叉关联查询"""
    query_type = None
    top = 20

    if any(kw in q for kw in ['没访谈', '没被访谈', '未被访谈', '没采访过', '从没被',
                                '没做过访谈', '不在访谈']):
        if any(kw in q for kw in ['最多', '被提及', '提到最多', '排行']):
            query_type = 'uninterviewed_most_mentioned'
    elif any(kw in q for kw in ['跨界', '跨社群', '桥接', '连接不同']):
        query_type = 'cross_community_bridges'
    elif any(kw in q for kw in ['正负评价', '正负反差', '争议最大', '评价分歧']):
        query_type = 'positive_vs_negative'
    elif any(kw in q for kw in ['被访谈但', '访谈过但', '访谈了但']):
        if any(kw in q for kw in ['连接少', '关系少', '孤立', '边缘']):
            query_type = 'interviewed_but_isolated'

    if not query_type:
        return None

    num_match = re.search(r'前\s*(\d+)', q) or re.search(r'top\s*(\d+)', q, re.I)
    if num_match:
        top = int(num_match.group(1))

    return {'cmd': 'cross-query', 'query_type': query_type, 'top': top}


def _detect_list_communities(q: str) -> dict | None:
    """检测社群列表查询"""
    if any(kw in q for kw in ['所有社群', '社群列表', '有哪些社群', '多少个社群',
                                '全部社群', '社群都有']):
        return {'cmd': 'list-communities'}
    return None


def _detect_author(q: str) -> dict | None:
    """检测作家详情查询"""
    if not any(kw in q for kw in ['详情', '详细信息', '所有关系', '连接数', '入边', '出边',
                                   '的关系网', '关系图谱', '哪些作家提到']):
        return None
    
    name = q
    for trigger in ['的详细信息', '的详情', '详情', '详细信息', '的所有关系', '所有关系',
                    '的连接数', '连接数', '的入边', '入边', '的出边', '出边',
                    '的关系网', '关系图谱', '有哪些作家提到']:
        name = name.replace(trigger, '')
    for prefix in ['查询', '查一下', '查', '看看', '关于', '作家']:
        if name.startswith(prefix):
            name = name[len(prefix):]
    name = name.strip('吗？?的 \t')
    
    if name and len(name) > 1:
        return {'cmd': 'author', 'name': name, 'limit': 20}
    
    return None


def _detect_interview_status(q: str) -> dict | None:
    """检测访谈状态查询"""
    if not any(kw in q for kw in ['访谈', '采访', '巴黎评论', '中文版', '收录']):
        return None
    
    # 模式 1：X 被《巴黎评论》访谈过/采访过
    m = re.search(r'(.+?)被(《巴黎评论》|巴黎评论|收录|访谈|采访)', q)
    if m:
        return {'cmd': 'interview-status', 'name': m.group(1).strip()}
    # 模式 2：X 访谈过没有/被访谈过没有
    m = re.search(r'(.+?)(被|访谈)过(没|了)', q)
    if m:
        return {'cmd': 'interview-status', 'name': m.group(1).strip()}
    # 模式 3：X 有没有中文版
    m = re.search(r'(.+?)有没有(中文版|被访谈|被收录)', q)
    if m:
        return {'cmd': 'interview-status', 'name': m.group(1).strip()}
    # 模式 4：查一下/查 X 的访谈状态
    m = re.search(r'(?:查一下|查|看看)\s*(.+?)的?(?:访谈状态|被访谈|被收录|访谈过)', q)
    if m:
        return {'cmd': 'interview-status', 'name': m.group(1).strip()}
    # 模式 5：X 被访谈过吗
    m = re.search(r'(.+?)被访谈过(吗|没|了)', q)
    if m:
        return {'cmd': 'interview-status', 'name': m.group(1).strip()}
    # 模式 6：《巴黎评论》访谈过 X 吗
    m = re.search(r'(《巴黎评论》|巴黎评论|该采访|访谈)过(.{2,20})吗', q)
    if m:
        return {'cmd': 'interview-status', 'name': m.group(2).strip()}
    # 退路：去掉所有修饰词
    name = re.sub(r'[？?吗。]', '', q)
    for kw in ['访谈状态', '被访谈过', '访谈过', '有没有中文版', '有没有', '查一下', '查', '看看', '被', '《巴黎评论》', '巴黎评论', '访谈']:
        name = name.replace(kw, '')
    name = name.strip()
    if name:
        return {'cmd': 'interview-status', 'name': name}
    
    return None


def _detect_stats(q: str) -> dict | None:
    """检测统计查询"""
    if any(kw in q for kw in ['统计', '多少作家', '总共有', '数据概况', '多少边', '多少节点']):
        return {'cmd': 'stats'}
    return None


def detect_command(question: str) -> dict:
    """根据自然语言提问检测要执行的命令和参数。

    检测顺序重要性（v2.1.3）：
    - path 必须先于 edge（"A 和 B 之间隔着谁" 应是路径，不是双边关系）
    - cross-query 必须先于 leaderboard（"未被访谈但被提及最多" 应是交叉查询，不是泛排行榜）
    """
    q = question.strip()

    for detector in [_detect_path, _detect_cross_query,
                     _detect_leaderboard, _detect_edge, _detect_list_communities,
                     _detect_community, _detect_story_path, _detect_author,
                     _detect_interview_status, _detect_stats]:
        result = detector(q)
        if result is not None:
            return result

    # 默认：搜索作家
    return {'cmd': 'search', 'name': q.strip('？?吗 ')}


# ============================================================
# 结果格式化
# ============================================================

def format_result(cmd: str, result: dict) -> str:
    """把 JSON 结果转换为人类可读的中文回答。"""
    
    if not result.get('ok', True) and result.get('error'):
        return f"❌ 查询失败：{result.get('error', '未知错误')}\n\n{result.get('hint', '')}"
    
    if cmd == 'stats':
        stats = result.get('stats', result)
        return f"""📊 巴黎评论作家关系网统计

- 总作家数：{stats.get('nodes', 'N/A')} 位
- 总关系边数：{stats.get('links', 'N/A')} 条
- 访谈目录收录：{stats.get('catalog_records', 'N/A')} 位
- 中文版已收录：{stats.get('authors_with_chinese_interview', 'N/A')} 位"""
    
    elif cmd == 'search':
        # API 的 interview-status 返回既包含图谱也包含访谈信息，用于搜索展示
        node = result.get('node')
        catalog_info = result.get('catalog_info')
        
        if node:
            return f"""🔍 搜索结果：找到「{result['resolved_name']}」

- 身份：{node.get('group', 'N/A')}
- 总连接数：{node.get('degree', 0)}
- 社群：#{node.get('community_id', 0)}（排名 {node.get('community_rank', 'N/A')}）
- 艺术分类：{node.get('art_category_label', '未分类')}"""
        elif catalog_info:
            cn_name = catalog_info.get('name_zh') or catalog_info.get('name_en')
            parts = []
            if catalog_info.get('series'):
                parts.append(f"系列：{catalog_info.get('series')}")
            if catalog_info.get('number'):
                parts.append(f"编号：{catalog_info.get('number')}")
            if catalog_info.get('issue_season_year'):
                issue_label = f"期号：{catalog_info.get('issue_season_year')}"
                if catalog_info.get('issue_number'):
                    issue_label += f"（第 {catalog_info.get('issue_number')} 期）"
                parts.append(issue_label)
            elif catalog_info.get('year'):
                parts.append(f"年份：{catalog_info.get('year')}")
            url = catalog_info.get('url')
            bullets = "\n".join(f"- {p}" for p in parts) if parts else "- 年份：N/A"
            link_line = f"\n- 🔗 原文：{url}" if url else ""
            return f"""📚 搜索结果：不在图谱中，但在访谈目录中找到「{cn_name}」

{bullets}{link_line}"""
        else:
            return f"❌ 未找到「{result.get('query', result.get('resolved_name', ''))}」\n\n该作家既不在关系图谱中，也不在《巴黎评论》访谈目录里。"
    
    elif cmd == 'interview-status':
        has_cn = result.get('has_chinese_interview', False)
        node = result.get('node')
        catalog_info = result.get('catalog_info')
        interview_count = result.get('interview_count', 0)
        all_interviews = result.get('all_interviews', [])
        
        lines = [f"「{result['resolved_name']}」访谈状态"]
        lines.append("")
        
        if has_cn:
            # 原刊信息优先取 catalog_info（顶层目录记录），其次取 node.interview
            ci = catalog_info or {}
            if not ci.get('series') and node and isinstance(node.get('interview'), dict):
                ci = node.get('interview') or ci
            series = ci.get('series')
            number = ci.get('number')
            issue_season_year = ci.get('issue_season_year')
            issue_number = ci.get('issue_number')
            cat_url = ci.get('url')

            if interview_count > 1:
                lines.append(f"✅ 已收录中文版（共 {interview_count} 篇）：")
            else:
                lines.append(f"✅ 已收录中文版：《{result.get('chinese_book', 'N/A')}》")

            # 原刊信息行（series + number + 期号）— 补 issue 内容
            if series or number:
                parts = []
                if series:
                    parts.append(f"系列：{series}")
                if number:
                    parts.append(f"编号：{number}")
                if issue_season_year:
                    parts.append(f"期号：{issue_season_year}（第 {issue_number} 期）" if issue_number else f"期号：{issue_season_year}")
                lines.append(f"   🏷  原刊：{' · '.join(parts)}")
                if cat_url:
                    lines.append(f"   🔗 原文：{cat_url}")

            if all_interviews:
                for i, iv in enumerate(all_interviews):
                    book = iv.get('book', 'N/A')
                    translator = iv.get('translator', 'N/A')
                    interviewer = iv.get('interviewer', 'N/A')
                    year = iv.get('year', 'N/A')
                    if interview_count > 1:
                        lines.append(f"   [{i+1}] 《{book}》— 译者：{translator}，采访者：{interviewer}，年份：{year}")
                    else:
                        lines.append(f"   译者：{translator}")
                        lines.append(f"   采访者：{interviewer}")
                        lines.append(f"   年份：{year}")
            else:
                lines.append(f"   译者：{result.get('translator', 'N/A')}")
                lines.append(f"   采访者：{result.get('interviewer', 'N/A')}")
                lines.append(f"   年份：{result.get('year', 'N/A')}")
        elif catalog_info:
            lines.append("✅ 被《巴黎评论》访谈过（英文版）")
            lines.append(f"   期号：{catalog_info.get('number', 'N/A')}")
            lines.append(f"   系列：{catalog_info.get('series', 'N/A')}")
            lines.append(f"   年份：{catalog_info.get('year', 'N/A')}")
            url = catalog_info.get('url', '')
            if url:
                lines.append(f"   链接：[The Paris Review 访谈原文]({url})")
            else:
                lines.append("   链接：N/A")
            if not has_cn:
                lines.append("")
                lines.append("   📕 尚未出版中文版")
        else:
            lines.append("❌ 未被《巴黎评论》访谈过")
        
        if node:
            lines.append("")
            lines.append(f"📍 在关系图谱中：是（{node.get('degree', 0)} 条连接）")
        
        return "\n".join(lines)
    
    elif cmd == 'author':
        if not result.get('found', result.get('found_in_network')):
            return f"未找到「{result.get('query', '')}」"
        
        node = result.get('node', {})
        resolved = result.get('resolved_name', node.get('id', ''))
        in_edges = result.get('in_edges', [])
        out_edges = result.get('out_edges', [])
        in_count = len(in_edges)
        out_count = len(out_edges)
        
        lines = [resolved]
        lines.append(f"被 {in_count} 位作家提及，自己提及了 {out_count} 位作家。")
        lines.append("")
        
        if in_edges:
            pos = [e.get('source', '') for e in in_edges if e.get('type') == 'positive']
            neg = [e.get('source', '') for e in in_edges if e.get('type') == 'negative']
            neu = [e.get('source', '') for e in in_edges if e.get('type') == 'neutral']
            if pos:
                lines.append(f"正面评价来自：{'、'.join(pos[:5])}{'…' if len(pos) > 5 else ''}")
            if neg:
                lines.append(f"负面评价来自：{'、'.join(neg[:5])}{'…' if len(neg) > 5 else ''}")
            if not pos and not neg:
                lines.append(f"提及者包括：{'、'.join([e.get('source', '') for e in in_edges[:5]])}")
        
        if out_edges:
            lines.append("")
            out_pos = [e.get('target', '') for e in out_edges if e.get('type') == 'positive']
            out_neg = [e.get('target', '') for e in out_edges if e.get('type') == 'negative']
            if out_pos:
                lines.append(f"他正面评价了：{'、'.join(out_pos[:5])}{'…' if len(out_pos) > 5 else ''}")
            if out_neg:
                lines.append(f"他负面评价了：{'、'.join(out_neg[:5])}{'…' if len(out_neg) > 5 else ''}")
        
        return "\n".join(lines)
    
    elif cmd == 'leaderboard':
        entries = result.get('entries', result.get('leaderboard', []))
        sort_by = result.get('sort_by', 'degree')
        
        sort_names = {
            'degree': '总连接数', 'inDegree': '被提及数', 'outDegree': '提及他人数',
            'pageRank': '影响力', 'betweenness': '中介中心性',
            'positiveIn': '正面评价数', 'negativeIn': '负面评价数', 'influenceIn': '影响关系数'
        }
        
        lines = [f"作家排行榜 — 按{sort_names.get(sort_by, sort_by)}排序"]
        lines.append("")
        
        for item in entries:
            rank = item.get('rank', '')
            wid = item.get('id', 'N/A')
            primary = item.get('degree', item.get('inDegree', 0))
            lines.append(f"  {rank}. {wid} — {primary}")
        
        return "\n".join(lines)
    
    elif cmd == 'edge':
        if not result.get('has_direct_edge'):
            found = result.get('found_in_network', [False, False])
            msg = f"「{result['resolved_names'][0]}」和「{result['resolved_names'][1]}」之间没有直接联系"
            if not all(found):
                msg += "\n（其中一位作家不在图谱中）"
            return msg
        
        lines = [f"「{result['resolved_names'][0]}」与「{result['resolved_names'][1]}」的关系"]
        lines.append(f"共 {result['edge_count']} 条直接关系")
        lines.append("")
        
        type_map = {'positive': '正面评价', 'negative': '负面评价', 'neutral': '中性提及'}
        edges = result.get('edges', [])
        for e in edges:
            type_label = type_map.get(e.get('type', ''), e.get('type', ''))
            infl_label = '（影响关系）' if e.get('influence') else ''
            lines.append(f"{e.get('source', '')} 对 {e.get('target', '')} — {type_label}{infl_label}")
            if e.get('reason'):
                reason = e['reason']
                parts = reason.split(' | ') if ' | ' in reason else [reason]
                for part in parts:
                    if '受访者对该作家表达正面评价' not in part and '受访者对该作家表达负面评价' not in part:
                        lines.append(f"   原文：「{part}」")
        
        if result.get('reverse_edge_count', 0) > 0:
            lines.append("")
            lines.append(f"反向（{result['resolved_names'][1]} → {result['resolved_names'][0]}）：{result['reverse_edge_count']} 条")
            for e in result.get('reverse_edges', []):
                type_label = type_map.get(e.get('type', ''), e.get('type', ''))
                lines.append(f"{e.get('source', '')} 对 {e.get('target', '')} — {type_label}")
                if e.get('reason'):
                    lines.append(f"   原文：「{e['reason']}」")
        
        return "\n".join(lines)
    
    elif cmd == 'community':
        if not result.get('found', result.get('ok', True)):
            return f"未找到社群 #{result.get('community_id', '')}"
        
        members = result.get('members', [])
        name = result.get('community_name', '')
        header = f"社群「{name}」（#{result.get('community_id', '')}，共 {result.get('member_count', len(members))} 位成员）"
        lines = [header, ""]
        
        for m in members[:15]:
            lines.append(f"  {m.get('id', 'N/A')} — {m.get('degree', 0)} 条连接")
        
        if len(members) > 15:
            lines.append(f"  …还有 {len(members) - 15} 位")
        
        return "\n".join(lines)
    
    elif cmd == 'shortest-path':
        if not result.get('has_path'):
            names = result.get('resolved_names', ['', ''])
            msg = f"「{names[0]}」和「{names[1]}」之间不存在连通路径"
            found = result.get('found_in_network', [True, True])
            if not all(found):
                msg += "\n（其中一位作家不在图谱中）"
            return msg
        
        path = result.get('path', [])
        length = result.get('path_length', 0)
        lines = [f"「{path[0]}」到「{path[-1]}」的最短路径（{length} 步）"]
        lines.append("")
        lines.append("  " + " → ".join(path))
        lines.append("")
        
        edges = result.get('edges', [])
        if edges:
            type_map = {'positive': '正面', 'negative': '负面', 'neutral': '中性'}
            for e in edges:
                direction = e.get('direction', 'forward')
                if direction == 'forward':
                    pair = f"{e.get('source', '')} → {e.get('target', '')}"
                else:
                    pair = f"{e.get('target', '')} → {e.get('source', '')}"
                type_label = type_map.get(e.get('type', ''), e.get('type', ''))
                lines.append(f"  {pair} ({type_label})")
        
        return "\n".join(lines)
    
    elif cmd == 'cross-query':
        entries = result.get('entries', [])
        qtype = result.get('type', '')
        type_names = {
            'uninterviewed_most_mentioned': '被提及最多但从未被《巴黎评论》访谈的作家',
            'interviewed_but_isolated': '被访谈过但在图谱中连接很少的作家',
            'cross_community_bridges': '跨社群桥接作家',
            'positive_vs_negative': '正负评价反差最大的作家',
        }
        lines = [type_names.get(qtype, qtype)]
        lines.append("")
        
        for item in entries:
            rank = item.get('rank', '')
            wid = item.get('id', 'N/A')
            if qtype == 'uninterviewed_most_mentioned':
                lines.append(f"  {rank}. {wid} — 被提及 {item.get('inDegree', 0)} 次")
            elif qtype == 'positive_vs_negative':
                pos = item.get('positiveIn', 0)
                neg = item.get('negativeIn', 0)
                lines.append(f"  {rank}. {wid} — 正面 {pos} / 负面 {neg}（净值 {'+' if item.get('net', 0) >= 0 else ''}{item.get('net', 0)}）")
            elif qtype == 'cross_community_bridges':
                lines.append(f"  {rank}. {wid} — 跨 {item.get('cross_community_count', 0)} 个社群，提及 {item.get('outDegree', 0)} 人")
            else:
                lines.append(f"  {rank}. {wid} — {item.get('degree', 0)} 条连接")
        
        return "\n".join(lines)
    
    elif cmd == 'list-communities':
        communities = result.get('communities', [])
        total = result.get('total_communities', len(communities))
        lines = [f"共 {total} 个社群"]
        lines.append("")
        
        for c in communities:
            name = c.get('community_name', '') or f"社群#{c.get('community_id', '')}"
            lines.append(f"  {name} — {c.get('member_count', 0)} 位成员")
        
        return "\n".join(lines)
    
    elif cmd == 'story-path_list':
        # 需要调 API 获取路径列表——但 API 不提供列表接口
        # 用 story-path key=0 作为兜底展示
        lines = ["📚 故事路径查询"]
        lines.append("")
        lines.append("可用关键词：拉美、女性、现代主义、美国、诗歌、四种、立场、美学")
        lines.append("使用方式：查询「第 0 条路径」或「拉美路径」")
        return "\n".join(lines)
    
    elif cmd == 'story-path':
        if not result.get('found', result.get('ok', True)):
            return "❌ 未找到该路径"
        
        path = result.get('path', result)
        lines = [f"📖 {path.get('title', '未命名')}"]
        lines.append(f"   涉及 {path.get('node_count', len(path.get('nodes', [])))} 位作家，{path.get('edge_count', len(path.get('edges', [])))} 条关系")
        lines.append("")
        lines.append("👤 涉及作家：")
        lines.append("   " + "、".join(path.get('nodes', [])))
        
        edges = path.get('edges', [])
        if edges:
            lines.append("")
            lines.append("🔗 关键关系：")
            for e in edges[:5]:
                type_label = {'positive': '👍', 'negative': '👎', 'neutral': '⚪'}.get(e.get('type', ''), '')
                lines.append(f"   {type_label} {e.get('source', 'N/A')} → {e.get('target', 'N/A')}")
        
        return "\n".join(lines)
    
    return json.dumps(result, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description='巴黎评论员 - 自然语言接口（API 模式）')
    parser.add_argument('question', nargs='*', help='自然语言提问')
    parser.add_argument('--raw', action='store_true', help='输出原始 JSON')
    parser.add_argument('--check-update', action='store_true', help='检查是否有新版本')
    parser.add_argument('--version', action='store_true', help='查看 API 版本')
    args = parser.parse_args()
    
    if args.version:
        result = get_version()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    
    # 检查更新模式
    if args.check_update:
        from check_update import check_update
        result = check_update()
        if result.get('has_update'):
            print(result['message'])
            sys.exit(1)
        else:
            if result.get('local') and result.get('remote'):
                print(f"✅ 已是最新版本：{result['local']}")
            else:
                print("ℹ️  无版本信息")
            sys.exit(0)
    
    question = ' '.join(args.question)
    
    # 检测命令
    cmd_info = detect_command(question)
    cmd = cmd_info.pop('cmd')
    
    # 执行命令 — 调用 API
    if cmd == '_author_first_then_community':
        # 先查作家获取 community_id，再查社群
        author_result = get_interview_status(cmd_info['question'])
        node = author_result.get('node')
        if node:
            comm_id = node.get('community_id')
            if comm_id is not None:
                result = get_community(comm_id)
                result['query_author'] = node.get('id')
            else:
                result = {'ok': False, 'error': '该作家没有社群信息'}
        else:
            result = {'ok': False, 'error': '未找到该作家'}
    elif cmd == 'stats':
        result = get_stats()
    elif cmd == 'search':
        result = get_interview_status(cmd_info['name'])
    elif cmd == 'interview-status':
        result = get_interview_status(cmd_info['name'])
    elif cmd == 'author':
        result = query_author(cmd_info['name'], cmd_info.get('limit', 20))
    elif cmd == 'leaderboard':
        result = get_leaderboard(cmd_info['sort_by'], cmd_info['top'])
    elif cmd == 'edge':
        result = query_edge(cmd_info['name1'], cmd_info['name2'])
    elif cmd == 'community':
        result = get_community(cmd_info['community_id'])
    elif cmd == 'story-path':
        result = get_story_path(cmd_info['key'])
    elif cmd == 'story-path_list':
        result = {'ok': True, 'found': False}
    elif cmd == 'shortest-path':
        result = get_shortest_path(cmd_info['name1'], cmd_info['name2'])
    elif cmd == 'cross-query':
        result = get_cross_query(cmd_info['query_type'], cmd_info['top'])
    elif cmd == 'list-communities':
        result = get_communities()
    else:
        result = {'ok': False, 'error': 'Unknown command', 'cmd': cmd}
    
    # 输出结果
    if args.raw:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(format_result(cmd, result))
        # 字段自检：interview-status 必须在输出前校验字段完整性（v2.1.3）
        if cmd == 'interview-status':
            missing = _self_check_interview_status(result)
            if missing:
                warn_lines = [
                    '',
                    '⚠️  [字段自检 v2.1.3] 以下字段缺失，建议核对：',
                    '   ' + '、'.join(missing),
                    '   这可能是 Worker 端数据缺失，请反馈给开发者。',
                ]
                print('\n'.join(warn_lines), file=sys.stderr)
        # 自动检查更新（带每日缓存）
        try:
            from check_update import auto_check_update
            update_msg = auto_check_update()
            if update_msg:
                print(update_msg)
        except Exception:
            pass


if __name__ == '__main__':
    main()