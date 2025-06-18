from typing import Optional, List, Tuple
import time
import json
import uuid
import aiohttp
import asyncio
import re
from urllib.parse import quote, urlparse


_SANITIZE_RE = re.compile(r"[^a-zA-Z0-9_-]")


def _sanitize(value: str, limit: int = 64) -> str:
    """Return ``value`` stripped of unsafe characters."""
    return _SANITIZE_RE.sub("_", value)[:limit]


class XUIRequestError(Exception):
    """Raised when a request to the 3x-ui panel fails."""


class ThreeXUI:
    """Client for interacting with 3x-ui panel."""

    def __init__(self, base_url: str, username: str, password: str, inbound_id: int = 2) -> None:
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session: aiohttp.ClientSession | None = None
        self.inbound_id = inbound_id
        self._token: Optional[str] = None
        self._token_expiry: Optional[float] = None
        self._login_lock = asyncio.Lock()

    async def close(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    async def login(self) -> Tuple[str, float]:
        """Authenticate with the 3x-ui panel and obtain a token.

        This implementation expects the panel to provide a ``/login`` API
        endpoint that accepts the API key and returns a JSON object with the
        token and its expiry time.  The exact endpoint may vary between
        installations; adjust the request as needed for your environment.
        """

        data = {
            "username": self.username,
            "password": self.password,
        }
        session = await self._ensure_session()
        try:
            # Some deployments require an initial request to obtain a CSRF cookie
            await session.get(self._url("/login"), timeout=10)
            resp = await session.post(
                self._url("/login"),
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
            resp.raise_for_status()
            payload = await resp.json()
        except aiohttp.ClientError as exc:
            raise XUIRequestError("Failed to authenticate") from exc

        if not payload.get("success", False):
            raise XUIRequestError("Authentication failed")
        token_cookie = session.cookie_jar.filter_cookies(self.base_url).get(
            "3x-ui"
        )
        token = token_cookie.value if token_cookie else None
        if not token:
            raise XUIRequestError("Missing authentication cookie")

        expiry = time.time() + 3600
        return token, expiry


    async def _ensure_token(self) -> None:
        expired = self._token_expiry is not None and time.time() >= self._token_expiry
        if self._token is None or expired:
            async with self._login_lock:
                expired = self._token_expiry is not None and time.time() >= self._token_expiry
                if self._token is None or expired:
                    self._token, self._token_expiry = await self.login()

    async def _get_inbound(self) -> dict:
        """Return inbound configuration for the configured ID."""
        await self._ensure_token()
        session = await self._ensure_session()
        try:
            resp = await session.get(
                self._url(f"/panel/api/inbounds/get/{self.inbound_id}"),
                timeout=10,
            )
            resp.raise_for_status()
            data = await resp.json()
        except aiohttp.ClientError as exc:
            raise XUIRequestError("Failed to get inbound") from exc

        if not data.get("success", False):
            raise XUIRequestError("Failed to get inbound")

        return data.get("obj", {})

    async def list_users(self) -> List[dict]:
        """Return all users for the configured inbound."""
        try:
            inbound = await self._get_inbound()
        except XUIRequestError as exc:
            raise XUIRequestError("Failed to list users") from exc

        settings = inbound.get("settings", "{}")
        if isinstance(settings, str):
            try:
                settings = json.loads(settings)
            except ValueError as exc:
                raise XUIRequestError("Invalid settings format") from exc
        return settings.get("clients", [])

    async def get_user_by_remark(self, remark: str) -> Optional[dict]:
        """Find user by ``remark``, ``email`` or ``tgId`` field."""
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
        """Return user with the given ID.

        ``user_id`` can be a numeric ID or a UUID string depending on the
        panel configuration.  We therefore compare the IDs as strings to avoid
        ``ValueError`` when casting to ``int``.
        """

        users = await self.list_users()
        for user in users:
            if str(user.get("id")) == str(user_id):
                return user
        return None

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
        """Create a VLESS user for the configured inbound.

        ``remark`` is the identifier shown in the panel. ``tg_id`` is stored in
        the ``email`` and ``tgId`` fields so the user can be found later by
        Telegram ID.  When ``tg_id`` is not provided, ``remark`` is used for all
        three fields for backwards compatibility.
        """
        await self._ensure_token()
        remark = _sanitize(remark)
        if tg_id is None:
            tg_id = remark
        else:
            tg_id = _sanitize(tg_id)

        email = tg_id
        if username:
            username = _sanitize(username)
            email = f"{username}_{tg_id}"
        if custom_id:
            custom_id = _sanitize(custom_id)

        now_ms = int(time.time() * 1000)
        client = {
            "id": custom_id or str(uuid.uuid4()),
            "email": email,
            "remark": remark,
            "flow": "",
            "limitIp": ip_limit,
            "totalGB": 0,
            "expiryTime": now_ms + days * 86400000,
            "enable": True,
            "tgId": tg_id,
            "subId": "",
            "reset": 0,
        }
        payload = {
            "id": self.inbound_id,
            "settings": json.dumps({"clients": [client]}),
        }
        session = await self._ensure_session()
        try:
            resp = await session.post(
                self._url("/panel/api/inbounds/addClient"),
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
            data = await resp.json()
        except aiohttp.ClientError as exc:
            raise XUIRequestError("Failed to create user") from exc
        except ValueError as exc:
            raise XUIRequestError("Invalid response") from exc

        if not data.get("success", False):
            msg = data.get("msg") or "Failed to create user"
            raise XUIRequestError(str(msg))

        # Fetch the created user to return complete info including the link
        return await self.get_user_by_remark(remark) or {}

    async def renew_user(self, user_id: int, days: int) -> None:
        """Extend existing user by a number of days."""
        await self._ensure_token()
        user = await self.get_user_by_id(user_id)
        if not user:
            raise XUIRequestError("User not found")

        try:
            expiry = int(user.get("expiryTime", 0))
        except (TypeError, ValueError):
            expiry = 0

        now_ms = int(time.time() * 1000)
        if expiry and expiry < 1_000_000_000_000:
            expiry *= 1000

        base = max(expiry, now_ms)
        user["expiryTime"] = base + days * 86400000

        payload = {
            "id": self.inbound_id,
            "settings": json.dumps({"clients": [user]}),
        }
        session = await self._ensure_session()
        try:
            resp = await session.post(
                self._url(f"/panel/api/inbounds/updateClient/{user_id}"),
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
        except aiohttp.ClientError as exc:
            raise XUIRequestError("Failed to renew user") from exc

    async def update_user(
        self,
        user_id: int,
        days: int,
        *,
        ip_limit: int | None = None,
        enable: bool | None = None,
    ) -> dict:
        """Replace an existing user's expiry time and optionally IP limit or status."""
        await self._ensure_token()
        user = await self.get_user_by_id(user_id)
        if not user:
            raise XUIRequestError("User not found")

        now_ms = int(time.time() * 1000)
        user["expiryTime"] = now_ms + days * 86400000
        if ip_limit is not None:
            user["limitIp"] = ip_limit
        if enable is not None:
            user["enable"] = enable

        payload = {
            "id": self.inbound_id,
            "settings": json.dumps({"clients": [user]}),
        }
        session = await self._ensure_session()
        try:
            resp = await session.post(
                self._url(f"/panel/api/inbounds/updateClient/{user_id}"),
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
        except aiohttp.ClientError as exc:
            raise XUIRequestError("Failed to update user") from exc
        return user

    async def set_enable(self, user_id: int, enabled: bool) -> dict:
        """Enable or disable an existing user without changing other settings."""
        await self._ensure_token()
        user = await self.get_user_by_id(user_id)
        if not user:
            raise XUIRequestError("User not found")

        user["enable"] = enabled

        payload = {
            "id": self.inbound_id,
            "settings": json.dumps({"clients": [user]}),
        }
        session = await self._ensure_session()
        try:
            resp = await session.post(
                self._url(f"/panel/api/inbounds/updateClient/{user_id}"),
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
        except aiohttp.ClientError as exc:
            raise XUIRequestError("Failed to update user") from exc
        return user

    async def get_vless_link(self, user: dict) -> str:
        """Return the VLESS connection URL for a user."""
        link = user.get("link")
        if link:
            return link

        try:
            inbound = await self._get_inbound()
        except XUIRequestError:
            return ""

        address = inbound.get("listen") or inbound.get("address", "")
        if not address:
            host = urlparse(self.base_url).hostname
            if host:
                address = host
        port = inbound.get("port", "")
        stream = inbound.get("streamSettings", {})
        if isinstance(stream, str):
            try:
                stream = json.loads(stream)
            except ValueError:
                stream = {}

        params = ["encryption=none"]
        network = stream.get("network")
        if network:
            params.append(f"type={network}")
        security = stream.get("security")
        if security:
            params.append(f"security={security}")
        reality = None
        if security == "reality":
            reality = stream.get("realitySettings") or stream.get("reality")
        if network == "ws":
            ws = stream.get("wsSettings", {})
            path = ws.get("path", "")
            host = ws.get("headers", {}).get("Host", "")
            if path:
                params.append("path=" + quote(path, safe=""))
            if host:
                params.append("host=" + quote(host))
        if reality:
            settings = reality.get("settings", {})
            pbk = reality.get("publicKey") or settings.get("publicKey")
            if pbk:
                params.append("pbk=" + quote(str(pbk)))
            fp = reality.get("fingerprint") or settings.get("fingerprint")
            if fp:
                params.append("fp=" + quote(str(fp)))
            sni = reality.get("serverName") or reality.get("serverNames")
            if isinstance(sni, list):
                sni = sni[0] if sni else ""
            if sni:
                params.append("sni=" + quote(str(sni)))
            sid = reality.get("shortId") or reality.get("shortIds")
            if isinstance(sid, list):
                sid = sid[0] if sid else ""
            if sid:
                params.append("sid=" + quote(str(sid)))
            spx = reality.get("spiderX") or settings.get("spiderX")
            if spx:
                params.append("spx=" + quote(str(spx), safe=""))

        remark = user.get("remark", "")
        query = "&".join(params)
        url = f"vless://{user.get('id')}@{address}:{port}?{query}"
        if remark:
            url += "#" + quote(remark)
        return url

    async def delete_user(self, user_id: str | int) -> None:
        """Remove user from the inbound."""
        await self._ensure_token()
        payload = {"id": self.inbound_id}
        session = await self._ensure_session()
        try:
            resp = await session.post(
                self._url(f"/panel/api/inbounds/{self.inbound_id}/delClient/{user_id}"),
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
        except aiohttp.ClientError as exc:
            raise XUIRequestError("Failed to delete user") from exc
