"""PII masking proxy.

Before tool results reach the agent, sensitive values are swapped for opaque
tokens (EMAIL_1, PHONE_2, SSN_1, ...). Every substitution is appended to an
audit log with a timestamp, the tool call, and the field — so there is a
paper trail of exactly what the model was *not* allowed to see.

`unmask()` restores tokens to values for display back to the human operator.
The agent itself never sees raw PII.
"""
from __future__ import annotations

import re
import time
from typing import Any

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

PATTERNS = [("EMAIL", EMAIL_RE), ("PHONE", PHONE_RE), ("SSN", SSN_RE)]


class PiiProxy:
    def __init__(self):
        self._map: dict[str, str] = {}   # token -> raw value
        self.audit: list[dict] = []      # every substitution, timestamped

    def mask(self, data: Any, tool: str) -> Any:
        """Recursively mask PII in tool results. Returns masked copy."""
        if isinstance(data, dict):
            return {k: self.mask(v, tool) for k, v in data.items()}
        if isinstance(data, list):
            return [self.mask(v, tool) for v in data]
        if isinstance(data, str):
            return self._mask_string(data, tool)
        return data

    def _mask_string(self, s: str, tool: str) -> str:
        def sub(kind: str, rx: re.Pattern):
            def repl(m: re.Match) -> str:
                raw = m.group(0)
                token = f"<{kind}_{len(self._map) + 1}>"
                self._map[token] = raw
                self.audit.append({
                    "ts": time.strftime("%H:%M:%S"),
                    "tool": tool,
                    "kind": kind,
                    "token": token,
                    # NOTE: the audit log stores only the *shape*, never the value.
                    "shape": f"{kind}({len(raw)} chars)",
                })
                return token
            return rx.sub(repl, s)
        for kind, rx in PATTERNS:
            s = sub(kind, rx)
        return s

    def unmask(self, data: Any) -> Any:
        """Restore tokens to raw values. For the human operator's eyes only."""
        if isinstance(data, dict):
            return {k: self.unmask(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self.unmask(v) for v in data]
        if isinstance(data, str):
            for token, raw in self._map.items():
                data = data.replace(token, raw)
            return data
        return data

    def reset(self) -> None:
        self._map.clear()
        self.audit.clear()
