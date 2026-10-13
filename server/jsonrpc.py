"""Hand-rolled JSON-RPC 2.0 dispatcher. No MCP SDK, no framework magic.

Implements the MCP-over-HTTP method surface:
  initialize   -> handshake: protocol version, server info, capabilities
  tools/list   -> tool schemas the agent may call
  tools/call   -> invoke one tool with arguments
  ping         -> liveness

Errors follow JSON-RPC 2.0 codes (-32700 parse, -32600 invalid request,
-32601 method not found, -32602 invalid params, -32603 internal), plus
-32001 for auth failures (server-defined range).
"""
from __future__ import annotations

import json
from typing import Any, Callable


class JsonRpcError(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


# Server-defined: authentication / authorization failures.
ERR_UNAUTHORIZED = -32001
ERR_FORBIDDEN = -32003


class Dispatcher:
    def __init__(self):
        self._methods: dict[str, Callable[[dict, dict], Any]] = {}
        # ctx carries per-request state: {"scopes": [...], "mask_pii": bool}

    def method(self, name: str):
        def deco(fn: Callable[[dict, dict], Any]):
            self._methods[name] = fn
            return fn
        return deco

    def dispatch(self, raw: str, ctx: dict) -> str:
        """Take a raw JSON-RPC payload, return a raw JSON-RPC response string."""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError as e:
            return self._error(None, -32700, "parse error", str(e))
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or "method" not in msg:
            return self._error(msg.get("id") if isinstance(msg, dict) else None,
                               -32600, "invalid request")
        mid = msg.get("id")
        fn = self._methods.get(msg["method"])
        if fn is None:
            return self._error(mid, -32601, f"method not found: {msg['method']}")
        try:
            result = fn(msg.get("params") or {}, ctx)
            return json.dumps({"jsonrpc": "2.0", "id": mid, "result": result})
        except JsonRpcError as e:
            return self._error(mid, e.code, e.message, e.data)
        except Exception as e:  # noqa: BLE001 - protocol must never leak tracebacks
            return self._error(mid, -32603, "internal error", str(e))

    @staticmethod
    def _error(mid: Any, code: int, message: str, data: Any = None) -> str:
        err: dict = {"code": code, "message": message}
        if data is not None:
            err["data"] = data
        return json.dumps({"jsonrpc": "2.0", "id": mid, "error": err})
