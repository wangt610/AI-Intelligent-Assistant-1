"""
会话历史路由

提供会话 CRUD 和消息查询接口。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

import database
from services import session_service
from models.schemas import (
    SessionCreate,
    SessionRename,
    SessionListResponse,
    SessionResponse,
    MessageListResponse,
    OkResponse,
)
from routers.dependencies import db_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sessions"])


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(db=Depends(db_session)):
    sessions = await database.get_sessions(db)
    return {"sessions": sessions}


@router.get("/sessions/search", response_model=SessionListResponse)
async def search_sessions_api(q: str = Query(..., min_length=1, max_length=100), db=Depends(db_session)):
    sessions = await database.search_sessions(db, q.strip())
    return {"sessions": sessions}


@router.post("/sessions", status_code=201, response_model=SessionResponse)
async def new_session(body: SessionCreate, db=Depends(db_session)):
    session_id = await database.create_session(db, body.title)
    session = await database.get_session(db, session_id)
    logger.info("创建新会话: %s (%s)", session["id"], body.title)
    return session


@router.put("/sessions/{session_id}", response_model=OkResponse)
async def edit_session(session_id: str, body: SessionRename, db=Depends(db_session)):
    if not await database.get_session(db, session_id):
        raise HTTPException(404, "会话不存在")
    await database.rename_session(db, session_id, body.title)
    return {"ok": True}


@router.delete("/sessions/{session_id}", response_model=OkResponse)
async def remove_session(session_id: str, db=Depends(db_session)):
    if not await database.get_session(db, session_id):
        raise HTTPException(404, "会话不存在")
    await session_service.delete_session_full(db, session_id)
    logger.info("删除会话: %s", session_id)
    return {"ok": True}


@router.get("/sessions/{session_id}/messages", response_model=MessageListResponse)
async def list_messages(session_id: str, db=Depends(db_session)):
    if not await database.get_session(db, session_id):
        raise HTTPException(404, "会话不存在")
    messages = await database.get_messages(db, session_id)
    return {"messages": messages}
