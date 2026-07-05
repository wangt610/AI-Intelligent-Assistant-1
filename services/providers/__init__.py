"""
模型提供商 seam

定义 ModelProvider / EmbeddingProvider 接口与适配器：
- OllamaProvider — 通过 Ollama 原生 API 流式生成
- OpenAIProvider — 通过 OpenAI 兼容 API 流式生成（vLLM / TGI / DeepSeek 等）
- OllamaEmbeddingProvider — 通过 Ollama Embeddings API 生成向量
"""

import logging

from config import get_settings
from services.ollama_client import get_ollama_async_client

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Ollama 服务相关错误的基类"""


class OllamaConnectionError(OllamaError):
    """Ollama 服务不可达"""


class OllamaModelError(OllamaError):
    """模型不存在或加载失败"""


class OllamaTimeoutError(OllamaError):
    """请求超时"""


async def check_ollama_health() -> tuple[bool, str]:
    try:
        client = get_ollama_async_client()
        await client.list()
        return True, "Ollama 服务正常"
    except Exception as e:
        return False, f"Ollama 不可达: {e}"


def get_provider(model_source: str | None, model_id: str | None):
    """工厂函数：根据来源名称和模型 ID 创建对应的提供商。"""
    from services.providers.model import OllamaProvider, OpenAIProvider

    settings = get_settings()
    source_name = model_source or "ollama"

    if source_name != "ollama":
        from services.model_manager import get_model_sources

        sources = get_model_sources()
        source = next((s for s in sources if s["name"] == source_name), None)
        if not source:
            raise OllamaError(f"模型来源 '{source_name}' 未配置")
        return OpenAIProvider(source=source, model_id=model_id)

    return OllamaProvider(model=model_id or settings.ollama_model)


def get_search_provider():
    from services.providers.search import DuckDuckGoProvider, TavilyProvider

    settings = get_settings()
    if settings.search_provider == "duckduckgo":
        return DuckDuckGoProvider()
    if settings.search_provider == "tavily":
        if not settings.tavily_api_key:
            raise RuntimeError(
                "Tavily API key 未配置，请在 .env 中设置 TAVILY_API_KEY"
            )
        return TavilyProvider(settings.tavily_api_key)
    raise ValueError(f"不支持的搜索提供商: {settings.search_provider}")


from services.providers.model import ModelProvider, OllamaProvider, OpenAIProvider
from services.providers.embedding import EmbeddingProvider, OllamaEmbeddingProvider
from services.providers.search import SearchResult, SearchProvider, TavilyProvider, DuckDuckGoProvider

__all__ = [
    "OllamaError", "OllamaConnectionError", "OllamaModelError", "OllamaTimeoutError",
    "check_ollama_health", "get_provider", "get_search_provider",
    "ModelProvider", "OllamaProvider", "OpenAIProvider",
    "EmbeddingProvider", "OllamaEmbeddingProvider",
    "SearchResult", "SearchProvider", "TavilyProvider", "DuckDuckGoProvider",
]
