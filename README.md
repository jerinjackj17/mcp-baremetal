# mcp-baremetal

A Model Context Protocol server written by hand. No SDK. The JSON-RPC 2.0
dispatcher is about 90 lines in `server/jsonrpc.py` and you can read the whole
protocol in one sitting. That is the point: if you cannot see the wire format,
you cannot reason about what the agent is allowed to touch.

Live demo: _(deploying)_

## What it exposes

Five tools over a sample SQLite store (fake e-commerce data; every customer
row carries synthetic emails, phones, and SSNs on purpose):

| Tool | Scope | Notes |
|---|---|---|
| `db.query` | read | ad-hoc `SELECT` only, anything else is rejected |
| `orders.get`, `orders.list` | read | point lookups and listings |
| `customers.search` | read | returns rows with PII tokenized (`<EMAIL_1>`) |
| `inventory.update` | write | 403s on a read-only token |

Try it in the demo UI:

1. Call `customers.search` with masking on. The agent sees `<EMAIL_1>`, never
   the address. Open the audit log: every substitution is timestamped.
2. Call `inventory.update` with the read-only token: JSON-RPC `-32003`,
   insufficient scope. Switch tokens and watch it succeed.
3. Turn masking off and compare the raw response.
4. Read the raw request/response panes. That exact JSON is what any agent
   sends. `client/client.py` uses stdlib only, no SDK, and proves interop.

## How it is built

Protocol (`server/jsonrpc.py`): parse, validate, route, serialize per
JSON-RPC 2.0. Never leaks tracebacks to the caller.

Auth (`server/auth.py`): bearer tokens map to scopes. Demo tokens are
hardcoded and labeled as such. Production tokens come from `TOKENS_JSON`.

PII proxy (`server/pii.py`): regex tokenization of emails, phones, and SSNs
on the response path. The audit log records shapes (`EMAIL(21 chars)`), never
values. `POST /operator/unmask` restores tokens. Operator eyes only.

SQL guardrail: `db.query` accepts `SELECT` and nothing else. `DROP TABLE`
gets a `-32003` before it touches the database.

## Run it

```bash
pip install -r requirements.txt
uvicorn api.index:app --port 8000   # POST /mcp

MCP_URL=http://localhost:8000/mcp python client/client.py
npm install && npm run dev          # UI on :5173, proxies /mcp
```

Deploy: push to `main`. Vercel builds the UI and serves `api/index.py`.
`POST /mcp` and `/operator/*` rewrite to the function (see `vercel.json`).

## Limits, stated plainly

* HTTP transport only (no stdio/SSE). The JSON-RPC semantics are identical;
  stdio is a thin adapter away. Browsers cannot do stdio, so HTTP it is.
* Demo tokens are public by design. Real deployments use `TOKENS_JSON` with
  rotated secrets.
* The audit log lives in process memory. Production would ship it to durable
  storage.

## Layout

```
server/         jsonrpc.py (protocol), auth.py (scopes), pii.py (masking),
                tools.py (tool handlers), db.py (synthetic SQLite dataset)
client/         hand-rolled JSON-RPC client, stdlib only
api/index.py    FastAPI entry: POST /mcp plus /operator/* helpers
src/            React demo UI: raw request/response panes, scope and PII toggles
docs/ADR-001.md why raw JSON-RPC instead of the MCP SDK
INTERVIEW.md    how I explain this in 60 seconds
```
