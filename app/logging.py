"""统一日志配置：结构化、带请求上下文、便于排查。

默认输出到 stdout；生产环境可在此基础上接入 JSON 收集器。
"""
import logging
import sys

from app.config import settings


def setup_logging(level: str | None = None) -> None:
    """初始化全局 logger。

    使用 `%(levelname)s` / `%(name)s` 和可读的 message 格式，
    并保证重复调用不会叠加 handler。
    """
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel((level or settings.log_level).upper())


def get_logger(name: str) -> logging.Logger:
    """获取带模块名的 logger。"""
    setup_logging()
    return logging.getLogger(name)
