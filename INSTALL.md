# 安装指南

> **⚠️ 请按以下步骤安装指定版本**（如 `v1.2.0`）。
> 默认 `git clone` 拉取的是 `main` 分支的最新代码，**不是**最新 tag。
> 为避免 Agent 误装老版本或未标记的 commit，**请明确指定 tag 版本号**。

**最新版本：** 查 [VERSIONS.md](./VERSIONS.md) 或 https://github.com/fictivedistance/balipinglunyuan/tags

---

## 🚀 链接即装（推荐）

把这个 GitHub 仓库地址发给支持「技能自动安装」的 AI Agent，例如：

```
帮我装这个技能：https://github.com/fictivedistance/balipinglunyuan
并安装到 v1.2.0 tag 版本
```

Agent 会自动：
1. 拉取仓库 v1.2.0 tag 的代码（`git clone --branch v1.2.0 --depth 1`）
2. 运行 `skill.yaml` 的元数据检查
3. 安装到 `skills/巴黎评论员/`
4. 运行验证脚本确认安装成功

> 💡 **给 Agent 的补充说明**：如果 Agent 不熟悉 `git clone --branch`，可以要求它“使用 v1.2.0 tag 拉取”或“检出 v1.2.0 标签”。

---

## 📦 手动安装

### 方式 1：git clone 指定 tag（推荐）

```bash
# 克隆指定 tag（以 v1.2.0 为例，请替换为最新版本）
git clone --branch v1.2.0 --depth 1 https://github.com/fictivedistance/balipinglunyuan.git

# 复制到 OpenClaw skills 目录
cp -r balipinglunyuan ~/.openclaw/workspace/skills/巴黎评论员
```

**说明：**
- `--branch v1.2.0`：只拉取指定 tag 的代码（默认是 main 分支，**不要用**）
- `--depth 1`：只下载 tag 指向的那一个 commit，不下载完整历史（速度更快）

### 方式 2：git clone 后 checkout tag

```bash
# 先 clone 完整仓库
git clone https://github.com/fictivedistance/balipinglunyuan.git
cd balipinglunyuan

# 列出所有可用 tag，选择最新的
git tag --sort=-version:refname

# checkout 最新 tag
git checkout v1.2.0
```

### 方式 3：下载指定 tag 的 ZIP

在浏览器中打开下面这个 URL（以 v1.2.0 为例，请替换为最新版本）：

```
https://github.com/fictivedistance/balipinglunyuan/archive/refs/tags/v1.2.0.zip
```

下载后解压，将解压后的文件夹重命名为 `巴黎评论员`，移动到 `~/.openclaw/workspace/skills/`。

### 方式 4：作为 Python 包

```bash
git clone --branch v1.2.0 --depth 1 https://github.com/fictivedistance/balipinglunyuan.git
cd balipinglunyuan
pip install -e .
```

---

## ✅ 安装后验证

```bash
cd ~/.openclaw/workspace/skills/巴黎评论员
python3 scripts/validate_skill_v1.py
```

**另外检查版本：**

```bash
# 手动检查是否有新版本
python3 scripts/nl_interface.py --check-update
```

> 从 v1.2.0 起，Skill 在主流程中会自动检查更新（每日一次），你会在使用过程中看到升级提示。

---

## 🔄 升级到新版本

如果你已经装过老版本，升级到最新版本：

```bash
cd ~/.openclaw/workspace/skills/巴黎评论员
git pull origin v1.2.0
git fetch --tags
```

> ⚠️ 使用 `git pull origin v1.2.0` 而不是 `git pull origin main`，以免拉取到未发布版本。

---

## 🗑️ 卸载

```bash
rm -rf ~/.openclaw/workspace/skills/巴黎评论员
```

期望输出：
```
✅ 所有测试通过！skill v1 与网页端 100% 对齐
```

---

## 🧪 快速测试

```bash
# 统计概览
python3 scripts/nl_interface.py "统计一下"

# 作家搜索
python3 scripts/nl_interface.py "海明威被访谈过吗"

# 关系查询
python3 scripts/nl_interface.py "海明威和福克纳有什么关系"
```

---

## 🗑️ 卸载

```bash
rm -rf ~/.openclaw/workspace/skills/巴黎评论员
```

---

## 🔄 更新

```bash
cd ~/.openclaw/workspace/skills/巴黎评论员
git pull origin main
python3 scripts/validate_skill_v1.py
```

---

## 💡 平台兼容性

| 平台 | 安装方法 |
|------|----------|
| OpenClaw | 直接复制到 `skills/` 目录 ✅ |
| Claude Code | 复制到 `.claude/skills/` 目录 ✅ |
| Codex | `pip install -e .` |
| Hermes Agent | 需要单独适配工具调用 |
