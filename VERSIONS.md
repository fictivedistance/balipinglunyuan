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
