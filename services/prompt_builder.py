"""
Prompt 构建器 — 纯函数，负责组装 messages 列表。

分层架构：
- system：角色设定 + 可选的会话摘要（session_summary）
- history：历史上下文（按 token 预算从新到旧裁剪，不含当前用户消息）
- user：当前用户消息（含 RAG/Web 上下文注入）
"""

import logging

from utils.token_counter import count_tokens

logger = logging.getLogger(__name__)


_system_token_cache: dict[str, int] = {}


def build_messages(
    system_prompt: str,
    history: list[dict],
    current_message: str,
    *,
    rag_context: list[dict] | None = None,
    web_context: list[dict] | None = None,
    images: list[str] | None = None,
    memory_hits: list[dict] | None = None,
    session_summary: str | None = None,
    max_history: int = 60,
    max_context_tokens: int = 24000,
) -> list[dict]:
    # ── 1. 固定开销 ──
    cached = _system_token_cache.get(system_prompt)
    if cached is None:
        cached = count_tokens(system_prompt)
        _system_token_cache[system_prompt] = cached
    system_tokens = cached

    # 预留输出空间（输出仅需单轮回复，留 max_context_tokens 的 1/4 足够）
    output_reserved = max(2048, min(8192, max_context_tokens // 4))

    # ── 2. RAG 上下文自适应选择（按分数降序，不超过预算） ──
    selected_rag = None
    if rag_context:
        remaining = max_context_tokens - system_tokens - output_reserved
        rag_budget = int(remaining * 0.35)
        selected_rag = _select_rag_chunks(rag_context, rag_budget)

    user_content = _assemble_user_content(
        current_message,
        rag_context=selected_rag,
        web_context=web_context,
    )
    user_tokens = count_tokens(user_content)

    history_budget = max_context_tokens - system_tokens - user_tokens - output_reserved

    # ── 2. 语义优先 + 新近优先裁剪 ──
    past = history[:-1] if history else []
    relevant_ids = {h["message_id"] for h in (memory_hits or [])}

    relevant_msgs = [msg for msg in past if msg.get("id") in relevant_ids]
    other_msgs = [msg for msg in past if msg.get("id") not in relevant_ids]

    accumulated = 0
    selected: list[dict] = []

    # 2a. 先装入语义相关消息（按相关度降序）
    if memory_hits:
        score_map = {h["message_id"]: h["score"] for h in memory_hits}
        relevant_msgs.sort(key=lambda m: score_map.get(m.get("id", 0), 0), reverse=True)
        for msg in relevant_msgs:
            msg_tokens = count_tokens(msg.get("content", ""))
            if accumulated + msg_tokens > history_budget:
                break
            selected.append(msg)
            accumulated += msg_tokens

    # 2b. 再按时间从新到旧装入其余消息
    for msg in reversed(other_msgs):
        msg_tokens = count_tokens(msg.get("content", ""))
        if accumulated + msg_tokens > history_budget:
            if not selected:
                selected.append(msg)
            break
        selected.append(msg)
        accumulated += msg_tokens
        if len(selected) >= max_history:
            break
    selected.sort(key=lambda m: m.get("id", 0))

    # ── 3. 组装 ──
    messages = [{"role": "system", "content": system_prompt}]
    if session_summary:
        messages.append({"role": "system", "content": f"[会话摘要] {session_summary}"})
    messages.extend(selected)

    user_msg = {"role": "user", "content": user_content}
    if images:
        user_msg["images"] = images
    messages.append(user_msg)

    return messages


def _select_rag_chunks(rag_context: list[dict], budget: int) -> list[dict]:
    selected = []
    used = 0
    for chunk in sorted(rag_context, key=lambda c: c.get("score", 0), reverse=True):
        chunk_tokens = count_tokens(chunk.get("text", ""))
        if used + chunk_tokens <= budget:
            selected.append(chunk)
            used += chunk_tokens
    return selected


def _assemble_user_content(
    current_message: str,
    *,
    rag_context: list[dict] | None = None,
    web_context: list[dict] | None = None,
) -> str:
    ctx_parts = []

    if rag_context:
        ctx_parts.append(_format_rag_section(rag_context))
    if web_context:
        ctx_parts.append(_format_web_section(web_context))

    if not ctx_parts:
        return current_message

    context_block = "\n\n".join(ctx_parts)
    instruction = _pick_instruction(
        has_rag=rag_context is not None,
        has_web=web_context is not None,
    )
    return f"{context_block}\n\n<指令>\n{instruction}\n</指令>\n\n<用户问题>\n{current_message}\n</用户问题>"


def _pick_instruction(has_rag: bool, has_web: bool) -> str:
    if has_rag and has_web:
        return (
            "请参考以上资料回答。对于参考资料中的内容请严格依据并标注来源；"
            "对于联网搜索结果请结合你的知识回答，不要照搬原文。"
            "引用联网搜索时用 [N] 标注来源编号（如 [1][2]）。"
            "若资料不足请直接说不知道。"
        )
    if has_rag:
        return (
            "请严格依据以上参考资料回答，必要时标注来源。"
            "若资料不足请直接说不知道。"
        )
    return (
        "以下是联网搜索结果，每项以 [N] 编号。请结合你的知识回答，"
        "引用时用 [N] 标注来源（如 [1][2]）。"
        "不要直接照搬搜索内容。若搜索结果不足以回答请直接说不知道。"
    )


def _format_rag_section(rag_context: list[dict]) -> str:
    lines = []
    for i, chunk in enumerate(rag_context):
        lines.append(
            f"[知识库] [{i+1}] {chunk['source_file']}（相关度：{chunk['score']}）\n\n{chunk['text']}"
        )
    return "<参考资料>\n" + "\n\n".join(lines) + "\n</参考资料>"


def _format_web_section(web_context: list[dict]) -> str:
    lines = []
    for i, r in enumerate(web_context):
        title = r.get("title", "") or r["source_file"]
        lines.append(f"[联网搜索] [{i+1}] {title}\n\n{r['text']}")
    return "<联网搜索>\n" + "\n\n".join(lines) + "\n</联网搜索>"
