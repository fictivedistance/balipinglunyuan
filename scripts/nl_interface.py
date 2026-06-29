#!/usr/bin/env python3
"""
巴黎评论员技能 - 自然语言接口
把用户的自然语言提问映射到对应的查询命令，并把 JSON 结果转换为人类可读的回答。
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

# 导入查询模块
sys.path.insert(0, str(Path(__file__).parent))
from paris_network_query import (
    DATA, unified_search, get_interview_status, query_author,
    get_leaderboard, query_edge, get_community, get_story_path,
    normalize_name_key
)


def detect_command(question: str) -> dict:
    """根据自然语言提问检测要执行的命令和参数。"""
    q = question.strip()
    
    # === leaderboard / 排行榜 ===
    if any(kw in q for kw in ['排行榜', '排名', '最多', '最高', '前十', 'top', 'Top', '排第几']):
        sort_by = 'degree'
        top = 10
        
        if any(kw in q for kw in ['提及', '被提到', 'inDegree']):
            sort_by = 'inDegree'
        elif any(kw in q for kw in ['提到', '评价别人', 'outDegree']):
            sort_by = 'outDegree'
        elif any(kw in q for kw in ['影响力', 'pageRank', '重要']):
            sort_by = 'pageRank'
        elif any(kw in q for kw in ['桥梁', '中介', 'betweenness']):
            sort_by = 'betweenness'
        elif any(kw in q for kw in ['正面', '好评', 'positive']):
            sort_by = 'positiveIn'
        elif any(kw in q for kw in ['负面', '批评', 'negative']):
            sort_by = 'negativeIn'
        elif any(kw in q for kw in ['影响', 'influence']):
            sort_by = 'influenceIn'
        
        # 提取数字
        num_match = re.search(r'前\s*(\d+)', q) or re.search(r'top\s*(\d+)', q, re.I) or re.search(r'(\d+)\s*名', q)
        if num_match:
            top = int(num_match.group(1))
        
        return {'cmd': 'leaderboard', 'sort_by': sort_by, 'top': top}
    
    # === edge / 双边关系 ===
    # 匹配模式："A 和 B 的关系"、"A 怎么评价 B"、"A 提到过 B 吗"
    and_patterns = [
        r'(.+?)(和|与|跟|对|怎么评价|如何评价|评价|提到|看法)(.+)',
        r'(.+?)(和|与|跟)(.+?)(的关系|有联系|有关系|的联系)',
    ]
    
    for pattern in and_patterns:
        match = re.search(pattern, q)
        if match:
            name1 = match.group(1).strip()
            name2 = match.group(3).strip()
            
            # 清理后缀
            for suffix in ['的关系', '有什么关系', '有联系吗', '有关系吗', '吗', '呢', '？', '?', '怎么看', '如何看', '的看法']:
                name2 = name2.replace(suffix, '').strip()
            
            if name1 and name2 and len(name1) > 1 and len(name2) > 1:
                return {'cmd': 'edge', 'name1': name1, 'name2': name2}
    
    # === community / 社群 ===
    if any(kw in q for kw in ['社群', '社区', 'community', '同一个群', '同属', '成员']):
        # 提取数字
        id_match = re.search(r'社群\s*(\d+)', q) or re.search(r'community\s*(\d+)', q, re.I)
        if id_match:
            return {'cmd': 'community', 'community_id': int(id_match.group(1))}
        
        # 问某作家在哪个社群
        if any(kw in q for kw in ['哪个社群', '哪个社区', '在哪个群']):
            # 先找到作家名，再查他的社群
            return {'cmd': '_author_first_then_community', 'question': q}
    
    # === story-path / 故事路径 ===
    if any(kw in q for kw in ['故事路径', '故事线', '路径', '主题', 'story']):
        # 提取关键词或数字
        key_match = re.search(r'第\s*(\d+)\s*条', q) or re.search(r'(\d+)', q)
        if key_match:
            return {'cmd': 'story-path', 'key': key_match.group(1)}
        
        # 关键词匹配："拉美"、"女性"等
        keywords = ['拉美', '女性', '现代主义', '美国', '诗歌', '四种', '立场', '美学']
        for kw in keywords:
            if kw in q:
                return {'cmd': 'story-path', 'key': kw}
        
        return {'cmd': 'story-path_list'}
    
    # === author / 作家详情 ===
    if any(kw in q for kw in ['详情', '详细信息', '所有关系', '连接数', '入边', '出边']):
        # 提取作家名
        for prefix in ['查询', '查一下', '看看', '关于', '作家', '详情']:
            if prefix in q:
                name = q.replace(prefix, '').strip('吗？?的')
                if name:
                    return {'cmd': 'author', 'name': name, 'limit': 20}
    
    # === interview-status / 访谈状态 ===
    if any(kw in q for kw in ['访谈', '采访', '巴黎评论', '中文版', '收录了吗']):
        # 使用正则模式提取作家名，避免 prefix replace 错误
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
        # 最后退路：去掉所有修饰词
        name = re.sub(r'[？?吗。]', '', q)
        for kw in ['访谈状态', '被访谈过', '访谈过', '有没有中文版', '有没有', '查一下', '查', '看看', '被', '《巴黎评论》', '巴黎评论', '访谈']:
            name = name.replace(kw, '')
        name = name.strip()
        if name:
            return {'cmd': 'interview-status', 'name': name}
    
    # === stats / 统计 ===
    if any(kw in q for kw in ['统计', '多少作家', '总共有', '数据概况', '多少边', '多少节点']):
        return {'cmd': 'stats'}
    
    # === 默认：搜索作家 ===
    return {'cmd': 'search', 'name': q.strip('？?吗 ')}


def format_result(cmd: str, result: dict) -> str:
    """把 JSON 结果转换为人类可读的中文回答。"""
    
    if cmd == 'stats':
        return f"""📊 巴黎评论作家关系网统计

