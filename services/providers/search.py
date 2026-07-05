"""
搜索提供商

定义 SearchProvider 接口与 Tavily/DuckDuckGo 适配器。
"""

import asyncio
import concurrent.futures
import random
import logging
from dataclasses import dataclass
from abc import ABC, abstractmethod

from utils.http_client import HttpClientPool

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    title: str
    url: str
    content: str
    score: float = 1.0


class SearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        ...


class TavilyProvider(SearchProvider):
    """通过 Tavily Search API 搜索（返回结构化摘要，无需清洗）。"""

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._client = HttpClientPool.get("tavily", timeout=15)

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        resp = await self._client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": self._api_key,
                "query": query,
                "max_results": max_results,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
            )
            for r in data.get("results", [])
        ]


_DDG_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=3)
_DDG_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]


class DuckDuckGoProvider(SearchProvider):
    """通过 DuckDuckGo 搜索（免费、实时、无需 API Key）。"""

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        loop = asyncio.get_event_loop()
        ua = random.choice(_DDG_USER_AGENTS)

        def _sync_search() -> list[SearchResult]:
            from duckduckgo_search import DDGS
            with DDGS(headers={"User-Agent": ua}) as ddgs:
                results = ddgs.text(
                    keywords=query,
                    max_results=max_results,
                    timeout=8,
                )
            return [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    content=r.get("body", ""),
                    score=1.0,
                )
                for r in results
            ]

        try:
            return await asyncio.wait_for(
                loop.run_in_executor(_DDG_POOL, _sync_search),
                timeout=10,
            )
        except asyncio.TimeoutError:
            logger.warning("DuckDuckGo 搜索超时 query=%s", query)
            return []
        except Exception as e:
            logger.warning("DuckDuckGo 搜索失败 query=%s: %s", query, e)
            return []
