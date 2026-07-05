"""
Ollama 客户端单例

全局共享 AsyncClient/SyncClient，避免重复创建连接。
"""

import ollama

from config import get_settings

_async_client: ollama.AsyncClient | None = None


def get_ollama_async_client() -> ollama.AsyncClient:
    """获取全局共享的 Ollama AsyncClient 单例。"""
    global _async_client
    if _async_client is None:
        settings = get_settings()
        _async_client = ollama.AsyncClient(
            host=settings.ollama_host,
            timeout=settings.ollama_timeout,
        )
    return _async_client
