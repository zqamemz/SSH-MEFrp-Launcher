"""签到屏幕."""

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Static, Header, Footer, Input, Label
from textual import work

from sml.api.client import MEFrpAPI, APIError
from sml.utils.clipboard import paste_to_input


class SignInScreen(Screen):
    """每日签到屏幕。"""

    TITLE = "每日签到 - SML"

    CSS = """
    SignInScreen {
        align: center middle;
    }

    #signin-box {
        width: 60;
        height: auto;
        padding: 2 3;
        background: #1f2335;
        border: solid #3b4261;
    }

    #signin-box > Static {
        margin-bottom: 1;
    }

    #signin-box > Input {
        margin-bottom: 1;
    }

    #signin-box > Horizontal {
        height: auto;
        align: center middle;
    }

    /* 输入框 + 粘贴按钮的横向布局：输入框自适应，按钮固定宽度 */
    #signin-box > Horizontal > Input {
        width: 1fr;
        margin-right: 1;
    }

    #signin-msg {
        height: 3;
    }

    #signin-result {
        height: auto;
        border: solid #3b4261;
        padding: 1 2;
        margin-top: 1;
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
        with Vertical(id="signin-box"):
            yield Static("每日签到", classes="title")
            yield Label("人机验证 Token:")
            with Horizontal():
                yield Input(placeholder="先完成人机验证并粘贴 Token 到此", id="captcha")
                yield Button("📋 粘贴", id="btn-paste-captcha", classes="paste-btn")
            yield Static("打开人机验证页面 → 验证 → 粘贴 Token", classes="label")
            yield Static("", id="signin-msg")
            with Horizontal():
                yield Button("立即签到", id="btn-signin", variant="primary")
                yield Button("返回", id="btn-back")
            yield Static("", id="signin-result")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-signin":
            self.do_signin()
        elif event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-paste-captcha":
            self._paste_into("captcha")

    @work(exclusive=True)
    async def do_signin(self):
        captcha_w = self.query_one("#captcha")
        captcha = captcha_w.value.strip() if isinstance(captcha_w, Input) else ""

        if not captcha:
            self._msg("请先完成人机验证")
            return

        btn = self.query_one("#btn-signin")
        if isinstance(btn, Button):
            btn.disabled = True
            btn.label = "签到中..."

        try:
            result = self.api.sign_in(captcha)
            msg_w = self.query_one("#signin-msg")
            if isinstance(msg_w, Static):
                msg_w.update("✓ 签到成功！")
                msg_w.styles.color = "#27ae60"
            result_w = self.query_one("#signin-result")
            if isinstance(result_w, Static):
                r = result if isinstance(result, str) else str(result)
                result_w.update(f"签到结果: {r}")
        except Exception as e:
            self._msg(f"签到失败: {e}")
        finally:
            if isinstance(btn, Button):
                btn.disabled = False
                btn.label = "立即签到"

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

    def _msg(self, text: str, error: bool = True):
        w = self.query_one("#signin-msg")
        if isinstance(w, Static):
            w.update(f"{'⚠' if error else '✓'} {text}")
            w.styles.color = "#e74c3c" if error else "#27ae60"
