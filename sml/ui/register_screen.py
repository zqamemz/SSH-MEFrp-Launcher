"""注册屏幕."""

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Header, Footer, Static
from textual import work

from sml.api.client import MEFrpAPI
from sml.utils.clipboard import paste_to_input


class RegisterScreen(Screen):
    """用户注册屏幕。"""

    TITLE = "注册 - SML"

    CSS = """
    RegisterScreen {
        align: center middle;
    }

    #register-box {
        width: 60;
        height: auto;
        padding: 2 3;
        background: #1f2335;
        border: solid #3b4261;
    }

    #register-box > Static {
        margin-bottom: 1;
    }

    #register-box > Input {
        margin-bottom: 1;
    }

    #register-box > Horizontal {
        height: auto;
        margin-top: 1;
        align: center middle;
    }

    /* 输入框 + 按钮的横向布局：输入框自适应，按钮固定宽度 */
    #register-box > Horizontal > Input {
        width: 1fr;
        margin-right: 1;
    }

    #reg-title {
        text-style: bold;
        color: #7dcfff;
        content-align: center middle;
        height: 3;
    }

    #reg-msg {
        height: 3;
    }
    .paste-btn {
        min-width: 8;
        height: 3;
        margin: 0 0 1 0;
    }
    """

    def __init__(self):
        super().__init__()
        self.api = MEFrpAPI()

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="register-box"):
            yield Static("注册 ME Frp 账号", id="reg-title")
            yield Label("用户名:")
            yield Input(placeholder="2-16 位字母数字组合", id="reg-username")
            yield Label("邮箱:")
            yield Input(placeholder="用于接收验证码", id="reg-email")
            yield Label("邮箱验证码:")
            with Horizontal():
                yield Input(placeholder="输入邮箱验证码", id="reg-emailcode")
                yield Button("获取验证码", id="btn-get-code", variant="default")
            yield Label("密码:")
            yield Input(placeholder="至少 8 位", password=True, id="reg-password")
            yield Label("人机验证 Token:")
            with Horizontal():
                yield Input(placeholder="需先完成人机验证", id="reg-captcha")
                yield Button("📋 粘贴", id="btn-paste-captcha", classes="paste-btn")
            yield Static("", id="reg-msg")
            with Horizontal():
                yield Button("注册", id="btn-register", variant="primary")
                yield Button("返回登录", id="btn-back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed):
        btn_id = event.button.id
        if btn_id == "btn-register":
            self.do_register()
        elif btn_id == "btn-get-code":
            self.get_email_code()
        elif btn_id == "btn-back":
            self.app.pop_screen()
        elif btn_id == "btn-paste-captcha":
            self._paste_into("reg-captcha")

    def _paste_into(self, input_id: str):
        w = self.query_one(f"#{input_id}")
        if isinstance(w, Input):
            if paste_to_input(w):
                self._msg("已粘贴", error=False)
            else:
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
                self._msg("已粘贴", error=False)

        self.app.push_screen("manual_paste", handle_paste)

    def _get(self, id_: str) -> str:
        w = self.query_one(f"#{id_}")
        if isinstance(w, Input):
            return w.value.strip()
        return ""

    def _msg(self, text: str, error: bool = True):
        w = self.query_one("#reg-msg")
        if isinstance(w, Static):
            w.update(f"{'⚠' if error else '✓'} {text}")
            w.styles.color = "#e74c3c" if error else "#27ae60"

    @work(exclusive=True)
    async def get_email_code(self):
        email = self._get("reg-email")
        captcha = self._get("reg-captcha")
        if not email:
            self._msg("请先输入邮箱")
            return
        if not captcha:
            self._msg("请先完成人机验证并输入 Token")
            return
        btn = self.query_one("#btn-get-code")
        if isinstance(btn, Button):
            btn.disabled = True
        try:
            self.api.get_email_code(email, captcha)
            self._msg("验证码已发送，请检查邮箱", error=False)
        except Exception as e:
            self._msg(f"获取失败: {e}")
        finally:
            if isinstance(btn, Button):
                btn.disabled = False

    @work(exclusive=True)
    async def do_register(self):
        username = self._get("reg-username")
        email = self._get("reg-email")
        email_code = self._get("reg-emailcode")
        password = self._get("reg-password")
        captcha = self._get("reg-captcha")

        if not all([username, email, email_code, password, captcha]):
            self._msg("请填写所有字段")
            return

        btn = self.query_one("#btn-register")
        if isinstance(btn, Button):
            btn.disabled = True
            btn.label = "注册中..."
        try:
            self.api.register(username, email, email_code, password)
            self._msg("注册成功！请返回登录", error=False)
        except Exception as e:
            self._msg(f"注册失败: {e}")
        finally:
            if isinstance(btn, Button):
                btn.disabled = False
                btn.label = "注册"
