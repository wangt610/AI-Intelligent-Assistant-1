"""
模型对话提供商

定义 ModelProvider 接口与 Ollama/OpenAI 适配器。
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import AsyncGenerator

from config import get_settings
from runtime_config import get_config
from utils.http_client import HttpClientPool
from services.ollama_client import get_ollama_async_client
from services.providers import OllamaError, OllamaConnectionError, OllamaModelError, OllamaTimeoutError

logger = logging.getLogger(__name__)


class ModelProvider(ABC):
    """模型提供商接口 — 从模型来源流式生成 token。"""

    @abstractmethod
    async def stream(
        self,
        messages: list[dict],
        show_thinking: bool = True,
    ) -> AsyncGenerator[dict, None]:
        ...

    async def complete(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 100,
        temperature: float = 0,
    ) -> str:
        parts: list[str] = []
        async for chunk in self.stream(messages, show_thinking=False):
            if chunk["type"] == "content":
                parts.append(chunk["text"])
        return "".join(parts)


class OllamaProvider(ModelProvider):
    """通过 Ollama 原生 API 进行流式对话。"""

    def __init__(self, model: str | None = None):
        settings = get_settings()
        self._model = model or settings.ollama_model
        self._client = get_ollama_async_client()

    async def stream(
        self,
        messages: list[dict],
        show_thinking: bool = True,
    ) -> AsyncGenerator[dict, None]:
        """流式生成对话回复。

        Yields:
            {"type": "thinking", "text": str} — 思考过程片段（仅当 show_thinking=True 且模型支持时）。
            {"type": "content", "text": str}  — 回复内容片段。
        """
        settings = get_settings()
        options = {
            "num_predict": get_config("max_output_tokens"),
            "num_ctx": settings.ollama_num_ctx,
            "num_batch": settings.ollama_num_batch,
            "temperature": get_config("temperature"),
            "top_p": get_config("top_p"),
        }
        try:
            stream = await self._client.chat(
                model=self._model,
                messages=messages,
                stream=True,
                think=show_thinking,
                keep_alive=settings.ollama_keep_alive,
                options=options,
            )
        except Exception as e:
            if "think" in str(e).lower() or "unexpected" in str(e).lower():
                logger.warning("模型不支持 think 参数，回退到无思考模式")
                stream = await self._client.chat(
                    model=self._model,
                    messages=messages,
                    stream=True,
                    keep_alive=settings.ollama_keep_alive,
                    options=options,
                )
            else:
                msg = str(e)
                if "ConnectionRefused" in msg or "Connection refused" in msg:
                    raise OllamaConnectionError("AI 服务未运行，请先启动 Ollama")
                elif "timeout" in msg.lower() or "timed out" in msg.lower():
                    raise OllamaTimeoutError("AI 服务响应超时")
                elif "not found" in msg.lower() or "model" in msg.lower():
                    raise OllamaModelError(
                        f"模型 {self._model} 不存在，请先拉取模型：ollama pull {self._model}"
                    )
                else:
                    raise OllamaError(f"AI 服务调用失败：{e}")

        async for chunk in stream:
            message = chunk.message
            thinking = getattr(message, "thinking", "") or ""
            content = getattr(message, "content", "") or ""
            if thinking and show_thinking:
                yield {"type": "thinking", "text": thinking}
            if content:
                yield {"type": "content", "text": content}

    async def complete(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 100,
        temperature: float = 0,
    ) -> str:
        settings = get_settings()
        options = {
            "num_predict": max_tokens,
            "temperature": temperature,
            "num_ctx": settings.ollama_num_ctx,
            "num_batch": settings.ollama_num_batch,
        }
        response = await self._client.chat(
            model=self._model,
            messages=messages,
            stream=False,
            options=options,
            keep_alive=settings.ollama_keep_alive,
        )
        return (response.message.content or "").strip()


class OpenAIProvider(ModelProvider):
    """通过 OpenAI 兼容 API 进行流式对话。"""

    def __init__(self, source: dict, model_id: str | None = None):
        self._source = source
        self._model_id = model_id

    async def stream(
        self,
        messages: list[dict],
        show_thinking: bool = True,
    ) -> AsyncGenerator[dict, None]:
        """流式生成对话回复（OpenAI 兼容 API）。

        Yields:
            {"type": "thinking", "text": str} — 推理过程片段（reasoning_content）。
            {"type": "content", "text": str}  — 回复内容片段。
        """
        settings = get_settings()
        headers = {"Content-Type": "application/json"}
        if self._source.get("api_key"):
            headers["Authorization"] = f"Bearer {self._source['api_key']}"

        body = {
            "model": self._model_id,
            "messages": messages,
            "stream": True,
            "max_tokens": get_config("max_output_tokens"),
        }

        client = HttpClientPool.get("default", timeout=get_settings().ollama_timeout)
        async with client.stream(
            "POST",
            f"{self._source['base_url']}/chat/completions",
            headers=headers,
            json=body,
        ) as resp:
            if resp.status_code != 200:
                error_body = await resp.aread()
                raise RuntimeError(
                    f"API 返回 {resp.status_code}: {error_body.decode()[:200]}"
                )

            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue

                choices = chunk.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})

                reasoning = delta.get("reasoning_content", "") or ""
                if reasoning and show_thinking:
                    yield {"type": "thinking", "text": reasoning}

                content = delta.get("content", "") or ""
                if content:
                    yield {"type": "content", "text": content}

    async def complete(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 100,
        temperature: float = 0,
    ) -> str:
        headers = {"Content-Type": "application/json"}
        if self._source.get("api_key"):
            headers["Authorization"] = f"Bearer {self._source['api_key']}"

        body = {
            "model": self._model_id,
            "messages": messages,
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        client = HttpClientPool.get("default", timeout=get_settings().ollama_timeout)
        resp = await client.post(
            f"{self._source['base_url']}/chat/completions",
            headers=headers,
            json=body,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"API 返回 {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return ""
        return (choices[0].get("message", {}).get("content", "") or "").strip()
