import unittest
from unittest.mock import patch, Mock, AsyncMock
import time
import aiohttp
import json

from threexui.api import ThreeXUI, XUIRequestError


class APITestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.api = ThreeXUI("http://xui", "user", "pass")
        self.session = AsyncMock()
        self.session.closed = False
        self.api._ensure_session = AsyncMock(return_value=self.session)
        self.api.login = AsyncMock(return_value=("tok", time.time() + 3600))

    async def test_list_users_request_error(self):
        self.session.get = AsyncMock(side_effect=aiohttp.ClientError)
        with self.assertRaises(XUIRequestError):
            await self.api.list_users()

    async def test_get_user_by_remark_propagates_error(self):
        with patch.object(self.api, "list_users", side_effect=XUIRequestError):
            with self.assertRaises(XUIRequestError):
                await self.api.get_user_by_remark("1")

    async def test_get_user_by_remark_matches_email(self):
        self.api.list_users = AsyncMock(return_value=[{"id": 1, "email": "foo"}])
        user = await self.api.get_user_by_remark("foo")
        self.assertEqual(user, {"id": 1, "email": "foo"})

    async def test_list_users_parses_inbound(self):
        payload = {
            "success": True,
            "obj": {"settings": '{"clients": [{"email": "a"}]}'},
        }
        mock_resp = AsyncMock()
        mock_resp.__aenter__.return_value = mock_resp
        mock_resp.__aexit__ = AsyncMock(return_value=None)
        mock_resp.json.return_value = payload
        mock_resp.raise_for_status.return_value = None
        async def _get(*a, **kw):
            return mock_resp
        self.session.get.side_effect = _get
        users = await self.api.list_users()
        self.assertEqual(users, [{"email": "a"}])
        self.session.get.assert_called_once_with(
            self.api._url("/panel/api/inbounds/get/2"), timeout=10
        )

    async def test_create_user_success(self):
        post_resp = Mock()
        post_resp.json.return_value = {"success": True, "msg": "ok", "obj": None}
        post_resp.raise_for_status.return_value = None
        post_cm = AsyncMock()
        post_cm.__aenter__ = AsyncMock(return_value=post_resp)
        post_cm.__aexit__ = AsyncMock(return_value=None)
        async def _post(*a, **kw):
            return post_cm
        self.session.post.side_effect = _post
        with patch.object(self.api, "get_user_by_remark", AsyncMock(return_value={"id": 1})), \
             patch("threexui.api.time.time", return_value=1000):
            user = await self.api.create_user("foo", 1)
        self.assertEqual(user, {"id": 1})
        self.session.post.assert_called_once()
        called_data = self.session.post.call_args.kwargs["json"]
        self.assertEqual(called_data["id"], 2)
        settings = json.loads(called_data["settings"])
        client = settings["clients"][0]
        self.assertEqual(client["email"], "foo")
        self.assertEqual(client["tgId"], "foo")
        self.assertEqual(client["expiryTime"], 1000 * 1000 + 86400000)

    async def test_create_user_username_email(self):
        post_resp = Mock()
        post_resp.json.return_value = {"success": True, "msg": "ok", "obj": None}
        post_resp.raise_for_status.return_value = None
        post_cm = AsyncMock()
        post_cm.__aenter__ = AsyncMock(return_value=post_resp)
        post_cm.__aexit__ = AsyncMock(return_value=None)
        async def _post(*a, **kw):
            return post_cm
        self.session.post.side_effect = _post
        with patch.object(self.api, "get_user_by_remark", AsyncMock(return_value={})) , \
             patch("threexui.api.time.time", return_value=1000):
            await self.api.create_user("foo", 1, tg_id="123", username="name")
        called_data = self.session.post.call_args.kwargs["json"]
        settings = json.loads(called_data["settings"])
        client = settings["clients"][0]
        self.assertEqual(client["email"], "name_123")

    async def test_create_user_request_error(self):
        self.session.post = AsyncMock(side_effect=aiohttp.ClientError)
        with self.assertRaises(XUIRequestError):
            await self.api.create_user("foo", 1)

    async def test_renew_user_adds_to_expiry(self):
        now = 1000 * 1000
        user = {"id": 5, "expiryTime": now + 3 * 86400000, "email": "foo"}
        post_resp = Mock()
        post_resp.raise_for_status.return_value = None
        post_cm = AsyncMock()
        post_cm.__aenter__ = AsyncMock(return_value=post_resp)
        post_cm.__aexit__ = AsyncMock(return_value=None)
        async def _post(*a, **kw):
            return post_cm
        self.session.post.side_effect = _post
        with patch.object(self.api, "list_users", AsyncMock(return_value=[user])), \
             patch("threexui.api.time.time", return_value=now/1000):
            await self.api.renew_user(5, 1)

        self.assertEqual(
            self.session.post.call_args.args[0],
            self.api._url("/panel/api/inbounds/updateClient/5"),
        )
        payload = self.session.post.call_args.kwargs["json"]
        self.assertEqual(payload["id"], 2)
        settings = json.loads(payload["settings"])
        client = settings["clients"][0]
        expected = (now + 3 * 86400000) * 1000 + 86400000
        self.assertEqual(client["expiryTime"], expected)

    async def test_update_user_sets_expiry(self):
        now = 1000 * 1000
        user = {"id": 5, "expiryTime": now + 3 * 86400000, "limitIp": 1}
        post_resp = Mock()
        post_resp.raise_for_status.return_value = None
        post_cm = AsyncMock()
        post_cm.__aenter__ = AsyncMock(return_value=post_resp)
        post_cm.__aexit__ = AsyncMock(return_value=None)
        async def _post(*a, **kw):
            return post_cm
        self.session.post.side_effect = _post
        with patch.object(self.api, "list_users", AsyncMock(return_value=[user])), \
             patch("threexui.api.time.time", return_value=now/1000):
            await self.api.update_user(5, 2, ip_limit=5)

        self.assertEqual(
            self.session.post.call_args.args[0],
            self.api._url("/panel/api/inbounds/updateClient/5"),
        )
        payload = self.session.post.call_args.kwargs["json"]
        settings = json.loads(payload["settings"])
        client = settings["clients"][0]
        self.assertEqual(client["limitIp"], 5)
        self.assertEqual(client["expiryTime"], now + 2 * 86400000)

    async def test_set_enable(self):
        user = {"id": 5, "enable": True}
        post_resp = Mock()
        post_resp.raise_for_status.return_value = None
        post_cm = AsyncMock()
        post_cm.__aenter__ = AsyncMock(return_value=post_resp)
        post_cm.__aexit__ = AsyncMock(return_value=None)
        async def _post(*a, **kw):
            return post_cm
        self.session.post.side_effect = _post
        with patch.object(self.api, "list_users", AsyncMock(return_value=[user])):
            await self.api.set_enable(5, False)

        payload = self.session.post.call_args.kwargs["json"]
        settings = json.loads(payload["settings"])
        client = settings["clients"][0]
        self.assertFalse(client["enable"])

    async def test_get_vless_link_prefers_existing(self):
        link = await self.api.get_vless_link({"link": "foo"})
        self.assertEqual(link, "foo")

    async def test_get_vless_link_builds_from_inbound(self):
        inbound = {
            "listen": "example.com",
            "port": 443,
            "streamSettings": json.dumps({
                "network": "ws",
                "security": "tls",
                "wsSettings": {"path": "/ws", "headers": {"Host": "host"}}
            })
        }
        with patch.object(self.api, "_get_inbound", AsyncMock(return_value=inbound)):
            link = await self.api.get_vless_link({"id": "uuid", "remark": "r"})
        self.assertIn("vless://uuid@example.com:443", link)
        self.assertIn("type=ws", link)
        self.assertIn("security=tls", link)
        self.assertIn("host=host", link)
        self.assertIn("path=%2Fws", link)
        self.assertTrue(link.endswith("#r"))

    async def test_get_vless_link_reality(self):
        inbound = {
            "port": 443,
            "streamSettings": json.dumps({
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "settings": {
                        "publicKey": "PUB",
                        "fingerprint": "chrome",
                        "spiderX": "/"
                    },
                    "serverNames": ["example.com"],
                    "shortIds": ["abcd"]
                }
            })
        }
        with patch.object(self.api, "_get_inbound", AsyncMock(return_value=inbound)):
            link = await self.api.get_vless_link({"id": "u"})
        self.assertIn("pbk=PUB", link)
        self.assertIn("fp=chrome", link)
        self.assertIn("sni=example.com", link)
        self.assertIn("sid=abcd", link)
        self.assertIn("spx=%2F", link)


if __name__ == "__main__":
    unittest.main()
