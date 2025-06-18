import unittest
from vpn_service_client import VpnServiceClient

class DummyClient(VpnServiceClient):
    def __init__(self, users):
        self.users = users

    async def list_users(self):
        return self.users

    async def create_user(self, *a, **kw):
        raise NotImplementedError

    async def renew_user(self, *a, **kw):
        raise NotImplementedError

    async def update_user(self, *a, **kw):
        raise NotImplementedError

    async def set_enable(self, *a, **kw):
        raise NotImplementedError

    async def get_vless_link(self, *a, **kw):
        raise NotImplementedError

    async def delete_user(self, *a, **kw):
        raise NotImplementedError

class BaseClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_user_by_remark(self):
        client = DummyClient([
            {"remark": "a", "id": 1},
            {"email": "b", "id": 2},
            {"tgId": "3", "id": 3},
        ])
        user = await client.get_user_by_remark("b")
        self.assertEqual(user["id"], 2)
        user = await client.get_user_by_remark("3")
        self.assertEqual(user["id"], 3)
        self.assertIsNone(await client.get_user_by_remark("none"))

    async def test_get_user_by_id(self):
        client = DummyClient([{"id": "abc"}, {"id": 2}])
        self.assertEqual(await client.get_user_by_id("abc"), {"id": "abc"})
        self.assertEqual(await client.get_user_by_id(2), {"id": 2})
        self.assertIsNone(await client.get_user_by_id(3))

if __name__ == "__main__":
    unittest.main()
