## v2.2.2 (2026-08-11)

### Bug 修复：Worker API 国内不可达

**问题：** Worker API 默认地址 `*.workers.dev` 在国内被墙，DNS 可解析但 TCP 连接超时，导致所有查询失败。

**修复：**
- 绑定自定义域 `api2.fictivedistance.com`（Cloudflare proxied）
- 脚本默认 API_BASE 改为 `https://api2.fictivedistance.com`
- `workers_dev = true` 保留（海外/代理兜底）

**改动文件：** `paris_network_query.py` / `README.md` / `data-contract.md` / `skill.yaml`

**验证：** 69/69 通过；国内直连 1.7s 返回 HTTP 200

---

## v2.2.1 (2026-08-10)

### Bug 修复：nl_interface 意图识别与输出格式（4 项）

**触发来源：** v2.2.0 跨 agent 评估发现 v2.1.0 遗留 bug

**修复清单：**

| # | 问题 | 修复 |
|---|------|------|
| 1 | shortest-path 不认「X 到 Y 最短几步」句式，误判为 search | `_detect_path` 新增「到」分隔词 fallback；`_extract_two_names` 后缀列表补「最短路径」「最短几步」 |
| 2 | edge 查询 `has_direct_edge=False` 时直接 return，丢弃反向边 | 无正向边时检查 `reverse_edge_count`，有则格式化输出反向关系 |
| 3 | leaderboard 显示值总取 `degree` 字段，inDegree/pageRank 等排序无效 | 按 `sort_by` 动态选字段，pageRank/betweenness 保留 6 位小数 |
| 4 | 「影响力最大的前N位作家」不触发排行榜（「最大」不在触发词里） | 触发词列表补「最大」 |

---

## v2.2.0 (2026-08-10)

### 发版：v2.1.3 → v2.2.0（次版本号升级）

**理由：** v2.1.3 的字段自检 + CI 体系算"新增功能"（次版本号升级），不是单纯 bug 修复（修订号）。

**打包状态：**
- 代码：v2.1.3 同等（字段自检 + 测试集 + CI）
- 元数据：版本号、CI workflow 全部对齐 v2.2.0
- commit 历史：去除 `Co-Authored-By: Claude` trailer（GitHub Contributors 列表只保留 fictivedistance）

**备注：**
- 如果以后改 SKILL/scripts，version 号要同步改 skill.yaml（之前 v2.1.3 漏改，v2.2.0 一起补上）

---

## v2.1.3 (2026-08-10)

### 跨 agent 一致性强化 + 回归测试基础设施

**背景：** 跨 agent 评估发现同一个 skill 在 codex / claude code / openclaw 表现不同，结论是 skill 是 prompt 文本不是程序，不同 agent 行为差异无法靠 SKILL.md 文本杜绝。改为三管齐下：

1. **脚本层硬性自检** — `scripts/nl_interface.py` 新增 `_self_check_interview_status()`，interview-status 输出前校验字段完整性，缺失字段往 stderr 告警（不静默）
2. **SKILL.md 字段自检清单** — 新增 "Interview-status output field checklist (v2.1.3)" 段，列出所有必填字段 + 回落规则 + 跨 agent 处理建议
3. **回归测试集 + CI** — `tests/` 目录建好（20 条字段 case + 20 条 CLI case + README），通过 `skill.yaml` 的 `distribution.exclude` 排除发布包

**改动清单：**

| 文件 | 改动 |
|------|------|
| `scripts/nl_interface.py` | + 60 行：字段自检函数 + stderr 告警输出 |
| `SKILL.md` | + 60 行：「输出字段自检清单」段（含跨 agent 处理建议） |
| `skill.yaml` | + 18 行：`distribution.include/exclude` 配置 |
| `tests/test_field_completeness.py` | 新建：20 条字段完整性 case（10 中文 + 6 英文 + 3 未访谈 + 1 多收录） |
| `tests/test_cli_smoke.py` | 新建：20 条 CLI 命令识别 case（不调 API） |
| `tests/README.md` | 新建：跑法 + CI 接入示例 + 设计原则 |

**验证：**
- CLI 烟雾测试：20/20 通过
- 字段完整性测试（offline）：1/1 通过（fixture 覆盖海明威；其余需在线跑）
- v2.1.2 bug（奥登缺 series/number/issue/url）：脚本层自检已拦住，stderr 告警

