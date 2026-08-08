"""Structured logging configuration for the Recruitment Assistant MVP.

Configures logging once for the whole application (called from src/app.py and
src/crew.py):

- Level from the LOG_LEVEL environment variable (default INFO).
- Format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'.
- Handlers: a StreamHandler (stdout) AND a FileHandler to logs/app.log.

The logs/ directory is created at runtime if missing and is gitignored, so no
runtime logs are committed.

Redaction policy (security.md L2): callers must never pass secrets or full
candidate PII / full free-text requirements into log messages. Use
summarize_text() to log a length-bounded, non-sensitive summary of free-text
inputs, and log API-key state as a boolean only, never the key value.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LOG_DIR = _PROJECT_ROOT / "logs"
_LOG_FILE = _LOG_DIR / "app.log"
_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

_APP_LOGGER_NAME = "recruitment_assistant"
_configured = False


def configure_logging() -> logging.Logger:
    """Configure application logging once and return the app logger.

    Idempotent: repeated calls do not add duplicate handlers. If the logs/
    directory cannot be created, file logging is skipped and stdout logging
    remains active so the app never fails to boot over logging alone.
    """
    global _configured
    logger = logging.getLogger(_APP_LOGGER_NAME)
    if _configured:
        return logger

    level_name = (os.getenv("LOG_LEVEL") or "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)

    formatter = logging.Formatter(_LOG_FORMAT)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    handlers: list[logging.Handler] = [stream_handler]

    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    except OSError:
        logger.warning("could not create log dir %s; file logging disabled", _LOG_DIR)

    for handler in handlers:
        logger.addHandler(handler)
    logger.setLevel(level)
    # Do not double-emit through the root logger's default handler.
    logger.propagate = False

    _configured = True
    return logger


def summarize_text(value: Any, max_len: int = 60) -> str:
    """Return a length-bounded, PII-safe summary of an input for logging.

    Never returns the full value. For strings it reports the character length
    and a short truncated preview; for non-strings it reports only the type.
    This keeps secrets, full requirements text, and candidate PII out of logs
    (security.md L2).
    """
    if value is None:
        return "none"
    if not isinstance(value, str):
        return f"type={type(value).__name__}"
    length = len(value)
    preview = value[:max_len].replace("\n", " ")
    suffix = "..." if length > max_len else ""
    return f"len={length} preview='{preview}{suffix}'"
