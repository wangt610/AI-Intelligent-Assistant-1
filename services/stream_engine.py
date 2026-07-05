"""
SSE 流式对话引擎

将 chat() 和 chat_with_file() 中重复的 SSE 生成逻辑
抽取为统一的可复用异步生成器。
"""

import json
import re
import asyncio
import logging
from dataclasses import dataclass
from typing import Any, AsyncGenerator

from database import get_db, get_messages, count_messages, save_message, delete_message, rename_session, get_session
from services.prompt_builder import build_messages
from services.providers import get_provider
from services.web_search import analyze_search_intent, do_web_search
from services.memory import retrieve as memory_retrieve
from config import get_settings
from runtime_config import get_config

logger = logging.getLogger(__name__)


def _safe_title(text: str, max_len: int = 30) -> str:
    """从文本开头截取安全的标题。"""
    clean = text.strip().replace("\n", " ")
    if len(clean) <= max_len:
        return clean
    truncated = clean[:max_len]
    match = re.search(r'^(.*)[\s,，。！？!?]', truncated)
    if match:
        return match.group(1) + "..."
    return truncated + "..."


async def _do_rag_search(
    session_id: str,
    user_message: str,
    rag_mode: str,
    history: list[dict] | None = None,
    current_file: str | None = None,
    memory_hits: list[dict] | None = None,
) -> list[dict] | None:
    """执行 RAG 检索，返回上下文块列表。"""
    if rag_mode == "off" or not get_config("rag_enabled"):
        return None
    from services.rag_service import search, count_indexed_chunks

    chunk_count = await count_indexed_chunks(session_id)
    do_search = rag_mode == "force" or (rag_mode == "auto" and chunk_count > 0)

    if do_search:
        return await search(
            query=user_message,
            session_id=session_id,
            history=history,
            source_file=current_file,
            memory_hits=memory_hits,
        )
    return None


@dataclass
class ChatContext:
    session_id: str
    user_message: str
    show_thinking: bool = False
    msg_count_before: int = 0
    title_source: str = ""
    images: list[str] | None = None
    rag_mode: str = "off"
    web_search: bool = False
    model_source: str | None = None
    model_id: str | None = None
    current_file: str | None = None  # 当前上传的文件名，用于 RAG 过滤


def _index_message(session_id: str, message_id: int, role: str, content: str) -> None:
    """非阻塞语义记忆索引（fire-and-forget）。"""
    try:
        from config import get_settings
        if get_settings().memory_enabled:
            from services.memory import index_message
            asyncio.create_task(index_message(session_id, message_id, role, content))
    except Exception as e:
        logger.warning("语义记忆索引失败: %s", e)


