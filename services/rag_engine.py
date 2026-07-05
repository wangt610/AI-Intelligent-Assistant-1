"""
RAG 编排引擎

专注检索增强生成的编排工作：
查询重写 → embedding → 向量检索 → HyDE(可选) → BM25 重排序。
embedding 和向量存储由外部适配器提供。
"""

import asyncio
import logging
import re
from collections import OrderedDict

from runtime_config import get_config
from services.reranker import rerank

logger = logging.getLogger(__name__)

# Embedding 缓存：OrderedDict 实现 LRU
_embedding_cache: OrderedDict[str, list[float]] = OrderedDict()
_EMBEDDING_CACHE_MAX = 256

_VAGUE_PRONOUN_RE = re.compile(r"(这|那|它|它们|他|她|这个|这些|那个|那些)")
_QUESTION_HEAD_RE = re.compile(r"^(什么是|如何|怎么|怎样|为什么|哪个|哪些|有没有|能否|请|解释|说明|介绍)")


class RAGEngine:
    def __init__(self, vector_store, embedder):
        self._store = vector_store
        self._embedder = embedder

    # ── Embedding ──────────────────────────────────────────

    async def get_embedding(self, text: str) -> list[float]:
        """获取文本的 embedding 向量，带 LRU 缓存。"""
        if text in _embedding_cache:
            _embedding_cache.move_to_end(text)
            return _embedding_cache[text]
        vector = await self._embedder.embed(text)
        if len(_embedding_cache) >= _EMBEDDING_CACHE_MAX:
            _embedding_cache.popitem(last=False)
        _embedding_cache[text] = vector
        return vector

    # ── 查询重写 ──────────────────────────────────────────

    @staticmethod
    def _needs_rewrite(query: str) -> bool:
        if _QUESTION_HEAD_RE.match(query):
            return False
        return len(query) < 12 and bool(_VAGUE_PRONOUN_RE.search(query))

    async def rewrite_query(self, query: str, history: list[dict] | None, memory_hits: list[dict] | None = None) -> str:
        if not history and not memory_hits:
            return query

        if memory_hits:
            ctx_lines = [h.get("text", "")[:200] for h in memory_hits[:3]]
            memory_ctx = "\n".join(ctx_lines)
            prompt = (
                "你是一个查询改写助手。下面有一段相关对话历史和原始问题。\n"
                "请将原始问题改写得更加完整、独立，保留所有关键信息。\n"
                "直接输出改写结果，不要解释。\n\n"
                f"相关对话：\n{memory_ctx}\n\n"
                f"原始问题：{query}"
            )
            from services.providers import get_provider
            provider = get_provider(None, None)
            try:
                rewritten = await asyncio.wait_for(
                    provider.complete(
                        [{"role": "user", "content": prompt}],
                        max_tokens=50, temperature=0,
                    ),
                    timeout=3,
                )
                rewritten = rewritten.strip()
                if rewritten:
                    logger.debug("记忆增强 query 改写: '%s' → '%s'", query[:40], rewritten[:60])
                    return rewritten
            except Exception as e:
                logger.debug("记忆增强 rewrite 失败，回退: %s", e)

        if not history or not self._needs_rewrite(query):
            return query
        last_user = None
        for msg in reversed(history):
            if msg.get("role") == "user":
                last_user = msg.get("content", "")
                break
        if last_user:
            prefix = last_user[:80].strip()
            return f"{prefix} -> {query}"
        return query

    # ── HyDE ──────────────────────────────────────────────

    async def generate_hypothetical(self, query: str, memory_hits: list[dict] | None = None) -> str:
        if not get_config("rag_hyde_enabled"):
            return query

        if memory_hits:
            ctx_lines = [h.get("text", "")[:200] for h in memory_hits[:3]]
            memory_ctx = "\n".join(ctx_lines)
            prompt = (
                "请根据以下对话上下文和问题，写一段假设性文档内容片段（50-100字），"
                "直接输出内容，不要解释：\n\n"
                f"相关对话：\n{memory_ctx}\n\n"
                f"问题：{query}"
            )
        else:
            prompt = (
                "请根据以下问题，写一段可能出现在文档中的内容片段（50-100字），"
                "直接输出内容，不要解释：\n"
                f"问题：{query}"
            )
        try:
            from services.providers import get_provider
            provider = get_provider(None, None)
            text = await provider.complete(
                [{"role": "user", "content": prompt}],
                max_tokens=get_config("rag_hyde_max_tokens"),
                temperature=0.3,
            )
            text = text.strip()
            if text:
                logger.debug("HyDE 生成: %s", text[:80])
                return text
        except Exception as e:
            logger.warning("HyDE 生成失败，回退到原始 query: %s", e)
        return query

    # ── 检索 ──────────────────────────────────────────────

    async def search(
        self,
        query: str,
        session_id: str,
        top_k: int | None = None,
        history: list[dict] | None = None,
        source_file: str | None = None,
        memory_hits: list[dict] | None = None,
    ) -> list[dict]:
        """检索与 query 最相关的文本块。

        完整流程：
        1. 查询重写（短查询补全 / 记忆增强）
        2. 快速向量检索
        3. 结果质量不佳时启用 HyDE 二次检索
        4. BM25 混合重排序
        5. 返回 top_k

        Args:
            query: 用户原始查询。
            session_id: 会话 ID，用于按会话过滤索引。
            top_k: 返回结果数（默认 runtime_config.rag_top_k）。
            history: 历史消息列表，用于查询重写补全上下文。
            source_file: 可选，按来源文件名过滤。
            memory_hits: 语义记忆检索结果，用于增强查询改写和 HyDE。
        """
        k = top_k or get_config("rag_top_k")

        rewritten = await self.rewrite_query(query, history, memory_hits=memory_hits)

        query_emb = await self.get_embedding(rewritten)
        candidate_k = get_config("rag_candidate_k")

        filter_cond = {"session_id": {"$eq": session_id}}
        if source_file:
            filter_cond["source_file"] = {"$eq": source_file}

        candidates = await self._store.similarity_search(
            query_embedding=query_emb,
            filter=filter_cond,
            top_k=candidate_k,
        )

        if not candidates:
            return []

        best_score = max(c["score"] for c in candidates)
        hyde_threshold = get_config("rag_score_threshold") + 0.1

        if best_score < hyde_threshold and get_config("rag_hyde_enabled"):
            logger.debug(
                "第一轮检索质量不佳 (best_score=%.4f < %.4f)，启用 HyDE 二次检索",
                best_score, hyde_threshold,
            )
            hypo = await self.generate_hypothetical(rewritten, memory_hits=memory_hits)
            if hypo != rewritten:
                hypo_emb = await self.get_embedding(hypo)
                hyde_candidates = await self._store.similarity_search(
                    query_embedding=hypo_emb,
                    filter=filter_cond,
                    top_k=candidate_k,
                )
                seen_ids = {c.get("id") for c in candidates}
                for c in hyde_candidates:
                    if c.get("id") not in seen_ids:
                        candidates.append(c)
                        seen_ids.add(c.get("id"))

        reranked = rerank(rewritten, candidates, get_config("rag_bm25_weight"))
        result = reranked[:k]

        logger.debug(
            "RAG 检索结果: candidate=%d → top=%d scores=%s",
            len(candidates), len(result),
            [r["score"] for r in result],
        )
        return result

    # ── 健康检查 ──────────────────────────────────────────

    async def health_check(self) -> tuple[bool, str]:
        return await self._store.health_check()
