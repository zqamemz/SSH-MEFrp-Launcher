"""mefrpc 自动安装模块 - 将内置的 mefrpc 二进制部署到系统路径。"""

import os
import shutil
import stat
import sys
from pathlib import Path

# mefrpc 在包内的位置
_BUNDLED_MEFRPC = Path(__file__).parent / "mefrpc"

# 平台相关安装目标
if sys.platform == "win32":
    INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SML" / "bin"
else:
    INSTALL_DIR = Path("/usr/local/bin")

INSTALL_NAME = "mefrpc"
INSTALL_PATH = INSTALL_DIR / INSTALL_NAME


def is_installed() -> bool:
    """检查 mefrpc 是否已正确安装到系统路径。"""
    return INSTALL_PATH.exists() and os.access(INSTALL_PATH, os.X_OK)


def install(force: bool = False) -> tuple[bool, str]:
    """将内置的 mefrpc 安装到系统路径。

    Args:
        force: 强制覆盖已存在的安装。

    Returns:
        (成功与否, 消息文本)
    """
    # 检查内置二进制是否存在
    if not _BUNDLED_MEFRPC.exists():
        return False, f"内置 mefrpc 未找到: {_BUNDLED_MEFRPC}"

    # 如果已安装且不需要强制覆盖
    if is_installed() and not force:
        return True, f"meFrpc 已安装: {INSTALL_PATH}"

    # 确保目标目录存在
    try:
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # 目录创建失败，回退到使用内置路径
        if _BUNDLED_MEFRPC.exists():
            os.chmod(str(_BUNDLED_MEFRPC), os.stat(str(_BUNDLED_MEFRPC)).st_mode | stat.S_IEXEC)
            return True, f"无法创建安装目录，使用内置版本: {_BUNDLED_MEFRPC}"
        return False, f"无法创建安装目录: {INSTALL_DIR}"

    # 复制二进制文件
    try:
        shutil.copy2(str(_BUNDLED_MEFRPC), str(INSTALL_PATH))
    except PermissionError:
        # Windows 下通常不需要 sudo cp，直接尝试
        if sys.platform != "win32":
            try:
                import subprocess
                r = subprocess.run(
                    ["sudo", "cp", str(_BUNDLED_MEFRPC), str(INSTALL_PATH)],
                    capture_output=True, text=True, timeout=30,
                )
                if r.returncode != 0:
                    return False, f"复制失败 (sudo): {r.stderr.strip()}"
            except Exception as e:
                return False, f"复制失败: {e}"
        else:
            return False, f"复制失败 (权限不足): 请手动将 mefrpc 复制到 {INSTALL_DIR}"
    except Exception as e:
        return False, f"复制失败: {e}"

    # 设置可执行权限 (Unix)
    if sys.platform != "win32":
        try:
            st = os.stat(str(INSTALL_PATH))
            os.chmod(str(INSTALL_PATH), st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        except Exception:
            pass

    # 验证安装
    if is_installed():
        return True, f"meFrpc 已安装到: {INSTALL_PATH}"
    else:
        # Windows 下 os.access 可能不准确，检查文件是否存在即可
        if INSTALL_PATH.exists():
            return True, f"meFrpc 已安装到: {INSTALL_PATH}"
        return False, f"安装后验证失败，请手动检查: {INSTALL_PATH}"


def uninstall() -> tuple[bool, str]:
    """卸载已安装的 mefrpc。"""
    if not INSTALL_PATH.exists():
        return True, "meFrpc 未安装，无需卸载"

    try:
        INSTALL_PATH.unlink()
    except PermissionError:
        if sys.platform != "win32":
            try:
                import subprocess
                subprocess.run(
                    ["sudo", "rm", "-f", str(INSTALL_PATH)],
                    capture_output=True, timeout=10,
                )
            except Exception as e:
                return False, f"卸载失败: {e}"
        else:
            return False, f"卸载失败 (权限不足): 请手动删除 {INSTALL_PATH}"
    except Exception as e:
        return False, f"卸载失败: {e}"

    if not INSTALL_PATH.exists():
        return True, "meFrpc 已卸载"
    return False, "卸载失败，请手动删除"


def get_install_path() -> str:
    """获取 mefrpc 的实际可用路径（已安装路径 > 内置路径）。"""
    if is_installed():
        return str(INSTALL_PATH)
    if _BUNDLED_MEFRPC.exists():
        return str(_BUNDLED_MEFRPC)
    return ""
