"""Adapter for the live Kit demo kits (the reference implementation).

Runs against the three public, read-only kits over keyless HTTP GETs. The
kits are pre-loaded, so load() is a no-op. Supersession walks the live typed
graph: subgraph of the hit, follow the outgoing `supersedes` edge, read the
target's title. Every call here is replayable with curl.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from .base import Hit, MemoryAdapter

KITS = {
    "whiskerdown": "https://demo.kit-project.com",
    "mews": "https://mews.kit-project.com",
    "real": "https://real.kit-project.com",
}


class KitHttpAdapter(MemoryAdapter):
    name = "kit-demo-http"

    def __init__(self, kits: dict[str, str] | None = None, timeout: int = 30):
        self.kits = kits or dict(KITS)
        self.timeout = timeout
        self.latencies: dict[str, list[float]] = {}

    def _get(self, world: str, path: str):
        import time
        url = self.kits[world] + path
        t0 = time.perf_counter()
        with urllib.request.urlopen(url, timeout=self.timeout) as r:
            data = json.loads(r.read().decode())
        self.latencies.setdefault(world, []).append(time.perf_counter() - t0)
        return data

    def load(self, world: str, dataset: dict) -> None:
        pass  # hosted and pre-loaded; datasets/ is the source of truth for what they hold

    def search(self, world: str, query: str, k: int = 5) -> list[Hit]:
        q = urllib.parse.quote(query)
        hits = self._get(world, f"/memories/search?query={q}&limit={k}&fields=compact")
        out = []
        for h in hits:
            m = h.get("memory") or {}
            out.append(Hit(title=m.get("title") or "", score=h.get("relevance")))
            # keep ids for the supersession walk without widening the contract
            self._last_ids = getattr(self, "_last_ids", {})
            self._last_ids[(world, m.get("title") or "")] = m.get("id")
        return out

    def supports_supersession(self) -> bool:
        return True

    def superseded_link(self, world: str, hit_title: str) -> str | None:
        mid = getattr(self, "_last_ids", {}).get((world, hit_title))
        if mid is None:
            return None
        g = self._get(world, f"/memories/subgraph?memory_id={mid}&hops=1")
        for e in g.get("edges") or []:
            if e.get("edge_type") == "supersedes" and e.get("from_id") == mid:
                target = self._get(world, f"/memories/{e['to_id']}")
                return target.get("title")
        return None
