import logging
import os
import sys
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path


class RequestIdFilter(logging.Filter):
    def __init__(self, request_id: str | None = None) -> None:
        super().__init__()
        self.request_id = request_id or str(uuid.uuid4())

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        if not hasattr(record, "request_id"):
            record.request_id = self.request_id
        return True


def get_logger(
    name: str = "debt_enrichment", request_id: str | None = None
) -> logging.Logger:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler(stream=sys.stdout)
        fmt = "%(asctime)s %(levelname)s %(request_id)s %(name)s - %(message)s"
        handler.setFormatter(logging.Formatter(fmt))
        handler.addFilter(RequestIdFilter(request_id))
        logger.addHandler(handler)
        logger.propagate = False

        # Optional file logging
        log_file = os.getenv("LOG_FILE")
        if not log_file:
            # default to logs/pipeline.log within repo
            log_dir = Path.cwd() / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = str(log_dir / "pipeline.log")
        try:
            file_handler = RotatingFileHandler(
                log_file, maxBytes=2_000_000, backupCount=5
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(logging.Formatter(fmt))
            file_handler.addFilter(RequestIdFilter(request_id))
            logger.addHandler(file_handler)
        except Exception:
            # If file handler fails, continue with stdout only
            pass
    return logger
