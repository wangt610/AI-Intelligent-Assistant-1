"""
请求耗时中间件

记录请求处理耗时，写入响应头 X-Process-Time。
trace_id 的注入由 RequestIDMiddleware 全权负责。
"""

import time
import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """记录请求处理耗时"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time"] = f"{duration_ms:.1f}ms"

        if not request.url.path.startswith("/static"):
            logger.info(
                "%s %s -> %d (%.1fms)",
                request.method, request.url.path,
                response.status_code, duration_ms,
            )

        return response
