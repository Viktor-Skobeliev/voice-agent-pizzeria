"""Lightweight structured logging.

One module logger for the whole package plus a helper for logging tool calls
as key=value pairs (cheap, greppable, and PII-aware via ``mask``).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("voice_agent_pizzeria")


def setup_logging(level: str = "INFO") -> None:
    """Configure root logging once. Safe to call multiple times."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def mask(value: str | None, *, keep: int = 2) -> str:
    """Mask PII (phone, address) for logs, keeping the last ``keep`` chars."""
    if not value:
        return "<empty>"
    if len(value) <= keep:
        return "*" * len(value)
    return "*" * (len(value) - keep) + value[-keep:]


def log_tool_call(tool: str, *, ok: bool, **fields: Any) -> None:
    """Emit a single structured line for a tool invocation."""
    parts = " ".join(f"{k}={v}" for k, v in fields.items())
    status = "ok" if ok else "fail"
    logger.info("tool=%s status=%s %s", tool, status, parts)
