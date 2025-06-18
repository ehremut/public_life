import unittest
import os
import json
import tempfile
from vpn_service_client import LocalVpnServiceClient, get_vpn_service_client, ApiVpnServiceClient
from threexui.api import ThreeXUI


class LocalClientTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg_path = os.path.join(self.tmp.name, "config.json")
        data = {"inbounds": [{"id": 2, "settings": {"clients": []}}]}
        with open(self.cfg_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)

    async def asyncTearDown(self):
        self.tmp.cleanup()

    async def test_create_user_writes_file_and_backup(self):
        client = LocalVpnServiceClient(self.cfg_path, inbound_id=2)
        await client.create_user("test", 1)
        with open(self.cfg_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(len(data["inbounds"][0]["settings"]["clients"]), 1)
        self.assertTrue(os.path.exists(self.cfg_path + ".bak"))

    async def test_full_flow(self):
        client = LocalVpnServiceClient(self.cfg_path, inbound_id=2)
        user = await client.create_user("rem", 1)
        uid = user["id"]
        users = await client.list_users()
        self.assertEqual(len(users), 1)
        await client.renew_user(uid, 1)
        users = await client.list_users()
        renewed = users[0]["expiryTime"]
        await client.update_user(uid, 2, ip_limit=10, enable=False)
        users = await client.list_users()
        updated = users[0]
        self.assertEqual(updated["limitIp"], 10)
        self.assertFalse(updated["enable"])
        self.assertGreater(updated["expiryTime"], renewed)
        link = await client.get_vless_link(updated)
        self.assertIn("vless://", link)
        await client.delete_user(uid)
        self.assertEqual(await client.list_users(), [])

    async def test_inbound_not_found(self):
        other = LocalVpnServiceClient(self.cfg_path, inbound_id=99)
        with self.assertRaises(Exception):
            await other.list_users()


class FactoryTests(unittest.TestCase):
    def test_get_vpn_service_client_api(self):
        os.environ["VPN_BACKEND_TYPE"] = "api"
        cli = get_vpn_service_client()
        self.assertIsInstance(cli, ApiVpnServiceClient)
        self.assertIsInstance(cli.xui, ThreeXUI)


if __name__ == "__main__":
    unittest.main()