**后续建议：**
- CI 接入后每次 PR 自动跑，避免再被字段缺失咬到
- `tests/snapshots/` 留空待人工 diff，发版前补上当前输出快照做 baseline

---

# 巴黎评论员 Skill 版本记录

> 本文件记录 Skill 自身的版本变更。
> 2026-06-25 ~ 06-26 的历史版本（v1.0/v1.1/v1.2）保留在
> `projects/paris_network/VERSIONS.md`，本文件不重复记录。
>
> **版本号规则（2026-06-29 起）：**
> - 采用 semver 三段式：`v主版本.次版本.修订号`
> - 主版本：不兼容的大改
> - 次版本：新增功能（向后兼容）
> - 修订号：bug 修复（向后兼容）

---

## v2.1.2 (2026-08-10)

### Bug 修复：访谈摘要缺编号与系列信息

**触发来源：** GitHub issue（用户反馈）

**问题：** `scripts/nl_interface.py` 的 `interview-status` 输出在 `has_chinese_interview=True` 分支完全没读 `catalog_info`，导致中文版收录的访谈只展示译者/采访者/年份，**缺：**
- 原刊编号（如 `The Art of Poetry No. 17`）
- 系列名称（如 `The Art of Poetry`）
- 原刊期号（含 `issue_season_year` 与 `issue_number`）
- 原文链接（`catalog_info.url`）

与底层 `paris_network_query.py interview-status` 相比字段不完整。

**复现：**
```bash
python3 scripts/nl_interface.py "W.H.奥登被《巴黎评论》访谈过吗"
# 改前：只输出译者/采访者/年份
# 改后：补"🏷 原刊：系列 / 编号 / 期号" + "🔗 原文" 链接
```

**修复：** `scripts/nl_interface.py`
- `cmd == 'interview-status'` 且 `has_cn=True` 分支：补原刊系列 / 编号 / 期号（含 `issue_number`） + 原文链接，数据源优先 `result.catalog_info`，缺失时回落 `node.interview`
- `cmd == 'search'` 且仅 `catalog_info` 命中但 `node` 未命中分支（同一类问题的姊妹路径）：同样补 series / number / issue_season_year / url

**附带维护改动（顺手带上）：**
- `SKILL.md` · `references/data-contract.md` · `skill.yaml`：把硬编码的 Worker API URL 抽成环境变量（`PARIS_API_BASE` 默认值见 `paris_network_query.py` 脚本顶部），v2.1.0 之后遗留未提交

**回归验证：**
- 奥登（中文收录 2 篇 · 原刊 1 次）：✅ The Art of Poetry No. 17 / Spring 1974 第 57 期
- 卡佛（中文收录 1 篇）：✅ The Art of Fiction No. 76 / Summer 1983 第 88 期
- Pat Barker（仅英文版 · 不在图谱）：✅ The Art of Fiction No. 243 / Winter 2018 第 227 期
- `validate_skill_v1.py`：69/69 通过，0 失败，1 警告（莎士比亚预期情况）

---

## v2.1.0 (2026-07-29)

### 新功能 + 输出叙事化改造

**新增 3 个 Worker 端点：**
- `shortest-path` — BFS 最短路径发现（中间经过谁）
- `cross-query` — 4 种交叉查询类型：
  - `uninterviewed_most_mentioned` — 被提及最多但从未被访谈
  - `interviewed_but_isolated` — 被访谈过但图谱连接少
  - `cross_community_bridges` — 跨社群桥接节点
  - `positive_vs_negative` — 正负评价反差最大
- `list-communities` — 列出全部 13 个社群名 + 成员人数

**Python 端：**
- `paris_network_query.py` 新增 shortest-path / cross-query / list-communities 三个命令
- `nl_interface.py` 意图识别扩展：路径 / 交叉查询 / 社群列表三类自然语言提问自动识别

**输出叙事化改造：**
- 去掉 emoji 图谱术语（👍/👎/⚪ → 正面/负面/中性文字）
- "入边/出边" → "被 X 位作家提及，提及了 Y 位作家"
- 排行榜去掉 "社群#" / 身份标签等噪音
- 边查询证据去掉分类标签噪音，用「」引用原文
- 重复访谈（同一篇收录在不同文集）标注说明
- 人名标点空格归一化（"乔治 · 普林顿" → "乔治·普林顿"）

