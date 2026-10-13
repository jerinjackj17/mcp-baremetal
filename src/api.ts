let idc = 1;

export interface Tool {
  name: string;
  scope: string;
  inputSchema: { properties: Record<string, { type: string; description?: string; default?: unknown }> };
}

async function j<T>(r: Response): Promise<T> {
  const body = await r.json();
  return body;
}

/** Raw JSON-RPC over POST /mcp. The UI speaks the same protocol as any agent would. */
export async function rpc(method: string, params: Record<string, unknown>, token: string, maskPii: boolean): Promise<{
  request: object; response: any; httpStatus: number;
}> {
  const request = { jsonrpc: "2.0", id: idc++, method, params };
  const url = `/mcp${maskPii ? "" : "?mask_pii=0"}`;
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(request),
  });
  const response = await j(r);
  return { request, response, httpStatus: r.status };
}

export const api = {
  tools: (token: string) =>
    rpc("tools/list", {}, token, true).then((x) => x.response.result.tools as Tool[]),
  audit: () => fetch("/operator/audit").then(j<{ entries: unknown[] }>),
  reset: () => fetch("/operator/reset", { method: "POST" }).then(j),
};
