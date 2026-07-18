"""SML - ME Frp 终端图形化管理工具.

在 SSH 和真实命令行环境下直接使用的 ME Frp 管理器。

Copyright (C) 2025  zqamemz

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import sys


def _auto_install_mefrpc():
    """应用启动时自动安装 mefrpc（静默模式，仅在未安装时执行）。"""
    from sml.installer import is_installed, install
    if is_installed():
        return
    ok, msg = install()
    if ok:
        from sml.manager.config import Config
        cfg = Config()
        from sml.installer import INSTALL_PATH
        cfg.frpc_path = str(INSTALL_PATH)


def main():
    """SML 入口 - 根据命令行参数分发到 TUI 或子命令。"""
    args = sys.argv[1:]

    # 子命令分发
    if args and args[0] in ("install", "uninstall"):
        _handle_install_command(args)
        return

    # 默认：启动 TUI
    _auto_install_mefrpc()
    from sml.app import SMLApp
    app = SMLApp()
    app.run()


def _handle_install_command(args: list[str]):
    """处理 sml install / sml uninstall / sml install --force。"""
    from sml.installer import is_installed, install, uninstall, get_install_path

    cmd = args[0]

    if cmd == "uninstall":
        ok, msg = uninstall()
        print(msg)
        sys.exit(0 if ok else 1)

    # cmd == "install"
    force = "--force" in args
    if is_installed() and not force:
        print(f"meFrpc 已安装: {get_install_path()}")
        print("使用 sml install --force 强制重新安装")
        sys.exit(0)

    if force:
        print("正在强制重新安装...")
    ok, msg = install(force=force)
    print(msg)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
