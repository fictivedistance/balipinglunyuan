# Paris Network Skill V1 Data Contract

## Source

- Data source: Paris Network public HTML → Cloudflare KV → Worker API
- No local data file in skill package (v2.0+)
- API endpoint: `https://paris-network-query-api.theparisreviewchina.workers.dev/api/query`
- Data in KV: graph, catalog_records, author_info, leaderboard, story_paths, name_map, meta
- Worker loads from KV on cold start, caches 5 min at instance level

## Counts expected for v15.2 (skill v2.1.0)

- nodes: 718
- links: 2707
- leaderboard boards: 8
- story paths: 8
- catalog records: 454
- authors with Chinese interview: 191

## Interview status fields

`interview-status <writer>` returns:

- `is_in_graph`: writer exists as graph node
- `node`: canonical node (with degree, community_id, etc.)
- `has_chinese_interview`: bool
- `interview_count`: number of Chinese interview records
- `all_interviews`: full list of Chinese interview records
- `chinese_book`: first interview's book name
- `translator`: first interview's translator
- `interviewer`: first interview's interviewer
- `year`: first interview's year
- `catalog_info`: matched catalog record (English series, issue, URL)

## English-name query regression

Must pass:

- `interview-status "Jhumpa Lahiri"` → The Art of Fiction No. 262, issue 247, Spring 2024
- `interview-status "Pat Barker"` → The Art of Fiction No. 243, issue 227, Winter 2018

Bug fixed 2026-06-24: query script previously checked only catalog `by_zh`, so English inputs produced false negatives despite existing catalog rows.

---

## v2.1.0 新增端点（2026-07-29）

- `shortest-path?name_a=X&name_b=Y` — BFS 最短路径，返回 `path` 节点列表 + `edges` 路径上每条边
- `cross-query?type=...&top=N` — 4 种交叉查询类型：
  - `uninterviewed_most_mentioned` — 被提及最多但未被访谈
  - `interviewed_but_isolated` — 被访谈但连接少
  - `cross_community_bridges` — 跨社群桥接节点
  - `positive_vs_negative` — 正负评价反差最大
- `list-communities` — 列出全部 13 个社群名 + 成员人数
