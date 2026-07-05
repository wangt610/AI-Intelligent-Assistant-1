"""
HTTP 客户端连接池

提供命名客户端单例管理，避免各模块重复创建 httpx.AsyncClient
以及重复定义超时等配置。
"""

import httpx


class HttpClientPool:
    """命名 HTTP 客户端池。"""

    _clients: dict[str, httpx.AsyncClient] = {}

    @classmethod
    def get(cls, name: str = "default", timeout: float = 30) -> httpx.AsyncClient:
        if name not in cls._clients:
            cls._clients[name] = httpx.AsyncClient(timeout=timeout)
        return cls._clients[name]
