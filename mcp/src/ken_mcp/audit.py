"""Append-only audit log for MCP tool invocations on gateway deployments."""

from __future__ import annotations

import functools
import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

F = TypeVar("F", bound=Callable[..., object])

DEFAULT_AUDIT_LOG = Path("/var/log/mcp-audit/audit.log")


def audit_log_path() -> Path:
    return Path(os.environ.get("MCP_AUDIT_LOG", str(DEFAULT_AUDIT_LOG)))


def log_tool_call(
    service: str,
    tool: str,
    *,
    client_id: str | None = None,
) -> None:
    """Record a tool invocation (never log secrets or tokens)."""
    path = audit_log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "service": service,
            "tool": tool,
            "client_id": client_id,
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        # Audit must not break tool execution; gateway ops should fix permissions.
        pass


def audited_tool(service: str, tool_name: str | None = None) -> Callable[[F], F]:
    """Decorator: log tool name before invoking handler."""

    def decorator(fn: F) -> F:
        name = tool_name or fn.__name__

        @functools.wraps(fn)
        def wrapper(*args: object, **kwargs: object) -> object:
            log_tool_call(service, name)
            return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
