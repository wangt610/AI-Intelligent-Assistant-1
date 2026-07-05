"""
消息数据库操作

messages 表 CRUD、消息编辑/删除、查询。
"""

import logging
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)


async def init_messages_table(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            role        TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
            content     TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'completed' CHECK(status IN ('completed', 'interrupted', 'failed')),
            created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
    """)
    # 迁移：为已有数据库添加 status 列
    try:
        await db.execute(
            "ALTER TABLE messages ADD COLUMN status TEXT NOT NULL DEFAULT 'completed' "
            "CHECK(status IN ('completed', 'interrupted', 'failed'))"
        )
        await db.commit()
        logger.info("已为 messages 表添加 status 列")
    except Exception:
        pass

    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_session_role ON messages(session_id, role, id)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id, id)"
    )


async def save_message(db: aiosqlite.Connection, session_id: str, role: str, content: str, status: str = "completed") -> int:
    cursor = await db.execute(
        "INSERT INTO messages (session_id, role, content, status) VALUES (?, ?, ?, ?)",
        (session_id, role, content, status),
    )
    await db.commit()
    message_id = cursor.lastrowid
    return message_id


async def delete_message(db: aiosqlite.Connection, message_id: int) -> None:
    """按主键删除单条消息，用于流式失败时回滚刚写入的用户消息。"""
    await db.execute("DELETE FROM messages WHERE id = ?", (message_id,))
    await db.commit()


async def get_messages(db: aiosqlite.Connection, session_id: str, limit: int = 20, after_id: int | None = None) -> list[dict]:
    """获取会话最近的 limit 条消息，按时间升序排列。
    
    after_id: 只返回 id > 此值的消息（用于跳过已压缩的旧消息）。
    """
    if after_id is not None:
        cursor = await db.execute(
            """SELECT id, session_id, role, content, created_at
               FROM messages
               WHERE session_id = ? AND id > ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (session_id, after_id, limit),
        )
    else:
        cursor = await db.execute(
            """SELECT id, session_id, role, content, created_at
               FROM messages
               WHERE session_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (session_id, limit),
        )
    rows = await cursor.fetchall()
    rows = list(reversed(rows))
    return [dict(r) for r in rows]


async def count_messages(db: aiosqlite.Connection, session_id: str, after_id: int | None = None) -> int:
    if after_id is not None:
        cursor = await db.execute(
            "SELECT COUNT(*) AS cnt FROM messages WHERE session_id = ? AND id > ?",
            (session_id, after_id),
        )
    else:
        cursor = await db.execute(
            "SELECT COUNT(*) AS cnt FROM messages WHERE session_id = ?",
            (session_id,),
        )
    row = await cursor.fetchone()
    return row["cnt"] if row else 0


async def get_last_user_message(db: aiosqlite.Connection, session_id: str) -> Optional[dict]:
    """获取会话中最后一条用户消息。"""
    cursor = await db.execute(
        """SELECT id, session_id, role, content, created_at
           FROM messages
           WHERE session_id = ? AND role = 'user'
           ORDER BY id DESC LIMIT 1""",
        (session_id,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_message(db: aiosqlite.Connection, message_id: int) -> Optional[dict]:
    """按主键获取单条消息。"""
    cursor = await db.execute(
        "SELECT id, session_id, role, content, created_at FROM messages WHERE id = ?",
        (message_id,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def update_message(db: aiosqlite.Connection, message_id: int, content: str) -> None:
    """更新消息内容。"""
    await db.execute(
        "UPDATE messages SET content = ? WHERE id = ?",
        (content, message_id),
    )
    await db.commit()


async def delete_messages_after(db: aiosqlite.Connection, message_id: int, session_id: str) -> int:
    """删除指定消息及其之后的所有消息，返回删除数量。"""
    cursor = await db.execute(
        "DELETE FROM messages WHERE session_id = ? AND id >= ?",
        (session_id, message_id),
    )
    await db.commit()
    return cursor.rowcount
