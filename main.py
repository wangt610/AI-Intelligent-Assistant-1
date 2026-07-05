"""
AI 智能助手 — 应用入口

FastAPI 应用初始化、中间件注册、路由挂载。
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from config import get_settings
from runtime_config import RuntimeSettingsStore, get_config
from database import init_db, close_db
from logging_config import setup_logging
from services.rag_service import init_vector_store, init_embedder
from middleware import (
    SecurityHeadersMiddleware,
    RequestBodyLimitMiddleware,
    RequestIDMiddleware,
    TimingMiddleware,
)
from routers import chat, events, history, health, index_routes, models, model_sources, settings

logger = logging.getLogger(__name__)


async def resume_incomplete_indexing():
    try:
        from database import get_db, get_incomplete_tasks
        from services.rag_service import index_file

        db = await get_db()
        tasks = await get_incomplete_tasks(db)
        if not tasks:
            return

        logger.info("发现 %d 个未完成的索引任务，正在恢复...", len(tasks))
        for task in tasks:
            file_path = task.get("file_path", "")
            if file_path and os.path.exists(file_path):
                from services.file_service import extract_text

                try:
                    text = extract_text(file_path)
                    await index_file(
                        db,
                        task["session_id"],
                        task["file_name"],
                        text,
                        task_id=task["id"],
                    )
                    logger.info("恢复索引成功: %s", task["file_name"])
                except Exception as e:
                    logger.error("恢复索引失败 %s: %s", task["file_name"], e)
            else:
                from database import mark_failed

                await mark_failed(db, task["id"], "原始文件已不存在")
                logger.warning("索引文件已不存在: %s", task.get("file_name"))
    except Exception as e:
        logger.warning("恢复索引任务时出错: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化资源。"""
    settings = get_settings()
    setup_logging(settings.log_level)

    RuntimeSettingsStore.init()

    prompt_path = os.path.join(os.path.dirname(__file__), settings.system_prompt_path)
    if os.path.isfile(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            settings.system_prompt = f.read()

    from services.vector_store import ChromaAdapter
    from services.providers import OllamaEmbeddingProvider

    init_vector_store(ChromaAdapter())
    logger.info("向量存储就绪: %s", settings.chroma_persist_dir)

    init_embedder(OllamaEmbeddingProvider())
    logger.info("Embedding 提供就绪: %s", settings.embedding_model)

    logger.info("正在初始化数据库...")
    await init_db()

    # 启动后台任务
    asyncio.create_task(resume_incomplete_indexing())

    from services.model_warmup import get_warmup_manager
    await get_warmup_manager().start()

    logger.info("应用启动完成 [model=%s] [rag=%s]", settings.ollama_model, get_config("rag_enabled"))

    yield
    await get_warmup_manager().shutdown()
    await close_db()
    logger.info("应用关闭")


app = FastAPI(
    title="AI 智能助手",
    version="2.0.0",
    lifespan=lifespan,
)


def _register_middleware(app: FastAPI) -> None:
    """注册所有中间件（注意：注册顺序与执行顺序相反）"""
    settings = get_settings()

    # 最内层：请求体限制
    max_body = settings.max_upload_size + 1024 * 1024  # 留 1MB 余量
    app.add_middleware(RequestBodyLimitMiddleware, max_size=max_body)

    # 安全头
    app.add_middleware(SecurityHeadersMiddleware)

    # 耗时统计（内层）
    app.add_middleware(TimingMiddleware)

    # 请求 ID（外层，先注入 trace_id，供 Timing 日志使用）
    app.add_middleware(RequestIDMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


_register_middleware(app)

# API 路由（优先于静态文件）
app.include_router(health.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(index_routes.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(model_sources.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(settings.router)

# 上传文件静态目录（保留源文件供前端预览）
app.mount("/uploads", StaticFiles(directory=get_settings().upload_dir), name="uploads")

# React 前端构建产物
_fe_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_fe_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(_fe_dist, "assets")), name="fe_assets")

    @app.get("/", response_class=HTMLResponse)
    async def index_react():
        fe_index = os.path.join(_fe_dist, "index.html")
        if os.path.isfile(fe_index):
            with open(fe_index, "r", encoding="utf-8") as f:
                return HTMLResponse(f.read())
        return HTMLResponse("Frontend not built. Run: cd frontend && npm run build")


if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading

    settings = get_settings()
    port = settings.port

    # 启动后自动打开浏览器
    def open_browser():
        webbrowser.open(f"http://127.0.0.1:{port}")

    threading.Timer(1.5, open_browser).start()
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=settings.dev_reload)
