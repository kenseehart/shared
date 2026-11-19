"""Gateway helpers: loopback bind default and gateway mode."""

from __future__ import annotations

import os


def mcp_bind_host(env_key: str, *, default: str = "127.0.0.1") -> str:
    """Listen address for MCP HTTP servers (loopback: only the tunnel reaches them)."""
    return os.getenv(env_key, default).strip() or default


def gateway_mode() -> bool:
    """True when MCP_GATEWAY=1 (the always-on box)."""
    return os.getenv("MCP_GATEWAY", "").strip() in ("1", "true", "yes")
