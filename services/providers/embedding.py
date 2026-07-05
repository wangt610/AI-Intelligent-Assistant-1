"""
Embedding 提供商

定义 EmbeddingProvider 接口与 Ollama 适配器。
"""

import asyncio
import logging
from abc import ABC, abstractmethod

from config import get_settings
from services.ollama_client import get_ollama_async_client

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Embedding 向量生成接口。"""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        ...


class OllamaEmbeddingProvider(EmbeddingProvider):
    """通过 Ollama Embeddings API 生成向量（复用连接）。"""

    def __init__(self):
        settings = get_settings()
        self._model = settings.embedding_model
        self._keep_alive = settings.ollama_keep_alive
        self._client = get_ollama_async_client()
        self._max_batch_size = 64

    async def embed(self, text: str) -> list[float]:
        try:
            response = await self._client.embeddings(
                model=self._model,
                prompt=text,
                keep_alive=self._keep_alive,
            )
            return response.embedding
        except Exception as e:
            logger.error("Embedding 生成失败: %s", e)
            raise

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for i in range(0, len(texts), self._max_batch_size):
            batch = texts[i:i + self._max_batch_size]
            try:
                resp = await self._client.embed(
                    model=self._model,
                    input=batch,
                    keep_alive=self._keep_alive,
                )
                results.extend(resp.embeddings)
            except Exception as e:
                logger.warning(
                    "批量 embedding 失败(%d chunks)，降级为并发单条重试: %s",
                    len(batch), e,
                )
                tasks = [
                    self._client.embeddings(
                        model=self._model, prompt=text, keep_alive=self._keep_alive,
                    )
                    for text in batch
                ]
                emb_results = await asyncio.gather(*tasks, return_exceptions=True)
                for r in emb_results:
                    if isinstance(r, Exception):
                        logger.error("单条 embedding 失败，跳过: %s", r)
                        results.append([0.0] * 1024)
                    else:
                        results.append(r.embedding)
        return results
