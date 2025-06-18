from __future__ import annotations

from typing import List

from threexui.api import ThreeXUI

from . import VpnServiceClient


class ApiVpnServiceClient(VpnServiceClient):
    """Client that delegates all operations to :class:`ThreeXUI`."""

    def __init__(self, xui: ThreeXUI) -> None:
        self.xui = xui

    async def list_users(self) -> List[dict]:
        return await self.xui.list_users()

    async def create_user(self, *args, **kwargs) -> dict:  # type: ignore[override]
        return await self.xui.create_user(*args, **kwargs)

    async def renew_user(self, user_id: int, days: int) -> None:  # type: ignore[override]
        await self.xui.renew_user(user_id, days)

    async def update_user(self, *args, **kwargs) -> dict:  # type: ignore[override]
        return await self.xui.update_user(*args, **kwargs)

    async def set_enable(self, user_id: int, enabled: bool) -> dict:  # type: ignore[override]
        return await self.xui.set_enable(user_id, enabled)

    async def get_vless_link(self, user: dict) -> str:  # type: ignore[override]
        return await self.xui.get_vless_link(user)

    async def delete_user(self, user_id: str | int) -> None:  # type: ignore[override]
        await self.xui.delete_user(user_id)
