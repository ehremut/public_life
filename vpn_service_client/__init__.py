"""Abstract VPN service client interface and factory."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import List, Optional

from threexui.api import ThreeXUI, XUIRequestError

__all__ = [
    "VpnServiceClient",
    "ApiVpnServiceClient",
    "LocalVpnServiceClient",
    "get_vpn_service_client",
    "XUIRequestError",
]


class VpnServiceClient(ABC):
    """Abstract base class for VPN configuration backends."""

    @abstractmethod
    async def list_users(self) -> List[dict]:
        """Return all configured users."""

    async def get_user_by_remark(self, remark: str) -> Optional[dict]:
        users = await self.list_users()
        for user in users:
            if (
                user.get("remark") == remark
                or user.get("email") == remark
                or str(user.get("tgId")) == remark
            ):
                return user
        return None

    async def get_user_by_id(self, user_id: str | int) -> Optional[dict]:
        users = await self.list_users()
        for user in users:
            if str(user.get("id")) == str(user_id):
                return user
        return None

    @abstractmethod
    async def create_user(
        self,
        remark: str,
        days: int,
        tg_id: str | None = None,
        *,
        ip_limit: int = 4,
        custom_id: str | None = None,
        username: str | None = None,
    ) -> dict:
        """Create a new user."""

    @abstractmethod
    async def renew_user(self, user_id: int, days: int) -> None:
        """Extend user's expiry."""

    @abstractmethod
    async def update_user(
        self,
        user_id: int,
        days: int,
        *,
        ip_limit: int | None = None,
        enable: bool | None = None,
    ) -> dict:
        """Replace existing user settings."""

    @abstractmethod
    async def set_enable(self, user_id: int, enabled: bool) -> dict:
        """Enable or disable a user."""

    @abstractmethod
    async def get_vless_link(self, user: dict) -> str:
        """Return VLESS link for a user."""

    @abstractmethod
    async def delete_user(self, user_id: str | int) -> None:
        """Remove a user."""


from .api_client import ApiVpnServiceClient  # noqa: E402
from .local_client import LocalVpnServiceClient  # noqa: E402


def get_vpn_service_client() -> VpnServiceClient:
    """Return an appropriate client based on ``VPN_BACKEND_TYPE``."""
    from config import config

    backend = (os.getenv("VPN_BACKEND_TYPE") or config.vpn_backend_type).lower()
    if backend == "local":
        path = os.getenv("VPN_CONFIG_PATH") or config.vpn_config_path
        return LocalVpnServiceClient(path, inbound_id=config.xui_inbound_id)
    xui = ThreeXUI(
        os.getenv("XUI_API_URL", config.xui_api_url),
        os.getenv("XUI_LOGIN", config.xui_login),
        os.getenv("XUI_PSW", config.xui_psw),
        inbound_id=int(os.getenv("XUI_INBOUND_ID", str(config.xui_inbound_id))),
    )
    return ApiVpnServiceClient(xui)
