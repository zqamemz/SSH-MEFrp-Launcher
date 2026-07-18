"""手动粘贴屏幕 - 用于 SSH 环境等无法读取系统剪贴板时的替代方案。"""

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Input, Static, Header, Footer, Label


class ManualPasteScreen(Screen):
    """手动粘贴屏幕。

    当系统剪贴板不可用时（如 SSH 环境），提供一个输入框让用户
    使用终端模拟器的粘贴功能（Ctrl+Shift/V 或右键粘贴）来粘贴文本。
    """

    TITLE = "手动粘贴 - SML"

    CSS = """
    ManualPasteScreen {
        align: center middle;
    }

    #paste-box {
        width: 60;
        height: auto;
        padding: 2 3;
        background: #1f2335;
        border: solid #3b4261;
    }

    #paste-box > Static {
        margin-bottom: 1;
    }

    #paste-box > Label {
        margin-bottom: 1;
    }

    #paste-box > Input {
        margin-bottom: 1;
    }

    #paste-instruction {
        color: #565f89;
        text-style: italic;
        height: auto;
        text-align: center;
    }

    #paste-title {
        text-style: bold;
        color: #7dcfff;
        content-align: center middle;
        height: 3;
    }

    #paste-msg {
        height: 3;
        color: #e67e22;
    }

    #paste-actions {
        height: auto;
        margin-top: 1;
        align: center middle;
    }

    #paste-actions > Button {
        margin: 0 1;
        min-width: 12;
    }
    """

    def __init__(self, input_id: str = ""):
        super().__init__()
        self._target_input_id = input_id

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="paste-box"):
            yield Static("手动粘贴", id="paste-title")
            yield Static(
                "系统剪贴板不可用（SSH 远程环境）\n"
                "请使用终端模拟器的粘贴功能将内容粘贴到下方输入框：",
                id="paste-instruction",
            )
            yield Label("粘贴内容（Ctrl+Shift+V / 右键粘贴）:")
            yield Input(placeholder="在此粘贴...", id="manual-paste-input")
            yield Static("", id="paste-msg")
            with Horizontal(id="paste-actions"):
                yield Button("✓ 确认", id="btn-confirm", variant="primary")
                yield Button("✗ 取消", id="btn-cancel")
        yield Footer()

    def on_mount(self):
        """自动聚焦到输入框。"""
        w = self.query_one("#manual-paste-input")
        if isinstance(w, Input):
            w.focus()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-confirm":
            self._confirm()
        elif event.button.id == "btn-cancel":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "manual-paste-input":
            self._confirm()

    def _confirm(self):
        w = self.query_one("#manual-paste-input")
        if isinstance(w, Input):
            text = w.value.strip()
            if text:
                self.dismiss(text)
            else:
                msg = self.query_one("#paste-msg")
                if isinstance(msg, Static):
                    msg.update("⚠ 内容不能为空，请粘贴后再确认")
