# GitHub MCP (shared)

Official [GitHub MCP server](https://github.com/github/github-mcp-server) for Cursor — one install for all projects under `/home/ken`.

## Quick setup

1. Create a [GitHub fine-grained PAT](https://github.com/settings/personal-access-tokens/new) or [classic PAT](https://github.com/settings/tokens) with **repo** access (and **read:org** if you use org repos).

2. Save the token:

```bash
mkdir -p ~/.config/ken
cp /home/ken/shared/mcp/github/env.example ~/.config/ken/github-mcp.env
chmod 600 ~/.config/ken/github-mcp.env
# edit and set GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...
```

3. Run the installer (merges into `/home/ken/.cursor/mcp.json`):

```bash
/home/ken/shared/mcp/github/install.sh
```

4. Restart Cursor. In **Settings → Tools & MCP**, confirm **github** shows a green dot.

5. Test in chat: *"List my GitHub repositories"* or *"Summarize issue 42 in kenseehart/daime"*.

## What you get

Remote server at `https://api.githubcopilot.com/mcp/` (no Docker). Tools include:

- Repos, branches, files, commits
- Issues and pull requests (read + create/update)
- Code search, notifications, Actions workflows

See the [tool list](https://github.com/github/github-mcp-server#toolsets) upstream.

## Config location

| File | Purpose |
|------|---------|
| `~/.config/ken/github-mcp.env` | PAT (never commit) |
| `/home/ken/.cursor/mcp.json` | Workspace MCP config (tesla, nfnc, github, …) |
| `shared/mcp/github/cursor-snippet.json` | Reference snippet only |

Re-run `install.sh` after rotating the token.

## Alternative: local Docker server

If you prefer a local container (requires Docker):

```json
{
  "github": {
    "command": "docker",
    "args": [
      "run", "-i", "--rm",
      "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
      "ghcr.io/github/github-mcp-server"
    ],
    "env": {
      "GITHUB_PERSONAL_ACCESS_TOKEN": "YOUR_GITHUB_PAT"
    }
  }
}
```

Do **not** use the deprecated npm package `@modelcontextprotocol/server-github`.

## gh CLI

Agents can also use the `gh` CLI for PRs when MCP is unavailable:

```bash
sudo apt install gh   # or: snap install gh
gh auth login
```

MCP is preferred in Cursor — it exposes structured tools without shell parsing.

## References

- [Install in Cursor](https://github.com/github/github-mcp-server/blob/main/docs/installation-guides/install-cursor.md)
- [github/github-mcp-server](https://github.com/github/github-mcp-server)
