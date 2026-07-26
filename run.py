#!/usr/bin/env python3
"""Run the exam against a memory adapter and score it.

    python3 run.py                          # reference run: live Kit demo kits
    python3 run.py --adapter yourmodule:YourAdapter --label yours
    python3 run.py --json                   # also write results/<label>-<date>.json

Scoring is per probe, rolled up per question and per capability:
  retrieval         expected entry title in top k
  absence_exact     fully out-of-corpus query returns an empty list
  absence_hard      the hard class, added 2026-07-26 after independent cold
                    reviews showed the easy class alone is passable by
                    accident: domain-adjacent queries, entity-anchored
                    unsupported propositions, and natural off-corpus
                    questions with common words. All expect empty.
  supersession      the typed link from the governing entry reaches the entry
                    it replaced (n/a for systems without typed relations;
                    reported, not punished, but the column will say n/a)
  chain             the M4 chain: five retrievals across two SEPARATE stores.
                    Renamed from "synthesis" 2026-07-26: this harness scores
                    that every link of the chain SURFACES. It does not produce
                    or grade the conclusion; that still needs a reader.

Worlds must be loaded into separate stores; merging them voids M-questions.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

WORLD_OF = {"papers": "whiskerdown", "mews": "mews", "real": "real"}
CAPABILITY_OF = {  # question id prefix -> capability bucket
    "M1": "retrieval", "M2": "absence_exact", "M3": "supersession",
    "M4": "chain", "M5": "retrieval",
    "B1": "retrieval", "B2": "retrieval", "B3": "retrieval",
    "B4": "retrieval", "B5": "supersession", "B6": "retrieval",
    "B7": "retrieval", "X1": "absence_exact",
    "H1": "absence_hard", "H2": "absence_hard", "H3": "absence_hard",
    "H4": "absence_hard",
}


def load_adapter(spec: str):
    if spec == "kit_http":
        from adapters.kit_http import KitHttpAdapter
        return KitHttpAdapter()
    mod_name, _, cls_name = spec.partition(":")
    mod = importlib.import_module(mod_name)
    return getattr(mod, cls_name)()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="kit_http")
    ap.add_argument("--label", default=None)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--date", default=str(date.today()))
    args = ap.parse_args()

    adapter = load_adapter(args.adapter)
    label = args.label or adapter.name
    Q = json.load(open(os.path.join(HERE, "questions.json")))

    datasets = {w: json.load(open(os.path.join(HERE, "datasets", f"{w}.json")))
                for w in set(WORLD_OF.values())}
    for w, d in datasets.items():
        adapter.load(w, d)

    results, caps = [], {}
    for q in Q["questions"]:
        cap = CAPABILITY_OF.get(q["id"].split("-")[0], "retrieval")
        probe_rows, q_ok, q_na = [], True, False
        for p in q["probes"]:
            world = WORLD_OF[p["kit"]]
            hits = adapter.search(world, p["query"], k=args.k)
            ts = [h.title for h in hits]
            if p.get("expect_empty"):
                ok = len(hits) == 0
                detail = "empty, honestly" if ok else f"expected empty, got {ts[:2]}"
            else:
                want = p.get("expect_titles_any") or []
                # A hit matches when the expected title contains it or vice
                # versa, but never on trivial containment: empty or tiny hit
                # titles must not satisfy a positive check (matcher bug found
                # by a cold review, fixed 2026-07-26).
                def _matches(t: str) -> bool:
                    tl = t.strip().lower()
                    if len(tl) < 6:
                        return False
                    return any(w2.lower() in tl or tl in w2.lower() for w2 in want)
                match = next((t for t in ts if _matches(t)), None)
                ok = match is not None
                detail = (f"rank {ts.index(match) + 1}: {match}" if ok
                          else f"none of expected in top {len(ts)}")
                edge_want = p.get("expect_supersedes_edge_to_title")
                if ok and edge_want:
                    if not adapter.supports_supersession():
                        ok, detail, q_na = True, detail + " | supersession n/a", True
                    else:
                        linked = adapter.superseded_link(world, match)
                        if not linked or edge_want.lower() not in linked.lower():
                            ok, detail = False, detail + f" | link missing/wrong: {linked}"
                        else:
                            detail += f" | supersedes -> {linked}"
            q_ok = q_ok and ok
            probe_rows.append({"kit": p["kit"], "query": p["query"], "ok": ok, "detail": detail})
        status = "n/a" if (q_na and q_ok) else ("pass" if q_ok else "fail")
        caps.setdefault(cap, []).append(status)
        results.append({"id": q["id"], "question": q["question"], "status": status,
                        "probes": probe_rows})

    npass = sum(1 for r in results if r["status"] == "pass")
    print(f"# kit-memory-eval · adapter: {label} · {args.date}\n")
    print(f"questions passed: {npass}/{len(results)}"
          + (f" ({sum(1 for r in results if r['status'] == 'n/a')} n/a)" if any(
              r['status'] == 'n/a' for r in results) else "") + "\n")
    for r in results:
        print(f"[{r['status'].upper():4}] {r['id']}: {r['question']}")
        for p in r["probes"]:
            print(f"    {'ok ' if p['ok'] else 'MISS'} {p['kit']} · {p['detail']}")
    print("\n## capabilities")
    for cap, statuses in sorted(caps.items()):
        n_ok = sum(1 for s in statuses if s == "pass")
        n_na = sum(1 for s in statuses if s == "n/a")
        line = f"  {cap}: {n_ok}/{len(statuses)}"
        if n_na:
            line += f" ({n_na} n/a)"
        print(line)
    lat = getattr(adapter, "latencies", None)
    if lat:
        import statistics
        allv = [v for vs in lat.values() for v in vs]
        allv.sort()
        p50 = allv[len(allv) // 2] * 1000
        p95 = allv[min(len(allv) - 1, int(0.95 * (len(allv) - 1)))] * 1000
        print(f"\n## latency (client-side, network included): n={len(allv)} "
              f"p50={p50:.0f}ms p95={p95:.0f}ms")

    if args.json:
        out = os.path.join(HERE, "results", f"{label}-{args.date}.json")
        json.dump({"adapter": label, "date": args.date, "passed": npass,
                   "total": len(results), "results": results}, open(out, "w"), indent=2)
        print(f"\nwritten: {out}")

    sys.exit(0 if npass + sum(1 for r in results if r["status"] == "n/a") == len(results) else 1)


if __name__ == "__main__":
    main()
