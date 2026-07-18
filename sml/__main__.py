"""SML - ME Frp 终端图形化管理工具.

在 SSH 和真实命令行环境下直接使用的 ME Frp 管理器。
"""

import sys

from sml.app import SMLApp


def _auto_install_mefrpc():
    """应用启动时自动安装 mefrpc（静默模式，仅在未安装时执行）。"""
    from sml.installer import is_installed, install
    if is_installed():
        return
    ok, msg = install()
    # 更新配置中的 frpc 路径指向新安装位置
    if ok:
        from sml.manager.config import Config
        cfg = Config()
        from sml.installer import INSTALL_PATH
        cfg.frpc_path = str(INSTALL_PATH)


def main():
    """SML 入口 - 自动安装 mefrpc 后启动 TUI。"""
    _auto_install_mefrpc()
    app = SMLApp()
    app.run()


def install_cli():
    """sml-install 命令行入口 - 安装/卸载 mefrpc。"""
    from sml.installer import is_installed, install, uninstall, get_install_path

    if len(sys.argv) > 1 and sys.argv[1] == "uninstall":
        ok, msg = uninstall()
        print(msg)
        sys.exit(0 if ok else 1)

    if is_installed():
        print(f"meFrpc 已安装: {get_install_path()}")
        if "--force" not in sys.argv:
            print("使用 --force 强制重新安装")
            return
        print("正在强制重新安装...")

    ok, msg = install(force="--force" in sys.argv)
    print(msg)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
