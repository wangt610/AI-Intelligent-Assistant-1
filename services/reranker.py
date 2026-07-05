"""
BM25 混合重排序

将向量相似度与 BM25 关键词匹配分数加权融合，提升检索质量。
"""

import numpy as np
from rank_bm25 import BM25Okapi


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    tokens: list[str] = []
    buf: list[str] = []
    is_cjk_buf: bool | None = None

    def flush():
        nonlocal buf
        if not buf:
            return
        word = ''.join(buf)
        if is_cjk_buf:
            if len(word) == 1:
                tokens.append(word)
            else:
                for i in range(len(word) - 1):
                    tokens.append(word[i:i+2])
        else:
            tokens.append(word)
        buf = []

    for ch in text:
        is_cjk = '\u4e00' <= ch <= '\u9fff'
        is_alnum = ch.isalnum()

        if not is_cjk and not is_alnum:
            flush()
            is_cjk_buf = None
            continue

        kind = is_cjk
        if is_cjk_buf is not None and kind != is_cjk_buf:
            flush()
        buf.append(ch)
        is_cjk_buf = kind

    flush()
    return tokens


def rerank(
    query: str,
    candidates: list[dict],
    bm25_weight: float,
) -> list[dict]:
    """混合重排序：向量相似度 + BM25 关键词匹配。

    BM25 分数只计算一次（O(n)），而非在循环中重复计算（O(n²)）。
    """
    if len(candidates) < 2:
        return candidates

    tokenized_corpus = [_tokenize(c["text"]) for c in candidates]
    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores = bm25.get_scores(_tokenize(query))
    bm25_max = bm25_scores.max() if bm25_scores.max() > 0 else 1.0

    vec_weight = 1 - bm25_weight
    for i, c in enumerate(candidates):
        vec_part = c["score"] * vec_weight
        bm25_norm = bm25_scores[i] / bm25_max
        c["score"] = round(vec_part + bm25_weight * bm25_norm, 4)

    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates
