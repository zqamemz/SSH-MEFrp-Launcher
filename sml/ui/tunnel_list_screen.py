"""隧道列表屏幕."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static, Header, Footer, DataTable, Label
from textual import work

from sml.api.client import MEFrpAPI, APIError


class TunnelListScreen(Screen):
    """隧道列表 - 显示所有隧道并支持操作。"""

    TITLE = "隧道列表 - SML"

    CSS = """
    TunnelListScreen {
        align: center top;
    }

    #tunnel-controls {
        height: auto;
        margin: 1 2;
        align: center middle;
    }

    #tunnel-controls > Button {
        margin: 0 1;
    }

    #tunnel-table {
        margin: 0 2;
        height: 1fr;
    }

    #tunnel-actions {
        height: auto;
        margin: 1 2;
        align: center middle;
    }

    #tunnel-actions > Button {
        margin: 0 1;
    }

    #tunnel-msg {
        height: 3;
        margin: 0 2;
    }

    .detail-label {
        color: #565f89;
        padding: 0 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.api = MEFrpAPI()
        self.proxies: list = []
        self.selected_id: int = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("隧道管理", classes="title")
        with Horizontal(id="tunnel-controls"):
            yield Button("刷新列表", id="btn-refresh", variant="primary")
            yield Button("新建隧道", id="btn-create", variant="success")
            yield Button("返回菜单", id="btn-back")
        yield DataTable(id="tunnel-table")
        yield Static("", id="tunnel-msg")
        with Horizontal(id="tunnel-actions"):
            yield Button("查看详情", id="btn-detail", variant="primary")
            yield Button("启动", id="btn-start", variant="success")
            yield Button("停止", id="btn-stop", variant="warning")
            yield Button("删除", id="btn-delete", variant="error")
        yield Footer()

    def on_mount(self):
        table = self.query_one("#tunnel-table")
        if isinstance(table, DataTable):
            table.add_columns("ID", "名称", "类型", "节点", "本地端口", "状态", "域名")
        self.refresh_data()

    def on_button_pressed(self, event: Button.Pressed):
        btn_id = event.button.id
        if btn_id == "btn-refresh":
            self.refresh_data()
        elif btn_id == "btn-create":
            self.app.push_screen("tunnel_create")
        elif btn_id == "btn-back":
            self.app.pop_screen()
        elif btn_id == "btn-detail":
            self.view_detail()
        elif btn_id == "btn-start":
            self.toggle_tunnel(start=True)
        elif btn_id == "btn-stop":
            self.toggle_tunnel(start=False)
        elif btn_id == "btn-delete":
            self.delete_selected()

    @work(exclusive=True)
    async def refresh_data(self):
        msg = self.query_one("#tunnel-msg")
        table = self.query_one("#tunnel-table")
        if isinstance(msg, Static):
            msg.update("正在加载...")
        try:
            data = self.api.get_proxy_list()
            if isinstance(data, list):
                self.proxies = data
            elif isinstance(data, dict):
                self.proxies = data.get("proxies", data.get("data", data.get("list", [])))
                if not self.proxies and "proxies" not in data:
                    self.proxies = [data]  # 单条记录

            if isinstance(table, DataTable):
                table.clear()
                for p in self.proxies:
                    if not isinstance(p, dict):
                        continue
                    pid = p.get("proxyId", p.get("id", "?"))
                    name = p.get("proxyName", p.get("name", "未命名"))
                    ptype = p.get("proxyType", p.get("type", "?"))
                    node = p.get("nodeName", p.get("node", "?"))
                    local = p.get("localAddr", p.get("localPort", "?"))
                    status = "启用" if not p.get("isDisabled", False) else "禁用"
                    domain = p.get("domain", p.get("customDomain", ""))
                    table.add_row(str(pid), name, ptype, node, str(local), status, str(domain))

            if isinstance(msg, Static):
                msg.update(f"共 {len(self.proxies)} 条隧道")
                msg.styles.color = "#27ae60"

        except Exception as e:
            if isinstance(msg, Static):
                msg.update(f"加载失败: {e}")
                msg.styles.color = "#e74c3c"

    def get_selected(self) -> dict:
        table = self.query_one("#tunnel-table")
        if not isinstance(table, DataTable):
            return {}
        cursor = table.cursor_row
        if cursor is None or cursor >= len(self.proxies):
            return {}
        return self.proxies[cursor]

    def view_detail(self):
        proxy = self.get_selected()
        if not proxy:
            self._msg("请先选择一个隧道")
            return
        pid = proxy.get("proxyId", proxy.get("id", 0))
        self.app.current_tunnel_id = pid
        self.app.push_screen("tunnel_detail")

    @work(exclusive=True)
    async def toggle_tunnel(self, start: bool):
        proxy = self.get_selected()
        if not proxy:
            self._msg("请先选择一个隧道")
            return
        pid = proxy.get("proxyId", proxy.get("id", 0))
        try:
            self.api.toggle_proxy(pid, is_disabled=not start)
            self._msg(f"{'启用' if start else '禁用'}成功", error=False)
            self.refresh_data()
        except Exception as e:
            self._msg(f"操作失败: {e}")

    @work(exclusive=True)
    async def delete_selected(self):
        proxy = self.get_selected()
        if not proxy:
            self._msg("请先选择一个隧道")
            return
        pid = proxy.get("proxyId", proxy.get("id", 0))
        name = proxy.get("proxyName", proxy.get("name", ""))
        # 直接删除，确认由用户快捷键操作
        try:
            self.api.delete_proxy(pid)
            self._msg(f"隧道 [{name}] 已删除", error=False)
            self.refresh_data()
        except Exception as e:
            self._msg(f"删除失败: {e}")

    def _msg(self, text: str, error: bool = False):
        w = self.query_one("#tunnel-msg")
        if isinstance(w, Static):
            w.update(text)
            w.styles.color = "#e74c3c" if error else "#27ae60"
