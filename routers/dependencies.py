"""
路由器共享依赖

集中管理 FastAPI Depends 和常量，消除路由器间的样板重复。
"""

from fastapi import Depends
from database import get_db


SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


async def db_session():
    """注入数据库连接。"""
    return await get_db()

