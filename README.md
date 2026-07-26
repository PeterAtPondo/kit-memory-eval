# kit-memory-eval

A small, sharp read-path exam for AI agent memory systems. Seventeen
questions, five capabilities, two kinds of proof. Call it what it is: a
deployment smoke test with teeth, written by the system's own builders, not
an independent comparative benchmark. Read any score here next to the
committed baseline's score; the gap is the finding.

- **Two invented worlds** (Mayfur: a regency society of cats, chronicled by two
  rival columnists in two sovereign archives). None of it exists in any
  training corpus, so a correct citation is strong evidence of retrieval, not
  prior knowledge. The mystery's paper trail is split across the two stores on
  purpose; the full case, with corroboration, only assembles across both.
- **One real corpus** (the public lifecycle of the OpenTelemetry Collector's
  memory-ballast mechanism, 2019-2024). The 62 published entries cite 73
  public source URLs, so every claim is checkable against the living record;
  the larger raw harvest and its quote validator live in the private Kit
  repository, so only the published subset is independently checkable. The
  fiction cannot be pretrained; the real corpus cannot be dismissed as an
  authored puzzle.

What it scores:

| capability | what passes |
|---|---|
| retrieval | the expected entry surfaces in the top k for a keyword probe (probes are tuned; verbatim natural-language questions score far lower, and that gap is a known limitation) |
| absence, exact | a fully out-of-corpus query (a proper noun with no lexical overlap) returns an empty list |
| absence, hard | a domain-adjacent query, an entity-anchored unsupported proposition, or a natural off-corpus question with common words returns an empty list, not confident neighbors |
| supersession | the governing entry links, via a typed relation, to the entry it replaced, and both remain citable |
| chain | a five-probe chain across two separately loaded stores all surfaces. Renamed from "synthesis" in v1.1: the harness scores that every link surfaces; it does not produce or grade the conclusion, which still needs a reader |

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

Merging the two Mayfur stores voids the chain result; that question exists
precisely to measure retrieval across memory boundaries.

## Reference result (v1.1 suite)

Kit's own demo kits (the systems this dataset was built for), 26 July 2026,
measured from Cape Town over public HTTP against a CPU-only host, no LLM in
the read path:

- questions: 13/17
- retrieval 8/8, absence_exact 2/2, **absence_hard 0/4**, supersession 2/2,
  chain 1/1
- latency: p50 997ms, p95 1145ms (client-side, network included)

The four failures are published on purpose. Two independent cold reviews of
this benchmark (26 July 2026) showed that the v1.0 suite's easy absence
questions could be passed while the system confidently returned neighbors for
domain-adjacent questions it holds nothing about. The H-class questions
encode exactly those probes, and the reference system currently fails them.
They stay red until the underlying grounding improves; a benchmark whose
author hides its own failures is advertising.

## Baseline

`adapters/token_overlap.py` is a deliberately primitive bag-of-words scorer:
no embeddings, no server, no model, no graph. Both cold reviews independently
demonstrated that a ~50-line lexical baseline passes the v1.0 suite, so we
committed one and publish it beside every reference run:

| adapter | retrieval | absence_exact | absence_hard | supersession | chain | questions |
|---|---|---|---|---|---|---|
| Kit (live demo kits) | 8/8 | 2/2 | 0/4 | 2/2 | 1/1 | 13/17 |
| token-overlap baseline | 7/8 | 2/2 | 2/4 | n/a | 1/1 | 11/17 + 2 n/a |

Read it honestly: the baseline ties or nearly ties everywhere except typed
supersession, and it currently beats the reference system on hard absence,
because a crude overlap floor abstains where semantic similarity confidently
wanders. If a system's margin over this baseline is thin, this exam cannot
distinguish it from lexical lookup; that is a property of the exam, stated
plainly.

Raw reports: `results/kit-demo-http-2026-07-26.json`,
`results/token-overlap-baseline-2026-07-26.json`. The pre-v1.1 reference run
(`results/kit-2026-07-26.json`, 13/13) is kept for the record. Replay any
probe with curl; the reference kits document themselves at
[demo.kit-project.com/llms.txt](https://demo.kit-project.com/llms.txt),
[mews.kit-project.com/llms.txt](https://mews.kit-project.com/llms.txt), and
[real.kit-project.com/llms.txt](https://real.kit-project.com/llms.txt).

Other frameworks: results welcome by pull request, with a runnable adapter.

## Spoilers

`answers/ground_truth.json` contains the answer key, including the solution to
the Mayfur mystery. If you would rather meet the mystery cold, run the guided
version first: [demo.kit-project.com/investigate](https://demo.kit-project.com/investigate).

## What this does not measure

Write-path quality, ingestion of messy data, consolidation accuracy over
time, durability, security, or scale. It also does not measure answers: no
model reads the retrieved entries, produces a conclusion, or gets graded on
correctness, citations, or declining unsupported claims. The questions,
expected titles, corpora, and reference system share an author, and the
probes are keyword-tuned; there is no held-out split. This is one leg of
evidence, deliberately small and fully replayable; treat any system's score
here as necessary, not sufficient.

## Changelog

- **v1.1 (2026-07-26).** After two independent cold reviews: renamed
  "synthesis" to "chain" (the harness scores surfacing, not reasoning);
  added four hard absence questions (H1-H4) from the reviewers' own probes,
  which the reference system currently fails; fixed a matcher bug where an
  empty hit title satisfied any positive check; committed the token-overlap
  baseline and its results. Headline honest number: 13/17, not 13/13.
- **v1.0 (2026-07-26).** Initial public release; 13 questions, 13/13.

## Provenance and ethics

The Mayfur worlds are original fiction, written for this purpose. The ballast
corpus is curated from public GitHub history: entries quote short excerpts
with their source URLs attached, people appear as roles (a maintainer, a
contributor, a user) rather than by name, and a validation gate enforces that
every quoted span exists verbatim in the harvested raw record. The curation
tooling and raw harvest live in the Kit repository; the build story is told in
[note No. 022](https://kit-project.com/blog/three-living-memories/).

## License

MIT for the code (`LICENSE`), CC BY 4.0 for the datasets and answers
(`DATA-LICENSE`), with quoted excerpts in the real corpus remaining their
original authors', cited by URL.

Built by [Kit](https://kit-project.com), an AI collaborator with persistent
memory, as its own demo exam made public. The three reference kits are live
museum copies of the substrate Kit runs on.
