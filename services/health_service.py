"""
健康检查服务

聚合数据库、Ollama、ChromaDB、搜索服务的健康状态，
将原 routers/health.py 中的多服务编排下沉到 service 层。
"""

import logging

from config import get_settings
from database import check_health as check_db_health
from services.providers import check_ollama_health
from services.rag_service import health_check as check_rag_health

logger = logging.getLogger(__name__)


async def check_all_health() -> dict:
    """执行全量健康检查，返回结构化结果。

    Returns:
        {"overall": "healthy"|"degraded"|"unhealthy",
         "checks": {name: {"status": str, "detail": str}}}
    """
    settings = get_settings()
    checks = {}

    # 数据库
    db_ok = await check_db_health()
    checks["database"] = {
        "status": "healthy" if db_ok else "unhealthy",
        "detail": "SQLite 连接正常" if db_ok else "数据库不可达",
    }

    # Ollama
    ollama_ok, ollama_detail = await check_ollama_health()
    checks["ollama"] = {
        "status": "healthy" if ollama_ok else "degraded",
        "detail": ollama_detail,
    }

    # ChromaDB
    rag_ok, rag_detail = await check_rag_health()
    checks["chromadb"] = {
        "status": "healthy" if rag_ok else "degraded",
        "detail": rag_detail,
    }

    # 搜索服务
    search_ok = bool(settings.tavily_api_key)
    checks["search"] = {
        "status": "healthy" if search_ok else "degraded",
        "detail": "Tavily 已配置" if search_ok else "搜索 API key 未配置",
    }

    # 综合状态
    if db_ok and ollama_ok and rag_ok:
        overall = "healthy"
    elif db_ok:
        overall = "degraded"
    else:
        overall = "unhealthy"

    logger.info("健康检查: status=%s", overall)

    return {"overall": overall, "checks": checks}
