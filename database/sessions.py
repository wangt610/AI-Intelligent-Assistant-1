"""
会话数据库操作

sessions 表 CRUD、搜索、概要更新。
"""

import uuid
import logging
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)


async def init_sessions_table(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL DEFAULT '新对话',
            created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    # 迁移：为 sessions 添加 summary 列（历史摘要缓存）
    try:
        await db.execute("ALTER TABLE sessions ADD COLUMN summary TEXT DEFAULT ''")
        await db.commit()
        logger.info("已为 sessions 表添加 summary 列")
    except Exception:
        pass

    # 迁移：为 sessions 添加 compressed_up_to_id 列（水位线压缩标记）
    try:
        await db.execute("ALTER TABLE sessions ADD COLUMN compressed_up_to_id INTEGER DEFAULT NULL")
        await db.commit()
        logger.info("已为 sessions 表添加 compressed_up_to_id 列")
    except Exception:
        pass

    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at)"
    )


async def create_session(db: aiosqlite.Connection, title: str = "新对话") -> str:
    session_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO sessions (id, title) VALUES (?, ?)",
        (session_id, title),
    )
    await db.commit()
    return session_id


async def get_sessions(db: aiosqlite.Connection) -> list[dict]:
    cursor = await db.execute(
        "SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_session(db: aiosqlite.Connection, session_id: str) -> Optional[dict]:
    cursor = await db.execute(
        "SELECT id, title, summary, compressed_up_to_id, created_at, updated_at FROM sessions WHERE id = ?",
        (session_id,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def rename_session(db: aiosqlite.Connection, session_id: str, title: str) -> None:
    await db.execute(
        "UPDATE sessions SET title = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
        (title, session_id),
    )
    await db.commit()


async def save_session_summary(db: aiosqlite.Connection, session_id: str, summary: str, compressed_up_to_id: int | None = None) -> None:
    if compressed_up_to_id is not None:
        await db.execute(
            "UPDATE sessions SET summary = ?, compressed_up_to_id = ? WHERE id = ?",
            (summary, compressed_up_to_id, session_id),
        )
    else:
        await db.execute(
            "UPDATE sessions SET summary = ? WHERE id = ?",
            (summary, session_id),
        )
    await db.commit()


async def delete_session(db: aiosqlite.Connection, session_id: str) -> None:
    await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    await db.commit()


async def search_sessions(db: aiosqlite.Connection, query: str, limit: int = 20) -> list[dict]:
    """按标题模糊搜索会话，同时搜索消息内容。"""
    cursor = await db.execute(
        """SELECT id, title, created_at, updated_at FROM sessions WHERE title LIKE ?
           UNION
           SELECT id, title, created_at, updated_at FROM sessions
           WHERE id IN (SELECT session_id FROM messages WHERE content LIKE ?)
           ORDER BY updated_at DESC
           LIMIT ?""",
        (f"%{query}%", f"%{query}%", limit),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]
