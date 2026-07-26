"""The adapter contract: what a memory system implements to sit this exam.

Deliberately small. The benchmark tests behavior, not API surface, so the
contract is four methods, two of them optional. A hit is anything with a
title and a score; how your system stores, chunks, embeds, or links memory
is your business.

Scoring uses only what you return here:
  - retrieval: does the expected entry title appear in your top k?
  - honest absence: does an off-corpus query return an empty list, rather
    than confident filler?
  - supersession: given a hit that has been superseded-forward, can your
    system name the entry that superseded it (or that it supersedes)?
    Optional: systems without typed relations score n/a here, which is
    itself a finding.

Load the datasets however suits your system (datasets/*.json: entities with
title, content, tags, dates, typed edges, and source URLs). Keep worlds in
SEPARATE stores: the M4 chain question tests retrieval across store
boundaries, and merging the two archives voids that result.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Hit:
    title: str
    score: float | None = None


class MemoryAdapter:
    name = "unnamed-adapter"

    def load(self, world: str, dataset: dict) -> None:
        """Ingest one world's dataset into an isolated store. Called once per
        world before any probes. Hosted systems that are pre-loaded (like the
        live Kit demo kits) may no-op."""
        raise NotImplementedError

    def search(self, world: str, query: str, k: int = 5) -> list[Hit]:
        """Top-k results for a natural-language query against one world."""
        raise NotImplementedError

    def supports_supersession(self) -> bool:
        return False

    def superseded_link(self, world: str, hit_title: str) -> str | None:
        """If your system holds a typed supersession relation for this entry,
        return the linked entry's title (the one this entry supersedes, or is
        superseded by). Return None when no such relation is held."""
        return None
