"""Gateway helpers — fail-closed OAuth and loopback bind defaults."""

from __future__ import annotations

import os

from ken_mcp.personal_auth import PersonalAuthProvider


def require_oauth_secret(secret: str, *, service: str) -> str:
    """Return secret or raise if missing (gateway must never start open)."""
    value = (secret or "").strip()
    if not value:
        raise RuntimeError(
            f"{service}: OAuth client secret is required for streamable-http gateway deploy. "
            f"Set the service MCP_CLIENT_SECRET env var."
        )
    return value


def mcp_bind_host(env_key: str, *, default: str = "127.0.0.1") -> str:
    """Listen address for MCP HTTP servers (loopback by default on gateway)."""
    return os.getenv(env_key, default).strip() or default


def require_mcp_auth(
    *,
    base_url: str,
    client_id: str,
    client_secret: str,
    service: str,
    client_name: str | None = None,
    state_dir: str | None = None,
    allow_dynamic_registration: bool = False,
) -> PersonalAuthProvider:
    """Build PersonalAuthProvider or fail closed if secret missing."""
    secret = require_oauth_secret(client_secret, service=service)
    return PersonalAuthProvider(
        base_url=base_url,
        client_id=client_id,
        client_secret=secret,
        client_name=client_name or f"{service}-mcp-client",
        state_dir=state_dir,
        allow_dynamic_registration=allow_dynamic_registration,
    )


def gateway_mode() -> bool:
    """True when MCP_GATEWAY=1 (production gateway on mcp-services VM)."""
    return os.getenv("MCP_GATEWAY", "").strip() in ("1", "true", "yes")
