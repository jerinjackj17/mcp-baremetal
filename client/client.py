"""Hand-rolled JSON-RPC client. No MCP SDK.

Proves the server speaks plain JSON-RPC 2.0: any HTTP client in any language
can drive it. Used by the demo script below and mirrored by the web UI.
"""
from __future__ import annotations

import itertools
import json
import os
import sys
import urllib.request

URL = os.environ.get("MCP_URL", "http://localhost:8000/mcp")


class McpClient:
    def __init__(self, url: str = URL, token: str = "demo_read_only"):
        self.url = url
        self.token = token
        self._ids = itertools.count(1)

    def _send(self, method: str, params: dict | None = None) -> dict:
        payload = json.dumps({
            "jsonrpc": "2.0", "id": next(self._ids),
            "method": method, "params": params or {},
        }).encode()
        req = urllib.request.Request(
            self.url, data=payload,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.token}"})
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())

    def initialize(self) -> dict:
        return self._send("initialize")

    def tools_list(self) -> dict:
        return self._send("tools/list")

    def call(self, name: str, arguments: dict) -> dict:
        return self._send("tools/call", {"name": name, "arguments": arguments})


if __name__ == "__main__":
    c = McpClient()
    print("== initialize ==")
    print(json.dumps(c.initialize()["result"]["serverInfo"], indent=2))
    print("== tools ==")
    print([t["name"] for t in c.tools_list()["result"]["tools"]])
    print("== orders.list (PII masked) ==")
    r = c.call("orders.list", {"limit": 2})
    print(json.dumps(r["result"]["structured"], indent=2)[:400])
    print("== inventory.update with read-only token (expect 403) ==")
    r = c.call("inventory.update", {"sku": "SKU-001", "delta": -1})
    print(json.dumps(r.get("error"), indent=2))
    print("== inventory.update with read-write token ==")
    c2 = McpClient(token="demo_read_write")
    r = c2.call("inventory.update", {"sku": "SKU-001", "delta": -1})
    print(json.dumps(r["result"]["structured"], indent=2))
