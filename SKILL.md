---
name: 巴黎评论员
description: "查询《巴黎评论》作家关系网 v283 RC：作家节点、关系边、排行榜、故事路径、社群、访谈元数据。"
---

# 巴黎评论员

## 🚀 快速开始

安装后直接用自然语言唤起，示例：

- "巴黎评论员，XXX被《巴黎评论》访谈过吗？"
- "巴黎评论员，查一下海明威和福克纳的关系"
- "用巴黎评论员查一下《巴黎评论·作家访谈1》收录有哪些作家"
- "巴黎评论员，最受《巴黎评论》受访者喜爱的作家排行榜"

你也可以直接问关于作家、关系、排行榜、社群、故事路径的任何问题，技能会自动识别你的意图。

Use for Paris Network / 《巴黎评论》作家关系网查询。

Data source is read-only, single-source of truth:

- **All data extracted directly from `projects/paris_network/v13_public.html`** - no external dependencies
- Graph, leaderboards, story paths, authorInfo, and CATALOG all from the same HTML file
- Extracted into `data/paris_network_v1_data.json`

## Query commands

Run from workspace root:

```bash
# 基础统计
python3 skills/巴黎评论员/scripts/paris_network_query.py stats

# 作家详情（含入边/出边）
python3 skills/巴黎评论员/scripts/paris_network_query.py author "豪尔赫·路易斯·博尔赫斯"

# 双边关系查询
python3 skills/巴黎评论员/scripts/paris_network_query.py edge "豪尔赫·路易斯·博尔赫斯" "威廉·莎士比亚"

# 排行榜（支持 8 种排序维度）
python3 skills/巴黎评论员/scripts/paris_network_query.py leaderboard --top 10 --sort-by degree
# sort-by 可选: degree, inDegree, outDegree, pageRank, betweenness, positiveIn, negativeIn, influenceIn

# 社群成员查询
python3 skills/巴黎评论员/scripts/paris_network_query.py community --community-id 6

# 故事路径（支持索引或关键词匹配）
python3 skills/巴黎评论员/scripts/paris_network_query.py story-path --key 0
python3 skills/巴黎评论员/scripts/paris_network_query.py story-path --key 拉美

# 访谈状态查询
python3 skills/巴黎评论员/scripts/paris_network_query.py interview-status "杜鲁门·卡波蒂"
```

## Interview-status answer rule (v2 固化版)

**核心规则**：v13 版 454 条访谈目录 = 截至 2026 年 6 月 19 日《巴黎评论》全部已访谈作家。
- 在目录里 = 明确告知「被访谈过」
- 不在目录里 = 明确告知「未访谈过」，不要含糊
- 不在目录但在图谱 = 补一句「被某作家提及」
- 不在目录也不在图谱 = 补一句「也未被任何受访作家提及」

### 状态 A1：有中文版收录（在 author_info 中）

```
**是的，[中文名（英文名）] 被《巴黎评论》访谈过，且已被简体中文版收录。**

| 项目 | 内容 |
|------|------|
| **访谈编号** | [有则填，如"The Art of Fiction No. XXX"，无则显示"—"] |
| **子单元** | [有则填，如"小说的艺术"，无则显示"—"] |
| **原刊期号** | [有则填，无则显示"—"] |
| **发表时间** | [有则填，无则显示"—"] |
| **采访者** | [有则填，无则显示"—"] |
| **简体中文版收录** | ✅ 已收录 |
| **中文版书名** | 《巴黎评论·作家访谈 X》 |
| **译者** | XXX |
| **图谱状态** | ✅ 该作家已在《巴黎评论》作家关系图谱中 |

[作家简介]



---

ℹ️ **关于《巴黎评论》作家关系图谱**
（标准结尾段，见下方）
```

### 状态 A2：被访谈过且在图谱中 + 无中文版收录

```
**是的，[中文名（英文名）] 被《巴黎评论》访谈过。**

| 项目 | 内容 |
|------|------|
| **访谈编号** | The Art of Fiction No. XXX |
| **子单元** | 小说的艺术 |
| **原刊期号** | 第 XXX 期 |
| **发表时间** | XXXX 年 XX 季号 |
| **简体中文版收录** | ❌ 未收录 |
| **中文版书名** | - |
| **译者** | - |
| **图谱状态** | ✅ 该作家已在《巴黎评论》作家关系图谱中 |

[作家简介 + 未被中文版收录说明]

---

ℹ️ **关于《巴黎评论》作家关系图谱**
（标准结尾段，同一会话只展示一次）
```