**验证：**
- 验证脚本扩展到 69 项（v2.0.0 为 24 项）
- 全部通过，0 失败，1 警告（莎士比亚也在图谱中的预期情况）

**风险点：**
- Worker BFS 在 718 节点 2707 边规模下性能安全（实测 <50ms）
- Worker 实例级缓存 TTL 5 分钟，跨边缘节点一致性可接受

---

## v2.0.0 (2026-07-29)

### 架构升级：本地数据 → API 查询模式

**核心变更：** skill 不再内嵌数据文件，所有查询走 Cloudflare Worker API。数据保护目标达成——skill 包不可被批量提取数据。

**架构：**
- **Worker** (`cloudflare-worker-query-api/`)：独立 Cloudflare Worker，从 KV 读取数据，暴露 8 个查询接口
- **KV 存储**：graph / catalog / author_info / leaderboard / story_paths / name_map 分键存储
- **Skill 端**：`paris_network_query.py` 改为 API 客户端，`nl_interface.py` 调用 API 客户端
- **离线降级**：最近查询结果缓存到 `~/.cache/巴黎评论员/`，API 不可达时降级使用（TTL 1 小时）
- **限流**：每 IP 每分钟 30 次查询

**Skill 包瘦身：**
- ❌ 删除 `data/paris_network_v1_data.json`（3MB）
- ❌ 删除 `scripts/build_data.py`（不再需要本地提取）
- ✅ 新增 Worker 代码（`projects/paris_network/cloudflare-worker-query-api/`）
- ✅ 新增 KV 上传脚本（`scripts/upload_kv.js`）
- skill 包从 ~3MB 降到 ~50KB

**API 接口：**
- `GET /api/query?action=stats` — 统计概览
- `GET /api/query?action=interview-status&name=X` — 访谈状态
- `GET /api/query?action=author&name=X` — 作家详情（入边/出边）
- `GET /api/query?action=edge&name_a=X&name_b=Y` — 双边关系
- `GET /api/query?action=leaderboard&sort_by=degree&top=10` — 排行榜
- `GET /api/query?action=community&community_id=N` — 社群
- `GET /api/query?action=story-path&key=X` — 故事路径
- `GET /api/query?action=version` — 数据版本

**安全设计：**
- API 只返回查询结果，不提供全量导出接口
- author 查询的入边/出边不带 reason 字段（版权保护），需单独请求 `in_edges_with_reason`
- CORS 白名单限制
- 限流防批量爬取

**环境变量：**
- `PARIS_API_BASE` — 覆盖 API 地址
- `PARIS_API_TIMEOUT` — 请求超时（默认 15 秒）
- `PARIS_CACHE_DIR` — 缓存目录

---

## v1.4.0 (2026-07-29)

### 数据同步：网站 v15.1 → Skill 数据更新

**背景：** Paris Network 网站已从 v13（6月26日）迭代到 v15.1（7月26日），skill 数据滞后一个月。

**数据变更：**
- 图谱节点：719 → 718（删除 4 个旧节点：约瑟夫·柯内尔、爱德华·霍珀、丹·H.劳伦斯、W.C.菲尔兹；新增 3 个新节点：艾萨克·阿西莫夫、F.R.利维斯、玛丽·莫里斯）
- 图谱边：2798 → 2707（删除 99 条旧边，新增 4 条新边）
- Catalog：454 条不变（数量不变，内容可能有修正）
- author_info / story_paths / leaderboard：不变

**build_data.py 修复：**
- `extract_js_const` 重写：改用 brace-matching 替代正则，正确处理嵌套大括号（旧正则在 v15 HTML 上失败）
- `extract_catalog_array` 替换为 `extract_catalog`：v15 HTML 的 `PARIS_REVIEW_CATALOG` 已改为结构化对象（含 `meta`/`records`/`name_map`），旧的启发式扫描会把 718 个图谱节点误抓为 catalog 记录（1172 条 vs 真实 454 条）
- 保留 `build_name_maps_fallback`：始终从 records 自建 name_map，因为 HTML 内置的 name_map 用 `name_key` slug（如 `achebe`）作 key，与查询脚本的 `normalize_name_key` 不兼容
- 默认 HTML 路径从 `v13_public.html` 改为 `dist_public/index.html`

