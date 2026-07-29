# 巴黎评论员

[![Latest Version](https://img.shields.io/github/v/tag/fictivedistance/balipinglunyuan?label=version&sort=semver)](https://github.com/fictivedistance/balipinglunyuan/tags)
[![Code License: AGPL-3.0-or-later](https://img.shields.io/badge/code%20license-AGPL--3.0--or--later-blue)](./LICENSE)
[![Data License: CC BY-NC-SA 4.0 + AI Restricted](https://img.shields.io/badge/data%20license-CC%20BY--NC--SA%204.0%20%2B%20AI%20Restricted-orange)](./LICENSE.data)
[![AI Training: Prohibited](https://img.shields.io/badge/AI%20training-prohibited-red)](./LICENSE.data)

> 《巴黎评论》作家关系网络查询技能

一个供AI agent使用的《巴黎评论》skill，基于简体中文版《巴黎评论》系列作家关系网络图谱创建，支持《巴黎评论》系列读者用自然语言查询访谈状态、作家关系、排行榜等。

---

## 📜 协议与使用限制

本项目采用**双协议**结构：

| 部分 | 协议 | 适用文件 |
|------|------|---------|
| **代码** | [AGPL-3.0-or-later](./LICENSE) | `scripts/`、`references/`、所有 `.py` 源文件 |
| **数据** | [CC BY-NC-SA 4.0 + AI 训练禁止条款](./LICENSE.data) | `data/` 目录下所有 JSON/CSV/结构化数据 |

**关键限制：**
- ❌ **禁止商用** — 代码与数据均禁止任何形式的商业用途
- ❌ **禁止批量训练 / 对外服务** — 数据不得用于系统性训练、微调、对第三方提供 RAG / 嵌入服务。详细豁免见 [LICENSE.data 第 2.0 条](./LICENSE.data)
- ✅ **Agent 正常使用豁免** — AI Agent 通过官方接口查询作家、访谈、关系、社群信息不在禁止范围；本技能即为该用途而设计
- ✅ **必须署名** — 必须明确标注"简体中文版《巴黎评论》系列编辑部"
- ✅ **衍生必须同样协议** — 衍生作品必须以相同协议发布

详见 [LICENSE](./LICENSE)、[LICENSE.data](./LICENSE.data) 和 [NOTICE](./NOTICE)。

---

## 关于本技能

本技能是 [**《巴黎评论》作家宇宙**](https://www.fictivedistance.com) 网站的 AI 伴随技能。

**什么是《巴黎评论》作家宇宙？**
> 一个以简体中文版《巴黎评论》系列访谈信息为原材料搭建的文学知识图谱。你可以拖动、点选、缩放、检索可视化查看 718 位作家之间的评价、影响、偏见与继承关系。
> 它是一个"能逛的"图谱。

**什么是巴黎评论员技能？**
> 本技能是同一套图谱数据的 AI 伴随查询接口。你不用打开网站、不用学会复杂检索，直接用自然语言问就可以。
> 它是一个"能问的"图谱。

**两者的关系：**
- **作家宇宙网站**负责浏览、探索、发现——适合慢慢看、随机踩点、发现新关联。
- **巴黎评论员技能**负责快速问答——适合明确查某个作家、某种关系、某个列表。
- 数据来自**同一版本**的图谱，技能通过 API 实时查询，不内嵌数据

> **v2.0 架构变更：** 技能不再内嵌 3MB 数据文件，改为通过 Cloudflare Worker API 实时查询。skill 包内零数据，无法被批量提取。支持离线缓存降级（TTL 1 小时）。

---

## 功能亮点

| 功能 | 说明 |
|------|------|
| **统计概览** | 718位作家 / 2707条关系边 / 454篇访谈基础信息收录 |
| **作家搜索** | 中英文双向匹配，支持日本人名反序查询 |
| **访谈状态** | 中文版收录状态、译者、采访者、年份完整信息 |
| **8种排行榜** | 被提及数、影响力、中介中心性、正负评价等 |
| **双边关系** | 任意两位作家之间的直接关系查询 + 原文证据 |
| **路径发现** | 两个作家之间的最短路径（中间经过谁） |
| **交叉关联** | 未被访谈但被提及最多 / 跨社群桥接 / 正负评价反差 |
| **社群浏览** | 列出全部 13 个社群名 + 成员人数 |
| **离线缓存** | API 不可达时自动降级到本地缓存（TTL 1 小时） |
| **数据保护** | skill 包零数据，所有查询走 API，无法批量提取 |

---

## 安装

> **⚠️ 重要：请按指定版本安装，不要使用 `git clone` 默认拉取 main 分支。**
> 默认拉取的是 main 分支最新代码，**不是**最新 tag。推荐明确指定 tag 版本号（如 `v2.1.0`）以避免装到老版本。
>
> **最新版本：** https://github.com/fictivedistance/balipinglunyuan/tags

### 链接即装（推荐）

把 GitHub 仓库地址发给支持「技能自动安装」的 AI Agent，例如：

```
帮我装这个技能：https://github.com/fictivedistance/balipinglunyuan
并安装到最新 tag 版本
```

Agent 会自动拉取最新 tag、安装、验证。

> 💡 **给 Agent 的补充提示**：“使用 git clone --branch <latest-tag> --depth 1”或“检出最新标签”。

### 手动安装

```bash
# ⚠️ 关键：使用 --branch 指定 tag，不要省略
git clone --branch <latest-tag> --depth 1 https://github.com/fictivedistance/balipinglunyuan.git

# 复制到 OpenClaw skills 目录
cp -r balipinglunyuan ~/.openclaw/workspace/skills/巴黎评论员

# 验证安装
python3 ~/.openclaw/workspace/skills/巴黎评论员/scripts/validate_skill_v1.py
```

### 独立使用

```bash
git clone --branch <latest-tag> --depth 1 https://github.com/fictivedistance/balipinglunyuan.git
cd balipinglunyuan
python3 scripts/nl_interface.py "海明威和福克纳有什么关系"
```

> **注意：** v2.0 起需要联网访问 API。默认 API 地址为 `https://paris-network-query-api.theparisreviewchina.workers.dev`，可通过环境变量 `PARIS_API_URL` 覆盖。API 不可达时自动降级到本地缓存。

### 下载指定 tag 的 ZIP

如果你的环境不支持 git，可以下载指定版本的 ZIP：

```
https://github.com/fictivedistance/balipinglunyuan/archive/refs/tags/<latest-tag>.zip
```

下载后解压，将文件夹重命名为 `巴黎评论员`，移动到 `~/.openclaw/workspace/skills/`。

---

## 升级

```bash
cd ~/.openclaw/workspace/skills/巴黎评论员
git checkout <latest-tag>
git fetch --tags
```

> ⚠️ 使用 `git checkout <latest-tag>` 而不是 `git pull origin main`，以免拉取到未发布版本。
>
> 从 v1.2.0 起，Skill 在主流程中会自动检查更新（每日一次），你会在使用过程中看到升级提示。
> 也可以手动检查：`python3 scripts/nl_interface.py --check-update`

详见 [INSTALL.md](./INSTALL.md)。

---

## 快速开始

安装后直接用自然语言唤起：

```
巴黎评论员，XXX被《巴黎评论》访谈过吗？

巴黎评论员，查一下海明威和福克纳的关系

用巴黎评论员查一下《巴黎评论·作家访谈1》收录有哪些作家

巴黎评论员，最受《巴黎评论》受访者喜爱的作家排行榜
```

你也可以直接问关于作家、关系、排行榜等的任何问题，技能会自动识别你的意图。

---

## 详细功能说明

### 1. 访谈状态查询
**提问示例**：
```
海明威被《巴黎评论》访谈过吗？

杜鲁门·卡波蒂访谈有没有中文版？

费兰特访谈收录在哪本《巴黎评论》里？
```

**返回信息**：
- 是否被访谈过（是/否）
- 是否有中文版（是/否）
- 中文书名、译者、采访者、年份

---

### 2. 双边关系查询
**提问示例**：
```
海明威和福克纳有什么关系？

博尔赫斯怎么评价卡夫卡？

琼·狄迪恩提到过哪些作家？
```

**返回信息**：
- 关系方向（谁提到谁）
- 关系类型（正面/负面/中性）
- 是否是影响关系
- 原文证据片段

---

### 3. 作家排行榜
**提问示例**：
```
被《巴黎评论》受访者提及最多的前10位作家是那些？

最受《巴黎评论》受访者喜爱的女性作家是谁？

《巴黎评论》受访者负面评价最多的作家是谁？
```

**支持的排序维度**：
- `degree` 总连接数
- `inDegree` 被提及数
- `outDegree` 提及他人数
- `pageRank` 影响力
- `betweenness` 中介中心性
- `positiveIn` 正面评价数
- `negativeIn` 负面评价数
- `influenceIn` 影响关系数

---

### 4. 关系路径发现
**提问示例**：
```
海明威和乔伊斯怎么联系上的？

卡夫卡到博尔赫斯隔着谁？

海明威到福克纳最短几步？
```

**返回信息**：
- 最短路径（中间经过的作家）
- 路径长度（步数）
- 路径上每一步的关系类型（正面/负面/中性）

---

### 5. 交叉关联查询
**提问示例**：
```
哪些作家被提及很多但从没被《巴黎评论》访谈过？

谁被访谈过但在图谱里几乎是孤立的？

哪些作家连接了多个不同流派社群？

哪两个作家的正负评价反差最大？
```

**支持的交叉查询类型**：
- `uninterviewed_most_mentioned` — 被提及最多但从未被访谈
- `interviewed_but_isolated` — 被访谈过但图谱连接少
- `cross_community_bridges` — 跨社群桥接节点
- `positive_vs_negative` — 正负评价反差最大

---

### 6. 社群浏览
**提问示例**：
```
所有社群有哪些？

共有多少个社群？
```

**返回信息**：所有 13 个社群的名称 + 成员人数。

---

## 命令行使用

### 自然语言接口（推荐）
```bash
python3 scripts/nl_interface.py "被提及最多的前5位作家"
python3 scripts/nl_interface.py "海明威和福克纳有什么关系"
```

### 精确命令模式
```bash
# 统计
python3 scripts/paris_network_query.py stats

# 作家详情
python3 scripts/paris_network_query.py author "海明威" --limit 10

# 访谈状态
python3 scripts/paris_network_query.py interview-status "杜鲁门·卡波蒂"

# 排行榜
python3 scripts/paris_network_query.py leaderboard --sort-by pageRank --top 10

# 双边关系
python3 scripts/paris_network_query.py edge "海明威" "福克纳"

# 最短路径发现
python3 scripts/paris_network_query.py shortest-path "海明威" "卡夫卡"

# 交叉关联查询
python3 scripts/paris_network_query.py cross-query --type uninterviewed_most_mentioned --top 10
python3 scripts/paris_network_query.py cross-query --type positive_vs_negative --top 10
python3 scripts/paris_network_query.py cross-query --type cross_community_bridges --top 10

# 社群列表
python3 scripts/paris_network_query.py list-communities

```

---

## 数据来源

所有数据提取自 **简体中文版《巴黎评论》系列** ，存储在 Cloudflare KV 中，通过 Worker API 提供查询：

- **数据版本**：v15.1（2026 年 7 月）
- **数据规模**：
 - 718 位作家节点
 - 2707 条关系边（含原文证据）
 - 454 篇《巴黎评论》官方访谈目录
 - 191 位已出版中文版的作家信息
- **API 地址**：`https://paris-network-query-api.theparisreviewchina.workers.dev`
- **限流**：每 IP 每分钟 30 次请求
- **离线缓存**：API 不可达时降级到本地缓存（`~/.cache/巴黎评论员/`，TTL 1 小时）

---

## 验证说明

本技能包含完整的验证脚本，确保与网页端行为一致：

```bash
python3 scripts/validate_skill_v1.py
```

验证项：
- API 连通性 + 版本检查
- 统计数据一致性
- 中英文双向映射（390 en→zh / 390 zh→en）
- 日本人名反序支持（Murakami Haruki → 村上春树）
- 目录回退机制（图谱中没有但访谈目录中有的作家也能找到）
- 访谈状态判断逻辑固化
- 排行榜查询（含 degree 动态排序）
- 社群查询、故事路径
- 最短路径发现（BFS）
- 交叉关联查询（3 种类型）
- 社群列表
- 离线缓存验证

---

## 目录结构

```
巴黎评论员/
├── README.md # 本文档（发布说明）
├── SKILL.md # OpenClaw 技能文档
├── scripts/
│ ├── paris_network_query.py # API 客户端（8个查询命令）
│ ├── nl_interface.py # 自然语言接口
│ ├── check_update.py # 版本检查（API + git tags）
│ └── validate_skill_v1.py # API 集成验证脚本
└── references/ # 参考资料
```

---

## 更新日志

### v2.1.0 (2026-07-29)
- **新增关系路径发现**：BFS 最短路径查询
- **新增交叉关联查询**：4 种类型（未被访谈但被提及最多 / 被访谈但孤立 / 跨社群桥接 / 正负评价反差）
- **新增社群列表**：列出全部 13 个社群名 + 成员人数
- **输出叙事化改造**：
 - 去掉 emoji 图谱术语（👍/👎/⚪ → 正面/负面/中性）
 - "入边/出边" → "被 X 位作家提及，提及了 Y 位作家"
 - 排行榜去掉"社群#"等噪音
 - 边查询证据去掉分类标签噪音，用「」引用原文
 - 重复访谈（同一篇收录在不同文集）标注说明
 - 人名标点空格归一化（"乔治 · 普林顿" → "乔治·普林顿"）
- **新增 3 个 API 端点**：`shortest-path` / `cross-query` / `list-communities`
- **意图识别扩展**：路径 / 交叉查询 / 社群列表三类自然语言提问自动识别
- 验证脚本扩展到 69 项

### v2.0.0 (2026-07-29)
- **架构变更：本地数据模式 → API 查询模式**
- 不再内嵌 3MB 数据文件，所有查询通过 Cloudflare Worker API 实时获取
- 新增离线缓存降级机制（TTL 1 小时，缓存在 `~/.cache/巴黎评论员/`）
- 数据保护：skill 包零数据，防止批量提取
- `paris_network_query.py` 重写为 API 客户端
- `nl_interface.py` 改为调用 API 客户端
- `validate_skill_v1.py` 重写为 API 集成测试（24 项）
- `check_update.py` 改为检查 API 版本 + git tags
- 删除 `data/paris_network_v1_data.json`（3MB）和 `scripts/build_data.py`
- API 限流：每 IP 每分钟 30 次
- API 端点：8 个查询接口（stats / interview-status / author / edge / leaderboard / community / story-path / version）

### v1.3.0 (2026-07-03)
- 重构 `detect_command`：拆分为独立函数，提升可维护性
- 修复作家详情查询名字提取 bug（"查一下博尔赫斯的详情" 现在能正确提取"博尔赫斯"）
- 修复 edge 查询正则贪婪匹配（"海明威对福克纳的评价" 不再把"的评价"残留）
- interview-status 支持展示全部中文版访谈（多篇时逐条列出）
- edge 查询的 reason 字段完整展示（不再截断，多段证据逐条展示）
- leaderboard 扩展关键词匹配（"最伟大""最牛""最受欢迎""喜爱""讨厌"等）
- story-path 关键词改为动态匹配（从数据标题提取，不再硬编码）
- 修复 README License badge（Apache-2.0 → MIT）
- 修复 SKILL.md 里旧路径引用（paris-network → 巴黎评论员）
- 修复 build_data.py 绝对路径泄露问题
- INSTALL.md 去硬编码版本号 + 清理重复段落
- 更新 data-contract.md 过时路径
- skill.yaml 版本号同步更新
- 清理死代码（return 后的 break）

### v1.2.2 (2026-06-30)
- 访谈状态查询中的作家链接改为 Markdown 格式，飞书/webchat 端可点击跳转原文

### v1.2.1 (2026-06-30)
- 安装说明加入指定 tag 版本号指引，避免装到老版本
- 新增多种安装方式（手动 git、指定 tag ZIP）

### v1.2.0 (2026-06-29)
- 主流程集成自动版本检查（每日缓存）
- 有更新时会在使用中看到升级提示

### v1.1.0 (2026-06-29)
- 新增手动版本检查功能（`--check-update`）
- 远程 tag 排序修复（按版本号比较）

### v1.0 (2026-06-29)
- 首个公开发布版本
- 8个核心查询命令
- 自然语言意图识别
- 中文自然语言输出格式化
- 与前端100% 对齐
- 完整的验证套件

---

## 版权说明

《巴黎评论》访谈内容版权归《巴黎评论》杂志和简体中文版《巴黎评论》系列编辑部所有。本技能仅用于研究和学习目的，禁止商用。

详细使用限制请见 [DATA_LICENSE](./DATA_LICENSE)。

---

## 贡献

欢迎提交 Issue 和 Pull Request 改进本技能。

联系我们：小红书@巴黎评论Paris Review，豆瓣@巴黎评论编辑部，微博@巴黎评论ParisReview

联系邮箱：<fictivedistance@agent.qq.com>

---

**发布日期**：2026-07-29 (v2.1.0)

**数据版本**：v15.1（截至 2026 年 7 月）
