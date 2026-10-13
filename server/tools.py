"""Tool implementations, wired to the JSON-RPC dispatcher.

Every tool declares: name, required scope, JSON schema, handler.
Read tools need "read"; inventory.update needs "write".
"""
from __future__ import annotations

import re
import sqlite3

from .auth import require
from .db import get_db
from .jsonrpc import ERR_FORBIDDEN, Dispatcher, JsonRpcError
from .pii import PiiProxy

dispatcher = Dispatcher()
pii = PiiProxy()

TOOLS: list[dict] = []


# -- method handlers -------------------------------------------------------

@dispatcher.method("initialize")
def _initialize(params: dict, ctx: dict) -> dict:
    return {
        "protocolVersion": "2026-10-13",
        "serverInfo": {"name": "mcp-baremetal", "version": "0.1.0"},
        "capabilities": {"tools": {"listChanged": False}},
    }


@dispatcher.method("ping")
def _ping(params: dict, ctx: dict) -> dict:
    return {}


@dispatcher.method("tools/list")
def _tools_list(params: dict, ctx: dict) -> dict:
    return {"tools": TOOLS}


def _rows(cur: sqlite3.Cursor) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]


@dispatcher.method("tools/call")
def _tools_call(params: dict, ctx: dict) -> dict:
    name = params.get("name")
    args = params.get("arguments") or {}
    spec = next((t for t in TOOLS if t["name"] == name), None)
    if spec is None:
        raise JsonRpcError(-32602, f"unknown tool: {name}")
    require(ctx.get("scopes", []), spec["scope"])
    handler = _HANDLERS[name]
    try:
        result = handler(args)
    except JsonRpcError:
        raise
    except Exception as e:  # noqa: BLE001
        raise JsonRpcError(-32603, f"tool {name} failed: {e}")
    masked = pii.mask(result, tool=name) if ctx.get("mask_pii", True) else result
    return {"content": [{"type": "text", "text": str(masked)}], "structured": masked}


# -- tool implementations ---------------------------------------------------

def _q_select(args: dict) -> list[dict]:
    sql = args.get("sql", "").strip()
    if not re.match(r"(?is)^\s*select\b", sql):
        raise JsonRpcError(ERR_FORBIDDEN, "only SELECT statements are allowed")
    if re.search(r"(?i)\b(insert|update|delete|drop|alter|create)\b", sql):
        raise JsonRpcError(ERR_FORBIDDEN, "only SELECT statements are allowed")
    cur = get_db().execute(sql)
    return _rows(cur)


def _orders_get(args: dict) -> dict:
    cur = get_db().execute(
        "SELECT o.*, c.name AS customer FROM orders o "
        "JOIN customers c ON c.id = o.customer_id WHERE o.id = ?",
        (args["order_id"],))
    row = cur.fetchone()
    if not row:
        raise JsonRpcError(-32602, f"no such order: {args['order_id']}")
    return dict(row)


def _orders_list(args: dict) -> list[dict]:
    limit = min(int(args.get("limit", 10)), 50)
    cur = get_db().execute(
        "SELECT o.*, c.name AS customer FROM orders o "
        "JOIN customers c ON c.id = o.customer_id "
        "ORDER BY o.placed_at DESC LIMIT ?", (limit,))
    return _rows(cur)


def _customers_search(args: dict) -> list[dict]:
    q = f"%{args.get('query', '')}%"
    cur = get_db().execute(
        "SELECT * FROM customers WHERE name LIKE ? OR email LIKE ? LIMIT 10", (q, q))
    return _rows(cur)


def _inventory_update(args: dict) -> dict:
    sku, delta = args["sku"], int(args["delta"])
    db = get_db()
    cur = db.execute("SELECT * FROM inventory WHERE sku = ?", (sku,))
    row = cur.fetchone()
    if not row:
        raise JsonRpcError(-32602, f"no such sku: {sku}")
    new_stock = row["stock"] + delta
    if new_stock < 0:
        raise JsonRpcError(-32602, f"insufficient stock: {row['stock']} on hand")
    db.execute("UPDATE inventory SET stock = ? WHERE sku = ?", (new_stock, sku))
    db.commit()
    return {"sku": sku, "name": row["name"], "old_stock": row["stock"],
            "new_stock": new_stock}


_HANDLERS = {
    "db.query": _q_select,
    "orders.get": _orders_get,
    "orders.list": _orders_list,
    "customers.search": _customers_search,
    "inventory.update": _inventory_update,
}

# Register tool schemas (order matters for the UI).
TOOLS.extend([
    {"name": "db.query", "scope": "read",
     "inputSchema": {"type": "object", "properties": {
         "sql": {"type": "string", "description": "SELECT statement only"}}}},
    {"name": "orders.get", "scope": "read",
     "inputSchema": {"type": "object", "properties": {
         "order_id": {"type": "integer"}}}},
    {"name": "orders.list", "scope": "read",
     "inputSchema": {"type": "object", "properties": {
         "limit": {"type": "integer", "default": 10}}}},
    {"name": "customers.search", "scope": "read",
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string"}}}},
    {"name": "inventory.update", "scope": "write",
     "inputSchema": {"type": "object", "properties": {
         "sku": {"type": "string"}, "delta": {"type": "integer",
          "description": "positive restocks, negative sells"}}}},
])
