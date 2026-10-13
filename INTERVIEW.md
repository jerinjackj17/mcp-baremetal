# mcp-baremetal, in 60 seconds

mcp-baremetal is a Model Context Protocol server I wrote without the SDK. The
JSON-RPC dispatcher is about ninety lines and you can read the whole protocol
in one sitting. It exposes five tools over a sample database: order lookups,
a guarded SQL tool that only allows SELECT, customer search, and an inventory
write.

Two security properties are the point. First, scoped credentials. There are
read-only and read-write bearer tokens, and the write tool returns a 403 with
insufficient scope on the wrong token. Least privilege, enforced at the
dispatcher, not in each tool.

Second, a PII masking proxy. Emails, phones, and SSNs get swapped for opaque
tokens before the response reaches the agent, and every substitution goes
into an audit log that records shapes, never values. Unmasking is an
operator-only endpoint. The agent never sees raw PII.

Honest limits: HTTP transport rather than stdio so the demo runs in a
browser, demo tokens are public by design, and the audit log is in-process
memory. The client in the repo is also hand-rolled with stdlib only, which
proves any agent in any language can drive it. I chose raw JSON-RPC over the
SDK deliberately. If you cannot see the wire format, you cannot reason about
what the agent is actually allowed to touch.