**SKILL.md 更新：**
- 数据源引用从 `v13_public.html` 改为 `dist_public/index.html`
- 去掉 "v13 版" 前缀
- Catalog 描述从 "v13_public.html" 改为 "public HTML"

**验证：**
- ✅ `validate_skill_v1.py` 全量测试通过（名字映射、搜索逻辑、边查询、访谈信息）
- ✅ 新节点查询正常（艾萨克·阿西莫夫、玛丽·莫里斯、F.R.利维斯）
- ✅ 删除节点查询正确返回 `in_graph=False`（约瑟夫·柯内尔）
- ✅ 新边查询正常（村上春树 → 玛丽·莫里斯）
- ✅ Catalog 454 条完整
- ✅ 日文名反序查询正常（Haruki Murakami → 村上春树）

---

## v1.3.0 (2026-07-03)

### 重构 + Bug 修复 + 体验优化

**重构：**
- `detect_command` 拆分为 7 个独立检测函数（`_detect_leaderboard` / `_detect_edge` / `_detect_community` / `_detect_story_path` / `_detect_author` / `_detect_interview_status` / `_detect_stats`），提升可维护性
- story-path 关键词改为动态匹配（从数据标题提取，不再硬编码关键词列表）
- 清理 `paris_network_query.py` 中的死代码（`return n` 后的 `break`）

**Bug 修复：**
- 修复作家详情查询名字提取 bug："查一下博尔赫斯的详情" 现在能正确提取"博尔赫斯"（之前提取成"博尔赫斯的"导致查询失败）
- 修复 edge 查询正则贪婪匹配："海明威对福克纳的评价" 不再把"的评价"残留到名字里
- 修复 `build_data.py` 绝对路径泄露问题（`source_html` 字段写入本地绝对路径，改为相对路径）
- 修复 README License badge 错误（Apache-2.0 → MIT）
- 修复 SKILL.md 里旧路径引用（`skills/paris-network/` → `skills/巴黎评论员/`）

**功能优化：**
- interview-status 支持展示全部中文版访谈（多篇时逐条列出书名/译者/采访者/年份）
- edge 查询的 reason 字段完整展示（不再截断为 80 字，多段证据用 `|` 分隔时逐条展示）
- leaderboard 扩展关键词匹配（"最伟大""最牛""最受欢迎""喜爱""讨厌""反感""赞赏"等）
- author 详情输出增加影响关系标记（⚡）

**文档修复：**
- INSTALL.md 去硬编码版本号（`v1.2.2` → `<latest-tag>`）+ 清理重复段落（卸载/升级段各出现两次）
- 更新 `data-contract.md` 过时路径（`v283.html` → `v13_public.html`，移除已不存在的 JSON catalog 路径）
- SKILL.md frontmatter description 去掉过时的 "v283 RC"
- README "数据版本" 从 "v283 RC" 改为 "v13（截至 2026 年 6 月）"
- `skill.yaml` 版本号从 `1.0.0` 更新为 `1.3.0`

---

## v1.2.2 (2026-06-30)

### Bug 修复：目录作家链接 Markdown 化 + 验证脚本数据硬编码改为范围检查

**背景：** 用户反馈 2 个 bug，影响使用体验和数据可维护性。

**Bug 1：目录作家链接不可点击**
- `scripts/nl_interface.py:198` 输出 `链接：URL` 纯文本
- 飞书/webchat 用户看不到可点击链接，终端用户无法直接访问

**修复：**
- 改为 Markdown 链接格式：`链接：[The Paris Review 访谈原文](URL)`
- 飞书/webchat 渲染为蓝色可点击链接
- 终端保留完整 URL（可手动复制）
- N/A 兜底保留（catalog 无 url 字段时显示"链接：N/A"）

**Bug 2：validate_skill_v1.py 数据硬编码**
- 脚本内硬编码 719 / 2798 / 454 / 191
- 改数据后需手动改脚本才能过验证

**修复：**
- 改为范围检查（基于 v1.0 ~ v1.2.1 历史数据 + 30% 余量）
- `nodes: (500, 1500)`、`links: (1000, 5000)`、`catalog_records: (300, 600)`、`authors_with_chinese_interview: (50, 300)`
- 数据更新无需修改脚本；保留数量级异常保护

