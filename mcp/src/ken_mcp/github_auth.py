"""Gateway sign-in: GitHub identity, OAuth self-registration for Claude (Ken, 2026-11-19).

Every Ken MCP service signs in the same way:

- Claude (chat, projects, mobile, desktop, Claude Code) registers itself
  (RFC 7591 dynamic client registration), so a connector is added by its URL
  alone: there is no client ID or secret to type in or to lose. The old
  static-client scheme (PersonalAuthProvider) failed exactly that way.
- The person signing in proves who they are with GitHub. Only the logins in
  MCP_ALLOWED_GITHUB_USERS get a working token; everyone else is refused on
  every request (``AllowlistGitHubVerifier``).
- Registrations and tokens live in an encrypted key-value store on disk
  (FastMCP's DiskStore, SQLite underneath), so a crash or a full disk cannot
  leave a truncated token file behind.

One GitHub App (not an OAuth App: an OAuth App allows a single callback
host) serves every service. It lists each service's callback,
``https://mcp-<service>.seehart.com/auth/callback``, needs no repository or
account permissions (sign-in only reads the user's identity), and is set up
as in the host repo's ``docs/box.md``.

Environment (fail closed: a service refuses to start without them):
  MCP_GITHUB_CLIENT_ID / MCP_GITHUB_CLIENT_SECRET   the GitHub OAuth app
  MCP_ALLOWED_GITHUB_USERS                          comma-separated logins
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import time
from pathlib import Path

import httpx
from cryptography.fernet import Fernet
from fastmcp.server.auth import OAuthProxy, TokenVerifier
from fastmcp.server.auth.auth import AccessToken
from fastmcp.server.auth.jwt_issuer import derive_jwt_key
from fastmcp.server.auth.redirect_validation import validate_redirect_uri
from mcp.server.auth.provider import RegistrationError
from mcp.shared.auth import OAuthClientInformationFull
from key_value.aio.stores.disk import DiskStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper

GITHUB_AUTHORIZE = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN = "https://github.com/login/oauth/access_token"
GITHUB_USER = "https://api.github.com/user"
SCOPES = ["read:user"]
# Claude's OAuth callbacks (claude.ai and claude.com), plus the MCP Inspector
# on localhost for local testing.
CLAUDE_REDIRECTS = [
    "https://claude.ai/api/mcp/auth_callback",
    "https://claude.com/api/mcp/auth_callback",
    "http://localhost:*",
    "http://127.0.0.1:*",
]
VERIFY_CACHE_SECONDS = 300


def _require_env(name: str, service: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{service}: {name} is not set; the gateway never starts without sign-in")
    return value


def allowed_logins(service: str) -> frozenset[str]:
    raw = _require_env("MCP_ALLOWED_GITHUB_USERS", service)
    logins = frozenset(x.strip().lower() for x in raw.split(",") if x.strip())
    if not logins:
        raise RuntimeError(f"{service}: MCP_ALLOWED_GITHUB_USERS names no GitHub login")
    return logins


class AllowlistGitHubVerifier(TokenVerifier):
    """Accept a GitHub token only when its owner's login is allowed.

    Runs on every request (the OAuth proxy verifies the upstream GitHub token
    behind each FastMCP token), so revoking the GitHub app or removing a login
    from the allowlist takes effect within ``VERIFY_CACHE_SECONDS``. A GitHub
    API failure refuses the request: no cached answer is extended past its time.
    """

    def __init__(self, logins: frozenset[str], *, timeout_seconds: float = 10.0,
                 cache_seconds: float = VERIFY_CACHE_SECONDS):
        super().__init__(required_scopes=None)
        self.logins = logins
        self.timeout_seconds = timeout_seconds
        self.cache_seconds = cache_seconds
        self._cache: dict[str, tuple[float, AccessToken]] = {}
        self._lock = asyncio.Lock()

    async def verify_token(self, token: str) -> AccessToken | None:
        key = hashlib.sha256(token.encode()).hexdigest()
        now = time.monotonic()
        hit = self._cache.get(key)
        if hit and now - hit[0] < self.cache_seconds:
            return hit[1]
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            r = await client.get(GITHUB_USER, headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "ken-mcp-gateway",
            })
        if r.status_code != 200:
            self._cache.pop(key, None)
            return None
        user = r.json()
        login = str(user.get("login") or "").lower()
        if login not in self.logins:
            self._cache.pop(key, None)
            return None
        access = AccessToken(
            token=token,
            client_id=str(user["id"]),
            scopes=SCOPES,
            expires_at=None,
            claims={"sub": str(user["id"]), "login": login, "name": user.get("name")},
        )
        async with self._lock:
            self._cache[key] = (now, access)
        return access


class ClaudeOnlyOAuthProxy(OAuthProxy):
    """FastMCP's proxy treats ``allowed_client_redirect_uris`` as an extra
    allowance: a client that REGISTERS a redirect may still use it. Here a
    registration naming any redirect outside CLAUDE_REDIRECTS is refused, so
    no code can ever be sent to a stranger's site, consent screen or not."""

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        uris = [str(u) for u in (client_info.redirect_uris or [])]
        if not uris:
            raise RegistrationError(error="invalid_redirect_uri",
                                    error_description="a redirect_uri is required")
        for uri in uris:
            if not validate_redirect_uri(uri, CLAUDE_REDIRECTS):
                raise RegistrationError(error="invalid_redirect_uri",
                                        error_description=f"redirect {uri} is not a Claude callback")
        await super().register_client(client_info)


def gateway_auth(*, service: str, base_url: str, state_dir: str | os.PathLike) -> ClaudeOnlyOAuthProxy:
    """The one sign-in every Ken MCP service uses (see module docstring).

    ``base_url`` is the service's public origin (``https://mcp-fish.seehart.com``);
    its MCP endpoint is ``/mcp`` and its OAuth metadata is served at the origin's
    root, so no proxy needs to rewrite paths. ``state_dir`` holds the encrypted
    registration and token store and must survive restarts.
    """
    client_id = _require_env("MCP_GITHUB_CLIENT_ID", service)
    client_secret = _require_env("MCP_GITHUB_CLIENT_SECRET", service)
    logins = allowed_logins(service)
    # One signing key per service, derived from the app secret: no extra secret
    # to manage, and a token minted for one service is not valid on another.
    jwt_key = derive_jwt_key(high_entropy_material=f"{client_secret}:{service}",
                             salt="ken-mcp-gateway-jwt")
    storage_key = derive_jwt_key(high_entropy_material=jwt_key.decode(),
                                 salt="ken-mcp-gateway-storage")
    state = Path(state_dir).expanduser()
    state.mkdir(parents=True, exist_ok=True)
    storage = FernetEncryptionWrapper(
        key_value=DiskStore(directory=state / "oauth-proxy"),
        fernet=Fernet(key=storage_key),
    )
    return ClaudeOnlyOAuthProxy(
        upstream_authorization_endpoint=GITHUB_AUTHORIZE,
        upstream_token_endpoint=GITHUB_TOKEN,
        upstream_client_id=client_id,
        upstream_client_secret=client_secret,
        token_verifier=AllowlistGitHubVerifier(logins),
        base_url=base_url,
        redirect_path="/auth/callback",
        issuer_url=base_url,
        allowed_client_redirect_uris=CLAUDE_REDIRECTS,
        valid_scopes=SCOPES,
        extra_authorize_params={"scope": " ".join(SCOPES)},
        client_storage=storage,
        jwt_signing_key=jwt_key,
        require_authorization_consent=True,
    )