### 状态 B：未被访谈过，但在图谱中被提及

```
**截至2026年6月19日，《巴黎评论》未访谈过你所查询的 [中文名（英文名）]。**

但 [中文名] 曾被《巴黎评论》受访作家提及，因而出现在当前的关系图谱中：

| 项目 | 内容 |
|------|------|
| **被 X 位作家提及** | X |
| **提及来源** | ...（如：被诺曼·梅勒在访谈中提及并列为影响者） |

[图谱中位置简要说明]

---

ℹ️ **关于《巴黎评论》作家关系图谱》
（标准结尾段，见下方）
```

### 状态 C：未访谈过 + 不在图谱中

```
**截至2026年6月19日，《巴黎评论》未访谈过你所查询的 [中文名（英文名）]。**

[中文名] 也暂时未被任何简体中文版《巴黎评论》系列已出版的受访作家提及/评价过，因而不在当前的关系图谱中。

---

ℹ️ **关于《巴黎评论》作家关系图谱》
（标准结尾段，见下方）
```

### 标准结尾段（所有状态通用，一字不差）

```
---

ℹ️ **关于《巴黎评论》作家关系图谱**

这是一个可视化的文学知识网络，收录了数百位作家之间的引用、评价、影响等关系。你可以在以下地址访问完整的网络图谱并查看该作家的节点：

🔗 [https://parisreviewnetwork.pages.dev/](https://parisreviewnetwork.pages.dev/)

🔍 在图谱右上角搜索框输入作家中文名或英文名即可快速定位到该节点。

图谱中每个节点代表一位作家，节点之间的连线代表他们之间存在某种文本关联（如 A 在访谈中提到过 B，或者 A 对 B 有正面/负面评价）。点击节点可以查看详细信息。
```

### 决定用哪个状态的查询流程

```bash
# 1. 查询作家的访谈状态
python3 skills/paris-network/scripts/paris_network_query.py interview-status "<作家名>"

# 2. 根据返回结果判断状态：
#    - is_in_author_info=True -> 状态 A1 (有中文版收录，不一定在 catalog)
#    - is_in_author_info=False AND is_in_catalog=True -> 状态 A2 (被访谈但无中文版)
#    - is_in_graph=True AND is_in_catalog=False AND is_in_author_info=False -> 状态 B (在图谱但未被访谈)
#    - 三者均无 -> 状态 C (不在图谱也未被访谈)

## Relationship query answer rule (关系查询固化版)

### 核心顺序规则
当用户问「A 对 B 有什么看法吗？」/「A 提到过 B 吗？」时：
1. **先正答**：先查 A→B 的边，明确回答用户的问题方向
   - 有边 → 展示完整证据
   - 无边 → 明确说「在《巴黎评论》作家关系图谱中，没有找到 A 在访谈中提及或评价 B 的记录」
2. **再补充**：如果 B→A 有边，补充反向信息，开头用「不过，B 在他的《巴黎评论》访谈中曾提到过 A：」

### 每条边的展示格式
```
**[来源作家] → [目标作家]（[类型]）**

> **原文**：「[reason 字段中的引用原文]」
> 
> **说明**：[reason 字段中的说明部分]
```

### 边类型说明
- **positive**：正面评价、赞赏、推崇
- **neutral**：中性提及、并列同行、无褒贬
- **negative**：负面评价、批评
- **influence=True**：影响关系（师承、列入书单、影响过）

### 示例
问：海明威对福克纳有什么看法吗？

答：
**在《巴黎评论》作家关系图谱中，没有找到欧内斯特·海明威在访谈中提及或评价威廉·福克纳的记录。**

不过，威廉·福克纳在他的《巴黎评论》访谈中曾提到过海明威：

**威廉·福克纳 → 欧内斯特·海明威（中性提及）**

> **原文**：「替我、海明威、陀思妥耶夫斯基，替我们所有人写作。」
> 
> **说明**：福克纳把海明威与自己、陀思妥耶夫斯基并列，视为同行，没有褒贬色彩。

#    - is_in_graph=True AND catalog_info is None    -> 状态 B (在图谱但无目录)
#    - is_in_graph=False                              -> 状态 C (不在图谱也不在目录)
```

