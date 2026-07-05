"""
RAG 服务层（外观）

将 VectorStore + EmbeddingProvider 装配为 RAGEngine 和 FileIndexer。
保留函数式接口供上层调用，同时将实现委托给深度模块。
"""

import logging
from typing import Any

from config import get_settings

logger = logging.getLogger(__name__)


class _RAGService:
    """类级单例持有 VectorStore、Embedder，避免 uvicorn --reload 导致的全局变量污染。"""
    vector_store: Any = None
    embedder: Any = None
    _rag_engine: Any = None
    _file_indexer: Any = None


def init_vector_store(store: Any) -> None:
    _RAGService.vector_store = store
    _RAGService._rag_engine = None
    _RAGService._file_indexer = None


def init_embedder(embedder: Any) -> None:
    _RAGService.embedder = embedder
    _RAGService._rag_engine = None
    _RAGService._file_indexer = None


def _get_store():
    if _RAGService.vector_store is None:
        raise RuntimeError("VectorStore 未初始化，请先调用 init_vector_store()")
    return _RAGService.vector_store


def _get_embedder():
    if _RAGService.embedder is None:
        raise RuntimeError("Embedder 未初始化，请先调用 init_embedder()")
    return _RAGService.embedder


def _get_rag_engine():
    from services.rag_engine import RAGEngine
    if _RAGService._rag_engine is None:
        _RAGService._rag_engine = RAGEngine(_get_store(), _get_embedder())
    return _RAGService._rag_engine


def _get_file_indexer():
    from services.indexer import FileIndexer
    if _RAGService._file_indexer is None:
        _RAGService._file_indexer = FileIndexer(_get_store(), _get_embedder())
    return _RAGService._file_indexer


# ── Embedding ──────────────────────────────────────────────

async def get_embedding(text: str) -> list[float]:
    return await _get_rag_engine().get_embedding(text)


# ── 检索 ───────────────────────────────────────────────────

async def search(
    query: str,
    session_id: str,
    top_k: int | None = None,
    history: list[dict] | None = None,
    source_file: str | None = None,
    memory_hits: list[dict] | None = None,
) -> list[dict]:
    return await _get_rag_engine().search(query, session_id, top_k, history, source_file, memory_hits=memory_hits)


# ── 索引 ───────────────────────────────────────────────────

async def index_file(db, session_id: str, file_name: str, text: str, task_id: int | None = None) -> dict:
    return await _get_file_indexer().index_file(db, session_id, file_name, text, task_id)


async def index_file_background(db, session_id: str, file_name: str, file_content: str) -> None:
    return await _get_file_indexer().index_file_background(db, session_id, file_name, file_content)


async def count_indexed_chunks(session_id: str) -> int:
    return await _get_file_indexer().count_indexed_chunks(session_id)


async def delete_file_index(session_id: str, file_name: str) -> int:
    return await _get_file_indexer().delete_file_index(session_id, file_name)


async def delete_session_index(session_id: str) -> None:
    return await _get_file_indexer().delete_session_index(session_id)


async def list_indexed_files(db, session_id: str) -> list[dict]:
    """列出会话内已索引的文件（facade，隔离 router 对 database 的直接依赖）。"""
    from database import get_indexed_files_by_session
    return await get_indexed_files_by_session(db, session_id)


# ── 健康检查 ──────────────────────────────────────────────

async def health_check() -> tuple[bool, str]:
    return await _get_rag_engine().health_check()
