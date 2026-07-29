#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 简体中文版《巴黎评论》系列编辑部
"""
版本检查脚本（API 模式）
- 读取本地 git tag 作为 skill 版本
- 调用 Worker API /api/query?action=version 获取数据版本
- 比对并返回结果
- 不阻塞主流程（5 秒超时，静默失败）
- 支持手动检查 + 自动检查（带每日缓存）

用法：
    python3 scripts/check_update.py
    # 或作为模块：
    from scripts.check_update import check_update, auto_check_update
"""
import json
import os
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from paris_network_query import API_BASE

# 仓库配置
GITHUB_REPO = "fictivedistance/balipinglunyuan"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/tags"
TIMEOUT_SECONDS = 5
SKILL_DIR = Path(__file__).parent.parent

# 缓存配置
CACHE_DIR = Path.home() / ".cache" / "巴黎评论员"
CACHE_FILE = CACHE_DIR / "last_check.json"
CACHE_TTL_SECONDS = 86400  # 24 小时

DISABLE_AUTO_CHECK_ENV = "BALIPINGLUNYUAN_AUTO_UPDATE_CHECK"


def get_local_tag() -> str | None:
    """读取本地最新 git tag"""
    try:
        result = subprocess.run(
            ["git", "tag", "--sort=-version:refname"],
            cwd=SKILL_DIR,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            tags = [t.strip() for t in result.stdout.strip().split("\n") if t.strip()]
            if tags:
                return tags[0]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _version_key(tag: str) -> tuple:
    import re
    s = tag.lstrip("v")
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-(.+))?", s)
    if m:
        major, minor, patch, pre = m.groups()
        key = (int(major), int(minor), int(patch))
        if pre:
            key = key + (-1, pre)
        else:
            key = key + (1,)
        return key
    return (0, tag)


def get_remote_tag() -> str | None:
    """从 GitHub API 获取远程最新 tag"""
    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "balipinglunyuan-skill"},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            tags = json.loads(response.read().decode("utf-8"))
            if tags and len(tags) > 0:
                tag_names = [t.get("name", "") for t in tags if t.get("name")]
                if not tag_names:
                    return None
                tag_names.sort(key=_version_key, reverse=True)
                return tag_names[0]
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
        pass
    return None


def get_api_version() -> dict | None:
    """获取 API 端的数据版本信息"""
    try:
        url = f"{API_BASE}/api/query?action=version"
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "balipinglunyuan-skill"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def check_update() -> dict:
    """检查是否有新版本（git tag + API 数据版本）"""
    local = get_local_tag()
    remote = get_remote_tag()
    api_ver = get_api_version()

    result = {
        "local": local,
        "remote": remote,
        "api_version": api_ver.get("version") if api_ver else None,
        "api_updated_at": api_ver.get("updated_at") if api_ver else None,
        "has_update": False,
        "message": None,
    }

    if local and remote and local != remote:
        result["has_update"] = True
        result["message"] = (
            f"⚠️ 巴黎评论员 Skill 有新版本可用\n"
            f"   当前版本：{local}\n"
            f"   最新版本：{remote}\n"
            f"   升级方式：cd ~/.openclaw/workspace/skills/巴黎评论员 && git pull origin main && git fetch --tags"
        )
    elif not remote and local:
        result["has_update"] = True
        result["message"] = (
            f"⚠️ 巴黎评论员 Skill 远程仓库暂无版本信息\n"
            f"   当前本地版本：{local}\n"
            f"   建议：检查网络或访问 https://github.com/{GITHUB_REPO}/releases"
        )

    return result


def main():
    result = check_update()
    if result["has_update"]:
        print(result["message"])
        return 1
    else:
        if result.get("api_version"):
            print(f"✅ skill 版本: {result.get('local', 'N/A')} | 数据版本: {result['api_version']} (更新于 {result.get('api_updated_at', 'N/A')})")
        elif result.get("local") and result.get("remote"):
            print(f"✅ 已是最新版本：{result['local']}")
        else:
            print("ℹ️  无版本信息")
        return 0


def _read_cache() -> dict | None:
    if not CACHE_FILE.exists():
        return None
    try:
        with CACHE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if time.time() - data.get("checked_at", 0) > CACHE_TTL_SECONDS:
            return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def _write_cache(local: str | None, remote: str | None) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_data = {"checked_at": time.time(), "local": local, "remote": remote}
        with CACHE_FILE.open("w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False)
    except OSError:
        pass


def auto_check_update() -> str | None:
    """自动检查更新（带每日缓存），仅在有更新时返回提示文字"""
    if os.environ.get(DISABLE_AUTO_CHECK_ENV, "").lower() in ("false", "0", "no", "off"):
        return None

    cached = _read_cache()
    if cached is not None:
        local = cached.get("local")
        remote = cached.get("remote")
    else:
        try:
            result = check_update()
            local = result["local"]
            remote = result["remote"]
            _write_cache(local, remote)
        except Exception:
            return None

    if local and remote and local != remote:
        return (
            f"\n\n💡 提示：巴黎评论员 Skill 有新版本可用\n"
            f"   当前版本：{local}\n"
            f"   最新版本：{remote}\n"
            f"   升级方式：cd ~/.openclaw/workspace/skills/巴黎评论员 && git pull origin main && git fetch --tags"
        )
    return None


if __name__ == "__main__":
    sys.exit(main())