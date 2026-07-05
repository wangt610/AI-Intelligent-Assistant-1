"""
Token 计数器 — 单一共享实现。

使用 tiktoken 估算 token 数，用于历史裁剪和 RAG 分块。
"""

import functools
import tiktoken

ENCODING_NAME = "cl100k_base"
_ENCODER: tiktoken.Encoding | None = None

# 跨模块 LRU 缓存，避免对重复文本反复 tokenize
_TOKEN_CACHE: dict[int, int] = {}
_TOKEN_CACHE_MAX = 512


def _cache_key(text: str) -> int:
    return hash(text)


def get_encoder() -> tiktoken.Encoding:
    """获取 tiktoken 编码器单例。"""
    global _ENCODER
    if _ENCODER is None:
        _ENCODER = tiktoken.get_encoding(ENCODING_NAME)
    return _ENCODER


def count_tokens(text: str) -> int:
    """估算文本的 token 数量（带 LRU 缓存）。"""
    key = _cache_key(text)
    cached = _TOKEN_CACHE.get(key)
    if cached is not None:
        return cached

    try:
        n = len(get_encoder().encode(text))
    except Exception:
        n = len(text) // 2

    if len(_TOKEN_CACHE) >= _TOKEN_CACHE_MAX:
        _TOKEN_CACHE.pop(next(iter(_TOKEN_CACHE)))
    _TOKEN_CACHE[key] = n
    return n
