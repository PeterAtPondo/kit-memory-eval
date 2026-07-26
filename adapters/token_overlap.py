"""A deliberately primitive baseline: bag-of-words token overlap. No
embeddings, no server, no model, no graph.

This adapter exists because of a finding, not despite one. On 2026-07-26 two
independent cold reviews of this benchmark showed that a ~50-line lexical
scorer passes every non-edge item of the v1.0 suite, which means the easy
suite measures lexical reachability, not memory. We committed the baseline
and its scores rather than argue with it: any system's result here should be
read NEXT TO this baseline's result, and the gap (or absence of one) is the
finding. The H-class questions were added in v1.1 for the same reason.

Run it:

    python3 run.py --adapter adapters.token_overlap:TokenOverlapAdapter \
        --label token-overlap-baseline
"""
from __future__ import annotations

import re

from adapters.base import Hit, MemoryAdapter

STOPWORDS = set(
    "a an and are as at be but by did do for from had has have in is it of on "
    "or the their there they this to was were what when where which who why "
    "will with your".split()
)

MIN_OVERLAP = 0.34  # at least a third of query tokens must appear in an entry


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9']+", text.lower()) if t not in STOPWORDS}


class TokenOverlapAdapter(MemoryAdapter):
    name = "token-overlap-baseline"

    def __init__(self) -> None:
        self.stores: dict[str, list[tuple[str, set[str]]]] = {}

    def load(self, world: str, dataset: dict) -> None:
        entries = []
        for e in dataset.get("entities", []):
            text = " ".join(str(e.get(f, "")) for f in ("title", "content", "tags", "topics"))
            entries.append((e.get("title", ""), _tokens(text)))
        self.stores[world] = entries

    def search(self, world: str, query: str, k: int = 5) -> list[Hit]:
        q = _tokens(query)
        if not q:
            return []
        scored = []
        for title, toks in self.stores.get(world, []):
            overlap = len(q & toks) / len(q)
            if overlap >= MIN_OVERLAP:
                scored.append((overlap, title))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [Hit(title=t, score=s) for s, t in scored[:k]]

    # No typed relations: supersession reports n/a, which is itself a finding.
    def supports_supersession(self) -> bool:
        return False
