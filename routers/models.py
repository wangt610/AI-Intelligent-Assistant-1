"""
模型管理路由

提供可用模型列表的查询接口。
"""

import logging

from fastapi import APIRouter

from models.schemas import ModelListResponse, OkResponse
from services.model_manager import discover_models, invalidate_cache

logger = logging.getLogger(__name__)

router = APIRouter(tags=["models"])


@router.get("/models", response_model=ModelListResponse)
async def list_models():
    """返回所有可用的模型列表。"""
    try:
        models = await discover_models()
        return {"models": models}
    except Exception as e:
        logger.error("获取模型列表失败: %s", e)
        return {"models": [], "error": str(e)}


@router.post("/models/refresh", response_model=ModelListResponse)
async def refresh_models():
    """强制刷新模型缓存并重新查询。"""
    invalidate_cache()
    models = await discover_models(force_refresh=True)
    return {"models": models}


@router.post("/models/warm", response_model=OkResponse)
async def warm_model(model_source: str = "ollama", model_id: str = ""):
    """手动预热指定模型，消除冷启动延迟。"""
    from config import get_settings
    from services.model_warmup import get_warmup_manager
    settings = get_settings()
    ok = await get_warmup_manager().warm(model_source, model_id or settings.ollama_model)
    return {"ok": ok}
