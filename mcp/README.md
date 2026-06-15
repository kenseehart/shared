# ken-mcp

Shared MCP utilities for Ken's workspace.

## PersonalAuthProvider

OAuth 2.1 provider for FastMCP with static client ID + secret — works with Claude.ai custom connectors.

```python
from ken_mcp import PersonalAuthProvider
from fastmcp import FastMCP

auth = PersonalAuthProvider(
    base_url="https://seehart.com/host",
    client_id="host-mcp",
    client_secret="...",
    client_name="host-mcp-client",
    state_dir="~/.config/ken/host/oauth-state",
)
mcp = FastMCP("my-server", auth=auth)
```

Used by: `host`, `tesla`, `fish` (via backward-compatible shims).
