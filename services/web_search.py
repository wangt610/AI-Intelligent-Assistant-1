"""
联网搜索模块

封装搜索缓存、搜索意图分析和网页搜索执行。
"""

import asyncio
import logging

from cachetools import TTLCache

from config import get_settings
from runtime_config import get_config

logger = logging.getLogger(__name__)

# 搜索缓存（自动过期 + LRU 淘汰）
_search_cache: TTLCache = TTLCache(maxsize=128, ttl=300)


async def cached_search(
    provider,
    query: str,
    max_results: int = 5,
) -> list:
    key = (query.strip(), max_results)
    if not key[0]:
        return []
    if key in _search_cache:
        logger.debug("搜索缓存命中: %.40s", key[0])
        return _search_cache[key]
    results = await provider.search(query, max_results=max_results)
    _search_cache[key] = results
    return results


async def analyze_search_intent(query: str, history: list[dict] | None) -> str | None:
    """判断是否需要联网搜索，返回改写后的搜索关键词，或 None（无需搜索）。"""
    settings = get_settings()
    if not settings.web_search_precheck:
        return query

    context_parts = []
    if history:
        for msg in reversed(history[-6:]):
            if msg.get("role") == "user" and len(context_parts) < 2:
                context_parts.append(msg.get("content", ""))
    context_str = ""
    if context_parts:
        context_str = f"历史对话：{' | '.join(reversed(context_parts))}\n\n"

    prompt = (
        "判断是否需要联网搜索。\n\n"
        f"{context_str}"
        f"问题：{query}\n\n"
        "仅输出：\n"
        "SEARCH:关键词（需搜索）\n"
        "NO（不需要）"
    )

    from services.providers import get_provider

    provider = get_provider(None, None)
    try:
        content = await asyncio.wait_for(
            provider.complete(
                [{"role": "user", "content": prompt}],
                max_tokens=15, temperature=0,
            ),
            timeout=3,
        )
        content = content.strip().upper()

        if content.startswith("SEARCH:"):
            return content[len("SEARCH:"):].strip()
        if content == "NO" or content.startswith("NO_SEARCH"):
            return None

        logger.debug("搜索预判解析异常: %s", content[:50])
        return query
    except asyncio.TimeoutError:
        logger.debug("搜索预判超时，降级为原始 query")
        return query
    except Exception as e:
        logger.debug("搜索预判失败: %s，降级为原始 query", e)
        return query


async def do_web_search(
    query: str,
    max_results: int = 5,
) -> list[dict] | None:
    settings = get_settings()
    from services.providers import get_search_provider

    provider = get_search_provider()
    results = await cached_search(provider, query, max_results)
    if not results:
        return None

    context = [
        {"source_file": r.url, "score": r.score, "text": r.content, "title": r.title}
        for r in results
    ]
    max_chars = get_config("search_max_context_tokens") * 4
    total = 0
    for i, item in enumerate(context):
        total += len(item["text"])
        if total > max_chars:
            context = context[:i]
            break
    return context
