"""
索引管理路由

提供会话内已索引文件的查询和删除接口。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from models.schemas import IndexedFileListResponse, IndexedFileDeleteResponse
from services.rag_service import delete_file_index, list_indexed_files
from routers.dependencies import db_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["index"])


@router.get("/sessions/{session_id}/indexed-files", response_model=IndexedFileListResponse)
async def list_indexed_files_api(session_id: str, db=Depends(db_session)):
    files = await list_indexed_files(db, session_id)
    return {"files": files}


@router.delete("/sessions/{session_id}/indexed-files", response_model=IndexedFileDeleteResponse)
async def remove_indexed_file(
    session_id: str,
    file_name: str = Query(..., description="要删除索引的文件名"),
):
    """删除某个文件的索引（ChromaDB + SQLite 记录）。"""
    try:
        chunks_removed = await delete_file_index(session_id, file_name)
        return {"deleted": chunks_removed > 0, "chunks_removed": chunks_removed}
    except Exception as e:
        logger.error("删除索引失败 session=%s file=%s: %s", session_id[:8], file_name, e)
        raise HTTPException(500, f"删除索引失败: {e}")
