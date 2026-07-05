"""
服务层 — 业务逻辑编排

各模块职责：
- stream_engine: SSE 流式对话引擎
- rag_service: RAG 服务外观（Facade）
- rag_engine: RAG 编排引擎（查询重写、向量检索、HyDE、BM25 重排序）
- session_service: 会话业务编排
- prompt_builder: Prompt 组装
- compress: 会话历史混合压缩
- web_search: 联网搜索
- memory: 语义记忆
- file_chat_service: 文件对话处理
- file_service: 文件上传/存储
- extractors: 文件文本提取（MarkItDown）
- chunker: 文本分块（标题感知分段）
- indexer: 文件索引器（分块 → embedding → 向量存储）
- vector_store: 向量存储 seam（ChromaAdapter）
- reranker: BM25 混合重排序
- summarizer: 增量摘要生成
- model_manager: 模型发现与管理
- model_warmup: 模型预热
- ollama_client: Ollama 客户端单例
- event_bus: 内存事件总线（SSE pub/sub）
- health_service: 多服务健康检查聚合
"""
