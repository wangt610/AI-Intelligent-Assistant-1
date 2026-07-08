"""
向量存储 seam

定义 VectorStore 接口与 ChromaDB 适配器实现。
复用全局共享的 ChromaDB 客户端单例。
所有 ChromaDB SDK 调用通过 run_in_executor 异步化，避免阻塞事件循环。
"""

import asyncio
import os
import logging
from abc import ABC, abstractmethod

import chromadb
from chromadb.config import Settings as ChromaSettings

from config import get_settings
from runtime_config import get_config

logger = logging.getLogger(__name__)

# ─── 全局 ChromaDB 客户端单例 ──────────────────────────

_client = None


def get_chroma_client():
    """获取全局共享的 ChromaDB PersistentClient 单例。"""
    global _client
    if _client is None:
        settings = get_settings()
        persist_dir = settings.chroma_persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info("ChromaDB 客户端初始化: path=%s", persist_dir)
    return _client


class VectorStore(ABC):
    """向量存储接口 — 嵌入向量的持久化与相似度检索。"""

    @abstractmethod
    async def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None: ...

    @abstractmethod
    async def similarity_search(
        self,
        query_embedding: list[float],
        filter: dict | None = None,
        top_k: int = 10,
    ) -> list[dict]: ...

    @abstractmethod
    async def get_ids(self, filter: dict) -> list[str]: ...

    @abstractmethod
    async def delete(self, ids: list[str]) -> None: ...

    @abstractmethod
    async def count(self, filter: dict | None = None) -> int: ...

    @abstractmethod
    async def health_check(self) -> tuple[bool, str]: ...


class ChromaAdapter(VectorStore):
    """ChromaDB 适配器 — 使用共享 PersistentClient 持久化向量。

    所有 ChromaDB SDK 调用通过 run_in_executor 委托到同步函数，
    确保不阻塞 asyncio 事件循环。
    """

    def __init__(self, distance_metric: str | None = None):
        settings = get_settings()
        self._distance_metric = distance_metric or settings.rag_distance_metric
        self._collection: chromadb.Collection | None = None
        self._collection_name = "rag_documents"

    # ── 同步辅助 ──────────────────────────────────────────────

    def _ensure_collection(self):
        if self._collection is None:
            client = get_chroma_client()
            metadata = {"hnsw:space": self._distance_metric}
            try:
                self._collection = client.get_collection(self._collection_name)
                existing_meta = self._collection.metadata or {}
                if existing_meta.get("hnsw:space") != self._distance_metric:
                    logger.warning(
                        "已存在的 collection 距离度量=%s，配置=%s，如需切换请重建",
                        existing_meta.get("hnsw:space"),
                        self._distance_metric,
                    )
            except Exception:
                self._collection = client.create_collection(
                    name=self._collection_name, metadata=metadata
                )
                logger.info("创建 ChromaDB collection: %s (%s)", self._collection_name, metadata)

    def _sync_add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        self._ensure_collection()
        self._collection.add(
            ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas
        )

    def _sync_similarity_search(
        self,
        query_embedding: list[float],
        filter: dict | None = None,
        top_k: int = 10,
    ) -> list[dict]:
        self._ensure_collection()
        results = self._collection.query(
            query_embeddings=[query_embedding],
            where=filter,
            n_results=min(top_k, 50),
            include=["documents", "metadatas", "distances"],
        )
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        hits = []
        threshold = get_config("rag_score_threshold")
        for doc, meta, dist in zip(docs, metas, dists):
            score = 1.0 - dist
            if score >= threshold:
                hits.append({
                    "text": doc,
                    "source_file": meta.get("source_file", "未知"),
                    "score": round(score, 4),
                    "chunk_index": meta.get("chunk_index"),
                })
        return hits

    def _sync_get_ids(self, filter: dict) -> list[str]:
        self._ensure_collection()
        result = self._collection.get(where=filter, include=[])
        return result.get("ids", [])

    def _sync_delete(self, ids: list[str]) -> None:
        self._ensure_collection()
        self._collection.delete(ids=ids)

    def _sync_count(self, filter: dict | None = None) -> int:
        self._ensure_collection()
        kwargs = {"include": []}
        if filter is not None:
            kwargs["where"] = filter
        result = self._collection.get(**kwargs)
        return len(result.get("ids", []))

    def _sync_health_check(self) -> tuple[bool, str]:
        try:
            client = get_chroma_client()
            client.heartbeat()
            return True, "ChromaDB 正常"
        except Exception as e:
            return False, f"ChromaDB 异常: {e}"

    # ── 公开 async 方法：委托到同步函数 ──────────────────────

    async def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._sync_add, ids, embeddings, documents, metadatas)

    async def similarity_search(
        self,
        query_embedding: list[float],
        filter: dict | None = None,
        top_k: int = 10,
    ) -> list[dict]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._sync_similarity_search, query_embedding, filter, top_k
        )

    async def get_ids(self, filter: dict) -> list[str]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._sync_get_ids, filter)

    async def delete(self, ids: list[str]) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._sync_delete, ids)

    async def count(self, filter: dict | None = None) -> int:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._sync_count, filter)

    async def health_check(self) -> tuple[bool, str]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._sync_health_check)
