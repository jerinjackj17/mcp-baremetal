"""mcp-baremetal: a raw MCP server, no wrapper SDK.

Hand-rolled JSON-RPC 2.0 over HTTP implementing the MCP method surface
(initialize, tools/list, tools/call, ping). Every byte of the protocol is
visible in server/jsonrpc.py — that is the point.

On top of the protocol:
- scoped credentials: read-only vs read-write bearer tokens; write tools
  403 without the right scope
- PII masking proxy: emails/phones/SSNs are tokenized before data reaches
  the agent, with an audit log of every substitution
"""
