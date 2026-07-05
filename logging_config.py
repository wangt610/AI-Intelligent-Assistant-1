"""
结构化日志配置模块

提供统一的日志系统：
- 控制台彩色输出（开发环境）
- 全链路追踪 (request_id) 注入
- 所有模块通过 logging.getLogger(__name__) 接入
"""

import contextvars
import logging
import sys


_trace_id: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")


TRACE_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)-30s | %(trace_id)s%(message)s"
)
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"


class TraceFilter(logging.Filter):
    """从 contextvars 读取 trace_id 并注入到每条日志记录。"""

    def filter(self, record: logging.LogRecord) -> bool:
        tid = _trace_id.get()
        record.trace_id = f"[{tid}] " if tid else ""
        return True


def setup_logging(level: str = "INFO") -> None:
    """初始化全局日志配置，应在应用启动时调用一次。"""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    for handler in root.handlers[:]:
        root.removeHandler(handler)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter(TRACE_FORMAT, datefmt=LOG_DATEFMT))
    console.addFilter(TraceFilter())
    root.addHandler(console)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("ollama").setLevel(logging.WARNING)
