import { useEffect, useState } from "react";
import { api, rpc, type Tool } from "./api";
import "./styles.css";

const TOKENS = [
  { id: "demo_read_only", label: "read-only token", scopes: ["read"] },
  { id: "demo_read_write", label: "read-write token", scopes: ["read", "write"] },
];

const EXAMPLES: Record<string, Record<string, unknown>> = {
  "db.query": { sql: "SELECT name, stock FROM inventory WHERE stock < 20" },
  "orders.get": { order_id: 103 },
  "orders.list": { limit: 3 },
  "customers.search": { query: "ava" },
  "inventory.update": { sku: "SKU-003", delta: -1 },
};

export default function App() {
  const [token, setToken] = useState(TOKENS[0].id);
  const [maskPii, setMaskPii] = useState(true);
  const [tools, setTools] = useState<Tool[]>([]);
  const [active, setActive] = useState<string>("customers.search");
  const [args, setArgs] = useState("{}");
  const [lastReq, setLastReq] = useState<object | null>(null);
  const [lastRes, setLastRes] = useState<object | null>(null);
  const [httpStatus, setHttpStatus] = useState<number | null>(null);
  const [audit, setAudit] = useState<unknown[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.tools(token).then((t) => {
      setTools(t);
      if (!t.find((x) => x.name === active)) setActive(t[0]?.name ?? "");
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    setArgs(JSON.stringify(EXAMPLES[active] ?? {}, null, 2));
  }, [active]);

  const refreshAudit = () => api.audit().then((a) => setAudit(a.entries)).catch(() => {});

  const call = async () => {
    setBusy(true);
    try {
      let parsed: Record<string, unknown> = {};
      try {
        parsed = JSON.parse(args);
      } catch {
        setLastRes({ client_error: "arguments are not valid JSON" });
        return;
      }
      const { request, response, httpStatus } = await rpc("tools/call", { name: active, arguments: parsed }, token, maskPii);
      setLastReq(request);
      setLastRes(response);
      setHttpStatus(httpStatus);
      refreshAudit();
    } finally {
      setBusy(false);
    }
  };

  const tool = tools.find((t) => t.name === active);
  const needsWrite = tool?.scope === "write";
  const tokenScopes = TOKENS.find((t) => t.id === token)?.scopes ?? [];

  return (
    <div className="page">
      <header>
        <div>
          <h1>mcp-baremetal</h1>
          <p className="sub">raw JSON-RPC 2.0 MCP server · no wrapper SDK · scoped credentials · PII masking proxy</p>
        </div>
      </header>

      <section className="controls">
        <div>
          <h2>credential</h2>
          <div className="row">
            {TOKENS.map((t) => (
              <button key={t.id} className={token === t.id ? "sel" : ""} onClick={() => setToken(t.id)}>
                {t.label}
              </button>
            ))}
          </div>
          <p className="hint">scopes granted: [{tokenScopes.join(", ")}]</p>
        </div>
        <div>
          <h2>pii masking</h2>
          <div className="row">
            <button className={maskPii ? "sel" : ""} onClick={() => setMaskPii(true)}>on — agent sees tokens</button>
            <button className={!maskPii ? "sel" : ""} onClick={() => setMaskPii(false)}>off — raw values</button>
          </div>
          <p className="hint">masking happens server-side before the response reaches the agent</p>
        </div>
      </section>

      <section className="cols">
        <div>
          <h2>tools</h2>
          <div className="tools">
            {tools.map((t) => (
              <button key={t.name} className={`tool ${active === t.name ? "sel" : ""}`} onClick={() => setActive(t.name)}>
                <code>{t.name}</code>
                <span className={`scope ${t.scope}`}>{t.scope}</span>
              </button>
            ))}
          </div>
          {needsWrite && !tokenScopes.includes("write") && (
            <p className="warn">this tool needs the <b>write</b> scope — your token will get a 403. try it.</p>
          )}
        </div>
        <div>
          <h2>arguments (json)</h2>
          <textarea value={args} onChange={(e) => setArgs(e.target.value)} rows={6} spellCheck={false} />
          <div className="actions">
            <button className="go" disabled={busy} onClick={call}>send tools/call</button>
            <button disabled={busy} onClick={() => { api.reset().then(refreshAudit); setLastReq(null); setLastRes(null); }}>
              reset pii vault
            </button>
          </div>
        </div>
      </section>

      {(lastReq || lastRes) && (
        <section className="cols">
          <div>
            <h2>raw request → POST /mcp</h2>
            <pre className="wire">{JSON.stringify(lastReq, null, 2)}</pre>
          </div>
          <div>
            <h2>raw response {httpStatus != null && <span className="http">· HTTP {httpStatus}</span>}</h2>
            <pre className="wire">{JSON.stringify(lastRes, null, 2)}</pre>
          </div>
        </section>
      )}

      <section>
        <div className="audit-head">
          <h2>pii audit log</h2>
          <button onClick={refreshAudit}>refresh</button>
        </div>
        {audit.length === 0 ? (
          <p className="hint">no substitutions yet — call <code>customers.search</code> with masking on.</p>
        ) : (
          <table className="calls">
            <thead><tr><th>time</th><th>tool</th><th>kind</th><th>token</th><th>shape</th></tr></thead>
            <tbody>
              {audit.map((e: any, i) => (
                <tr key={i}><td>{e.ts}</td><td>{e.tool}</td><td>{e.kind}</td><td>{e.token}</td><td>{e.shape}</td></tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="hint">the audit log records shapes, never values. unmasking is operator-only.</p>
      </section>

      <footer>
        <p>mcp-baremetal · hand-rolled json-rpc 2.0 · <a href="https://github.com/jerinjackj17/mcp-baremetal">github</a></p>
      </footer>
    </div>
  );
}
