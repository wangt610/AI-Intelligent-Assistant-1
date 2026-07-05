"""JSON 原子写入工具 — 提供可靠的持久化基元。"""

import json
import os
import logging

logger = logging.getLogger(__name__)


def atomic_json_write(path: str, data: object) -> None:
    """原子方式写入 JSON 文件（.tmp → os.replace），防止崩溃导致文件损坏。"""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception as e:
        logger.warning("JSON 写入失败 %s: %s", path, e)
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def atomic_json_read(path: str, default: object = None) -> object:
    """安全读取 JSON 文件，不存在或损坏时返回 default。"""
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("JSON 读取失败 %s: %s", path, e)
        return default
