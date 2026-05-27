"""日志工具."""
from __future__ import annotations

import logging
import sys

from configdrift.config import settings

_FMT = "%(asctime)s %(levelname)-7s %(name)s - %(message)s"


def get_logger(name: str = "configdrift") -> logging.Logger:
    """返回一个配置好的 logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_FMT))
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    return logger
