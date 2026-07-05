"""
对话路由

提供文本对话和文件对话的 SSE 流式接口。
"""

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse

from models.schemas import ChatRequest, RegenerateRequest, MessageEditRequest, OkResponse
import database
from services import session_service
from services.file_chat_service import FileChatResult, process_file_chat
from services.stream_engine import ChatContext, sse_chat_stream
from config import get_settings
from routers.dependencies import SSE_HEADERS, db_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


def _map_message_error(e: ValueError) -> HTTPException:
    """将 session_service 的 ValueError 映射为对应的 HTTPException。"""
    msg = str(e)
    if msg == "消息不存在":
        return HTTPException(404, msg)
    if msg == "消息不属于该会话":
        return HTTPException(403, msg)
    return HTTPException(400, msg)


@router.post("/chat")
async def chat(body: ChatRequest, db=Depends(db_session)):
    msg_count_before = await database.count_messages(db, body.session_id)

    logger.info(
        "开始对话 session=%s msg_count=%d rag_mode=%s",
        body.session_id[:8], msg_count_before, body.rag_mode,
    )

    message = body.message
    max_len = get_settings().max_input_length
    if len(message) > max_len:
        message = message[:max_len] + "\n\n[消息过长，已截断]"
        logger.warning("消息过长已截断 session=%s len=%d", body.session_id[:8], len(body.message))

    return StreamingResponse(
        sse_chat_stream(ChatContext(
            session_id=body.session_id,
            user_message=message,
            show_thinking=body.show_thinking,
            msg_count_before=msg_count_before,
            title_source=message,
            rag_mode=body.rag_mode,
            web_search=body.web_search,
            model_source=body.model_source or None,
            model_id=body.model_id or None,
        )),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.post("/chat/regenerate")
async def regenerate(body: RegenerateRequest, db=Depends(db_session)):
    """重新生成最后一条 AI 回复。"""

    last_msg = await database.get_last_user_message(db, body.session_id)
    if not last_msg:
        raise HTTPException(400, "没有可重新生成的消息")

    # 删除该用户消息及其之后的所有消息
    await session_service.delete_message_and_after(db, body.session_id, last_msg["id"])
    msg_count_before = await database.count_messages(db, body.session_id)

    logger.info(
        "重新生成 session=%s msg_id=%d",
        body.session_id[:8], last_msg["id"],
    )

    return StreamingResponse(
        sse_chat_stream(ChatContext(
            session_id=body.session_id,
            user_message=last_msg["content"],
            show_thinking=body.show_thinking,
            msg_count_before=msg_count_before,
            title_source=last_msg["content"],
            rag_mode=body.rag_mode,
            web_search=body.web_search,
            model_source=body.model_source or None,
            model_id=body.model_id or None,
        )),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.post("/chat/upload")
async def chat_with_file(
    session_id: str = Form(...),
    message: str = Form("请分析这个文件"),
    file: UploadFile = File(...),
    show_thinking: bool = Form(True),
    rag_mode: str = Form("off"),
    web_search: bool = Form(False),
    model_source: str = Form("ollama"),
    model_id: str = Form(""),
    db=Depends(db_session),
):

    try:
        result = await process_file_chat(db, session_id, message, file)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error("文件处理失败 session=%s: %s", session_id[:8], e)
        raise HTTPException(500, f"文件处理失败: {e}")

    logger.info(
        "文件对话 session=%s file=%s rag_mode=%s",
        session_id[:8], file.filename, rag_mode,
    )

    # 大文件已索引，强制启用 RAG 检索
    if result.images is None and rag_mode == "off":
        rag_mode = "auto"

    async def _file_chat_stream(ctx: ChatContext, fi: FileChatResult) -> AsyncGenerator[str, None]:
        file_data = {
            "url": fi.file_url,
            "name": fi.file_name,
            "size": fi.file_size,
            "type": fi.file_type,
        }
        yield f"event: file_info\ndata: {json.dumps(file_data)}\n\n"
        async for event in sse_chat_stream(ctx):
            yield event

    return StreamingResponse(
        _file_chat_stream(ChatContext(
            session_id=session_id,
            user_message=result.augmented_message,
            show_thinking=show_thinking,
            msg_count_before=result.msg_count_before,
            title_source=message,
            images=result.images,
            rag_mode=rag_mode,
            web_search=web_search,
            model_source=model_source or None,
            model_id=model_id or None,
            current_file=file.filename,
        ), result),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.put("/sessions/{session_id}/messages/{message_id}", response_model=OkResponse)
async def edit_message(session_id: str, message_id: int, body: MessageEditRequest, db=Depends(db_session)):
    """编辑用户消息。仅允许编辑 user 角色消息，编辑后截断后续消息。"""
    try:
        await session_service.edit_user_message(db, session_id, message_id, body.content)
    except ValueError as e:
        raise _map_message_error(e)

    logger.info("编辑消息 session=%s msg_id=%d", session_id[:8], message_id)
    return {"ok": True}


@router.delete("/sessions/{session_id}/messages/{message_id}", response_model=OkResponse)
async def delete_message_endpoint(session_id: str, message_id: int, db=Depends(db_session)):
    """删除消息及其之后的所有消息。"""
    try:
        await session_service.delete_message_and_after(db, session_id, message_id)
    except ValueError as e:
        raise _map_message_error(e)

    logger.info("删除消息 session=%s msg_id=%d", session_id[:8], message_id)
    return {"ok": True}
