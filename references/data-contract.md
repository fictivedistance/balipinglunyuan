# Paris Network Skill V1 Data Contract

## Source

- Data source: Paris Network public HTML → Cloudflare KV → Worker API
- No local data file in skill package (v2.0+)
- API endpoint: `https://paris-network-query-api.theparisreviewchina.workers.dev/api/query`
- Data in KV: graph, catalog_records, author_info, leaderboard, story_paths, name_map, meta
- Worker loads from KV on cold start, caches 5 min at instance level

## Counts expected for v15.1 (skill v1.4.0)

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
