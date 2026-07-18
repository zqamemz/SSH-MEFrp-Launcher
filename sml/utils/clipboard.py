"""跨平台剪贴板读取工具.

优先使用 pyperclip（若已安装），否则用平台命令回退：
- Linux: xclip / xsel / wl-paste
- Windows: powershell Get-Clipboard
- macOS: pbpaste

在 SSH 等无系统剪贴板的环境下，自动回退到手动粘贴模式。
"""

import logging
import os
import shutil
import subprocess
import sys
from typing import Optional

logger = logging.getLogger("sml.clipboard")


def _try_pyperclip() -> Optional[str]:
    """尝试使用 pyperclip 库读取剪贴板。"""
    try:
        import pyperclip
        text = pyperclip.paste()
        return text.strip() if text and text.strip() else None
    except Exception:
        return None


def _try_powershell() -> Optional[str]:
    """Windows: 通过 PowerShell Get-Clipboard 读取。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            text = result.stdout.strip()
            return text if text else None
    except Exception:
        pass
    return None


def _try_xclip() -> Optional[str]:
    """Linux X11: 通过 xclip 读取。"""
    if not shutil.which("xclip"):
        return None
    try:
        result = subprocess.run(
            ["xclip", "-o", "-selection", "clipboard"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            text = result.stdout.strip()
            return text if text else None
    except Exception:
        pass
    return None


def _try_xsel() -> Optional[str]:
    """Linux X11: 通过 xsel 读取。"""
    if not shutil.which("xsel"):
        return None
    try:
        result = subprocess.run(
            ["xsel", "-ob"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            text = result.stdout.strip()
            return text if text else None
    except Exception:
        pass
    return None


def _try_wl_paste() -> Optional[str]:
    """Linux Wayland: 通过 wl-paste 读取。"""
    if not shutil.which("wl-paste"):
        return None
    try:
        result = subprocess.run(
            ["wl-paste"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            text = result.stdout.strip()
            return text if text else None
    except Exception:
        pass
    return None


def _try_pbpaste() -> Optional[str]:
    """macOS: 通过 pbpaste 读取。"""
    if not shutil.which("pbpaste"):
        return None
    try:
        result = subprocess.run(
            ["pbpaste"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            text = result.stdout.strip()
            return text if text else None
    except Exception:
        pass
    return None


def is_ssh_environment() -> bool:
    """检测当前是否运行在 SSH 环境中（无系统剪贴板）。

    检测条件：
    - SSH_CONNECTION 或 SSH_CLIENT 环境变量存在（SSH 连接）
    - 且没有 DISPLAY 或 WAYLAND_DISPLAY（无图形桌面）
    """
    has_ssh_env = "SSH_CONNECTION" in os.environ or "SSH_CLIENT" in os.environ
    has_display = "DISPLAY" in os.environ or "WAYLAND_DISPLAY" in os.environ

    # Linux 且无图形显示 → 大概率是 SSH 或无头环境
    if sys.platform.startswith("linux") and not has_display:
        return True

    # 有 SSH 环境变量 → 明确是 SSH 连接
    if has_ssh_env:
        return True

    return False


def get_clipboard_text() -> Optional[str]:
    """从系统剪贴板读取文本（跨平台）。

    探测顺序: pyperclip > powershell (Win) > xclip > xsel > wl-paste > pbpaste (macOS)
    """
    # 1. pyperclip 库（需安装 python -m pip install pyperclip）
    text = _try_pyperclip()
    if text:
        return text

    # 2. 平台特定命令
    if sys.platform == "win32":
        text = _try_powershell()
        if text:
            return text
    elif sys.platform == "darwin":
        text = _try_pbpaste()
        if text:
            return text
    else:
        # Linux — 依次尝试 xclip / xsel / wl-paste
        text = _try_xclip()
        if text:
            return text
        text = _try_xsel()
        if text:
            return text
        text = _try_wl_paste()
        if text:
            return text

    return None


def paste_to_input(input_widget) -> bool:
    """将剪贴板内容粘贴到 Textual Input 组件中。

    返回是否粘贴成功。
    """
    text = get_clipboard_text()
    if text is None:
        return False

    # 在光标位置插入文本
    cursor_pos = input_widget.cursor_position
    old_value = input_widget.value
    new_value = old_value[:cursor_pos] + text + old_value[cursor_pos:]
    input_widget.value = new_value
    # 将光标移到粘贴内容之后
    input_widget.cursor_position = cursor_pos + len(text)
    return True
