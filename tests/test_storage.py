import unittest
import tempfile
import os
import json

from bot.storage import UserStorage
class StorageTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, 'users.db')
        self.json_path = os.path.join(self.tmp.name, 'users.json')
        with open(self.json_path, 'w', encoding='utf-8') as fh:
            json.dump([
                {
                    "user_id": 1,
                    "username": "test",
                    "role": "admin",
                    "status": "active",
                    "request_days": 0,
                    "days": 0,
                    "remark": "",
                    "xui_id": None,
                    "config_counter": 0,
                }
            ], fh)
        self.store = UserStorage(self.db_path, self.json_path)

    async def asyncTearDown(self):
        await self.store._connect()  # ensure connection closed gracefully
        if self.store.conn:
            await self.store.conn.close()
        self.tmp.cleanup()

    async def test_migrate_from_json(self):
        user = await self.store.get(1)
        self.assertIsNotNone(user)
        self.assertFalse(os.path.exists(self.json_path))

    async def test_add_and_list(self):
        await self.store.add(2, 'name', 'limited', 'awaiting')
        users = await self.store.list_all()
        ids = {u.user_id for u in users}
        self.assertIn(2, ids)

