"""
应用配置模块

使用 pydantic-settings 管理所有配置项，支持：
- 环境变量覆盖（自动映射，如 OLLAMA_HOST）
- .env 文件加载
- 类型校验与默认值
"""

import os

from pydantic import BaseModel
from pydantic_settings import BaseSettings


class ModelSourceConfig(BaseModel):
    name: str
    label: str = ""
    type: str = "ollama"
    base_url: str = ""
    api_key: str = ""


class Settings(BaseSettings):
    """应用全局配置"""

    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:2b"
    ollama_timeout: int = 300
    ollama_keep_alive: str = "-1"
    ollama_num_ctx: int = 20480
    ollama_num_batch: int = 2048

    # 对话
    max_input_length: int = 2000
    system_prompt_path: str = "prompts/default_system.md"
    system_prompt: str = ""

    # 文件上传
    upload_dir: str = "uploads"
    max_upload_size: int = 30 * 1024 * 1024

    # 数据库
    db_path: str = "data/chat.db"

    # RAG 基础设施
    rag_distance_metric: str = "cosine"
    embedding_model: str = "bge-m3"
    chroma_persist_dir: str = "data/chroma_db"

    # 语义记忆
    memory_enabled: bool = True

    # 联网搜索
    search_provider: str = "duckduckgo"
    search_cache_ttl: int = 300
    web_search_precheck: bool = True
    tavily_api_key: str = ""

    # 模型管理
    model_sources: list[ModelSourceConfig] = [
        ModelSourceConfig(name="ollama", label="本地 Ollama", type="ollama", base_url=""),
    ]

    # 服务
    log_level: str = "INFO"
    cors_origins: list[str] = ["*"]
    port: int = 8001
    dev_reload: bool = False

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_ignore_empty": True,
    }


_settings: Settings | None = None


def get_settings() -> Settings:
    """获取全局 Settings 单例。"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

