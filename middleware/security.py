"""
安全相关中间件

提供：
- SecurityHeadersMiddleware: 注入安全响应头
- RequestBodyLimitMiddleware: 请求体大小限制
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """为所有响应注入安全 HTTP 头"""

    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "X-XSS-Protection": "1; mode=block",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        for header, value in self.SECURITY_HEADERS.items():
            response.headers[header] = value
        return response


class _BodyTooLarge(Exception):
    """请求体超限的信号异常"""


class RequestBodyLimitMiddleware(BaseHTTPMiddleware):
    """限制请求体大小，防止超大上传耗尽服务器内存"""

    def __init__(self, app, max_size: int):
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        original_receive = request.receive
        state = {"received": 0}

        async def guarded_receive():
            message = await original_receive()
            if message.get("type") == "http.request":
                state["received"] += len(message.get("body", b""))
                if state["received"] > self.max_size:
                    raise _BodyTooLarge()
            return message

        request._receive = guarded_receive

        try:
            return await call_next(request)
        except _BodyTooLarge:
            logger.warning(
                "请求体超过大小限制 (%d bytes), client=%s, path=%s",
                state["received"],
                request.client.host if request.client else "unknown",
                request.url.path,
            )
            return JSONResponse(
                {"detail": "请求体超过大小限制"},
                status_code=413,
            )
