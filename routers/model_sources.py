"""
自定义 API 模型来源管理路由

提供添加/删除用户自定义的 OpenAI 兼容 API 来源。
"""

import logging

from fastapi import APIRouter

from models.schemas import ModelSourceCreate, ModelSourceListResponse
from services.model_manager import (
    load_custom_sources,
    add_custom_source,
    remove_custom_source,
    discover_models,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["model_sources"])


def _mask_api_key(key: str) -> str:
    if len(key) < 8:
        return "*" * len(key)
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


def _masked_sources(sources: list[dict]) -> list[dict]:
    return [{**s, "api_key": _mask_api_key(s.get("api_key", ""))} for s in sources]


@router.get("/model-sources", response_model=ModelSourceListResponse)
async def list_model_sources():
    """返回所有自定义 API 来源（API Key 仅显示首尾4位）。"""
    return {"sources": _masked_sources(load_custom_sources())}


@router.post("/model-sources", response_model=ModelSourceListResponse)
async def create_model_source(body: ModelSourceCreate):
    """添加一个自定义 API 来源。"""
    sources = add_custom_source({
        "name": body.name,
        "label": body.label,
        "base_url": body.base_url.rstrip("/"),
        "api_key": body.api_key,
        "type": "openai",
    })

    try:
        await discover_models(force_refresh=True)
    except Exception as e:
        logger.warning("添加来源后刷新模型列表失败: %s", e)

    return {"sources": _masked_sources(sources)}


@router.delete("/model-sources/{name}", response_model=ModelSourceListResponse)
async def delete_model_source(name: str):
    """删除一个自定义 API 来源。"""
    sources = remove_custom_source(name)

    try:
        await discover_models(force_refresh=True)
    except Exception as e:
        logger.warning("删除来源后刷新模型列表失败: %s", e)

    return {"sources": _masked_sources(sources)}
