"""
轻量级内存事件总线 — 为 SSE 实时推送提供进程内 pub/sub。

设计：
- 每个 session_id 维护一组 asyncio.Queue
- publish() 向该 session 所有订阅者广播
- 订阅者通过 async for 消费事件，断开时自动清理
"""

import asyncio
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

_subscribers: dict[str, list[asyncio.Queue]] = {}


async def publish(session_id: str, event: str, data: dict) -> None:
    """向指定会话的所有订阅者发布事件。"""
    queues = _subscribers.get(session_id, [])
    if not queues:
        return
    payload = {"event": event, "data": data}
    for q in queues:
        await q.put(payload)


def subscribe(session_id: str) -> asyncio.Queue:
    """为指定会话创建订阅队列。"""
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.setdefault(session_id, []).append(q)
    return q


def unsubscribe(session_id: str, queue: asyncio.Queue) -> None:
    """取消订阅并清理空列表。"""
    queues = _subscribers.get(session_id)
    if queues:
        queues[:] = [q for q in queues if q is not queue]
        if not queues:
            _subscribers.pop(session_id, None)


async def event_stream(session_id: str) -> AsyncGenerator[str, None]:
    """生成 SSE 事件流，客户端断开时自动清理。"""
    import json

    queue = subscribe(session_id)
    try:
        while True:
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"event: {payload['event']}\ndata: {json.dumps(payload['data'])}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
    finally:
        unsubscribe(session_id, queue)
