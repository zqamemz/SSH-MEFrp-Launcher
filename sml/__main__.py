"""SML - ME Frp 终端图形化管理工具.

在 SSH 和真实命令行环境下直接使用的 ME Frp 管理器。

用法:
  sml                  # 启动 TUI
  sml install          # 安装 mefrpc
  sml install --force  # 强制重装
  sml uninstall        # 卸载 mefrpc
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
