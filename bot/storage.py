import os
import json
from pathlib import Path
from typing import List, Optional

import aiosqlite

from .models.user import User


class UserStorage:
    """SQLite-based user repository with optional JSON migration."""

    def __init__(self, db_path: str = "users.db", json_path: str = "users.json") -> None:
        self.db_path = db_path
        self.json_path = json_path
        self.conn: Optional[aiosqlite.Connection] = None

    async def _connect(self) -> aiosqlite.Connection:
        if self.conn is None:
            self.conn = await aiosqlite.connect(self.db_path)
            await self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    role TEXT,
                    status TEXT,
                    request_days INTEGER,
                    days INTEGER,
                    remark TEXT,
                    xui_id TEXT,
                    config_counter INTEGER
                )
                """
            )
            await self.conn.commit()
            await self._maybe_migrate()
        return self.conn

    async def _maybe_migrate(self) -> None:
        conn = await self._connect()
        async with conn.execute("SELECT COUNT(*) FROM users") as cur:
            row = await cur.fetchone()
        if row[0] == 0 and Path(self.json_path).exists():
            with open(self.json_path, "r", encoding="utf-8") as fh:
                try:
                    items = json.load(fh)
                except ValueError:
                    items = []
            for item in items:
                await self.add(**item)
            os.remove(self.json_path)

    async def list_all(self) -> List[User]:
        conn = await self._connect()
        async with conn.execute("SELECT * FROM users") as cur:
            rows = await cur.fetchall()
        return [User(*row) for row in rows]

    async def get(self, user_id: int) -> Optional[User]:
        conn = await self._connect()
        async with conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
        return User(*row) if row else None

    async def add(
        self,
        user_id: int,
        username: str,
        role: str,
        status: str,
        request_days: int = 0,
        days: int = 0,
        remark: str = "",
        xui_id: str | None = None,
        config_counter: int = 0,
    ) -> User:
        conn = await self._connect()
        await conn.execute(
            """
            INSERT INTO users (user_id, username, role, status, request_days, days, remark, xui_id, config_counter)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                role,
                status,
                request_days,
                days,
                remark,
                xui_id,
                config_counter,
            ),
        )
        await conn.commit()
        return User(
            user_id=user_id,
            username=username,
            role=role,
            status=status,
            request_days=request_days,
            days=days,
            remark=remark,
            xui_id=xui_id,
            config_counter=config_counter,
        )

    async def update(self, user: User, **fields) -> None:
        conn = await self._connect()
        for key, value in fields.items():
            setattr(user, key, value)
        await conn.execute(
            """
            UPDATE users
            SET username=?, role=?, status=?, request_days=?, days=?, remark=?, xui_id=?, config_counter=?
            WHERE user_id=?
            """,
            (
                user.username,
                user.role,
                user.status,
                user.request_days,
                user.days,
                user.remark,
                user.xui_id,
                user.config_counter,
                user.user_id,
            ),
        )
        await conn.commit()

    async def delete(self, user_id: int) -> None:
        conn = await self._connect()
        await conn.execute("DELETE FROM users WHERE user_id=?", (user_id,))
        await conn.commit()