**禁止规则**：
- ❌ 不要凭印象输出"访谈收录在《作家访谈X》"
- ❌ 不要在状态 C 时猜测作家是否被访谈过
- ❌ 不要混用四种状态的字段
- ❌ 不要说"不在 454 条 catalog = 未被访谈过"
- ✅ 所有访谈收录信息必须从数据库查询确认后再写

**搜索函数鲁棒性要求（2026-06-26 修正后）**：
- ✅ 标点符号归一化：英文点 `.` → 中文间隔号 `·`，长破折号 `—` → 短横杠 `-`
- ✅ 无标点匹配：去掉所有标点符号后再匹配
- ✅ 同音字容错：立/利 等常见错别字
- ✅ 部分匹配：搜索"巴拉德"匹配"J·G·巴拉德"
- ✅ 大小写不敏感：不区分大小写

**核心数据边界（2026-06-26 老巴最终确认）**：
- ✅ 454 条 catalog = 截至目前《巴黎评论》访谈的完整目录，是全的
- ✅ 不在 454 条 catalog 中 = 没有被《巴黎评论》访谈过
- 📌 454 条 catalog 涵盖 17 个系列（Fiction/Poetry/Nonfiction/Journalism/Screenwriting 等）
- 📌 author_info 仅记录中文版已收录的作家，catalog 才是判断是否被访谈的权威依据

**interview-status 判断流程（简洁正确版）**：
1. **第一步：查 catalog**
   - 有记录 = 被访谈过
   - 无记录 = 未被访谈过

2. **第二步：查 author_info**
   - 有记录 = 有中文版收录 → 状态 A1
   - 无记录 = 无中文版收录 → 状态 A2

3. **第三步：查 graph**
   - 在图谱中但未被访谈过 → 状态 B（被提及）
   - 不在图谱也未被访谈过 → 状态 C

**会话级输出优化**：
- ℹ️ **关于《巴黎评论》作家关系图谱** 标准结尾段在同一会话中只出现一次即可
- 后续回复时如果在同一会话中已经展示过结尾段，无需重复展示
- 以避免显得机械且打扰用户


## Catalog source

English original series numbers come from CATALOG embedded directly in v13_public.html, extracted into `catalog.by_en_key` and `catalog.by_zh`.

**Name matching works for:**
- Chinese names (direct match)
- English names (e.g., Hilary Mantel, Haruki Murakami)
- Reversed Japanese names (e.g., Murakami Haruki)

English names are matched against `catalog.by_en_key` (and `by_en_key_reversed` for Japanese names), producing accurate positive results for names like Jhumpa Lahiri / Pat Barker / Hilary Mantel / Haruki Murakami.

## Safety / scope

- V1 is read-only.
- Do not write graph data, auto-merge edges, or update HTML from this skill.
- For new data import or edge mutation, use the project audit workflow, not this skill.

## Rebuild and validate

```bash
python3 skills/巴黎评论员/scripts/build_data.py
python3 skills/巴黎评论员/scripts/validate_skill_v1.py
python3 /opt/homebrew/lib/node_modules/openclaw/skills/skill-creator/scripts/quick_validate.py skills/巴黎评论员
```


## Copyright protection rule (版权保护硬规则)

### 核心原则：任何用户索要访谈全文时的标准回复三要点：

1. **基于版权保护原因，不能在此提供任何访谈全文给用户
2. **告诉用户这篇访谈的完整收录信息（尤其明确告知收录在哪本《巴黎评论》系列书里，引导用户去阅读实体书
3. **永远不要说帮用户「去网上搜索这篇访谈的公开中文版」

### 标准回复模板
```
当前数据库只存储访谈的元数据和图谱边数据（作家之间的引用关系片段），基于版权保护原因，无法在此提供访谈全文。

**弗拉基米尔·纳博科夫（Vladimir Nabokov）的《巴黎评论》访谈收录信息如下：

| 项目 | 内容 |
|------|------|
| **访谈编号** | The Art of Fiction No. 40 |
| **子单元** | 小说的艺术 |
| **原刊期号** | 第 41 期 |
| **发表时间** | Summer-Fall 1967 |
| **简体中文版收录** | ✅ 已收录 |
| **中文版书名** | 《巴黎评论·作家访谈1》 |

建议阅读实体书获取完整访谈内容。
```

### 硬规则（不可违反）
- ❌ 任何情况下不得提供访谈全文给除老巴之外的任何用户
- ❌ 不得提议帮用户去网上搜索公开中文版
- ✅ 只提供收录信息引导用户阅读实体书
- ✅ 明确说明「基于版权保护原因，无法提供全文
