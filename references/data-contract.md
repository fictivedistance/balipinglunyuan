# Paris Network Skill V1 Data Contract

## Source

- Graph source: `projects/paris_network/v283.html`
- Extracted JS constants:
  - `GRAPH`
  - `LEADERBOARD_BUBBLES`
  - `STORY_PATHS_V1`
- Interview source: `~/.openclaw/openclaw_data/workspace/paris_review.db`, table `interviews`
- English catalog source: `projects/paris_network/catalog/paris_review_interview_catalog_v246.json`, derived from `巴黎评论_作家访谈全目录_20260114更新版.xlsx / sheet=全目录`

## Counts expected for v283 RC

- nodes: 719
- links: 2798
- leaderboard boards: 8
- story paths: 8
- interview records: 253
- catalog records: 454

## Interview status fields

`interview-status <writer>` returns:

- `found_in_network`: writer exists as v283 graph node
- `network_node`: canonical node name
- `network_sub_unit`: v283 node art-category label, e.g. 小说的艺术 / 诗歌的艺术 / 非虚构的艺术
- `catalog_matches`: matched rows from the total catalog
- `original_series`: e.g. The Art of Fiction
- `original_series_number`: e.g. No. 17
- `original_title`: e.g. Truman Capote, The Art of Fiction No. 17
- `interviewed_by_paris_review`: local interview record exists
- `interviews[]`:
  - `magazine_issue`: parsed from original note, e.g. 第十六期，一九五七年春/夏季号
  - `magazine_season_unit`: parsed seasonal issue, e.g. 一九五七年春/夏季号
  - `network_sub_unit`
  - `has_chinese`
  - `chinese_book`
  - `translator`
  - `interviewer`
  - `year`
  - `source_record_id`

## Note

The local DB alone does not store exact English series numbers, but the project catalog does. V1 joins both: Chinese book/translator from `paris_review.db`, original series number from `paris_review_interview_catalog_v246.json`.

## English-name query regression

Must pass:

- `interview-status "Jhumpa Lahiri"` → The Art of Fiction No. 262, issue 247, Spring 2024
- `interview-status "Pat Barker"` → The Art of Fiction No. 243, issue 227, Winter 2018

Bug fixed 2026-06-24: query script previously checked only catalog `by_zh`, so English inputs produced false negatives despite existing catalog rows.
