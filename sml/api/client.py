"""ME Frp API 客户端封装."""

import requests
from typing import Any, Optional

from sml.manager.config import Config

BASE_URL = "https://api.mefrp.com/api"
CAPTCHA_URL = "https://www.mefrp.com/3rdparty/captcha"


class APIError(Exception):
    """API 调用异常。"""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class MEFrpAPI:
    """ME Frp API 封装，提供所有公开接口的调用方法。"""

    def __init__(self):
        self.cfg = Config()
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "SML/1.0.0 (Linux TUI Client; https://github.com/sml)",
        })

    # ------------------------------------------------------------------ #
    # 内部工具
    # ------------------------------------------------------------------ #

    def _headers(self) -> dict:
        h = {}
        token = self.cfg.token
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
        auth_required: bool = True,
    ) -> Any:
        """发起 API 请求并返回 data 字段。"""
        url = f"{BASE_URL}{path}"
        headers = self._headers() if auth_required else {}

        try:
            resp = self._session.request(
                method, url, params=params, json=json_data, headers=headers, timeout=30,
            )
        except requests.ConnectionError:
            raise APIError(0, "无法连接到服务器，请检查网络")
        except requests.Timeout:
            raise APIError(0, "请求超时")
        except Exception as e:
            raise APIError(0, f"请求异常: {e}")

        # 检查是否被 CDN/WAF 拦截
        if resp.text and resp.text.strip().startswith("<"):
            raise APIError(0, "请求被 CDN/WAF 拦截，请检查 User-Agent 设置")

        try:
            body = resp.json()
        except ValueError:
            raise APIError(0, f"响应不是有效的 JSON: {resp.text[:200]}")

        code = body.get("code", 500)
        message = body.get("message", "未知错误")

        if code != 200:
            raise APIError(code, message)

        return body.get("data")

    def _get(self, path: str, **kwargs) -> Any:
        return self._request("GET", path, **kwargs)

    def _post(self, path: str, **kwargs) -> Any:
        return self._request("POST", path, **kwargs)

    # ------------------------------------------------------------------ #
    # 人机验证帮助
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_captcha_url(client_name: str = "SML") -> str:
        """返回人机验证页面的 URL，提示用户打开并完成验证。"""
        return f"{CAPTCHA_URL}?client={client_name}"

    @staticmethod
    def decode_captcha_token(encoded: str) -> Optional[str]:
        """解码用户从人机验证页面获取的 token（Base64 解码后取 token||client 的第一段）。"""
        import base64
        try:
            decoded = base64.b64decode(encoded.encode()).decode()
            token = decoded.split("||")[0]
            return token
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    # 公共信息
    # ------------------------------------------------------------------ #

    def get_statistics(self) -> dict:
        """获取统计信息（用户数、节点数、隧道数、流量）。"""
        return self._get("/public/statistics", auth_required=False)

    def get_store_products(self) -> list:
        """获取商城商品列表。"""
        return self._get("/public/store/products", auth_required=False)

    # ------------------------------------------------------------------ #
    # 注册 / 登录
    # ------------------------------------------------------------------ #

    def get_email_code(self, email: str, captcha_token: str) -> str:
        """获取邮箱注册验证码。"""
        data = self._post("/public/register/emailCode", json_data={
            "email": email,
            "captchaToken": captcha_token,
        }, auth_required=False)
        return data  # 成功时 data 为 null，message 包含提示

    def register(self, username: str, email: str, email_code: str, password: str) -> str:
        """注册新账户。"""
        data = self._post("/public/register", json_data={
            "username": username,
            "email": email,
            "emailCode": email_code,
            "password": password,
        }, auth_required=False)
        return data

    def login(self, username: str, password: str, captcha_token: str) -> str:
        """密码登录，成功后将 token 自动存入配置。返回 token。"""
        url = f"{BASE_URL}/public/login"
        headers = {"User-Agent": "SML/1.0.0 (Linux TUI Client; https://github.com/sml)"}

        try:
            resp = self._session.post(url, json={
                "username": username,
                "password": password,
                "captchaToken": captcha_token,
            }, headers=headers, timeout=30)
        except Exception as e:
            raise APIError(0, f"登录请求异常: {e}")

        if resp.text.strip().startswith("<"):
            raise APIError(0, "请求被 CDN/WAF 拦截")

        try:
            body = resp.json()
        except ValueError:
            raise APIError(0, f"响应异常: {resp.text[:200]}")

        code = body.get("code", 500)
        message = body.get("message", "未知错误")

        if code != 200:
            raise APIError(code, message)

        # 尝试从响应头中提取 Bearer token
        token = ""
        auth_header = resp.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        # 也尝试从 Set-Cookie 或其他位置获取
        if not token:
            set_cookie = resp.headers.get("Set-Cookie", "")
            if "token=" in set_cookie:
                for part in set_cookie.split(";"):
                    if "token=" in part:
                        token = part.split("token=", 1)[1].strip()
        # 如果 body data 中有 token
        data = body.get("data")
        if not token and isinstance(data, dict):
            token = data.get("token", data.get("accessToken", ""))

        if token:
            self.cfg.token = token
            self.cfg.username = username
        return token

    def forgot_password(self, username: str, password: str) -> str:
        """找回账户。"""
        return self._post("/public/iforgot", json_data={
            "username": username,
            "password": password,
        }, auth_required=False)

    # ------------------------------------------------------------------ #
    # 隧道相关
    # ------------------------------------------------------------------ #

    def get_create_proxy_data(self) -> dict:
        """获取创建隧道所需的所有数据（节点信息、用户组等）。"""
        return self._get("/auth/createProxyData")

    def get_proxy_list(self) -> dict:
        """获取隧道列表。"""
        return self._get("/auth/proxy/list")

    def create_proxy(self, **kwargs) -> Any:
        """创建隧道（新版本）。字段见 API 文档。"""
        return self._post("/auth/proxy/create", json_data=kwargs)

    def delete_proxy(self, proxy_id: int) -> str:
        """删除指定隧道。"""
        return self._post("/auth/proxy/delete", json_data={"proxyId": proxy_id})

    def kick_proxy(self, proxy_id: int) -> str:
        """强制下线指定隧道。"""
        return self._post("/auth/proxy/kick", json_data={"proxyId": proxy_id})

    def toggle_proxy(self, proxy_id: int, is_disabled: bool) -> str:
        """启用/禁用隧道。"""
        return self._post("/auth/proxy/toggle", json_data={
            "proxyId": proxy_id,
            "isDisabled": is_disabled,
        })

    def get_proxy_config(self, proxy_id: int, fmt: str = "toml") -> dict:
        """获取单一隧道配置。fmt: toml/json/yml/ini。"""
        return self._post("/auth/proxy/config", json_data={
            "proxyId": proxy_id,
            "format": fmt,
        })

    def get_multiple_proxy_config(self, proxy_ids: list[int], fmt: str = "toml") -> dict:
        """获取多个隧道配置（Beta）。"""
        return self._post("/auth/proxy/config/multiple", json_data={
            "proxyIds": proxy_ids,
            "format": fmt,
        })

    def update_proxy(self, **kwargs) -> Any:
        """更新隧道（已弃用，建议使用新版本）。"""
        return self._post("/auth/proxy/update", json_data=kwargs)

    # ------------------------------------------------------------------ #
    # 账户相关
    # ------------------------------------------------------------------ #

    def get_user_info(self) -> dict:
        """获取当前用户信息。"""
        return self._get("/auth/user/info")

    def sign_in(self, captcha_token: str) -> str:
        """签到（需人机验证）。"""
        return self._post("/auth/user/sign", json_data={"captchaToken": captcha_token})

    def get_frp_token(self) -> str:
        """获取用户 frpToken（启动令牌）。"""
        data = self._get("/auth/user/frpToken")
        if isinstance(data, dict):
            return data.get("token", "")
        return ""

    def get_user_groups(self) -> dict:
        """获取用户组信息。"""
        return self._get("/auth/user/groups")

    def reset_access_key(self, captcha_token: str) -> dict:
        """重置访问密钥（需人机验证）。返回新密钥。"""
        return self._post("/auth/user/tokenReset", json_data={"captchaToken": captcha_token})

    def change_password(self, old_password: str, new_password: str) -> str:
        """修改密码。"""
        return self._post("/auth/user/passwordReset", json_data={
            "oldPassword": old_password,
            "newPassword": new_password,
        })

    def get_operation_logs(
        self, page: int = 1, page_size: int = 20,
        start_time: Optional[str] = None, end_time: Optional[str] = None,
    ) -> dict:
        """获取用户操作日志。"""
        params = {"page": page, "pageSize": page_size}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return self._get("/auth/operationLog/list", params=params)

    def get_log_stats(self) -> dict:
        """获取用户日志统计。"""
        return self._get("/auth/operationLog/stats")

    def lottery_draw(self) -> dict:
        """权益抽取（抽奖）。"""
        return self._post("/auth/user/luckydraw")

    def get_lottery_remaining(self) -> dict:
        """获取剩余抽奖次数。"""
        return self._get("/auth/user/luckydraw")

    # ------------------------------------------------------------------ #
    # 节点相关
    # ------------------------------------------------------------------ #

    def get_node_list(self) -> list:
        """获取节点列表。"""
        return self._get("/auth/node/list")

    def get_node_name_list(self) -> list:
        """获取节点连接地址列表（仅已有隧道的节点）。"""
        return self._get("/auth/node/nameList")

    def get_node_status(self) -> list:
        """获取节点状态。"""
        return self._get("/auth/node/status")

    def get_node_secret(self, node_id: int) -> dict:
        """获取节点 Token 和服务端口。"""
        return self._post("/auth/node/secret", json_data={"nodeId": node_id})

    # ------------------------------------------------------------------ #
    # 系统相关
    # ------------------------------------------------------------------ #

    def get_system_status(self) -> dict:
        """获取系统状态。"""
        return self._get("/auth/system/status")

    def get_notice(self) -> str:
        """获取系统公告（Markdown）。"""
        return self._get("/auth/notice")

    def get_popup_notice(self) -> str:
        """获取重要公告（Markdown）。"""
        return self._get("/auth/popupNotice")


# 更方便的 setter —— 手动设置 token（登录后从 UI 获取）
def set_token_direct(token: str):
    """在 UI 层手动设置 token。"""
    cfg = Config()
    cfg.token = token
