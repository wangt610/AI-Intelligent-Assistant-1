# AI 智能助手 — 领域语言

## 核心概念

### 会话 (Session)
一个独立的对话线程，包含标题、创建时间和更新时间。支持历史摘要缓存（summary）和压缩水位线（compressed_up_to_id）。删除时同步清理 RAG 索引与语义记忆。

### 消息 (Message)
会话中的单次交互记录。角色包括：用户（user）、助手（assistant）、系统（system）。消息按时间升序排列，构成会话的完整上下文。支持状态标记：completed / interrupted / failed。

### 模型来源 (Model Source)
语言模型的供应来源配置，包含来源名称、基础 URL、API 密钥。分为两类：
- **Ollama 原生来源** — 直接连接本地 Ollama 守护进程
- **OpenAI 兼容来源** — 通过 OpenAI 兼容 API 格式调用（vLLM / TGI / DeepSeek 等）

### 模型提供商 (Model Provider)
从模型来源流式生成 token 的具体实现。每个来源类型对应一个提供商适配器。

### 文件索引 (File Index)
上传文件 → 提取文本 → 分块 → 生成 Embedding → 存入向量存储的完整过程。

### 索引任务 (Index Task)
文件索引的工作单元，有生命周期状态机：pending → indexing → completed / failed。持久化在 index_tasks 表中，支持崩溃恢复。

### 向量存储 (Vector Store)
嵌入向量的持久化存储与相似度检索引擎。当前实现使用 ChromaDB 作为适配器。

### RAG 引擎 (RAG Engine)
接收查询 → 查询重写 → 向量检索 → HyDE 二次检索(可选) → BM25 重排序 → 返回结构化的上下文块（含文本、来源文件、相关度分数）。

### 语义记忆 (Semantic Memory)
将对话消息 embedding 存入 ChromaDB，检索与当前 query 语义相关的历史回合，增强多轮对话的上下文感知能力。通过 `memory_enabled` 配置开关。

### 会话历史压缩 (History Compression)
混合压缩策略：裁剪旧轮次（trim）+ 对富内容轮次调用 LLM 增量摘要。通过 `compressed_up_to_id` 水位线标记已压缩位置。

## 分层架构

```
路由层 (routers/) → 编排层 (services/) → 存储层 (database / vector store)
                        ↓
                   模型提供商 (Ollama / OpenAI)
```

## 关键 seam

| Seam | 适配器 | 用途 |
|------|--------|------|
| `VectorStore` | `ChromaAdapter` | 向量存储的持久化与检索 |
| `ModelProvider` | `OllamaProvider`, `OpenAIProvider` | 流式 token 生成 |
| `EmbeddingProvider` | `OllamaEmbeddingProvider` | 文本向量化 |
| `SearchProvider` | `DuckDuckGoProvider`, `TavilyProvider` | 联网搜索 |
| `TextExtractor` | `MarkItDown`（统一引擎） | 文件文本提取，输出结构化 Markdown |
| Task CRUD | `database/tasks.py`（函数式） | 索引任务的持久化跟踪 |
| Session CRUD | `database/sessions.py`（函数式） | 会话与消息的持久化 |
