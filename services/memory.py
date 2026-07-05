"""
Semantic Active Working Memory

利用已有的 ChromaDB + EmbeddingProvider 将对话历史按语义存储和检索。
每条消息保存时自动建立 embedding，新对话时检索与当前 query 语义相关的历史回合。
复用全局共享的 ChromaDB 客户端单例。
"""

import asyncio
import logging

from config import get_settings
from services.vector_store import get_chroma_client

logger = logging.getLogger(__name__)

_collection = None


def _ensure():
    global _collection
    if _collection is not None:
        return

    client = get_chroma_client()
    name = "session_messages"
    try:
        _collection = client.get_collection(name)
    except Exception:
        _collection = client.create_collection(name)
    logger.info("语义记忆集合就绪: %s", name)


def _cleanup_session(session_id: str, max_messages: int, batch_size: int) -> None:
    """删除指定会话中最旧的 embedding，控制在 max_messages 以内。"""
    result = _collection.get(where={"session_id": session_id}, include=["metadatas"])
    ids = result.get("ids", [])
    metas = result.get("metadatas", [])
    if len(ids) <= max_messages:
        return
    sorted_pairs = sorted(zip(ids, metas), key=lambda x: x[1].get("message_id", 0))
    delete_count = min(len(ids) - max_messages, batch_size)
    delete_ids = [p[0] for p in sorted_pairs[:delete_count]]
    _collection.delete(ids=delete_ids)
    logger.info("语义记忆清理: session=%s 删除了 %d 条旧消息", session_id[:8], delete_count)


async def index_message(
    session_id: str,
    message_id: int,
    role: str,
    content: str,
    max_per_session: int = 500,
    cleanup_batch: int = 100,
) -> None:
    """将单条消息嵌入向量存储（非阻塞调用）。"""
    try:
        _ensure()
        from services.rag_service import get_embedding

        text = content[:2000]
        if not text.strip():
            return

        embedding = await get_embedding(text)

        # ChromaDB 的 add/get/delete 是同步阻塞操作，用 to_thread 避免阻塞事件循环
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: _collection.add(
                ids=[f"msg_{session_id[:8]}_{message_id}"],
                embeddings=[embedding],
                documents=[f"{role}: {text}"],
                metadatas=[{
                    "session_id": session_id,
                    "role": role,
                    "message_id": message_id,
                }],
            ),
        )
        # 清理旧 embedding，避免无限膨胀
        await loop.run_in_executor(
            None,
            lambda: _cleanup_session(session_id, max_per_session, cleanup_batch),
        )
    except Exception as e:
        logger.warning("语义记忆索引失败 msg=%d: %s", message_id, e)


async def retrieve(
    session_id: str,
    query: str,
    top_k: int = 5,
    min_score: float = 0.4,
) -> list[dict]:
    """检索与 query 语义相关的历史消息，按相关度降序排列。"""
    try:
        _ensure()
        from services.rag_service import get_embedding

        query_emb = await get_embedding(query)

        # ChromaDB 的 query 是同步阻塞操作
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: _collection.query(
                query_embeddings=[query_emb],
                where={"session_id": session_id},
                n_results=top_k + 5,
                include=["documents", "metadatas", "distances"],
            ),
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        hits = []
        for doc, meta, dist in zip(docs, metas, dists):
            score = round(1.0 - dist, 4)
            if score >= min_score:
                hits.append({
                    "text": doc,
                    "role": meta.get("role", "user"),
                    "message_id": meta.get("message_id"),
                    "score": score,
                })
        return hits[:top_k]
    except Exception as e:
        logger.warning("语义记忆检索失败: %s", e)
        return []


async def delete_session(session_id: str) -> None:
    """删除会话的所有消息 embedding。"""
    try:
        _ensure()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _collection.get(where={"session_id": session_id}, include=[]),
        )
        ids = result.get("ids", [])
        if ids:
            await loop.run_in_executor(None, lambda: _collection.delete(ids=ids))
            logger.info("已删除会话语义记忆: %s (%d 条)", session_id[:8], len(ids))
    except Exception as e:
        logger.warning("删除会话语义记忆失败: %s", e)
