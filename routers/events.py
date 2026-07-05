"""
会话事件路由 — SSE 实时事件推送

提供 /api/sessions/{session_id}/events SSE 端点，
客户端连接后可实时收到索引状态等事件。
"""

import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from services.event_bus import event_stream
from routers.dependencies import SSE_HEADERS

logger = logging.getLogger(__name__)

router = APIRouter(tags=["events"])


@router.get("/sessions/{session_id}/events")
async def session_events(session_id: str):
    """订阅会话的实时事件流（SSE）。"""
    return StreamingResponse(
        event_stream(session_id),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
