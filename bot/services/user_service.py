from __future__ import annotations

from telegram import ReplyKeyboardMarkup

from config import config
from vpn_service_client import VpnServiceClient
from ..storage import UserStorage
from ..models.user import User


class UserService:
    """High level operations for bot handlers."""

    def __init__(
        self,
        xui: VpnServiceClient,
        storage: UserStorage,
        admin_menu: ReplyKeyboardMarkup,
        main_menu: ReplyKeyboardMarkup,
    ) -> None:
        self.xui = xui
        self.storage = storage
        self._admin_menu = admin_menu
        self._main_menu = main_menu

    # --- utilities -----------------------------------------------------
    def is_admin(self, user_id: int) -> bool:
        return user_id in config.admin_ids

    def menu_for(self, user_id: int) -> ReplyKeyboardMarkup:
        return self._admin_menu if self.is_admin(user_id) else self._main_menu

    async def ensure_user(self, tg_id: int, username: str) -> User:
        user = await self.storage.get(tg_id)
        if not user:
            role = "admin" if self.is_admin(tg_id) else "limited"
            status = "active" if role == "admin" else "awaiting"
            user = await self.storage.add(
                tg_id, username or str(tg_id), role, status
            )
        return user

    # --- xui wrappers --------------------------------------------------
    async def get_user_by_remark(self, remark: str) -> dict | None:
        return await self.xui.get_user_by_remark(remark)

