import asyncio
import os
import logging
from dataclasses import dataclass

from fastapi import UploadFile

from config import get_settings
from services.file_service import save_upload, extract_text, is_image_file, image_to_base64
from services.rag_service import index_file_background

logger = logging.getLogger(__name__)

_SMALL_FILE_THRESHOLD = 5000


@dataclass
class FileChatResult:
    augmented_message: str
    images: list[str] | None
    msg_count_before: int
    file_url: str | None = None
    file_name: str = ""
    file_size: int = 0
    file_type: str = "document"


async def process_file_chat(
    db,
    session_id: str,
    message: str,
    file: UploadFile,
) -> FileChatResult:
    from database import count_messages

    image_data = None
    filepath = await save_upload(file)
    if is_image_file(filepath):
        # 图片直接传 base64 给视觉模型理解，不需要文本提取
        image_data = image_to_base64(filepath)
        file_content = ""
    else:
        file_content = await asyncio.to_thread(extract_text, filepath)
        logger.info("文件提取完成: %s len=%d", file.filename, len(file_content))

    if not image_data and (not file_content or not file_content.strip()):
        raise ValueError(
            "无法从文件中提取有效文本内容"
        )

    if image_data:
        augmented = message
        images = [image_data]
        # 图片不需要 RAG 索引，跳过
    elif len(file_content) <= _SMALL_FILE_THRESHOLD:
        asyncio.create_task(
            index_file_background(db, session_id, file.filename, file_content)
        )
        augmented = f"【文件：{file.filename}】\n{file_content}\n\n---\n{message}"
        images = None
    else:
        _INLINE_CHARS = 2500
        inline_body = file_content[:_INLINE_CHARS].strip()
        if len(file_content) > _INLINE_CHARS:
            inline_body += "\n\n[文件内容过长，仅展示开头，剩余部分正在后台索引]"
        asyncio.create_task(
            index_file_background(db, session_id, file.filename, file_content)
        )
        augmented = f"【文件：{file.filename}】\n{inline_body}\n\n---\n{message}"
        images = None

    max_len = get_settings().max_input_length
    if len(augmented) > max_len:
        head = f"【文件：{file.filename}】\n"
        tail = f"\n\n---\n{message}"
        body_max = max_len - len(head) - len(tail) - len("\n\n[文件内容过长，已截断，仅保留首尾]\n\n")
        if body_max > 0:
            body = file_content[:body_max // 2] + \
                "\n\n[文件内容过长，已截断，仅保留首尾]\n\n" + \
                file_content[-(body_max // 2):]
            augmented = head + body + tail
        else:
            augmented = augmented[:max_len] + "\n\n[消息过长，已截断]"

    msg_count_before = await count_messages(db, session_id)

    ext = os.path.splitext(file.filename)[1].lower()
    file_url = f"/uploads/{os.path.basename(filepath)}"
    file_size = os.path.getsize(filepath)

    if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        file_type = "image"
    elif ext == ".pdf":
        file_type = "pdf"
    elif ext in {".txt", ".md"}:
        file_type = "text"
    else:
        file_type = "document"

    return FileChatResult(
        augmented_message=augmented,
        images=images,
        msg_count_before=msg_count_before,
        file_url=file_url,
        file_name=file.filename,
        file_size=file_size,
        file_type=file_type,
    )
