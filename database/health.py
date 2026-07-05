"""
数据库健康检查
"""

import logging

from database import get_db

logger = logging.getLogger(__name__)


async def check_health() -> bool:
    """检查数据库连通性，用于健康检查端点。"""
    try:
        db = await get_db()
        await db.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error("数据库健康检查失败: %s", e)
        return False
