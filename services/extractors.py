"""
文件文本提取器 — 基于 MarkItDown 的统一实现。

所有受支持的文档格式由 MarkItDown 引擎统一处理，
输出结构化 Markdown 文本，供后续 RAG 分块与检索使用。
图片文件不支持文本提取，返回空字符串（图片直接传 base64 给视觉模型理解）。
"""

import os
import logging
from markitdown import MarkItDown

logger = logging.getLogger(__name__)

_md = MarkItDown()

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

_SUPPORTED_EXTENSIONS: set[str] = {
    ".txt", ".md",
    ".pdf",
    ".docx",
    ".xlsx",
    ".pptx",
    ".html",
    ".csv",
    ".json",
    ".xml",
    ".epub",
    ".zip",
} | IMAGE_EXTENSIONS


def extract_text(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in _SUPPORTED_EXTENSIONS:
        raise ValueError(f"不支持的文件类型: {ext}")
    try:
        if ext in IMAGE_EXTENSIONS:
            # 图片不支持文本提取，直接传 base64 给视觉模型理解
            return ""
        result = _md.convert(filepath)
        text = result.text_content
        if not text or not text.strip():
            raise ValueError("文件内容为空，无法提取有效文本")
        return text
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"文件解析失败: {e}")
