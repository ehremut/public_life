import unittest
from unittest.mock import AsyncMock

from telegram import ReplyKeyboardMarkup

from bot.services.user_service import UserService
from bot.models.user import User
from config import config


class UserServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.storage = AsyncMock()
        self.xui = AsyncMock()
        self.admin_menu = ReplyKeyboardMarkup([["a"]])
        self.main_menu = ReplyKeyboardMarkup([["b"]])
        self.service = UserService(self.xui, self.storage, self.admin_menu, self.main_menu)
        self.orig_admin = config.admin_ids
        config.admin_ids = [1]

    async def asyncTearDown(self):
        config.admin_ids = self.orig_admin

    async def test_is_admin_and_menu(self):
        self.assertTrue(self.service.is_admin(1))
        self.assertFalse(self.service.is_admin(2))
        self.assertIs(self.service.menu_for(1), self.admin_menu)
        self.assertIs(self.service.menu_for(2), self.main_menu)

    async def test_ensure_user_existing(self):
        user = User(1, "u", "admin", "active")
        self.storage.get.return_value = user
        result = await self.service.ensure_user(1, "name")
        self.storage.get.assert_awaited_once_with(1)
        self.storage.add.assert_not_called()
        self.assertIs(result, user)

    async def test_ensure_user_new(self):
        self.storage.get.return_value = None
        new_user = User(2, "n", "limited", "awaiting")
        self.storage.add.return_value = new_user
        result = await self.service.ensure_user(2, "n")
        self.storage.add.assert_awaited_once()
        self.assertEqual(result.role, "limited")
        self.assertEqual(result.status, "awaiting")

    async def test_get_user_by_remark(self):
        self.xui.get_user_by_remark.return_value = {"id": "5"}
        res = await self.service.get_user_by_remark("5")
        self.xui.get_user_by_remark.assert_awaited_with("5")
        self.assertEqual(res, {"id": "5"})


if __name__ == "__main__":
    unittest.main()
