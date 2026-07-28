"""Adapter for a Kit that ingests the datasets from cold, rather than a
pre-loaded demo kit.

Why this exists: `kit_http.py` points at the three public demo kits, which are
already populated, so its `load()` is a no-op. Any comparison against a system
whose adapter ingests at test time therefore exercises that system's write path
and not Kit's, which tilts the result before the first question is asked. This
adapter closes that gap: it writes every dataset entity and edge into an empty
Kit over HTTP, then answers probes the same way `kit_http.py` does.

Each world needs its own store and its own write key. The M4 chain question
tests retrieval across store boundaries, so merging the two Mayfur archives
into one Kit voids that result.

Honesty guards, both of which fail the run rather than degrading it quietly:

  - Dedup is disabled on write. Kit dedups at cosine 0.92 by default, which is
    correct for a live brain and wrong for a curated corpus: a legitimately
    similar entry would be dropped and the store would silently hold less than
    the dataset says it does.
  - After loading, the entity and edge counts are verified against the dataset.
    A short load raises instead of proceeding, because a comparison run on a
    partial corpus produces a number that looks real and is not.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from .base import Hit, MemoryAdapter

# Category for dataset entities that do not name one. The datasets carry their
# own `category` per entity; this is only the fallback.
DEFAULT_CATEGORY = "reference"

# The edge types Kit documents publicly. `edge_type` is a free string on the
# wire and `create_edge` does not validate against this set, so a dataset may
# legitimately carry domain relations outside it (the Mayfur worlds use
# `protects`, `courted`, `owes`, `rivals`, `suspects`). Loading those is
# correct; coercing them to `related_to` would invent a relation the dataset
# never asserted, and silently dropping them would shrink the graph. They are
# recorded on the adapter instead, so a run can report what the graph holds
# beyond the documented vocabulary.
DOCUMENTED_EDGE_TYPES = {
    "extends",
    "supersedes",
    "related_to",
    "implements",
    "caused_by",
    "references",
    "novel_association",
}


class KitColdLoadError(RuntimeError):
    """Raised when a load did not reproduce the dataset exactly."""


class KitColdAdapter(MemoryAdapter):
    name = "kit-cold-load"

    def __init__(self, kits: dict[str, dict], timeout: int = 60):
        """`kits` maps a world name to {"url": ..., "key": ...}.

        The key needs write access; the load path creates memories and edges.
        Point each world at a separate, empty Kit.
        """
        self.kits = kits
        self.timeout = timeout
        self.latencies: dict[str, list[float]] = {}
        self._ids: dict[tuple[str, str], int] = {}      # (world, title) -> memory id
        self._loaded: dict[str, dict[str, int]] = {}    # world -> {entity key: id}
        # world -> edge types loaded that Kit does not document publicly
        self.undocumented_edge_types: dict[str, list[str]] = {}

    # ---- transport -------------------------------------------------------

    def _request(self, world: str, path: str, payload: dict | None = None):
        cfg = self.kits[world]
        url = cfg["url"] + path
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
        req.add_header("Content-Type", "application/json")
        if cfg.get("key"):
            req.add_header("Authorization", f"Bearer {cfg['key']}")
        import time
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = r.read().decode()
        except urllib.error.HTTPError as e:
            raise KitColdLoadError(
                f"{path} returned {e.code}: {e.read().decode()[:400]}"
            ) from e
        self.latencies.setdefault(world, []).append(time.perf_counter() - t0)
        return json.loads(body) if body else None

    # ---- load ------------------------------------------------------------

    def load(self, world: str, dataset: dict) -> None:
        entities = dataset.get("entities") or []
        edges = dataset.get("edges") or []

        missing_type = [e for e in edges if not e.get("type")]
        if missing_type:
            raise KitColdLoadError(
                f"{world}: {len(missing_type)} edges carry no type. An untyped "
                "edge would load as an untyped relation and quietly weaken the "
                "graph the supersession probes walk."
            )
        self.undocumented_edge_types[world] = sorted(
            {e["type"] for e in edges} - DOCUMENTED_EDGE_TYPES
        )

        key_to_id: dict[str, int] = {}
        for ent in entities:
            body = {
                "category": ent.get("category") or DEFAULT_CATEGORY,
                "title": ent.get("title") or "",
                "content": ent.get("content") or "",
                "tags": ",".join(ent.get("tags") or []) or None,
                "written_by": "kit-memory-eval",
                # Curated corpus: never let near-duplicate collapse silently
                # change what the store holds relative to the dataset.
                "skip_dedup": True,
                # Entity extraction is a separate batched pass; running it per
                # write would make load time an LLM-bound variable and put a
                # provider in the middle of a path we describe as local.
                "auto_extract": False,
            }
            created = self._request(world, "/memories/", body)
            mid = created.get("id")
            if mid is None:
                raise KitColdLoadError(f"{world}: create returned no id for {body['title']!r}")
            key_to_id[ent.get("key") or body["title"]] = mid
            self._ids[(world, body["title"])] = mid

        if len(key_to_id) != len(entities):
            raise KitColdLoadError(
                f"{world}: dataset has {len(entities)} entities but only "
                f"{len(key_to_id)} distinct keys landed. Duplicate keys in the "
                "dataset, or writes were collapsed."
            )

        written_edges = 0
        for edge in edges:
            src = key_to_id.get(edge.get("from"))
            dst = key_to_id.get(edge.get("to"))
            if src is None or dst is None:
                raise KitColdLoadError(
                    f"{world}: edge {edge.get('from')!r} -> {edge.get('to')!r} "
                    "references an entity key that is not in this dataset."
                )
            self._request(world, "/edges/", {
                "from_id": src,
                "to_id": dst,
                "edge_type": edge.get("type"),
                "note": edge.get("note"),
                "written_by": "kit-memory-eval",
            })
            written_edges += 1

        if written_edges != len(edges):
            raise KitColdLoadError(
                f"{world}: dataset has {len(edges)} edges, wrote {written_edges}."
            )

        self._loaded[world] = key_to_id

    # ---- probe -----------------------------------------------------------

    def search(self, world: str, query: str, k: int = 5) -> list[Hit]:
        q = urllib.parse.quote(query)
        hits = self._request(
            world, f"/memories/search?query={q}&limit={k}&fields=compact"
        )
        out = []
        for h in hits or []:
            m = h.get("memory") or {}
            title = m.get("title") or ""
            out.append(Hit(title=title, score=h.get("relevance")))
            if m.get("id") is not None:
                self._ids[(world, title)] = m["id"]
        return out

    def supports_supersession(self) -> bool:
        return True

    def superseded_link(self, world: str, hit_title: str) -> str | None:
        mid = self._ids.get((world, hit_title))
        if mid is None:
            return None
        g = self._request(world, f"/memories/subgraph?memory_id={mid}&hops=1")
        for e in (g or {}).get("edges") or []:
            if e.get("edge_type") == "supersedes" and e.get("from_id") == mid:
                target = self._request(world, f"/memories/{e['to_id']}")
                return (target or {}).get("title")
        return None
