"""
索引任务数据库操作

index_tasks 表 CRUD、状态机转换。
"""

import time
import logging

import aiosqlite

logger = logging.getLogger(__name__)


async def init_tasks_table(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS index_tasks (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      TEXT NOT NULL,
            file_name       TEXT NOT NULL,
            file_path       TEXT NOT NULL DEFAULT '',
            status          TEXT NOT NULL DEFAULT 'pending',
            total_chunks    INTEGER DEFAULT 0,
            error_message   TEXT,
            created_at      REAL NOT NULL,
            updated_at      REAL NOT NULL
        )
    """)
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_status ON index_tasks(status)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_session ON index_tasks(session_id)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_session_file ON index_tasks(session_id, file_name)"
    )


async def create_task(db: aiosqlite.Connection, session_id: str, file_name: str, file_path: str = "") -> int:
    now = time.time()
    cursor = await db.execute(
        "INSERT INTO index_tasks (session_id, file_name, file_path, status, created_at, updated_at) "
        "VALUES (?, ?, ?, 'pending', ?, ?)",
        (session_id, file_name, file_path, now, now),
    )
    await db.commit()
    return cursor.lastrowid


async def mark_indexing(db: aiosqlite.Connection, task_id: int) -> None:
    now = time.time()
    await db.execute(
        "UPDATE index_tasks SET status='indexing', updated_at=? WHERE id=?",
        (now, task_id),
    )
    await db.commit()


async def mark_completed(db: aiosqlite.Connection, task_id: int, total_chunks: int) -> None:
    now = time.time()
    await db.execute(
        "UPDATE index_tasks SET status='completed', total_chunks=?, updated_at=? WHERE id=?",
        (total_chunks, now, task_id),
    )
    await db.commit()


async def mark_failed(db: aiosqlite.Connection, task_id: int, error: str) -> None:
    now = time.time()
    await db.execute(
        "UPDATE index_tasks SET status='failed', error_message=?, updated_at=? WHERE id=?",
        (error, now, task_id),
    )
    await db.commit()


async def get_incomplete_tasks(db: aiosqlite.Connection) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM index_tasks WHERE status IN ('pending', 'indexing')"
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_indexed_files_by_session(db: aiosqlite.Connection, session_id: str) -> list[dict]:
    cursor = await db.execute(
        "SELECT file_name, status, total_chunks, MAX(updated_at) as updated_at "
        "FROM index_tasks WHERE session_id=? "
        "GROUP BY file_name ORDER BY updated_at DESC",
        (session_id,),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]
