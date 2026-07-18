"""SML - ME Frp 终端图形化管理工具.

在 SSH 和真实命令行环境下直接使用的 ME Frp 管理器。
"""

from sml.app import SMLApp


def main():
    app = SMLApp()
    app.run()


if __name__ == "__main__":
    main()
