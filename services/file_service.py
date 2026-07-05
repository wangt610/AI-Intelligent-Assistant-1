import os
import uuid
import base64
from config import get_settings
from services.extractors import extract_text, IMAGE_EXTENSIONS

ALLOWED_EXTENSIONS = {
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


async def save_upload(file) -> str:
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        supported = "txt/md/pdf/docx/xlsx/pptx/html/csv/json/xml/epub/zip/jpg/png/gif/webp"
        raise ValueError(f"不支持的文件类型: {ext}，支持 {supported}")

    settings = get_settings()
    os.makedirs(settings.upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(settings.upload_dir, filename)

    # 分块读取并检查大小，避免将超大文件全部读入内存（阻塞事件循环）。
    # 使用 UploadFile.read() 异步读取。
    chunk_size = 64 * 1024  # 64KB 分块
    with open(filepath, "wb") as f:
        written = 0
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            written += len(chunk)
            if written > settings.max_upload_size:
                f.close()
                os.remove(filepath)
                raise ValueError(f"文件大小超过 {settings.max_upload_size // (1024*1024)}MB 限制")
            f.write(chunk)

    return filepath


def is_image_file(filepath: str) -> bool:
    """判断文件是否为图片。"""
    ext = os.path.splitext(filepath)[1].lower()
    return ext in IMAGE_EXTENSIONS


def image_to_base64(filepath: str) -> str:
    """读取图片文件并转换为 base64 字符串。"""
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# extract_text 委托给 services/extractors
