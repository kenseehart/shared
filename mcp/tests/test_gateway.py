"""ken_mcp gateway sign-in and health, against a real FastMCP app (no network)."""

from __future__ import annotations

import asyncio
import subprocess
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastmcp import FastMCP
from starlette.testclient import TestClient

from ken_mcp import AllowlistGitHubVerifier, add_health_route, gateway_auth

BASE = "https://mcp-fish.seehart.com"
REAL_ASYNC_CLIENT = httpx.AsyncClient
CLAUDE_CB = "https://claude.ai/api/mcp/auth_callback"


@pytest.fixture()
def env(monkeypatch):
    monkeypatch.setenv("MCP_GITHUB_CLIENT_ID", "Iv23test")
    monkeypatch.setenv("MCP_GITHUB_CLIENT_SECRET", "s" * 40)
    monkeypatch.setenv("MCP_ALLOWED_GITHUB_USERS", "KenSeehart")


@pytest.fixture()
def app(env, tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path / "repo")], check=True)
    subprocess.run(["git", "-C", str(tmp_path / "repo"), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-q", "--allow-empty", "-m", "x"], check=True)
    mcp = FastMCP("fish", auth=gateway_auth(service="fish", base_url=BASE, state_dir=tmp_path / "state"))

    @mcp.tool()
    def ping() -> str:
        return "pong"

    add_health_route(mcp, service="fish", repo=tmp_path / "repo", watch=[tmp_path])
    return mcp.http_app(path="/mcp")


def test_refuses_to_start_without_settings(monkeypatch, tmp_path):
    monkeypatch.delenv("MCP_GITHUB_CLIENT_ID", raising=False)
    with pytest.raises(RuntimeError, match="MCP_GITHUB_CLIENT_ID"):
        gateway_auth(service="fish", base_url=BASE, state_dir=tmp_path)


def test_claude_can_discover_register_and_is_sent_to_github(app):
    with TestClient(app, base_url=BASE) as c:
        r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "ping"})
        assert r.status_code == 401
        assert "resource_metadata" in r.headers["www-authenticate"]
        prm = c.get("/.well-known/oauth-protected-resource/mcp").json()
        assert prm["authorization_servers"][0].rstrip("/") == BASE
        meta = c.get("/.well-known/oauth-authorization-server").json()
        assert meta["registration_endpoint"] == f"{BASE}/register"
        reg = c.post("/register", json={"redirect_uris": [CLAUDE_CB], "client_name": "claude",
                                         "token_endpoint_auth_method": "none",
                                         "grant_types": ["authorization_code", "refresh_token"],
                                         "response_types": ["code"]})
        assert reg.status_code == 201, reg.text
        client_id = reg.json()["client_id"]
        # A stranger's redirect cannot even register, so no code can reach it.
        bad = c.post("/register", json={"redirect_uris": ["https://evil.example/cb"],
                                        "token_endpoint_auth_method": "none"})
        assert bad.status_code == 400 and bad.json()["error"] == "invalid_redirect_uri", bad.text
        a = c.get("/authorize", params={
            "response_type": "code", "client_id": client_id, "redirect_uri": CLAUDE_CB,
            "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
            "code_challenge_method": "S256", "state": "st", "resource": f"{BASE}/mcp"},
            follow_redirects=False)
        assert a.status_code in (302, 303, 307), a.text[:300]
        loc = a.headers["location"]
        # Consent screen first (require_authorization_consent), then GitHub.
        assert "/consent" in loc or loc.startswith("https://github.com/login/oauth/authorize"), loc


def test_health_is_open_and_reports_revision(app):
    with TestClient(app, base_url=BASE) as c:
        h = c.get("/health")
        assert h.status_code == 200, h.text
        body = h.json()
        assert body["service"] == "fish" and body["ok"] is True and len(body["revision"]) >= 7


def _verifier_with(user: dict | None, status: int = 200):
    v = AllowlistGitHubVerifier(frozenset({"kenseehart"}))
    real = REAL_ASYNC_CLIENT

    def fake(*a, **k):
        k["transport"] = httpx.MockTransport(lambda req: httpx.Response(status, json=user or {}))
        return real(*a, **k)
    return v, fake


def test_allowlist(monkeypatch):
    for user, ok in (({"id": 1, "login": "KenSeehart"}, True), ({"id": 2, "login": "mallory"}, False)):
        v, fake = _verifier_with(user)
        monkeypatch.setattr(httpx, "AsyncClient", fake)
        got = asyncio.run(v.verify_token("tok"))
        assert (got is not None) is ok
        if ok:
            assert got.claims["login"] == "kenseehart"
    v, fake = _verifier_with(None, status=401)
    monkeypatch.setattr(httpx, "AsyncClient", fake)
    assert asyncio.run(v.verify_token("revoked")) is None


def test_a_failed_deploy_makes_health_not_ok(app, tmp_path, monkeypatch):
    status = tmp_path / "deploy-status"
    status.write_text('{"ok": false, "error": "fish: git fetch failed"}')
    monkeypatch.setenv("BOX_DEPLOY_STATUS", str(status))
    with TestClient(app, base_url=BASE) as c:
        h = c.get("/health")
        assert h.status_code == 503 and h.json()["deploy"]["error"] == "fish: git fetch failed"