**验证：**
- ✅ `validate_skill_v1.py` 全量测试通过
- ✅ 真实查询（Joyce Cary、Irwin Shaw 等无中文版作家）输出 Markdown 链接
- ✅ N/A 兜底验证（François Mauriac 等无 url 字段的作家）

**Commit：** `922a7c8 fix: 目录作家链接改为 Markdown 格式 + 验证脚本数据硬编码改为范围检查`

---

## v1.2.1 (2026-06-30)

### 安装说明加入指定 tag 版本号指引

**背景：** 有用户反馈 Agent 默认使用 `git clone` 装到了老版本（如 v1.0.0）或未标记的 commit，无法获得最新功能。

**修复：**
- `INSTALL.md` 顶部加 ⚠️ 重要提示：不要使用默认 `git clone`
- `README.md` 安装段落加警告
- 所有安装方式都明确指定 `v1.2.0` tag
- 新增"如何升级到新版本"段落
- 新增"下载指定 tag 的 ZIP"方式

**安装示例：**
```bash
git clone --branch v1.2.0 --depth 1 https://github.com/fictivedistance/balipinglunyuan.git
```

**Commit：** `dddeb04 docs: 安装说明加入指定 tag 版本号指引`

---

## v1.2.0 (2026-06-29)

### 主流程集成自动版本检查（带每日缓存）

**新增功能：**
- `check_update.py` 新增 `auto_check_update()` 函数
- 缓存文件：`~/.cache/巴黎评论员/last_check.json`
- 缓存策略：24 小时 TTL
- 每日首次调用 `nl_interface.py` 时检查一次

**用户体验：**
- 用户每次使用 Skill 时自动检查更新
- 有更新时在主结果下方追加升级提示
- 无更新时不显示任何内容（静默）
- 网络错误静默失败，不影响主流程

**配置项：**
- 环境变量 `BALIPINGLUNYUAN_AUTO_UPDATE_CHECK=false` 关闭自动检查
- `--raw` 模式跳过自动检查（保持 JSON 纯净）
- `--check-update` 独立检查模式不受影响

**测试：**
- ✅ 无更新场景：静默通过
- ✅ 有更新场景：显示完整升级指令
- ✅ 环境变量关闭：返回 None
- ✅ 缓存读写：正常

**Commit：** `201d48e feat: nl_interface.py 主流程集成自动版本检查`

---

## v1.1.0 (2026-06-29)

### 新增手动版本检查功能

**新增功能：**
- 新增 `scripts/check_update.py` 模块
- 支持对比本地与远程 git tag
- 5 秒超时静默失败
- 远程 tag 按版本号排序（解决 1.10 < 1.9 字符串比较问题）

**集成方式：**
- `nl_interface.py` 新增 `--check-update` 参数
- 独立检查模式，不与主功能冲突

**Bug 修复：**
- 远程 tag 排序改用 `_version_key` 解析为元组比较
- 预发布版本号支持（如 1.0.0-rc1）

**Commit：**
- `81c2566 feat: 添加版本检查功能（--check-update 参数）`
- `07bf43d fix: 远程 tag 排序改用版本号比较`

---

## v1.0.0 (2026-06-29)

### 初始发布版本

**核心功能：**
- 自然语言查询接口（`nl_interface.py`）
- 6 种作家名提取正则模式
- 访谈状态查询
- 关系图谱查询
- 关系边查询
- 社群查询
- 故事路径查询
- 排行榜

**包含的 bug 修复：**
- **作家名提取**：之前用简单 `prefix.replace` 会把关键词残留在名字里，现在改用 6 种正则模式匹配
- **目录回退展示**：有英文访谈但无中文版的作家现在能正确显示期号、系列、年份、链接，并标注"📕 尚未出版中文版"

**Commit：** `a28a1af fix: 修正访谈状态查询的目录回退展示`

**首个 git tag：** `v1.0.0`（指向 commit a28a1af）

---

## 版本约定

### Commit → Tag 流程

1. 功能/修复 commit 到 main 分支
2. 完成后打 git tag：`git tag -a vX.Y.Z -m "..."`
3. 推送：`git push origin main && git push origin vX.Y.Z`
4. 更新本文件，添加版本记录

### 何时需要发新版

- **新功能**：vX.Y+1.0（次版本号 +1）
- **bug 修复**：vX.Y.Z+1（修订号 +1）
- **不兼容改动**：vX+1.0.0（主版本号 +1）
