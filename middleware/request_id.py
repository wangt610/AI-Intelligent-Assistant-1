"""
请求 ID 中间件（纯 ASGI 实现）

为每个 HTTP 请求生成唯一 ID：
- 注入日志上下文（contextvars）供全链路追踪
- 注入到 ASGI scope 供下游访问
- 写入响应头

使用纯 ASGI 而非 BaseHTTPMiddleware 以避免 anyio 子任务
导致的 contextvars 隔离问题。
"""

import uuid

from starlette.types import ASGIApp, Scope, Receive, Send, Message

from logging_config import _trace_id


class RequestIDMiddleware:
    """为每个请求生成唯一 ID，注入日志上下文与响应头"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 从请求头中读取或生成 request_id
        request_id = None
        for key, value in scope.get("headers", []):
            if key == b"x-request-id":
                request_id = value.decode()
                break
        if not request_id:
            request_id = uuid.uuid4().hex[:16]

        # 注入日志上下文（此处设置的 contextvar 会在 start_soon 时被复制到子任务）
        _trace_id.set(request_id)

        # 注入到 scope 供下游 starlette.Request.state 使用
        scope.setdefault("state", {}).setdefault("request_id", request_id)

        # 包装 send 以注入响应头
        orig_send = send

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await orig_send(message)

        await self.app(scope, receive, send_with_header)
