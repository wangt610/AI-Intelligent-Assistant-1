"""
富内容轮次增量摘要生成 — 仅当压缩引擎发现有富内容轮次时才调用 LLM。

专门针对本地小模型优化：
- 只输入用户消息（减半 input token）
- temperature=0（确定性，节省推理）
- num_predict=100（输出控制在 50-80 字）
"""

import logging

logger = logging.getLogger(__name__)


async def summarize_rich_rounds(pairs: list, existing_summary: str = "") -> str | None:
    """对富内容轮次生成增量摘要。

    Args:
        pairs: _Pair 对象列表（来自 compress 模块）。
        existing_summary: 已有累积摘要（空字符串表示首次压缩）。

    Returns:
        新摘要文本，失败时返回 None。
    """
    try:
        user_msgs = []
        for p in pairs:
            text = p.user.get("content", "")[:300]
            if text:
                user_msgs.append(text)

        if not user_msgs:
            return None

        if existing_summary:
            prompt = (
                "以下是已有的对话摘要和新的对话内容。"
                "请将它们合并为一段简洁的新摘要（50字以内），保留关键信息：\n\n"
                f"已有摘要：{existing_summary}\n\n"
                f"新对话：\n" + "\n".join(user_msgs)
            )
        else:
            prompt = (
                "以下对话的核心内容是什么？用一句话概括（50字以内）：\n"
                + "\n".join(user_msgs)
            )

        from services.providers import get_provider

        provider = get_provider(None, None)
        summary = await provider.complete(
            [{"role": "user", "content": prompt}],
            max_tokens=100, temperature=0,
        )
        summary = summary.strip()
        if summary:
            logger.debug("增量摘要生成 len=%d", len(summary))
            return summary
    except Exception as e:
        logger.warning("摘要生成失败: %s", e)

    return None
