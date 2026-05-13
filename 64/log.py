import logging
import sys
from pathlib import Path


def setup_logger(
    name: str,
    log_level: str = "INFO",
    log_file: str = None,
    rotation_config: dict = None
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(log_level.upper())
    logger.handlers.clear()

    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(format_str)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        rotation_config = rotation_config or {}
        enabled = rotation_config.get("enabled", False)

        if enabled:
            from logging.handlers import RotatingFileHandler
            max_bytes = rotation_config.get("max_bytes", 10485760)
            backup_count = rotation_config.get("backup_count", 5)
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8"
            )
            logger.info(f"Log rotation enabled: max_bytes={max_bytes}, backup_count={backup_count}")
        else:
            file_handler = logging.FileHandler(log_path, encoding="utf-8")

        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


logger = setup_logger("download_organizer")
