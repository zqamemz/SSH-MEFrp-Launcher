"""SML 辅助工具函数."""

import os
import sys
from typing import Optional


def check_root() -> bool:
    """检查是否 root 用户（用于 systemd 管理）。"""
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False


def format_bytes(n: int) -> str:
    """将字节数格式化为可读字符串。"""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def format_timestamp(ts: int) -> str:
    """将 Unix 时间戳格式化为日期字符串。"""
    import datetime
    if ts == 0:
        return "从未"
    try:
        dt = datetime.datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, ValueError):
        return str(ts)


def format_uptime(seconds: int) -> str:
    """将秒数格式化为可读运行时长。"""
    if seconds <= 0:
        return "离线"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    mins, secs = divmod(rem, 60)
    parts = []
    if days > 0:
        parts.append(f"{days}天")
    if hours > 0:
        parts.append(f"{hours}时")
    if mins > 0:
        parts.append(f"{mins}分")
    parts.append(f"{secs}秒")
    return "".join(parts)


def check_command(cmd: str) -> Optional[str]:
    """检测命令是否存在，返回路径或 None。"""
    return shutil.which(cmd)


import shutil
