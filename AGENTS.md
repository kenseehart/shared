# Agent onboarding — shared resources

Read this when adding **cross-project UI**, **MCP boilerplate**, or **new project scaffolding**.

## What this repo is

Single home for assets reused across Ken's projects under `/home/ken`:

- **Web**: zero-build static components (no npm required for consumers)
- **Templates**: `AGENTS.md` and Cursor rule starters
- **MCP**: FastMCP starter for new tool servers; shared GitHub MCP install

Path: **`/home/ken/shared`**

## Chat widget (`web/chat/`)

Claude-inspired chat UI extracted and modernized from the legacy agi.green Vue frontend.

| File | Role |
|------|------|
| `agi-chat.css` | Warm light theme, user/assistant bubbles, sticky input |
| `agi-chat.js` | `AgiChat` class — append messages, typing indicator, markdown via marked.js CDN |
| `demo.html` | Standalone preview with mock responses |

**Integrate** by linking CSS/JS from your site's static dir, or copy the two files into a project. Wire `onSend` to your backend (FastAPI, aiohttp, MCP bridge, etc.).

Do **not** pull in Vue, RabbitMQ, or Docker from agi.green for new sites.

## Templates (`templates/`)

| File | Use |
|------|-----|
| `AGENTS.project.md` | Starter agent doc — copy to `<project>/AGENTS.md` |
| `project.mdc` | Cursor rule — copy to `<project>/.cursor/rules/<name>.mdc` |

## MCP (`mcp/`)

| Path | Role |
|------|------|
| `starter_server.py` | FastMCP boilerplate for **project-specific** tool servers |
| `github/` | Shared **GitHub MCP** install for all projects (issues, PRs, repos) |

### GitHub MCP (shared)

One server for the whole workspace — configured in `/home/ken/.cursor/mcp.json`:

```bash
cp shared/mcp/github/env.example ~/.config/ken/github-mcp.env
# set GITHUB_PERSONAL_ACCESS_TOKEN, then:
shared/mcp/github/install.sh
```

See `mcp/github/README.md` for PAT scopes and troubleshooting.

### FastMCP starter

Minimal server for new project tools. Pattern matches `nfnc` and `tesla`:

```bash
cd /home/ken/<project> && uv run python /home/ken/shared/mcp/starter_server.py
```

Register in `/home/ken/.cursor/mcp.json` when the project grows its own server module.

## agi.green verdict

**Keep the repo as reference; do not build new work on the full stack.**

| Keep | Discard for new work |
|------|----------------------|
| Chat UX patterns (message layout, input bar) | RabbitMQ requirement |
| Python-first / backend-driven app idea | Vue + Vite build chain |
| Markdown-in-chat concept | Docker-first deployment |
| Protocol handler architecture (as reference) | Vueform dependency |

**Migration path**: use `shared/web/chat/` for UI; FastMCP + uv for tools; static HTML or a thin Python HTTP handler for backends. Revisit agi.green's `Dispatcher` pattern only if you need multi-protocol event-driven apps (email + chat + timers).

## Deploy notes

Static assets deploy to [my.hosting.com](https://my.hosting.com/) docroots. No build step for `web/chat/`.
