#!/usr/bin/env python3
"""
版本检查脚本
- 读取本地最新 git tag
- 调用 GitHub API 读取远程最新 tag
- 比对并返回结果
- 不阻塞主流程（5 秒超时，静默失败）
- 支持手动检查 + 自动检查（带每日缓存）

用法：
    python3 scripts/check_update.py
    # 或作为模块：
    from scripts.check_update import check_update, auto_check_update
    result = check_update()                # 手动检查
    message = auto_check_update()          # 自动检查（带每日缓存，返回 None 或提示文字）
"""
import json
import os
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path
import sys

# 仓库配置
GITHUB_REPO = "fictivedistance/balipinglunyuan"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/tags"
TIMEOUT_SECONDS = 5
SKILL_DIR = Path(__file__).parent.parent

# 缓存配置
CACHE_DIR = Path.home() / ".cache" / "巴黎评论员"
CACHE_FILE = CACHE_DIR / "last_check.json"
CACHE_TTL_SECONDS = 86400  # 24 小时

# 环境变量：关闭自动检查
DISABLE_AUTO_CHECK_ENV = "BALIPINGLUNYUAN_AUTO_UPDATE_CHECK"


def get_local_tag() -> str | None:
    """读取本地最新 git tag（按版本号排序）"""
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
                return tags[0]  # 已按版本号降序，第一个就是最新
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _version_key(tag: str) -> tuple:
    """
    把 tag 字符串转为可比较的元组
    例如 v1.10.0 → (1, 10, 0)，v1.9.0 → (1, 9, 0)
    支持 'v' 前缀、预发布后缀（如 1.0.0-rc1 → (1, 0, 0, -1, 'rc1')）
    """
    import re
    s = tag.lstrip("v")
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-(.+))?", s)
    if m:
        major, minor, patch, pre = m.groups()
        key = (int(major), int(minor), int(patch))
        if pre:
            # 预发布版低于正式版
            key = key + (-1, pre)
        else:
            key = key + (1,)  # 正式版标记
        return key
    return (0, tag)  # 解析失败：按字符串兜底


def get_remote_tag() -> str | None:
    """从 GitHub API 获取远程最新 tag（按版本号排序）"""
    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "balipinglunyuan-skill"},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            tags = json.loads(response.read().decode("utf-8"))
            if tags and len(tags) > 0:
                # GitHub API 默认按创建时间排序，需按版本号重新排序取最新
                tag_names = [t.get("name", "") for t in tags if t.get("name")]
                if not tag_names:
                    return None
                # 按版本号排序取最新（注意：sort 默认按元组逐个元素比较）
                tag_names.sort(key=_version_key, reverse=True)
                return tag_names[0]
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
        pass
    return None


def check_update() -> dict:
    """
    检查是否有新版本

    Returns:
        {
            "local": "v1.0.0" 或 None,
            "remote": "v1.0.0" 或 None,
            "has_update": bool,
            "message": str 或 None  # 有更新时的提示信息
        }
    """
    local = get_local_tag()
    remote = get_remote_tag()

    result = {
        "local": local,
        "remote": remote,
        "has_update": False,
        "message": None,
    }

    # 双方都有数据且不一致 → 有更新
    if local and remote and local != remote:
        result["has_update"] = True
        result["message"] = (
            f"⚠️ 巴黎评论员 Skill 有新版本可用\n"
            f"   当前版本：{local}\n"
            f"   最新版本：{remote}\n"
            f"   升级方式：cd ~/.openclaw/workspace/skills/巴黎评论员 && git pull origin main && git fetch --tags"
        )
    # 远程没有（GitHub 还没 tag）但本地有 → 静默
    # 都没有 → 静默
    # 本地有远程没有（老版本）→ 提示
    elif not remote and local:
        result["has_update"] = True
        result["message"] = (
            f"⚠️ 巴黎评论员 Skill 远程仓库暂无版本信息\n"
            f"   当前本地版本：{local}\n"
            f"   建议：检查网络或访问 https://github.com/{GITHUB_REPO}/releases"
        )

    return result


def main():
    """命令行直接运行：输出简洁结果"""
    result = check_update()
    if result["has_update"]:
        print(result["message"])
        return 1  # 有更新时返回非零
    else:
        if result["local"] and result["remote"]:
            print(f"✅ 已是最新版本：{result['local']}")
        elif result["local"]:
            print(f"📦 本地版本：{result['local']}（远程无版本信息）")
        else:
            print("ℹ️  无版本信息")
        return 0


def _read_cache() -> dict | None:
    """读取缓存（返回 None 表示无缓存或缓存已过期）"""
    if not CACHE_FILE.exists():
        return None
    try:
        with CACHE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        checked_at = data.get("checked_at", 0)
        # 过期检查
        if time.time() - checked_at > CACHE_TTL_SECONDS:
            return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def _write_cache(local: str | None, remote: str | None) -> None:
    """写入缓存（出错静默）"""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_data = {
            "checked_at": time.time(),
            "local": local,
            "remote": remote,
        }
        with CACHE_FILE.open("w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False)
    except OSError:
        # 缓存写入失败静默（不影响主流程）
        pass


def auto_check_update() -> str | None:
    """
    自动检查更新（带每日缓存）

    - 每日最多请求一次 GitHub
    - 缓存文件：~/.cache/巴黎评论员/last_check.json
    - 环境变量 BALIPINGLUNYUAN_AUTO_UPDATE_CHECK=false 可关闭
    - 静默失败：网络错误、读写错误都不抛异常
    - 仅当有更新时返回提示文字（str），否则返回 None

    Returns:
        str | None: 提示文字（仅在有更新时），None 表示无需提示或静默失败
    """
    # 检查环境变量是否关闭
    if os.environ.get(DISABLE_AUTO_CHECK_ENV, "").lower() in ("false", "0", "no", "off"):
        return None

    # 尝试读取缓存
    cached = _read_cache()
    if cached is not None:
        # 缓存有效：复用上次结果
        local = cached.get("local")
        remote = cached.get("remote")
    else:
        # 缓存失效：重新检查
        try:
            result = check_update()
            local = result["local"]
            remote = result["remote"]
            _write_cache(local, remote)
        except Exception:
            # 静默失败：网络错误等不打扰主流程
            return None

    # 判断是否有更新
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
