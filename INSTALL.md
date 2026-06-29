# 安装指南

## 🚀 链接即装（推荐）

把这个 GitHub 仓库地址发给支持「技能自动安装」的 AI Agent，例如：

```
帮我装这个技能：https://github.com/fictivedistance/balipinglunyuan
```

Agent 会自动：
1. 拉取仓库代码
2. 运行 `skill.yaml` 的元数据检查
3. 安装到 `skills/巴黎评论员/`
4. 运行验证脚本确认安装成功

---

## 📦 手动安装

### 方式 1：git clone

```bash
git clone https://github.com/fictivedistance/balipinglunyuan.git
cp -r balipinglunyuan ~/.openclaw/workspace/skills/巴黎评论员
```

### 方式 2：直接下载 ZIP

1. 在 GitHub 仓库页面点击「Code」→「Download ZIP」
2. 解压
3. 把解压后的文件夹移动到 `~/.openclaw/workspace/skills/巴黎评论员`

### 方式 3：作为 Python 包

```bash
git clone https://github.com/fictivedistance/balipinglunyuan.git
cd balipinglunyuan
pip install -e .
```

---

## ✅ 安装后验证

```bash
cd ~/.openclaw/workspace/skills/巴黎评论员
python3 scripts/validate_skill_v1.py
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
