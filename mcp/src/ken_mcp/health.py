"""An unauthenticated ``GET /health`` for every gateway service.

The hourly compute audit reads it (urgent when a service is unreachable or a
disk is nearly full): the 2026-09-12 and 2026-11 outages were both a full disk
that every write tripped over while reads still worked. It reveals nothing a
stranger could use: the service name, its git revision, free space and, on the
box, whether the last deploy (box/update.sh, BOX_DEPLOY_STATUS) succeeded.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse

# Below this free fraction on any watched filesystem the service reports
# ``ok: false`` (the audit makes that urgent).
MIN_FREE_FRACTION = 0.10


def _revision(repo: Path) -> str:
    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                       capture_output=True, text=True, timeout=5)
    if r.returncode != 0:
        raise RuntimeError(f"git rev-parse in {repo}: {r.stderr.strip()}")
    return r.stdout.strip()


def health_payload(service: str, repo: Path, paths: list[Path]) -> dict:
    disks = {}
    ok = True
    deploy = None
    # On the box, update.sh records its last run; a failed deploy is not ok.
    status_file = os.getenv("BOX_DEPLOY_STATUS")
    if status_file:
        deploy = json.loads(Path(status_file).read_text())
        ok = ok and bool(deploy.get("ok"))
    for p in paths:
        u = shutil.disk_usage(p)
        free = u.free / u.total
        disks[str(p)] = {"free_fraction": round(free, 4), "free_gb": round(u.free / 1e9, 1)}
        ok = ok and free >= MIN_FREE_FRACTION
    body = {"service": service, "ok": ok, "revision": _revision(repo), "disks": disks}
    if deploy is not None:
        body["deploy"] = deploy
    return body


def add_health_route(mcp, *, service: str, repo: str | os.PathLike,
                     watch: list[str | os.PathLike]) -> None:
    """Register ``GET /health`` on a FastMCP server. ``repo`` is the service's
    git checkout (its revision is reported); ``watch`` lists the paths whose
    filesystems must keep free space (state dir, data dir)."""
    repo_p = Path(repo).expanduser()
    paths = [Path(p).expanduser() for p in watch]

    @mcp.custom_route("/health", methods=["GET"])
    async def health(request: Request) -> JSONResponse:  # noqa: ARG001 - Starlette signature
        body = health_payload(service, repo_p, paths)
        return JSONResponse(body, status_code=200 if body["ok"] else 503)
