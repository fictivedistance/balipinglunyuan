# 巴黎评论员

> 《巴黎评论》作家关系网络查询技能

一个供AI agent使用的skill，基于简体中文版《巴黎评论》系列作家关系网络图谱创建，支持《巴黎评论》读者用自然语言查询访谈状态、作家关系、排行榜等。

---

## 关于本技能

本技能是 [**《巴黎评论》作家宇宙**](https://www.fictivedistance.com) 网站的 AI 伴随技能。

**什么是《巴黎评论》作家宇宙？**
> 一个以简体中文版《巴黎评论》系列访谈信息为原材料搭建的文学知识图谱。你可以拖动、点选、缩放、检索可视化查看 719 位作家之间的评价、影响、偏见与继承关系。
> 它是一个"能逛的"图谱。

**什么是巴黎评论员技能？**
> 本技能是同一套图谱数据的 AI 伴随查询接口。你不用打开网站、不用学会复杂检索、不用记住作家名字的译法，直接用自然语言问就可以。
> 它是一个"能问的"图谱。

**两者的关系：**
- **作家宇宙网站**负责浏览、探索、发现——适合慢慢看、随机踩点、发现新关联
- **巴黎评论员技能**负责快速问答——适合明确查某个作家、某种关系、某个列表
- 数据来自同一版本的图谱，技能是网站的子集+文本化接口

---

## 功能亮点

| 功能 | 说明 |
|------|------|
| **统计概览** | 719位作家 / 2798条关系边 / 454篇访谈基本信息收录 |
| **作家搜索** | 中英文双向匹配，支持日本人名反序查询 |
| **访谈状态** | 中文版收录状态、译者、采访者、年份完整信息 |
| **8种排行榜** | 被提及数、影响力、中介中心性、正负评价等 |
| **双边关系** | 任意两位作家之间的直接关系查询 + 原文证据 |

---

## 安装

### 链接即装（推荐）

把 GitHub 仓库地址发给支持「技能自动安装」的 AI Agent，例如：

```
帮我装这个技能：https://github.com/fictivedistance/balipinglunyuan
```

Agent 会自动拉取、安装、验证。

### 手动安装

```bash
# 克隆仓库
git clone https://github.com/fictivedistance/balipinglunyuan.git

# 复制到 OpenClaw skills 目录
cp -r balipinglunyuan ~/.openclaw/workspace/skills/巴黎评论员

# 验证安装
python3 ~/.openclaw/workspace/skills/巴黎评论员/scripts/validate_skill_v1.py
```

### 独立使用

```bash
# 克隆后直接运行
git clone https://github.com/fictivedistance/balipinglunyuan.git
cd balipinglunyuan
python3 scripts/nl_interface.py "海明威和福克纳有什么关系"
```

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
马尔克斯提到过哪些作家？
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
被《巴黎评论》受访者提及最多的前10位作家
最受《巴黎评论》受访者喜爱的女性作家排名
《巴黎评论》受访者负面评价最多的作家
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

```

---

## 数据来源

所有数据提取自 **简体中文版《巴黎评论》系列** ：

- **提取时间**：2026年6月
- **数据规模**：
 - 719 位作家节点
 - 2798 条关系边（含原文证据）
 - 454 篇《巴黎评论》官方访谈目录
 - 191 位已出版中文版的作家信息
- **搜索逻辑**：与网页端 100% 对齐（标点归一化、中英文映射、模糊匹配）

---

## 验证说明

本技能包含完整的验证脚本，确保与网页端行为一致：

```bash
python3 scripts/validate_skill_v1.py
```

验证项：
- 搜索逻辑与前端 100% 对齐
- 中英文双向映射（736 en→zh / 390 zh→en）
- 日本人名反序支持（Murakami Haruki → 村上春树）
- 目录回退机制（图谱中没有但访谈目录中有的作家也能找到）
- 访谈状态判断逻辑固化

---

## 目录结构

```
巴黎评论员/
├── README.md # 本文档（发布说明）
├── SKILL.md # OpenClaw 技能文档
├── data/
│ └── paris_network_v1_data.json # 完整数据（719节点/2798边）
├── scripts/
│ ├── paris_network_query.py # 底层查询引擎（8个命令）
│ ├── nl_interface.py # 自然语言接口
│ ├── build_data.py # 数据构建脚本
│ └── validate_skill_v1.py # 验证脚本
└── references/ # 参考资料
```

---

## 更新日志

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

**技能版本**：v1.0

**发布日期**：2026-06-29

**数据版本**：v283 RC
