from __future__ import annotations

import os
import json
import shutil
import time
import uuid
import asyncio
from pathlib import Path
from typing import List

from threexui.api import XUIRequestError

from . import VpnServiceClient


class LocalVpnServiceClient(VpnServiceClient):
    """Manage 3x-ui configuration directly via local files."""

    def __init__(self, config_path: str | None = None, inbound_id: int = 2) -> None:
        self.config_path = Path(config_path or os.getenv("VPN_CONFIG_PATH", "config.json"))
        self.inbound_id = inbound_id

    async def _read_config(self) -> dict:
        return await asyncio.to_thread(self._read_config_sync)

    def _read_config_sync(self) -> dict:
        with self.config_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    async def _write_config(self, data: dict) -> None:
        await asyncio.to_thread(self._write_config_sync, data)

    def _write_config_sync(self, data: dict) -> None:
        backup = self.config_path.with_suffix(self.config_path.suffix + ".bak")
        if self.config_path.exists():
            shutil.copy2(self.config_path, backup)
        tmp = self.config_path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, self.config_path)

    def _get_inbound(self, cfg: dict) -> dict:
        inbounds = cfg.get("inbounds", [])
        for inbound in inbounds:
            if str(inbound.get("id")) == str(self.inbound_id):
                return inbound
        raise XUIRequestError("Inbound not found")

    async def list_users(self) -> List[dict]:
        cfg = await self._read_config()
        inbound = self._get_inbound(cfg)
        settings = inbound.get("settings", {})
        if isinstance(settings, str):
            try:
                settings = json.loads(settings)
            except ValueError:
                settings = {}
        return list(settings.get("clients", []))

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
        cfg = await self._read_config()
        inbound = self._get_inbound(cfg)
        settings = inbound.get("settings", {})
        if isinstance(settings, str):
            try:
                settings = json.loads(settings)
            except ValueError:
                settings = {}
        clients = settings.setdefault("clients", [])
        tg = tg_id or remark
        email = tg
        if username:
            email = f"{username}_{tg}"
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
            "tgId": tg,
            "subId": "",
            "reset": 0,
        }
        clients.append(client)
        inbound["settings"] = settings
        await self._write_config(cfg)
        return client

    async def renew_user(self, user_id: int, days: int) -> None:
        cfg = await self._read_config()
        inbound = self._get_inbound(cfg)
        settings = inbound.get("settings", {})
        if isinstance(settings, str):
            settings = json.loads(settings)
        clients = settings.get("clients", [])
        now_ms = int(time.time() * 1000)
        for user in clients:
            if str(user.get("id")) == str(user_id):
                expiry = int(user.get("expiryTime", 0))
                if expiry and expiry < 1_000_000_000_000:
                    expiry *= 1000
                base = max(expiry, now_ms)
                user["expiryTime"] = base + days * 86400000
                await self._write_config(cfg)
                return
        raise XUIRequestError("User not found")

    async def update_user(
        self,
        user_id: int,
        days: int,
        *,
        ip_limit: int | None = None,
        enable: bool | None = None,
    ) -> dict:
        cfg = await self._read_config()
        inbound = self._get_inbound(cfg)
        settings = inbound.get("settings", {})
        if isinstance(settings, str):
            settings = json.loads(settings)
        clients = settings.get("clients", [])
        now_ms = int(time.time() * 1000)
        for user in clients:
            if str(user.get("id")) == str(user_id):
                user["expiryTime"] = now_ms + days * 86400000
                if ip_limit is not None:
                    user["limitIp"] = ip_limit
                if enable is not None:
                    user["enable"] = enable
                await self._write_config(cfg)
                return user
        raise XUIRequestError("User not found")

    async def set_enable(self, user_id: int, enabled: bool) -> dict:
        return await self.update_user(user_id, 0, enable=enabled)

    async def get_vless_link(self, user: dict) -> str:
        cfg = await self._read_config()
        inbound = self._get_inbound(cfg)
        address = inbound.get("listen") or inbound.get("address", "")
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
        query = "&".join(params)
        remark = user.get("remark", "")
        url = f"vless://{user.get('id')}@{address}:{port}?{query}"
        if remark:
            url += "#" + remark
        return url

    async def delete_user(self, user_id: str | int) -> None:
        cfg = await self._read_config()
        inbound = self._get_inbound(cfg)
        settings = inbound.get("settings", {})
        if isinstance(settings, str):
            settings = json.loads(settings)
        clients = settings.get("clients", [])
        new_clients = [c for c in clients if str(c.get("id")) != str(user_id)]
        if len(new_clients) == len(clients):
            raise XUIRequestError("User not found")
        settings["clients"] = new_clients
        inbound["settings"] = settings
        await self._write_config(cfg)
