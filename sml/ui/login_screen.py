"""登录屏幕 - 支持密码登录和 Token 直接登录."""

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Header, Footer, Static
from textual import work

from sml.api.client import MEFrpAPI, set_token_direct
from sml.manager.config import Config
from sml.utils.clipboard import paste_to_input, is_ssh_environment


class LoginScreen(Screen):
    """登录屏幕。"""

    TITLE = "登录 - SML"

    CSS = """
    LoginScreen {
        align: center middle;
    }

    #login-box {
        width: 60;
        height: auto;
        padding: 2 3;
        background: #1f2335;
        border: solid #3b4261;
    }

    #login-box > Static {
        margin-bottom: 1;
    }

    #login-box > Input {
        margin-bottom: 1;
    }

    #login-box > Horizontal {
        height: auto;
        margin-top: 1;
        align: center middle;
    }

    /* 输入框 + 粘贴按钮的横向布局：输入框自适应，按钮固定宽度 */
    #login-box > Horizontal > Input {
        width: 1fr;
        margin-right: 1;
    }

    #title-label {
        text-style: bold;
        color: #7dcfff;
        content-align: center middle;
        height: 3;
    }

    #captcha-hint {
        color: #565f89;
        text-style: italic;
        height: 2;
    }

    #msg-log {
        height: 3;
        color: #e67e22;
    }

    .paste-btn {
        min-width: 8;
        height: 3;
        margin: 0 0 1 0;
    }

    .login-btn {
        margin: 0 1;
        min-width: 12;
    }
    """

    def __init__(self):
        super().__init__()
        self.api = MEFrpAPI()
        self.cfg = Config()

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="login-box"):
            yield Static("SML - ME Frp TUI Manager", id="title-label")
            yield Label("用户名 / 邮箱:")
            yield Input(placeholder="输入用户名或邮箱", id="username")
            yield Label("密码:")
            with Horizontal():
                yield Input(placeholder="输入密码", password=True, id="password")
                yield Button("📋 粘贴", id="btn-paste-password", classes="paste-btn")
            yield Label("人机验证 Token (可选):")
            with Horizontal():
                yield Input(placeholder="留空则跳过验证", id="captcha")
                yield Button("📋 粘贴", id="btn-paste-captcha", classes="paste-btn")
            yield Static("打开下方链接完成人机验证，将 token 粘贴到上方", id="captcha-hint")
            yield Static("", id="msg-log")
            with Horizontal():
                yield Button("密码登录", id="btn-login", variant="primary", classes="login-btn")
                yield Button("Token登录", id="btn-token", classes="login-btn")
                yield Button("注册", id="btn-register", classes="login-btn")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed):
        btn_id = event.button.id
        if btn_id == "btn-login":
            self.do_login()
        elif btn_id == "btn-token":
            self.do_token_login()
        elif btn_id == "btn-register":
            self.app.push_screen("register")
        elif btn_id == "btn-paste-captcha":
            self._paste_into("captcha")
        elif btn_id == "btn-paste-password":
            self._paste_into("password")

    def _paste_into(self, input_id: str):
        """将剪贴板内容粘贴到指定 Input 组件。

        在 SSH 等无系统剪贴板环境下手动粘贴回退。
        """
        w = self.query_one(f"#{input_id}")
        if isinstance(w, Input):
            if paste_to_input(w):
                self._set_msg("已粘贴", error=False)
            else:
                # 系统剪贴板不可用，打开手动粘贴屏幕
                self._manual_paste_fallback(w)

    def _manual_paste_fallback(self, target_input: Input):
        """当系统剪贴板不可用时，打开手动粘贴屏幕。"""

        def handle_paste(result: Optional[str]):
            if result:
                cursor_pos = target_input.cursor_position
                old_value = target_input.value
                new_value = old_value[:cursor_pos] + result + old_value[cursor_pos:]
                target_input.value = new_value
                target_input.cursor_position = cursor_pos + len(result)
                self._set_msg("已粘贴", error=False)

        self.app.push_screen("manual_paste", handle_paste)

    def _get_input(self, id_: str) -> str:
        widget = self.query_one(f"#{id_}")
        if isinstance(widget, Input):
            return widget.value.strip()
        return ""

    def _set_msg(self, msg: str, error: bool = True):
        w = self.query_one("#msg-log")
        if isinstance(w, Static):
            if error:
                w.update(f"⚠ {msg}")
                w.styles.color = "#e74c3c"
            else:
                w.update(f"✓ {msg}")
                w.styles.color = "#27ae60"

    @work(exclusive=True)
    async def do_login(self):
        username = self._get_input("username")
        password = self._get_input("password")
        captcha = self._get_input("captcha")

        if not username or not password:
            self._set_msg("请填写用户名和密码")
            return

        btn = self.query_one("#btn-login")
        if isinstance(btn, Button):
            btn.disabled = True
            btn.label = "登录中..."
        try:
            token = self.api.login(username, password, captcha)
            if token:
                self._set_msg("登录成功！", error=False)
                self.app.push_screen("main")
            else:
                self._set_msg("登录成功，但未获取到 Token。请使用 Token 登录方式手动填写")
        except Exception as e:
            self._set_msg(f"登录失败: {e}")
        finally:
            if isinstance(btn, Button):
                btn.disabled = False
                btn.label = "密码登录"

    @work(exclusive=True)
    async def do_token_login(self):
        token = self._get_input("captcha") or self._get_input("password")
        if not token:
            self._set_msg("请在验证 Token 字段输入 Token，或在密码字段输入 Token")
            return

        btn = self.query_one("#btn-token")
        if isinstance(btn, Button):
            btn.disabled = True
            btn.label = "验证中..."
        try:
            set_token_direct(token)
            self.cfg.token = token
            # 尝试获取用户信息验证 token 有效性
            info = self.api.get_user_info()
            if info:
                username = info.get("username", info.get("email", "用户"))
                self.cfg.username = username
                self._set_msg(f"Token 验证成功！欢迎 {username}", error=False)
                self.app.push_screen("main")
            else:
                self._set_msg("Token 无效或已过期")
                self.cfg.token = ""
        except Exception as e:
            self._set_msg(f"Token 验证失败: {e}")
            self.cfg.token = ""
        finally:
            if isinstance(btn, Button):
                btn.disabled = False
                btn.label = "Token登录"

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "captcha":
            self.do_login()
