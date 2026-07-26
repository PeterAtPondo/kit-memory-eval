# kit-memory-eval

A small, sharp benchmark for AI agent memory systems. Thirteen questions, four
capabilities, two kinds of proof:

- **Two invented worlds** (Mayfur: a regency society of cats, chronicled by two
  rival columnists in two sovereign archives). None of it exists in any
  training corpus, so a correct answer is provably retrieval, not prior
  knowledge. The central mystery is split across the two stores on purpose:
  answering it requires cross-store synthesis, and each store alone dead-ends
  honestly.
- **One real corpus** (the complete public lifecycle of the OpenTelemetry
  Collector's memory-ballast mechanism, 2019-2024, curated from 140 GitHub
  threads). Every entry carries the source URL it was curated from, so every
  claim is checkable against the living record. The fiction cannot be
  pretrained; the real corpus cannot be dismissed as an authored puzzle.

What it scores:

| capability | what passes |
|---|---|
| retrieval | the expected entry surfaces in the top k for a natural query |
| honest absence | an off-corpus query returns an empty list, not confident filler |
| supersession | the governing entry links, via a typed relation, to the entry it replaced, and both remain citable |
| synthesis | a five-probe chain across two separately loaded stores all surfaces; the conclusion is written in neither store |

## Run it

Against the live reference kits (public, read-only, keyless):

```bash
python3 run.py
```

Against your own system: implement the four-method adapter in
`adapters/base.py`, load the three datasets into **separate** stores, then:

```bash
python3 run.py --adapter yourmodule:YourAdapter --label yours
```

Merging the two Mayfur stores voids the synthesis result; that question exists
precisely to measure reasoning across memory boundaries.

## Reference result

Kit's own demo kits (the systems this dataset was built for), 26 July 2026,
measured from Cape Town over public HTTP against a CPU-only host, no LLM in
the read path:

- questions: 13/13
- retrieval 8/8, honest absence 2/2, supersession 2/2, synthesis 1/1
- latency: p50 989ms, p95 1043ms (client-side, network included)

Raw report: `results/kit-2026-07-26.json`. Replay any probe with curl; the
reference kits document themselves at
[demo.kit-project.com/llms.txt](https://demo.kit-project.com/llms.txt),
[mews.kit-project.com/llms.txt](https://mews.kit-project.com/llms.txt), and
[real.kit-project.com/llms.txt](https://real.kit-project.com/llms.txt).

Other frameworks: results welcome by pull request, with a runnable adapter.

## Spoilers

`answers/ground_truth.json` contains the answer key, including the solution to
the Mayfur mystery. If you would rather meet the mystery cold, run the guided
version first: [demo.kit-project.com/investigate](https://demo.kit-project.com/investigate).

## What this does not measure

Write-path quality, ingestion of messy data, consolidation accuracy over time,
durability, security, or scale. This benchmark measures read-time behavior
against curated corpora. It is one leg of evidence, deliberately small and
fully replayable; treat any system's score here as necessary, not sufficient.

## Provenance and ethics

The Mayfur worlds are original fiction, written for this purpose. The ballast
corpus is curated from public GitHub history: entries quote short excerpts
with their source URLs attached, people appear as roles (a maintainer, a
contributor, a user) rather than by name, and a validation gate enforces that
every quoted span exists verbatim in the harvested raw record. The curation
tooling and raw harvest live in the Kit repository; the build story is told in
[note No. 022](https://kit-project.com/blog/three-living-memories/).

## License

TBD before public release: proposed MIT for code, CC BY 4.0 for the datasets.

Built by [Kit](https://kit-project.com), an AI collaborator with persistent
memory, as its own demo exam made public. The three reference kits are live
museum copies of the substrate Kit runs on.
