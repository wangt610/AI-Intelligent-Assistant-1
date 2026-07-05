"""
文件索引器

管理文件索引生命周期：分块 → embedding → 向量存储写入 → 任务状态追踪。
"""

import asyncio
import logging
from typing import Any

from config import get_settings
from services.chunker import chunk_text

logger = logging.getLogger(__name__)


class FileIndexer:
    def __init__(self, vector_store, embedder):
        self._store = vector_store
        self._embedder = embedder

    async def index_file(
        self,
        db,
        session_id: str,
        file_name: str,
        text: str,
        task_id: int | None = None,
    ) -> dict[str, Any]:
        """索引单个文件：分块 → embedding → 存储。"""
        if task_id is not None:
            from database import mark_indexing
            await mark_indexing(db, task_id)

        loop = asyncio.get_event_loop()
        chunks = await loop.run_in_executor(None, chunk_text, text)
        if not chunks:
            if task_id is not None:
                from database import mark_completed
                await mark_completed(db, task_id, 0)
            logger.warning("文件 %s 内容为空，未创建索引块", file_name)
            return {"file": file_name, "chunks": 0, "status": "empty"}

        embeddings = await self._embedder.embed_batch(chunks)
        ids = [f"{session_id}_{file_name}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "session_id": session_id,
                "source_file": file_name,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            for i in range(len(chunks))
        ]

        try:
            await self._store.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
        except Exception as e:
            if task_id is not None:
                from database import mark_failed
                await mark_failed(db, task_id, str(e))
            raise

        if task_id is not None:
            from database import mark_completed
            await mark_completed(db, task_id, len(chunks))

        logger.info("文件索引完成: %s (%d chunks)", file_name, len(chunks))
        return {"file": file_name, "chunks": len(chunks), "status": "ok"}

    async def count_indexed_chunks(self, session_id: str) -> int:
        return await self._store.count(filter={"session_id": {"$eq": session_id}})

    async def delete_file_index(self, session_id: str, file_name: str) -> int:
        store = self._store
        try:
            ids = await store.get_ids(
                filter={
                    "$and": [
                        {"session_id": {"$eq": session_id}},
                        {"source_file": {"$eq": file_name}},
                    ]
                }
            )
            if ids:
                await store.delete(ids=ids)
                logger.info("删除文件索引: %s (%d chunks)", file_name, len(ids))
            return len(ids)
        except Exception as e:
            logger.error("删除文件索引失败 %s: %s", file_name, e)
            raise

    async def delete_session_index(self, session_id: str) -> None:
        store = self._store
        try:
            ids = await store.get_ids(filter={"session_id": {"$eq": session_id}})
            if ids:
                await store.delete(ids=ids)
                logger.info("删除会话索引: %s (%d chunks)", session_id, len(ids))
        except Exception as e:
            logger.error("删除会话索引失败: %s", e)

    async def index_file_background(
        self,
        db,
        session_id: str,
        file_name: str,
        file_content: str,
    ) -> None:
        from services.event_bus import publish

        try:
            from database import create_task
            task_id = await create_task(db, session_id, file_name)
            await self.index_file(db, session_id, file_name, file_content, task_id=task_id)
            await publish(session_id, "index_status", {
                "file": file_name, "status": "completed",
            })
        except Exception as e:
            logger.error("后台索引失败 %s: %s", file_name, e)
            await publish(session_id, "index_status", {
                "file": file_name, "status": "failed", "error": str(e),
            })
