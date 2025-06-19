import sqlite3
import asyncio

class Cursor:
    def __init__(self, cur):
        self._cur = cur
    async def fetchone(self):
        return await asyncio.to_thread(self._cur.fetchone)
    async def fetchall(self):
        return await asyncio.to_thread(self._cur.fetchall)
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass

class Connection:
    def __init__(self, conn):
        self._conn = conn
    async def execute(self, sql, params=()):
        cur = await asyncio.to_thread(self._conn.execute, sql, params)
        return Cursor(cur)
    async def commit(self):
        await asyncio.to_thread(self._conn.commit)
    async def close(self):
        await asyncio.to_thread(self._conn.close)
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

async def connect(path):
    conn = await asyncio.to_thread(sqlite3.connect, path)
    return Connection(conn)
