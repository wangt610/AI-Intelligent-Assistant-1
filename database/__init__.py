"""
数据库访问层（异步）

使用 aiosqlite 替代同步 sqlite3，消除事件循环阻塞。
所有函数均为 async，通过 async context manager 管理连接生命周期。
"""

import os
import logging

import aiosqlite

from config import get_settings

logger = logging.getLogger(__name__)

# ─── 单例连接 ──────────────────────────────────────────

_db: aiosqlite.Connection | None = None


def _db_path() -> str:
    return get_settings().db_path


async def init_db() -> None:
    """初始化数据库表和索引（应用启动时调用一次）"""
    from database.sessions import init_sessions_table
    from database.messages import init_messages_table
    from database.tasks import init_tasks_table

    global _db
    db_path = _db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    _db = await aiosqlite.connect(db_path)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute("PRAGMA foreign_keys=ON")

    await init_sessions_table(_db)
    await init_messages_table(_db)
    await init_tasks_table(_db)

    await _db.commit()
    logger.info("数据库初始化完成: %s", db_path)


async def close_db() -> None:
    """关闭全局数据库连接（应用关闭时调用）。"""
    global _db
    if _db:
        await _db.close()
        _db = None
        logger.info("数据库连接已关闭")


async def get_db() -> aiosqlite.Connection:
    """获取全局数据库连接。

    使用方式：
        db = await get_db()
        sessions = await get_sessions(db)
    """
    if _db is None:
        raise RuntimeError("数据库未初始化，请先调用 init_db()")
    return _db


# ─── 重新导出子模块公开函数（保持向后兼容） ─────────────

from database.sessions import (
    create_session,
    get_sessions,
    get_session,
    rename_session,
    save_session_summary,
    delete_session,
    search_sessions,
)
from database.messages import (
    save_message,
    delete_message,
    get_messages,
    count_messages,
    get_last_user_message,
    get_message,
    update_message,
    delete_messages_after,
)
from database.tasks import (
    create_task,
    mark_indexing,
    mark_completed,
    mark_failed,
    get_incomplete_tasks,
    get_indexed_files_by_session,
)
from database.health import check_health