async def sse_chat_stream(
    ctx: ChatContext,
) -> AsyncGenerator[str, None]:
    """SSE 流式对话生成器。

    编排 RAG 检索、语义记忆检索、联网搜索、模型流式生成，
    输出 SSE 事件流（token / thinking / rag_sources / search_sources / done / error / heartbeat）。

    Yields:
        符合 SSE 格式的字符串行。
    """
    full_text = ""
    full_thinking = ""
    user_msg_id = None
    event_id = 0

    db = await get_db()
    try:
        user_msg_id = await save_message(db, ctx.session_id, "user", ctx.user_message)
        _index_message(ctx.session_id, user_msg_id, "user", ctx.user_message)

        settings = get_settings()
        session = await get_session(db, ctx.session_id)
        compressed_up_to_id = (session or {}).get("compressed_up_to_id") or None
        history = await get_messages(
            db, ctx.session_id, get_config("max_history_messages"),
            after_id=compressed_up_to_id,
        )
        session_summary = (session or {}).get("summary") or None

        # 并行启动 RAG、语义记忆检索、搜索预判、和投机性联网搜索
        rag_task = asyncio.create_task(
            _do_rag_search(
                ctx.session_id, ctx.user_message, ctx.rag_mode, history, ctx.current_file,
            )
        )
        memory_task = asyncio.create_task(
            memory_retrieve(ctx.session_id, ctx.user_message, top_k=50, min_score=0.0)
        ) if get_settings().memory_enabled else None
        intent_task = asyncio.create_task(
            analyze_search_intent(ctx.user_message, history)
        ) if ctx.web_search else None

        spec_web_task = asyncio.create_task(
            do_web_search(ctx.user_message)
        ) if ctx.web_search else None

        # 等所有预取任务（投机搜索在后台独立运行）
        await asyncio.wait(
            [t for t in [rag_task, intent_task, memory_task] if t is not None]
        )

        rag_context = rag_task.result()
        if isinstance(rag_context, Exception):
            logger.warning("RAG 检索失败: %s", rag_context)
            rag_context = None

        memory_hits = memory_task.result() if memory_task else None
        if isinstance(memory_hits, Exception):
            logger.debug("语义记忆检索异常: %s", memory_hits)
            memory_hits = None

        # Phase 2: 条件记忆增强 RAG（已移除 — 与首 token 延迟权重大于收益）
        # 语义记忆历史重排序功能保持正常（memory_hits → build_messages）

        web_context = None
        if intent_task:
            intent_result = intent_task.result()
            if isinstance(intent_result, Exception):
                logger.debug("搜索预判异常，降级搜索: %s", intent_result)
                intent_result = ctx.user_message

            if intent_result and spec_web_task:
                # 需要联网搜索 — 投机搜索已在运行，等待它完成
                done, _ = await asyncio.wait([spec_web_task], timeout=3.0)
                if done:
                    web_context = spec_web_task.result()
                else:
                    # 投机未完成且预判改写了查询 → 用改写后的查询重搜
                    if intent_result != ctx.user_message:
                        spec_web_task.cancel()
                        web_context = await do_web_search(intent_result)
                    else:
                        web_context = await spec_web_task
            elif spec_web_task:
                # 不需要联网搜索 — 取消投机任务
                spec_web_task.cancel()

        sources = []
        if rag_context:
            sources.extend({"file": r["source_file"], "score": r["score"], "type": "rag"} for r in rag_context)
        if web_context:
            sources.extend({"file": r["source_file"], "score": r["score"], "type": "web", "title": r.get("title", "")} for r in web_context)
        if sources:
            event_id += 1
            yield f"id: {event_id}\nevent: rag_sources\ndata: {json.dumps({'sources': sources})}\n\n"

        # 联网搜索结果元数据（含 title/url，供前端渲染 [N] 角标）
        if web_context:
            event_id += 1
            search_sources = [
                {"index": i + 1, "title": r.get("title", ""), "url": r["source_file"]}
                for i, r in enumerate(web_context)
            ]
            yield f"id: {event_id}\nevent: search_sources\ndata: {json.dumps(search_sources)}\n\n"

        messages = build_messages(
            system_prompt=settings.system_prompt,
            history=history,
            current_message=ctx.user_message,
            rag_context=rag_context,
            web_context=web_context,
            images=ctx.images,
            memory_hits=memory_hits,
            session_summary=session_summary,
            max_history=get_config("max_history_messages"),
            max_context_tokens=get_config("max_context_tokens"),
        )

        heartbeat_interval = 5.0
        last_heartbeat = asyncio.get_event_loop().time()

        provider = get_provider(ctx.model_source, ctx.model_id)
        async for token in provider.stream(messages, ctx.show_thinking):
            now = asyncio.get_event_loop().time()
            if now - last_heartbeat >= heartbeat_interval:
                last_heartbeat = now
                event_id += 1
                yield f"id: {event_id}\nevent: heartbeat\ndata: {json.dumps({'ts': now})}\n\n"

            event_id += 1
            if token["type"] == "thinking":
                full_thinking += token["text"]
                yield f"id: {event_id}\nevent: thinking\ndata: {json.dumps({'text': token['text']})}\n\n"
            elif token["type"] == "content":
                full_text += token["text"]
                yield f"id: {event_id}\nevent: token\ndata: {json.dumps({'token': token['text']})}\n\n"

        if full_text:
            assistant_msg_id = await save_message(db, ctx.session_id, "assistant", full_text)
            _index_message(ctx.session_id, assistant_msg_id, "assistant", full_text)

        title = None
        if ctx.msg_count_before == 0:
            title = _safe_title(ctx.title_source)
            if title:
                await rename_session(db, ctx.session_id, title)

        event_id += 1
        yield (
            f"id: {event_id}\nevent: done\ndata: "
            f"{json.dumps({'full_text': full_text, 'full_thinking': full_thinking, 'session_title': title})}\n\n"
        )

        from services.model_warmup import get_warmup_manager
        get_warmup_manager().observe_use(ctx.model_source or "ollama", ctx.model_id or settings.ollama_model)

        # 当未压缩消息数接近预算上限时，后台异步执行混合压缩
        uncompressed_count = await count_messages(db, ctx.session_id, after_id=compressed_up_to_id)
        if uncompressed_count >= get_config("max_history_messages") * 0.8:
            from services.compress import maybe_compress
            asyncio.create_task(
                maybe_compress(db, ctx.session_id, get_config("max_history_messages")),
            )

        logger.info(
            "对话完成 session=%s tokens=%d",
            ctx.session_id[:8], len(full_text),
        )

    except asyncio.CancelledError:
        logger.warning("对话流被中断 session=%s partial=%d", ctx.session_id[:8], len(full_text))
        if full_text:
            interrupted_msg_id = await save_message(db, ctx.session_id, "assistant", full_text + "\n\n[回复被中断]", status="interrupted")
            _index_message(ctx.session_id, interrupted_msg_id, "assistant", full_text + "\n\n[回复被中断]")
        elif user_msg_id is not None:
            await delete_message(db, user_msg_id)
        return
    except Exception as e:
        if user_msg_id is not None:
            try:
                await delete_message(db, user_msg_id)
            except Exception:
                pass
        logger.error("对话流异常 session=%s: %s", ctx.session_id[:8], e)
        event_id += 1
        yield (
            f"id: {event_id}\nevent: error\ndata: "
            f"{json.dumps({'detail': str(e)})}\n\n"
        )
