"""
会话历史混合压缩引擎

策略：
- 裁剪（trim）：总是执行。未压缩消息超出预算时丢弃最旧 N 轮，零 LLM 开销。
- 摘要（summarize）：按需执行。被丢弃的轮次中包含富内容（助手回复 >200 字）
  时才调用 LLM 做增量摘要。
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_RICH_THRESHOLD = 200
_COMPRESS_MIN_ROUNDS = 2


@dataclass
class _Pair:
    user: dict
    assistant: dict | None
    last_id: int


def _extract_pairs(msgs: list[dict]) -> list[_Pair]:
    """从有序消息列表中提取 user-assistant 轮次对。"""
    pairs: list[_Pair] = []
    i = 0
    while i < len(msgs):
        if msgs[i].get("role") == "user":
            user_msg = msgs[i]
            asst_msg = None
            last_id = user_msg["id"]
            if i + 1 < len(msgs) and msgs[i + 1].get("role") == "assistant":
                asst_msg = msgs[i + 1]
                last_id = asst_msg["id"]
                i += 2
            else:
                i += 1
            pairs.append(_Pair(user=user_msg, assistant=asst_msg, last_id=last_id))
        else:
            i += 1
    return pairs


def _has_rich_content(pairs: list[_Pair]) -> bool:
    """判断轮次中是否有富内容（助手回复 >200 字符）。"""
    for p in pairs:
        if p.assistant and len(p.assistant.get("content", "")) > _RICH_THRESHOLD:
            return True
    return False


def _count_uncompressed(
    msgs: list[dict], compressed_up_to_id: int | None,
) -> int:
    """统计未压缩消息条数。"""
    if compressed_up_to_id is None:
        return len(msgs)
    return sum(1 for m in msgs if m["id"] > compressed_up_to_id)


async def maybe_compress(
    db,
    session_id: str,
    max_messages: int,
) -> tuple[int, bool]:
    """检查并执行会话历史压缩。

    返回 (compressed_count, did_summarize)。
        compressed_count: 被裁剪的轮次对数。
        did_summarize: 是否生成了增量摘要。
    """
    from database import get_messages, count_messages, get_session, save_session_summary

    session = await get_session(db, session_id)
    compressed_up_to_id = session.get("compressed_up_to_id") if session else None

    total = await count_messages(db, session_id)
    uncompressed = total
    if compressed_up_to_id is not None:
        uncompressed = await count_messages(db, session_id, after_id=compressed_up_to_id)

    if uncompressed <= max_messages:
        return (0, False)

    # 获取全部未压缩消息（不分页）
    all_msgs = await get_messages(db, session_id, limit=uncompressed, after_id=compressed_up_to_id)
    pairs = _extract_pairs(all_msgs)
    budget = max_messages // 2
    if len(pairs) <= budget:
        return (0, False)

    drop_pairs = pairs[:len(pairs) - budget]
    drop_pairs = drop_pairs[:_COMPRESS_MIN_ROUNDS if len(drop_pairs) > _COMPRESS_MIN_ROUNDS else len(drop_pairs)]
    last_id = drop_pairs[-1].last_id
    did_summarize = False

    if _has_rich_content(drop_pairs):
        from services.summarizer import summarize_rich_rounds
        existing = session.get("summary", "") if session else ""
        summary = await summarize_rich_rounds(drop_pairs, existing_summary=existing)
        if summary:
            await save_session_summary(db, session_id, summary, last_id)
            did_summarize = True
            logger.info(
                "富内容压缩 session=%s 裁剪 %d 轮，摘要已更新 len=%d",
                session_id[:8], len(drop_pairs), len(summary),
            )

    if not did_summarize:
        existing = session.get("summary", "") if session else ""
        await save_session_summary(db, session_id, existing, last_id)
        logger.info(
            "常规压缩 session=%s 裁剪 %d 轮，无摘要",
            session_id[:8], len(drop_pairs),
        )

    return (len(drop_pairs), did_summarize)
