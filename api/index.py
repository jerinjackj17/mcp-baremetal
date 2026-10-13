"""mcp-baremetal HTTP surface (FastAPI, Vercel serverless entry).

  POST /mcp            raw JSON-RPC 2.0 in, raw JSON-RPC 2.0 out.
                       Auth: Authorization: Bearer <token>.
                       Query/body param mask_pii=0 disables PII masking (demo).

The /operator/* helpers exist for the demo UI only: the audit log and the
unmask view are the *human operator's* eyes, never the agent's.
"""
from __future__ import annotations

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from server.auth import authenticate
from server.jsonrpc import ERR_UNAUTHORIZED, JsonRpcError
from server.tools import dispatcher, pii

app = FastAPI(title="mcp-baremetal")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.post("/mcp")
async def mcp(request: Request) -> Response:
    try:
        scopes = authenticate(request.headers.get("authorization"))
    except JsonRpcError as e:
        body = dispatcher._error(None, e.code, e.message, e.data)
        return Response(content=body, media_type="application/json",
                        status_code=401 if e.code == ERR_UNAUTHORIZED else 403)
    mask_pii = request.query_params.get("mask_pii", "1") != "0"
    ctx = {"scopes": scopes, "mask_pii": mask_pii}
    raw = (await request.body()).decode("utf-8") or "{}"
    out = dispatcher.dispatch(raw, ctx)
    return Response(content=out, media_type="application/json")


@app.get("/operator/audit")
def audit() -> dict:
    return {"entries": pii.audit}


@app.post("/operator/unmask")
def unmask(body: dict) -> dict:
    # Operator-only: restore tokens for human display.
    return {"data": pii.unmask(body.get("data"))}


@app.post("/operator/reset")
def reset() -> dict:
    pii.reset()
    return {"ok": True}


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "protocol": "json-rpc/2.0", "transport": "http"}
