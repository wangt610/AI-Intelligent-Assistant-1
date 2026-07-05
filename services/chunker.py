"""
文本分块器 — 标题感知分段 + token 级切分。
"""

import re

from config import get_settings
from runtime_config import get_config
from utils.token_counter import get_encoder

_HEADING_RE = re.compile(r"^#{1,6}\s+.+", re.MULTILINE)


def _chunk_by_tokens_only(text: str, max_tokens: int, step: int) -> list[str]:
    encoder = get_encoder()
    tokens = encoder.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunks.append(encoder.decode(tokens[start:end]).strip())
        if end >= len(tokens):
            break
        start = end - step
    return [c for c in chunks if c]


def _split_at_headings(text: str, _cache: dict | None = None) -> list[dict]:
    in_code = False
    in_comment = False
    code_fence: str | None = None
    if _cache is None:
        _cache = {}
    encoder = get_encoder()

    def _tc(t: str) -> int:
        if t not in _cache:
            _cache[t] = len(encoder.encode(t))
        return _cache[t]

    sections: list[dict] = []
    current_lines: list[str] = []
    current_heading: str | None = None

    for line in text.split("\n"):
        stripped = line.strip()

        if stripped.startswith("```") or stripped.startswith("~~~"):
            fence = "```" if stripped.startswith("```") else "~~~"
            if not in_code:
                in_code = True
                code_fence = fence
            elif code_fence == fence:
                in_code = False
                code_fence = None
            in_comment = False
            current_lines.append(line)
            continue

        if not in_code:
            if not in_comment and "<!--" in line:
                in_comment = True
                current_lines.append(line)
                if "-->" in line:
                    in_comment = False
                continue
            if in_comment:
                current_lines.append(line)
                if "-->" in line:
                    in_comment = False
                continue

        if not in_code and not in_comment:
            match = _HEADING_RE.match(line)
            if match:
                if current_lines:
                    section_text = "\n".join(current_lines)
                    sections.append({
                        "text": section_text,
                        "tokens": _tc(section_text),
                        "heading": current_heading,
                        "heading_text": current_heading,
                    })
                current_lines = [line]
                current_heading = line
                continue

        current_lines.append(line)

    if current_lines:
        section_text = "\n".join(current_lines)
        sections.append({
            "text": section_text,
            "tokens": _tc(section_text),
            "heading": current_heading,
            "heading_text": current_heading,
        })

    return sections


def _split_oversize_section(section: dict, max_tokens: int, step: int, _cache: dict | None = None) -> list[str]:
    encoder = get_encoder()
    if _cache is None:
        _cache = {}
    heading = section.get("heading_text") or ""

    if not heading:
        return _chunk_by_tokens_only(section["text"], max_tokens, step)

    def _tc(t: str) -> int:
        if t not in _cache:
            _cache[t] = len(encoder.encode(t))
        return _cache[t]

    heading_tokens = _tc(heading)
    body_max = max_tokens - heading_tokens - 1
    if body_max < 64:
        body_max = max_tokens

    body = section["text"][len(heading):]
    body_tokens = encoder.encode(body) if body else []

    chunks = []
    for i in range(0, len(body_tokens), body_max):
        chunk = heading + "\n" + encoder.decode(body_tokens[i:i + body_max])
        chunks.append(chunk.strip())
    return chunks


def _merge_and_split(sections: list[dict], max_tokens: int, step: int, _cache: dict | None = None) -> list[str]:
    if _cache is None:
        _cache = {}
    result: list[str] = []
    buffer_lines: list[str] = []
    buffer_tokens = 0

    for section in sections:
        if buffer_tokens + section["tokens"] <= max_tokens:
            buffer_lines.append(section["text"])
            buffer_tokens += section["tokens"]
            continue

        if buffer_lines:
            result.append("\n".join(buffer_lines))

        if section["tokens"] <= max_tokens:
            buffer_lines = [section["text"]]
            buffer_tokens = section["tokens"]
        else:
            buffer_lines = []
            buffer_tokens = 0
            result.extend(_split_oversize_section(section, max_tokens, step, _cache))

    if buffer_lines:
        result.append("\n".join(buffer_lines))

    return [c for c in result if c]


def _chunk_by_headings(text: str, max_tokens: int, step: int, _cache: dict | None = None) -> list[str]:
    if _cache is None:
        _cache = {}
    sections = _split_at_headings(text, _cache)
    if len(sections) <= 1:
        if sections and sections[0]["heading"] and sections[0]["tokens"] > max_tokens:
            return _split_oversize_section(sections[0], max_tokens, step, _cache)
        return _chunk_by_tokens_only(text, max_tokens, step)
    return _merge_and_split(sections, max_tokens, step, _cache)


def chunk_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    max_tokens = chunk_size or get_config("rag_chunk_size")
    overlap_tokens = overlap or get_config("rag_chunk_overlap")
    step = max_tokens - overlap_tokens
    if step < 1:
        step = max_tokens

    if not text:
        return []

    _cache: dict[str, int] = {}

    if _HEADING_RE.search(text):
        return _chunk_by_headings(text, max_tokens, step, _cache)

    return _chunk_by_tokens_only(text, max_tokens, step)
