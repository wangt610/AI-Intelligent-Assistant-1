"""
模型预热管理器

管理本地模型的预热和保持活跃，消除冷启动延迟。
适用于资源受限的本地小模型场景：
- 一次只预热一个模型，避免竞争 GPU 显存
- 预热 payload 极轻量（单 token）
- 自适应心跳：仅在模型即将过期时发送
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field

from config import get_settings

logger = logging.getLogger(__name__)


@dataclass(order=True)
class _WarmupJob:
    priority: int
    model_source: str = field(compare=False)
    model_id: str = field(compare=False)


@dataclass
class _WarmupState:
    last_used_at: float = 0.0
    warming: bool = False
    warmed: bool = False


class ModelWarmupManager:
    def __init__(self):
        self._queue: asyncio.PriorityQueue[_WarmupJob] = asyncio.PriorityQueue()
        self._states: dict[str, _WarmupState] = {}
        self._warmup_task: asyncio.Task | None = None
        self._heartbeat_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()

    async def start(self):
        settings = get_settings()

        # 默认对话模型（最高优先级）
        self._queue.put_nowait(_WarmupJob(
            priority=0, model_source="ollama", model_id=settings.ollama_model
        ))
        # Embedding 模型
        self._queue.put_nowait(_WarmupJob(
            priority=1, model_source="ollama", model_id=settings.embedding_model
        ))

        self._warmup_task = asyncio.create_task(self._warmup_loop())
        if settings.ollama_keep_alive:
            self._heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(settings.ollama_keep_alive)
            )

        logger.info("ModelWarmupManager 已启动")

    async def shutdown(self):
        self._shutdown_event.set()
        if self._warmup_task:
            self._warmup_task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()

    async def _do_warmup(self, model_source: str, model_id: str) -> None:
        """执行模型预热，根据类型选择方式。

        Raises:
            Exception: 预热失败的任意异常。
        """
        from services.model_manager import is_llm_model

        if is_llm_model(model_id):
            from services.providers import get_provider
            provider = get_provider(model_source, model_id)
            async for _ in provider.stream(
                [{"role": "user", "content": "."}],
                show_thinking=False,
            ):
                break
        else:
            from services.providers import OllamaEmbeddingProvider
            embedder = OllamaEmbeddingProvider()
            await embedder.embed(".")

    async def warm(self, model_source: str, model_id: str) -> bool:
        """立即预热指定模型，最多等待 60s。返回是否成功。"""
        key = f"{model_source}/{model_id}"
        state = self._states.get(key)
        if state and state.warmed:
            return True

        self._states[key] = _WarmupState(
            last_used_at=time.monotonic(), warming=True, warmed=False
        )

        try:
            await self._do_warmup(model_source, model_id)
            self._states[key] = _WarmupState(
                last_used_at=time.monotonic(), warmed=True, warming=False
            )
            logger.info("模型预热完成: %s/%s", model_source, model_id)
            return True
        except Exception as e:
            logger.warning("模型预热失败 %s/%s: %s", model_source, model_id, e)
            self._states.pop(key, None)
            return False

    def observe_use(self, model_source: str, model_id: str):
        """记录模型被使用的时间戳，避免心跳打扰活跃模型。"""
        key = f"{model_source}/{model_id}"
        if key in self._states:
            self._states[key].last_used_at = time.monotonic()

    async def _warmup_loop(self):
        """按优先级依次预热模型，一次只预热一个。"""
        while not self._shutdown_event.is_set():
            try:
                job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            await self.warm(job.model_source, job.model_id)

    async def _heartbeat_loop(self, keep_alive: str):
        seconds = _parse_keep_alive(keep_alive)
        if seconds <= 0:
            return
        interval = seconds / 2

        while not self._shutdown_event.is_set():
            await asyncio.sleep(interval)
            now = time.monotonic()
            for key, state in list(self._states.items()):
                if not state.warmed:
                    continue
                if now - state.last_used_at < seconds * 0.75:
                    continue
                model_source, model_id = key.split("/", 1)
                try:
                    await self._do_warmup(model_source, model_id)
                    state.last_used_at = now
                    logger.debug("心跳维持: %s", key)
                except Exception as e:
                    logger.debug("心跳失败 %s: %s", key, e)


def _parse_keep_alive(value: str | int) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if value.endswith("m"):
        return float(value[:-1]) * 60
    if value.endswith("h"):
        return float(value[:-1]) * 3600
    if value.endswith("s"):
        return float(value[:-1])
    if value == "-1" or value == "-1m":
        return 86400
    try:
        return float(value)
    except ValueError:
        return 1800


_warmup_manager: ModelWarmupManager | None = None


def get_warmup_manager() -> ModelWarmupManager:
    global _warmup_manager
    if _warmup_manager is None:
        _warmup_manager = ModelWarmupManager()
    return _warmup_manager
