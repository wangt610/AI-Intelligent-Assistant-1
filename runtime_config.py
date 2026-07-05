"""
运行时配置 — 调优参数的单一权威源。

所有可热改的推理/RAG/搜索参数集中在 RuntimeSettingsStore 中，
不再继承或 fallback 到 config.Settings。
config.Settings 只负责基础设施参数（ollama_host、db_path 等）。
"""

import os
import logging
from typing import Any

from utils.json_store import atomic_json_write, atomic_json_read

logger = logging.getLogger(__name__)


_DEFAULTS: dict[str, Any] = {
    "temperature": 0.3,
    "top_p": 0.9,
    "max_context_tokens": 20480,
    "max_history_messages": 40,
    "max_output_tokens": 4096,
    "rag_enabled": True,
    "rag_chunk_size": 800,
    "rag_chunk_overlap": 200,
    "rag_top_k": 3,
    "rag_score_threshold": 0.35,
    "rag_query_rewrite": True,
    "rag_hyde_enabled": True,
    "rag_hyde_max_tokens": 150,
    "rag_candidate_k": 20,
    "rag_bm25_weight": 0.4,
    "search_max_results": 5,
    "search_max_context_tokens": 4000,
}

_TYPES: dict[str, type] = {k: type(v) for k, v in _DEFAULTS.items()}

_OLD_ENV_MAP: dict[str, str] = {
    "OLLAMA_TEMPERATURE": "temperature",
    "OLLAMA_TOP_P": "top_p",
    "MAX_OUTPUT_TOKENS": "max_output_tokens",
    "MAX_HISTORY_MESSAGES": "max_history_messages",
    "RAG_ENABLED": "rag_enabled",
    "RAG_CHUNK_SIZE": "rag_chunk_size",
    "RAG_CHUNK_OVERLAP": "rag_chunk_overlap",
    "RAG_TOP_K": "rag_top_k",
    "RAG_SCORE_THRESHOLD": "rag_score_threshold",
    "RAG_QUERY_REWRITE": "rag_query_rewrite",
    "RAG_HYDE_ENABLED": "rag_hyde_enabled",
    "RAG_HYDE_MAX_TOKENS": "rag_hyde_max_tokens",
    "RAG_CANDIDATE_K": "rag_candidate_k",
    "RAG_BM25_WEIGHT": "rag_bm25_weight",
    "SEARCH_MAX_RESULTS": "search_max_results",
    "SEARCH_MAX_CONTEXT_TOKENS": "search_max_context_tokens",
}


class RuntimeSettingsStore:
    _data: dict[str, Any] = {}
    _persist_path: str = "data/runtime_settings.json"

    @classmethod
    def init(cls) -> None:
        cls._data = dict(_DEFAULTS)

        runtime_file_exists = os.path.isfile(cls._persist_path)
        cls._load()

        # 一次性迁移：仅当 runtime_settings.json 尚未存在时
        # 从旧版 .env 键读取值（如 OLLAMA_TEMPERATURE），避免用户重启后丢失设置
        if not runtime_file_exists:
            migrated = False
            for env_key, runtime_key in _OLD_ENV_MAP.items():
                env_val = os.environ.get(env_key)
                if env_val is not None:
                    cls._data[runtime_key] = cls._coerce(runtime_key, env_val)
                    migrated = True
            if migrated:
                logger.info("已从环境变量迁移 %d 个运行时设置", sum(
                    1 for k in _OLD_ENV_MAP if os.environ.get(k) is not None
                ))

    @classmethod
    def _coerce(cls, key: str, value: Any) -> Any:
        expected = _TYPES.get(key)
        if expected is None:
            return value
        if isinstance(value, expected):
            return value
        if expected is bool:
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
            return bool(value)
        try:
            return expected(value)
        except (ValueError, TypeError):
            return _DEFAULTS.get(key, value)

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        return cls._data.get(key, default)

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        cls._data[key] = cls._coerce(key, value)

    @classmethod
    def all(cls) -> dict[str, Any]:
        return dict(cls._data)

    @classmethod
    def save(cls) -> None:
        try:
            atomic_json_write(cls._persist_path, cls._data)
        except Exception as e:
            logger.warning("运行时设置持久化失败: %s", e)

    @classmethod
    def _load(cls) -> None:
        try:
            stored = atomic_json_read(cls._persist_path)
            if stored is None:
                return
            for k, v in stored.items():
                if k in _DEFAULTS:
                    cls._data[k] = cls._coerce(k, v)
            logger.info("已加载持久化的运行时设置")
        except Exception as e:
            logger.warning("加载持久化运行时设置失败: %s", e)


def get_config(key: str):
    """读取调优参数：优先运行时设置，未命中返回 _DEFAULTS。"""
    val = RuntimeSettingsStore.get(key)
    if val is not None:
        return val
    return _DEFAULTS.get(key)
