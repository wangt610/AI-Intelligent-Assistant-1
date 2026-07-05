"""
Pydantic Schema 定义

集中管理所有 API 请求/响应的数据模型。
"""

from pydantic import BaseModel, Field


# ─── 会话相关 ──────────────────────────────────────────


class SessionCreate(BaseModel):
    title: str = "新对话"


class SessionRename(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)


# ─── 对话相关 ──────────────────────────────────────────


class ChatRequest(BaseModel):
    session_id: str
    message: str
    show_thinking: bool = True
    rag_mode: str = "off"
    web_search: bool = False
    model_source: str = "ollama"
    model_id: str = ""


class RegenerateRequest(BaseModel):
    session_id: str
    show_thinking: bool = True
    rag_mode: str = "off"
    web_search: bool = False
    model_source: str = "ollama"
    model_id: str = ""


# ─── 健康检查 ──────────────────────────────────────────


class HealthCheckItem(BaseModel):
    status: str
    detail: str = ""


class HealthResponse(BaseModel):
    status: str  # healthy | degraded | unhealthy
    checks: dict[str, HealthCheckItem]


# ─── 响应模型 ──────────────────────────────────────────


class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]


class MessageItem(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    created_at: str


class MessageListResponse(BaseModel):
    messages: list[MessageItem]


class ModelItem(BaseModel):
    id: str
    source: str
    name: str
    type: str  # "ollama" | "openai"


class ModelListResponse(BaseModel):
    models: list[ModelItem]
    error: str | None = None


class ModelSourceItem(BaseModel):
    name: str
    label: str
    base_url: str
    api_key: str = ""
    type: str


class ModelSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    label: str = Field(..., min_length=1, max_length=100)
    base_url: str = Field(..., min_length=1, max_length=500)
    api_key: str = Field(..., min_length=1, max_length=1000)


class ModelSourceListResponse(BaseModel):
    sources: list[ModelSourceItem]


class IndexedFileItem(BaseModel):
    file_name: str
    status: str
    total_chunks: int
    updated_at: str


class IndexedFileListResponse(BaseModel):
    files: list[IndexedFileItem]


class IndexedFileDeleteResponse(BaseModel):
    deleted: bool
    chunks_removed: int


class MessageEditRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=100000)


class SearchStatusResponse(BaseModel):
    configured: bool
    provider: str = "duckduckgo"
    detail: str = ""


class RuntimeSettingsResponse(BaseModel):
    temperature: float
    top_p: float
    max_context_tokens: int
    max_history_messages: int
    max_output_tokens: int
    rag_enabled: bool
    rag_chunk_size: int
    rag_chunk_overlap: int
    rag_top_k: int
    rag_score_threshold: float
    rag_query_rewrite: bool
    rag_hyde_enabled: bool
    rag_hyde_max_tokens: int
    rag_candidate_k: int
    rag_bm25_weight: float
    search_max_results: int
    search_max_context_tokens: int


class RuntimeSettingsUpdate(BaseModel):
    temperature: float | None = Field(None, ge=0.0, le=1.0)
    top_p: float | None = Field(None, ge=0.0, le=1.0)
    max_context_tokens: int | None = Field(None, gt=0)
    max_history_messages: int | None = Field(None, gt=0)
    max_output_tokens: int | None = Field(None, gt=0)
    rag_enabled: bool | None = None
    rag_chunk_size: int | None = Field(None, gt=0)
    rag_chunk_overlap: int | None = Field(None, ge=0)
    rag_top_k: int | None = Field(None, gt=0)
    rag_score_threshold: float | None = Field(None, ge=0.0, le=1.0)
    rag_query_rewrite: bool | None = None
    rag_hyde_enabled: bool | None = None
    rag_hyde_max_tokens: int | None = Field(None, gt=0)
    rag_candidate_k: int | None = Field(None, gt=0)
    rag_bm25_weight: float | None = Field(None, ge=0.0, le=1.0)
    search_max_results: int | None = Field(None, gt=0)
    search_max_context_tokens: int | None = Field(None, gt=0)


class OkResponse(BaseModel):
    ok: bool
