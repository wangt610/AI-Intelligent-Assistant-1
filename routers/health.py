"""
健康检查路由

提供结构化的服务健康状态端点。
"""

import logging

from fastapi import APIRouter

from services import health_service
from models.schemas import HealthResponse, HealthCheckItem, SearchStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/search/status", response_model=SearchStatusResponse)
async def search_status():
    """检查联网搜索是否已配置。"""
    from config import get_settings
    settings = get_settings()
    if settings.tavily_api_key:
        return SearchStatusResponse(
            configured=True,
            provider=settings.search_provider,
            detail="Tavily API key 已配置",
        )
    return SearchStatusResponse(
        configured=False,
        detail="Tavily API key 未配置，请在 .env 中设置 TAVILY_API_KEY",
    )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """服务健康检查端点"""
    result = await health_service.check_all_health()
    checks = {
        name: HealthCheckItem(**item) for name, item in result["checks"].items()
    }
    return HealthResponse(status=result["overall"], checks=checks)
