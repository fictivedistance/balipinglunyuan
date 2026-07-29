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
    api_get
)


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
            name2 = name2.lstrip('的').strip()
            if name1 and name2 and len(name1) > 1 and len(name2) > 1:
                return (name1, name2)
    
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
    """根据自然语言提问检测要执行的命令和参数。"""
    q = question.strip()
    
    for detector in [_detect_leaderboard, _detect_edge, _detect_community,
                     _detect_story_path, _detect_author, _detect_interview_status,
                     _detect_stats]:
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
            return f"""📚 搜索结果：不在图谱中，但在访谈目录中找到「{catalog_info.get('name_zh') or catalog_info.get('name_en')}」

- 访谈系列：{catalog_info.get('series', 'N/A')}
- 出版年份：{catalog_info.get('year', 'N/A')}"""
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
            if interview_count > 1:
                lines.append(f"✅ 已收录中文版（共 {interview_count} 篇）：")
            else:
                lines.append(f"✅ 已收录中文版：《{result.get('chinese_book', 'N/A')}》")
            
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
            return f"❌ 未找到「{result.get('query', '')}」"
        
        node = result.get('node', {})
        resolved = result.get('resolved_name', node.get('id', ''))
        in_count = result.get('in_degree_edges_count', len(result.get('in_edges', [])))
        out_count = result.get('out_degree_edges_count', len(result.get('out_edges', [])))
        
        lines = [f"👤 {resolved} 详情"]
        lines.append("")
        lines.append(f"- 入边（被提及）：{in_count} 条")
        lines.append(f"- 出边（提及他人）：{out_count} 条")
        lines.append("")
        
        in_edges = result.get('in_edges', [])
        out_edges = result.get('out_edges', [])
        
        if in_edges:
            lines.append("📥 被谁提及（前5条）：")
            for e in in_edges[:5]:
                type_label = {'positive': '👍正面', 'negative': '👎负面', 'neutral': '⚪中性'}.get(e.get('type', ''), e.get('type', ''))
                infl_label = ' ⚡影响' if e.get('influence') else ''
                lines.append(f"  {e.get('source', 'N/A')} → {type_label}{infl_label}")
        
        if out_edges:
            lines.append("")
            lines.append("📤 提及了谁（前5条）：")
            for e in out_edges[:5]:
                type_label = {'positive': '👍正面', 'negative': '👎负面', 'neutral': '⚪中性'}.get(e.get('type', ''), e.get('type', ''))
                infl_label = ' ⚡影响' if e.get('influence') else ''
                lines.append(f"  → {e.get('target', 'N/A')} ({type_label}{infl_label})")
        
        return "\n".join(lines)
    
    elif cmd == 'leaderboard':
        entries = result.get('entries', result.get('leaderboard', []))
        sort_by = result.get('sort_by', 'degree')
        
        sort_names = {
            'degree': '总连接数', 'inDegree': '被提及数', 'outDegree': '提及他人数',
            'pageRank': '影响力', 'betweenness': '中介中心性',
            'positiveIn': '正面评价数', 'negativeIn': '负面评价数', 'influenceIn': '影响关系数'
        }
        
        lines = [f"🏆 作家排行榜（按 {sort_names.get(sort_by, sort_by)} 排序）"]
        lines.append("")
        
        for item in entries:
            rank = item.get('rank', '')
            wid = item.get('id', 'N/A')
            deg = item.get('degree', 0)
            group_label = {'interviewee': '🎤受访', 'mentioned': '📝提及', 'both': '✨两者'}.get(item.get('group', ''), item.get('group', ''))
            comm = item.get('community_id', '')
            lines.append(f"  {rank}. {wid} — {deg} 连接 {group_label} 社群#{comm}")
        
        return "\n".join(lines)
    
    elif cmd == 'edge':
        if not result.get('has_direct_edge'):
            found = result.get('found_in_network', [False, False])
            msg = f"❌ 「{result['resolved_names'][0]}」和「{result['resolved_names'][1]}」之间没有直接联系"
            if not all(found):
                msg += "\n   （其中一位作家不在图谱中）"
            return msg
        
        lines = [f"🔗 「{result['resolved_names'][0]}」和「{result['resolved_names'][1]}」的关系"]
        lines.append(f"   共 {result['edge_count']} 条直接边")
        lines.append("")
        
        edges = result.get('edges', [])
        for e in edges:
            type_label = {'positive': '👍正面', 'negative': '👎负面', 'neutral': '⚪中性'}.get(e.get('type', ''), e.get('type', ''))
            infl_label = ' ⚡影响关系' if e.get('influence') else ''
            lines.append(f"  {e.get('source', 'N/A')} → {e.get('target', 'N/A')} ({type_label}{infl_label})")
            if e.get('reason'):
                reason = e['reason']
                if ' | ' in reason:
                    parts = reason.split(' | ')
                    for i, part in enumerate(parts):
                        lines.append(f"    证据{i+1}：{part}")
                else:
                    lines.append(f"    原文：{reason}")
        
        # 反向边
        if result.get('reverse_edge_count', 0) > 0:
            lines.append("")
            lines.append(f"   反向边（{result['resolved_names'][1]} → {result['resolved_names'][0]}）：{result['reverse_edge_count']} 条")
            for e in result.get('reverse_edges', []):
                type_label = {'positive': '👍正面', 'negative': '👎负面', 'neutral': '⚪中性'}.get(e.get('type', ''), e.get('type', ''))
                lines.append(f"  {e.get('source', 'N/A')} → {e.get('target', 'N/A')} ({type_label})")
                if e.get('reason'):
                    lines.append(f"    原文：{e['reason']}")
        
        return "\n".join(lines)
    
    elif cmd == 'community':
        if not result.get('found', result.get('ok', True)):
            return f"❌ 未找到社群 #{result.get('community_id', '')}\n\n共有 {result.get('total_communities', '?')} 个社群"
        
        members = result.get('members', [])
        lines = [f"👥 社群 #{result.get('community_id', '')}（共 {result.get('member_count', len(members))} 位成员）"]
        if result.get('community_name'):
            lines[0] += f" — {result['community_name']}"
        lines.append("")
        
        for m in members[:15]:
            art_label = f" [{m.get('art_category', '')}]" if m.get('art_category') else ''
            lines.append(f"  {m.get('id', 'N/A')} — {m.get('degree', 0)} 连接{art_label}")
        
        if len(members) > 15:
            lines.append(f"  ... 还有 {len(members) - 15} 位")
        
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
    else:
        result = {'ok': False, 'error': 'Unknown command', 'cmd': cmd}
    
    # 输出结果
    if args.raw:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(format_result(cmd, result))
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