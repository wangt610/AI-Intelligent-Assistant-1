"""
会话业务服务

封装 sessions/messages 的业务操作：
- 跨服务编排（删会话时同步清理 RAG 索引与语义记忆）
- 消息编辑/删除的校验逻辑
"""

import logging

logger = logging.getLogger(__name__)


async def delete_session_full(db, session_id: str) -> None:
    """删除会话并同步清理 RAG 索引与语义记忆。

    部分失败不阻断：删库成功后清索引/记忆失败仅记日志。
    """
    import database
    await database.delete_session(db, session_id)

    try:
        from services.rag_service import delete_session_index
        await delete_session_index(session_id)
    except Exception as e:
        logger.warning("清理会话 RAG 索引失败: %s", e)

    try:
        from services.memory import delete_session as delete_memory_session
        await delete_memory_session(session_id)
    except Exception as e:
        logger.warning("清理会话语义记忆失败: %s", e)


async def edit_user_message(db, session_id: str, message_id: int, content: str) -> None:
    """编辑用户消息并截断后续消息。

    Raises:
        ValueError: 消息不存在 / 不属于该会话 / 非用户消息
    """
    import database
    msg = await database.get_message(db, message_id)
    if not msg:
        raise ValueError("消息不存在")
    if msg["session_id"] != session_id:
        raise ValueError("消息不属于该会话")
    if msg["role"] != "user":
        raise ValueError("只能编辑用户消息")

    await database.update_message(db, message_id, content)
    await database.delete_messages_after(db, message_id + 1, session_id)


async def delete_message_and_after(db, session_id: str, message_id: int) -> None:
    """删除消息及其之后的所有消息。

    Raises:
        ValueError: 消息不存在 / 不属于该会话
    """
    import database
    msg = await database.get_message(db, message_id)
    if not msg:
        raise ValueError("消息不存在")
    if msg["session_id"] != session_id:
        raise ValueError("消息不属于该会话")

    await database.delete_messages_after(db, message_id, session_id)
