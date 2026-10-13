"""Scoped bearer-token auth. Two demo tokens, least privilege by default.

  demo_read_only   scopes: [read]
  demo_read_write  scopes: [read, write]

In production these come from an env-var-backed token store (TOKENS_JSON)
mapping token -> scopes. The demo tokens are hardcoded and documented as such.
"""
from __future__ import annotations

import json
import os

from .jsonrpc import ERR_FORBIDDEN, ERR_UNAUTHORIZED, JsonRpcError

DEMO_TOKENS = {
    "demo_read_only": ["read"],
    "demo_read_write": ["read", "write"],
}


def load_tokens() -> dict[str, list[str]]:
    raw = os.environ.get("TOKENS_JSON")
    if raw:
        try:
            return {k: list(v) for k, v in json.loads(raw).items()}
        except Exception:
            pass
    return dict(DEMO_TOKENS)


def authenticate(authorization: str | None) -> list[str]:
    """Return scopes for the bearer token, or raise 401."""
    if not authorization or not authorization.startswith("Bearer "):
        raise JsonRpcError(ERR_UNAUTHORIZED, "missing bearer token",
                           {"hint": "Authorization: Bearer <token>"})
    token = authorization[len("Bearer "):].strip()
    scopes = load_tokens().get(token)
    if scopes is None:
        raise JsonRpcError(ERR_UNAUTHORIZED, "unknown token")
    return scopes


def require(scopes: list[str], need: str) -> None:
    if need not in scopes:
        raise JsonRpcError(
            ERR_FORBIDDEN,
            f"insufficient scope: need '{need}', token has {scopes}",
            {"required": need, "granted": scopes},
        )