- 总作家数：{result['nodes']} 位
- 总关系边数：{result['links']} 条
- 访谈目录收录：{result['catalog_records']} 位
- 中文版已收录：{result['authors_with_chinese_interview']} 位"""
    
    elif cmd == 'search':
        if result.get('matched_node'):
            node = result['matched_node']
            return f"""🔍 搜索结果：找到「{node['id']}」

- 身份：{node['group']}
- 总连接数：{node.get('degree', 0)}
- 社群：#{node.get('community_id', 0)}（排名 {node.get('community_rank', 'N/A')}）
- 艺术分类：{node.get('art_category_label', '未分类')}"""
        elif result.get('catalog_record'):
            cat = result['catalog_record']
            return f"""📚 搜索结果：不在图谱中，但在访谈目录中找到「{cat.get('name_zh') or cat.get('name_en')}」

- 访谈系列：{cat.get('series', 'N/A')}
- 出版年份：{cat.get('year', 'N/A')}"""
        else:
            return f"""❌ 未找到「{result.get('search_keyword')}」

该作家既不在关系图谱中，也不在《巴黎评论》访谈目录里。"""
    
    elif cmd == 'interview-status':
        has_cn = result.get('has_chinese_interview', False)
        node = result.get('node')
        catalog_info = result.get('catalog_info') or result.get('catalog_record')
        
        lines = [f"「{result['resolved_name']}」访谈状态"]
        lines.append("")
        
        if has_cn:
            lines.append(f"✅ 已收录中文版：《{result.get('chinese_book', 'N/A')}》")
            lines.append(f"   译者：{result.get('translator', 'N/A')}")
            lines.append(f"   采访者：{result.get('interviewer', 'N/A')}")
            lines.append(f"   年份：{result.get('year', 'N/A')}")
        elif catalog_info:
            lines.append("✅ 被《巴黎评论》访谈过（英文版）")
            lines.append(f"   期号：{catalog_info.get('number', 'N/A')}")
            lines.append(f"   系列：{catalog_info.get('series', 'N/A')}")
            lines.append(f"   年份：{catalog_info.get('year', 'N/A')}")
            lines.append(f"   链接：{catalog_info.get('url', 'N/A')}")
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
        if not result.get('found_in_network'):
            return f"❌ 未找到「{result['query']}」"
        
        lines = [f"👤 {result['resolved_chinese_name']} 详情"]
        lines.append("")
        lines.append(f"- 入边（被提及）：{result['in_degree_edges_count']} 条")
        lines.append(f"- 出边（提及他人）：{result['out_degree_edges_count']} 条")
        lines.append("")
        
        if result.get('incoming_edges'):
            lines.append("📥 被谁提及（前5条）：")
            for e in result['incoming_edges'][:5]:
                type_label = {'positive': '👍正面', 'negative': '👎负面', 'neutral': '⚪中性'}.get(e['type'], e['type'])
                lines.append(f"  {e['source']} → {type_label}")
        
        if result.get('outgoing_edges'):
            lines.append("")
            lines.append("📤 提及了谁（前5条）：")
            for e in result['outgoing_edges'][:5]:
                type_label = {'positive': '👍正面', 'negative': '👎负面', 'neutral': '⚪中性'}.get(e['type'], e['type'])
                lines.append(f"  → {e['target']} ({type_label})")
        
        return "\n".join(lines)
    
    elif cmd == 'leaderboard':
        sort_names = {
            'degree': '总连接数', 'inDegree': '被提及数', 'outDegree': '提及他人数',
            'pageRank': '影响力', 'betweenness': '中介中心性',
            'positiveIn': '正面评价数', 'negativeIn': '负面评价数', 'influenceIn': '影响关系数'
        }
        
        lines = [f"🏆 作家排行榜（按 {sort_names.get(result['sort_by'], result['sort_by'])} 排序，Top {result['top_n']}）"]
        lines.append("")
        
        for item in result['leaderboard']:
            group_label = {'interviewee': '🎤受访', 'mentioned': '📝提及', 'both': '✨两者'}.get(item['group'], item['group'])
            lines.append(f"  {item['rank']}. {item['id']} — {item['degree']} 连接 {group_label} 社群#{item['community_id']}")
        
        return "\n".join(lines)
    
    elif cmd == 'edge':
        if not result['has_direct_edge']:
            found1, found2 = result['found_in_network']
            msg = f"❌ 「{result['resolved_names'][0]}」和「{result['resolved_names'][1]}」之间没有直接联系"
            if not found1 or not found2:
                msg += "\n   （其中一位作家不在图谱中）"
            return msg
        
        lines = [f"🔗 「{result['resolved_names'][0]}」和「{result['resolved_names'][1]}」的关系"]
        lines.append(f"   共 {result['edge_count']} 条直接边")
        lines.append("")
        
        for e in result['edges']:
            type_label = {'positive': '👍正面', 'negative': '👎负面', 'neutral': '⚪中性'}.get(e['type'], e['type'])
            infl_label = ' ⚡影响关系' if e.get('influence') else ''
            lines.append(f"  {e['source']} → {e['target']} ({type_label}{infl_label})")
            if e.get('reason'):
                reason = e['reason'].split(' | ')[0] if ' | ' in e['reason'] else e['reason']
                lines.append(f"    原文：{reason[:80]}{'…' if len(reason) > 80 else ''}")
        
        return "\n".join(lines)
    
    elif cmd == 'community':
        if not result['found']:
            return f"❌ 未找到社群 #{result.get('community_id')}\n\n共有 {result['total_communities']} 个社群"
        
        lines = [f"👥 社群 #{result['community_id']}（共 {result['size']} 位成员）"]
        lines.append("")
        
        for m in result['members'][:15]:  # 只显示前15个
            art_label = f" [{m['art_category']}]" if m['art_category'] else ''
            lines.append(f"  {m['id']} — {m['degree']} 连接{art_label}")
        
        if len(result['members']) > 15:
            lines.append(f"  ... 还有 {len(result['members']) - 15} 位")
        
        return "\n".join(lines)
    
    elif cmd == 'story-path_list':
        story_paths = json.loads(DATA.read_text()).get('story_paths', {}).get('paths', [])
        lines = ["📚 可用的故事路径（共 {} 条）：\n".format(len(story_paths))]
        for i, p in enumerate(story_paths):
            lines.append(f"  {i}. {p.get('title', '未命名')}")
        lines.append("\n使用方式：查询「第 0 条路径」或「拉美路径」")
        return "\n".join(lines)
    
    elif cmd == 'story-path':
        if not result['found']:
            return "❌ 未找到该路径\n\n" + "\n".join(result.get('available_paths', []))
        
        lines = [f"📖 {result['title']}"]
        lines.append(f"   涉及 {result['node_count']} 位作家，{result['edge_count']} 条关系")
        lines.append("")
        lines.append("👤 涉及作家：")
        lines.append("   " + "、".join(result['nodes']))
        
        if result.get('edges'):
            lines.append("")
            lines.append("🔗 关键关系：")
            for e in result['edges'][:5]:
                type_label = {'positive': '👍', 'negative': '👎', 'neutral': '⚪'}.get(e['type'], '')
                lines.append(f"   {type_label} {e['source']} → {e['target']}")
        
        return "\n".join(lines)
    
    return json.dumps(result, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description='巴黎评论员 - 自然语言接口')
    parser.add_argument('question', nargs='+', help='自然语言提问')
    parser.add_argument('--raw', action='store_true', help='输出原始 JSON')
    args = parser.parse_args()
    
    question = ' '.join(args.question)
    data = json.loads(DATA.read_text())
    
    # 检测命令
    cmd_info = detect_command(question)
    cmd = cmd_info.pop('cmd')
    
    # 执行命令
    if cmd == '_author_first_then_community':
        # 先查作家，再查他的社群
        author_result = unified_search(data, cmd_info['question'])
        if author_result.get('matched_node'):
            comm_id = author_result['matched_node'].get('community_id')
            result = get_community(data, comm_id)
            result['query_author'] = author_result['matched_node']['id']
        else:
            result = {'error': '未找到该作家'}
    else:
        if cmd == 'stats':
            result = data['counts']
        elif cmd == 'search':
            result = unified_search(data, cmd_info['name'])
        elif cmd == 'interview-status':
            result = get_interview_status(data, cmd_info['name'])
        elif cmd == 'author':
            result = query_author(data, cmd_info['name'], cmd_info.get('limit', 20))
        elif cmd == 'leaderboard':
            result = get_leaderboard(data, cmd_info['sort_by'], cmd_info['top'])
        elif cmd == 'edge':
            result = query_edge(data, cmd_info['name1'], cmd_info['name2'])
        elif cmd == 'community':
            result = get_community(data, cmd_info['community_id'])
        elif cmd == 'story-path':
            result = get_story_path(data, cmd_info['key'])
        elif cmd == 'story-path_list':
            result = 'list'
        else:
            result = {'error': 'Unknown command', 'cmd': cmd}
    
    # 输出结果
    if args.raw:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_result(cmd, result))


if __name__ == '__main__':
    main()
