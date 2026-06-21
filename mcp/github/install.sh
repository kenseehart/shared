#!/usr/bin/env bash
# Merge GitHub MCP config into /home/ken/ws/.cursor/mcp.json using ~/.config/ken/github-mcp.env
set -euo pipefail

ENV_FILE="${GITHUB_MCP_ENV:-$HOME/.config/ken/github-mcp.env}"
MCP_JSON="/home/ken/ws/.cursor/mcp.json"
SNIPPET="/home/ken/ws/shared/mcp/github/cursor-snippet.json"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE"
  echo "Run: cp /home/ken/ws/shared/mcp/github/env.example $ENV_FILE"
  echo "Then set GITHUB_PERSONAL_ACCESS_TOKEN and re-run this script."
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

if [[ -z "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]]; then
  echo "GITHUB_PERSONAL_ACCESS_TOKEN is empty in $ENV_FILE"
  exit 1
fi

python3 - "$MCP_JSON" "$SNIPPET" "$GITHUB_PERSONAL_ACCESS_TOKEN" <<'PY'
import json
import sys
from pathlib import Path

mcp_path, snippet_path, token = sys.argv[1:4]
mcp_file = Path(mcp_path)
snippet = json.loads(Path(snippet_path).read_text())

if mcp_file.exists():
    config = json.loads(mcp_file.read_text())
else:
    config = {"mcpServers": {}}

servers = config.setdefault("mcpServers", {})
github = dict(snippet["github"])
github["headers"] = {"Authorization": f"Bearer {token}"}
servers["github"] = github

mcp_file.parent.mkdir(parents=True, exist_ok=True)
mcp_file.write_text(json.dumps(config, indent=2) + "\n")
print(f"Updated {mcp_file} — github MCP server configured.")
PY

echo "Restart Cursor to load the GitHub MCP server."
