# ken-mcp

Shared MCP utilities for Ken's services (fish, host, nfnc, tesla) on the
always-on box. The deployment as a whole is described in the host repo's
`docs/box.md`.

## Sign-in: `gateway_auth`

Every service signs in the same way: Claude registers itself (OAuth dynamic
client registration), so a connector is added in claude.ai by its URL alone,
and the person signing in proves who they are with GitHub. Only the logins in
`MCP_ALLOWED_GITHUB_USERS` get a working token; registrations whose redirect
is not a Claude callback are refused.

```python
from fastmcp import FastMCP
from ken_mcp import add_health_route, gateway_auth

mcp = FastMCP(
    "fish",
    auth=gateway_auth(service="fish", base_url="https://mcp-fish.seehart.com",
                      state_dir="~/.config/fish/oauth-state"),
)
add_health_route(mcp, service="fish", repo="/srv/ws/fish", watch=["/srv/data"])
mcp.run(transport="streamable-http", host="127.0.0.1", port=8753)
```

Environment (a service refuses to start without it):

| Variable | Meaning |
|---|---|
| `MCP_GITHUB_CLIENT_ID`, `MCP_GITHUB_CLIENT_SECRET` | the one GitHub App every service uses |
| `MCP_ALLOWED_GITHUB_USERS` | comma-separated GitHub logins allowed in |

Each service is its own hostname (`https://mcp-<service>.seehart.com`), with
its MCP endpoint at `/mcp` and its OAuth metadata at the root, so the
Cloudflare tunnel routes by hostname and nothing rewrites paths.

The old static client ID + secret scheme (`PersonalAuthProvider`) is removed:
when claude.ai lost those settings there was no way back in (2026-11).

## `add_health_route`

An unauthenticated `GET /health`: service name, git revision, free space on
the watched filesystems; `503` with `ok: false` below 10% free. The hourly
compute audit reads it.

## Tests

```bash
pip install -e . pytest && python -m pytest -q tests
```
