"""创建隧道屏幕."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Header, Footer, Static, Select
from textual import work

from sml.api.client import MEFrpAPI, APIError


class TunnelCreateScreen(Screen):
    """创建隧道表单。"""

    TITLE = "创建隧道 - SML"

    CSS = """
    TunnelCreateScreen {
        align: center top;
    }

    #create-form {
        width: 60;
        height: auto;
        padding: 1 2;
        background: #1f2335;
        border: solid #3b4261;
        margin: 1 0;
    }

    #create-form > Label {
        margin-top: 1;
    }

    #create-form > Input, #create-form > Select {
        margin-bottom: 1;
    }

    #create-actions {
        height: auto;
        margin-top: 1;
        align: center middle;
    }

    #create-actions > Button {
        margin: 0 1;
    }

    #create-msg {
        height: 3;
    }
    """

    def __init__(self):
        super().__init__()
        self.api = MEFrpAPI()
        self.nodes: list = []
        self.proxy_types = ["tcp", "udp", "http", "https", "stcp", "xtcp"]

    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer():
            with Vertical(id="create-form"):
                yield Static("创建新隧道", classes="title")
                yield Label("隧道名称:")
                yield Input(placeholder="例如: 我的MC服务器", id="t-name")
                yield Label("隧道类型:")
                yield Select(
                    [(t, t) for t in self.proxy_types],
                    id="t-type", value="tcp",
                )
                yield Label("选择节点:")
                yield Select([], id="t-node")
                yield Label("本地地址:")
                yield Input(placeholder="例如: 127.0.0.1", id="t-local-addr", value="127.0.0.1")
                yield Label("本地端口:")
                yield Input(placeholder="例如: 25565", id="t-local-port")
                yield Label("远程端口 (TCP/UDP):")
                yield Input(placeholder="留空自动分配", id="t-remote-port")
                yield Label("域名 (HTTP/HTTPS):")
                yield Input(placeholder="例如: example.com", id="t-domain")
                yield Static("", id="create-msg")
                with Horizontal(id="create-actions"):
                    yield Button("创建隧道", id="btn-create", variant="primary")
                    yield Button("返回", id="btn-back")
        yield Footer()

    def on_mount(self):
        self._load_nodes()

    @work(exclusive=True)
    async def _load_nodes(self):
        msg = self.query_one("#create-msg")
        if isinstance(msg, Static):
            msg.update("正在加载节点列表...")
        try:
            data = self.api.get_create_proxy_data()
            nodes = data if isinstance(data, list) else data.get("nodes", data.get("nodeList", []))
            self.nodes = nodes
            select = self.query_one("#t-node")
            if isinstance(select, Select):
                options = []
                for n in nodes:
                    if isinstance(n, dict):
                        nid = n.get("nodeId", n.get("id", 0))
                        nname = n.get("nodeName", n.get("name", f"节点{nid}"))
                        options.append((f"{nname} (ID:{nid})", str(nid)))
                select.set_options(options)
                if isinstance(msg, Static):
                    msg.update(f"已加载 {len(nodes)} 个节点")
                    msg.styles.color = "#27ae60"
        except Exception as e:
            if isinstance(msg, Static):
                msg.update(f"加载节点失败: {e}")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-create":
            self.do_create()
        elif event.button.id == "btn-back":
            self.app.pop_screen()

    def _get(self, id_: str) -> str:
        w = self.query_one(f"#{id_}")
        if isinstance(w, Input):
            return w.value.strip()
        return ""

    def _msg(self, text: str, error: bool = True):
        w = self.query_one("#create-msg")
        if isinstance(w, Static):
            w.update(f"{'⚠' if error else '✓'} {text}")
            w.styles.color = "#e74c3c" if error else "#27ae60"

    @work(exclusive=True)
    async def do_create(self):
        name = self._get("t-name")
        local_addr = self._get("t-local-addr")
        local_port = self._get("t-local-port")
        remote_port = self._get("t-remote-port")
        domain = self._get("t-domain")

        type_select = self.query_one("#t-type")
        node_select = self.query_one("#t-node")

        ptype = type_select.value if isinstance(type_select, Select) else "tcp"
        node_val = node_select.value if isinstance(node_select, Select) else ""

        if not name or not local_port:
            self._msg("请填写隧道名称和本地端口")
            return

        params = {
            "proxyName": name,
            "proxyType": ptype,
            "localAddr": local_addr,
            "localPort": int(local_port),
        }

        if node_val:
            params["nodeId"] = int(node_val) if node_val.isdigit() else node_val
        if remote_port:
            params["remotePort"] = int(remote_port)
        if domain and ptype in ("http", "https"):
            params["domain"] = domain

        btn = self.query_one("#btn-create")
        if isinstance(btn, Button):
            btn.disabled = True
            btn.label = "创建中..."

        try:
            result = self.api.create_proxy(**params)
            self._msg(f"隧道 [{name}] 创建成功！", error=False)
        except Exception as e:
            self._msg(f"创建失败: {e}")
        finally:
            if isinstance(btn, Button):
                btn.disabled = False
                btn.label = "创建隧道"
