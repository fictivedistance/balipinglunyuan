# Tests — 巴黎评论员 Skill

> ⚠️ 本目录**不**随 skill 发布包分发（见 `skill.yaml` `distribution.exclude`）。
> 仅供开发者在本地 + CI 跑测用。

## 用例

| 文件 | 用途 | 何时跑 |
|---|---|---|
| `test_cli_smoke.py` | CLI 命令识别烟雾测试（20 条，不调 API） | 每次改 `nl_interface.py` |
| `test_field_completeness.py` | 字段完整性回归（20 条，需 API） | 每次改 SKILL.md 或 scripts/ |
| `snapshots/` | 输出快照（手动对比） | 发版前人肉 diff |

## 跑法

```bash
# CLI 烟雾测试（无需 API）
python3 tests/test_cli_smoke.py

# 字段完整性（在线，需 Worker 已部署）
python3 tests/test_field_completeness.py

# 字段完整性（离线，用 fixtures）
python3 tests/test_field_completeness.py --offline

# 指定 API 地址
PARIS_API_BASE=http://localhost:8788 python3 tests/test_field_completeness.py
```

## CI 接入（建议）

```yaml
# .github/workflows/test-skill.yml
name: test-skill
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: CLI smoke
        run: python3 skills/巴黎评论员/tests/test_cli_smoke.py
      - name: Field completeness
        env:
          PARIS_API_BASE: ${{ secrets.WORKER_API_URL }}
        run: python3 skills/巴黎评论员/tests/test_field_completeness.py
```

## 设计原则

1. **不依赖网络**：CLI 测试用纯本地 detect_command，秒级反馈
2. **fixtures 可离线**：字段测试支持 `--offline`，开发机无 Worker 也能跑
3. **失败信息具体**：每个 case 打印作家名 + 缺字段名，不靠"全跑通"
4. **回归可追溯**：用例基于 v2.1.2 bug 的真实修复点（series/number/issue/url）

## 为什么不放发布包

- 用户解压 skill 包后看到的应该是"问答工具"，不是"测试套件"
- 测试文件会让 SKILL.md / scripts/ 的视线被冲淡
- 发布包尺寸：当前 ~80KB，加测试集 ~16KB，对问答型 skill 不划算
- 质量保证是开发者 + CI 的事，不是终端用户的事