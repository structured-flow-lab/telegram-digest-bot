"""Async SQLite connection via aiosqlite."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiosqlite

from app import config


@asynccontextmanager
async def get_connection() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async context manager that yields an open aiosqlite connection."""
    async with aiosqlite.connect(config.DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA foreign_keys=ON")
        yield conn
