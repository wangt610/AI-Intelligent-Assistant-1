"""
模型管理器

支持多来源模型发现与统一流式调用：
- Ollama 本地模型
- OpenAI 兼容 API（vLLM / TGI / 等）

使用时在 config.py 的 model_sources 中配置来源。
"""

import asyncio
import os
import logging

from config import get_settings
from utils.json_store import atomic_json_write, atomic_json_read
from utils.http_client import HttpClientPool

logger = logging.getLogger(__name__)

_model_cache: list[dict] | None = None

# 非 LLM 模型清单（嵌入/视觉/工具类）
_NON_LLM_NAMES = frozenset({
    # 嵌入模型
    "nomic-embed-text", "mxbai-embed-large", "all-minilm",
    "bge-m3", "bge-large", "bge-small", "bge-base", "bge-reranker",
    "snowflake-arctic-embed", "snowflake-arctic-embed2",
    "gte-large", "gte-base", "gte-small", "gte-Qwen2",
    "e5-large", "e5-base", "e5-small", "e5-mistral",
    "jina-embeddings", "jina-embedding", "multilingual-e5",
    "instructor-xl", "instructor-base",
    "stella", "stella-base-zh", "stella-base-en",
    "text-embedding", "text2vec",
    "conan-embed", "m3e", "m3e-base", "m3e-large",
    "luotuo-embedding", "bilingual-embedding",
    # 视觉模型（纯视觉无法对话）
    "llava", "bakllava", "llava-llama3",
    "minicpm-v", "minicpm-llama3-v",
    "cogvlm", "cogvlm2",
    "deepseek-vl", "internvl", "internvl2",
    "qwen-vl", "qwen-vl-plus", "qwen2-vl",
    "glm-4v", "xcomposer",
    # 重排序/工具类
    "reranker", "cross-encoder",
})


def is_llm_model(model_name: str) -> bool:
    """判断是否为可对话的 LLM 模型（过滤非 LLM）。"""
    base_name = model_name.split(":")[0].strip()
    if base_name in _NON_LLM_NAMES:
        return False
    return True


def get_custom_sources_path() -> str:
    """自定义模型来源的持久化 JSON 文件路径。"""
    settings = get_settings()
    base_dir = os.path.dirname(settings.db_path) if settings.db_path else "data"
    return os.path.join(base_dir, "custom_model_sources.json")


def load_custom_sources() -> list[dict]:
    """读取用户自定义的 API 来源。"""
    path = get_custom_sources_path()
    result = atomic_json_read(path, default=[])
    if not isinstance(result, list):
        logger.warning("自定义来源文件格式异常，返回空列表")
        return []
    return result


def save_custom_sources(sources: list[dict]):
    """持久化自定义 API 来源列表（原子写，防中途崩溃损坏）。"""
    try:
        atomic_json_write(get_custom_sources_path(), sources)
    except Exception as e:
        logger.warning("持久化自定义模型来源失败: %s", e)


def add_custom_source(source: dict) -> list[dict]:
    """添加一个自定义 API 来源，同名则覆盖。"""
    sources = load_custom_sources()
    existing = [s for s in sources if s["name"] != source["name"]]
    existing.append(source)
    save_custom_sources(existing)
    invalidate_cache()
    return existing


def remove_custom_source(name: str) -> list[dict]:
    """删除一个自定义 API 来源。"""
    sources = load_custom_sources()
    sources = [s for s in sources if s["name"] != name]
    save_custom_sources(sources)
    invalidate_cache()
    return sources


def get_model_sources() -> list[dict]:
    settings = get_settings()
    config_sources = [s.model_dump() for s in settings.model_sources]
    custom_sources = load_custom_sources()
    return config_sources + custom_sources


async def _discover_source(source: dict) -> list[dict]:
    """查询单个来源的模型列表（供 gather 并行调用）。"""
    client = HttpClientPool.get("discovery", timeout=10)
    if source["type"] == "ollama":
        base_url = source.get("base_url") or get_settings().ollama_host
        resp = await client.get(f"{base_url}/api/tags")
        if resp.status_code != 200:
            return []
        discovered = []
        for model in resp.json().get("models", []):
            name = model["name"]
            if is_llm_model(name):
                discovered.append({
                    "id": name,
                    "source": source["name"],
                    "name": name,
                    "type": "ollama",
                })
        return discovered

    if source["type"] == "openai":
        headers = {}
        if source.get("api_key"):
            headers["Authorization"] = f"Bearer {source['api_key']}"
        resp = await client.get(
            f"{source['base_url']}/models", headers=headers
        )
        if resp.status_code != 200:
            return []
        return [
            {"id": m["id"], "source": source["name"], "name": m["id"], "type": "openai"}
            for m in resp.json().get("data", [])
        ]

    return []


async def discover_models(force_refresh: bool = False) -> list[dict]:
    """并行查询所有来源，返回合并后的模型列表。

    每项格式:
        {"id": str, "source": str, "name": str, "type": "ollama"|"openai"}
    """
    global _model_cache
    if _model_cache is not None and not force_refresh:
        return _model_cache

    sources = get_model_sources()
    tasks = [_discover_source(s) for s in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    models: list[dict] = []
    for source, result in zip(sources, results):
        if isinstance(result, Exception):
            logger.warning("模型发现失败 [%s]: %s", source["name"], result)
        else:
            models.extend(result)
            logger.info("模型发现: %s 返回 %d 个模型", source["name"], len(result))

    _model_cache = models
    return models


def invalidate_cache():
    """清空模型缓存，下次 discover_models 重新查询。"""
    global _model_cache
    _model_cache = None
