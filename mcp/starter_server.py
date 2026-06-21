"""Minimal FastMCP server — copy into a project and extend.

Run standalone:
  uv run --with fastmcp python /home/ken/ws/shared/mcp/starter_server.py
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("starter")


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


@mcp.tool()
def starter_ping(message: str = "hello") -> str:
    """Health check — returns echo payload."""
    return _json({"ok": True, "echo": message})


if __name__ == "__main__":
    mcp.run()
