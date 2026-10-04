# Yosoi Benchmark Lab

Yosoi Benchmark Lab is the independent evidence repository for comparing
[Yosoi](https://github.com/CascadingLabs/Yosoi)
with open-source software that can run locally or be self-hosted without paid
API access. Competitor packages and benchmark tooling stay outside the Yosoi
repository and build graph.

Pass the Yosoi checkout path (for example, `../Yosoi`) to the artifact builders
with `--yosoi-repository`. Benchmark runners consume the resulting built artifacts.

## Baseline v1

Baseline v1 is complete. It is an intentionally unflattering, current-host
optimization baseline—not a public “fastest” claim or release certification.
Every ranked result passed exact output correctness first.

| Quadrant | Best retained arm | Yosoi | Current result |
| --- | ---: | ---: | --- |
| Parser end-to-end, 87,928 B | Parsel 0.608 ms | 1.205 ms | Yosoi took 1.98× as long |
| HTTP, 64 responses, 20 ms delay, c8 | Colly 370.5 req/s | 332.6 req/s | Yosoi was 10.2% lower throughput |
| Rendered acquisition, four pages, c4 | Crawlee/Playwright 0.789 s | 1.389 s | Yosoi took 1.76× as long |

The lower-level direct Playwright control completed the rendered c4 workload in
0.487 s. It is useful evidence for browser-pool potential, but it is not treated
as a product-equivalent framework arm.

Read the plain-English [Baseline v1 report](docs/baseline-v1.md), or inspect the
sealed evidence directly:

- [parser and selector engines](evidence/2026-09-27-parser-exploratory/README.md);
- [HTTP acquisition and extraction](evidence/2026-09-27-http-e2e/README.md);
- [rendered browser acquisition](evidence/2026-09-27-browser-requests/README.md);
- [machine-readable baseline identity](evidence/baseline-v1.json);
- [explicit V1 gaps and the non-KPI V2 backlog](docs/coverage-gaps.md).

## Scope

The completed benchmark program has three quadrants:

1. parser and selector engines;
2. HTTP scraping frameworks;
3. rendered browser Requests.

It stops there. Persistent sessions, Actions, arbitrary JavaScript, multi-step
browser automation, hosted APIs, paid services, and hosted-only capabilities
are outside this project. AI/adaptive algorithms may be evaluated separately,
but they are not part of Baseline v1.

## Diagnostic Baseline v2

V2 is implemented as a separate internal, non-KPI matrix. It covers all 36
frozen compatible document/query/projection cells across source HTML, XML,
JSON, decoded text, rendered DOM, and accessibility trees, plus six typed
Contract/Extractor lanes.

- [V2 methodology](docs/benchmark-v2-methodology.md)
- [V2 results and interpretation](evidence/2026-09-27-diagnostics-v2/README.md)
- [V2 machine-readable coverage](evidence/2026-09-27-diagnostics-v2/coverage.json)
- [V2 evidence manifest](evidence/2026-09-27-diagnostics-v2/evidenceManifest.json)

V2 retains 3,105 timed matrix records, 135 extraction records, 30 conformance
cases, eight malformed/recovery fixtures, and three expected repeated-Contract
resource-bound outcomes. It deliberately emits no cross-format aggregate and
does not change the public Baseline v1 KPI scoreboard.

## What is measured

Correctness is the admission gate. Admitted arms retain internal latency,
outer process wall time, throughput, peak/mean/p95 RSS where available, CPU,
cold startup, package or runnable footprint, language/runtime identity,
streaming mode, concurrency scaling, and browser cleanup. A metric is reported
only where its runner actually measured it; one metric is never inferred from
another.

## Verify the retained evidence

Python environments are managed by uv from one lock with quadrant-specific
groups:

```bash
uv sync --only-group parser
uv sync --only-group http
uv sync --only-group browser
```

The retained evidence itself needs only the standard library to verify:

```bash
python3 tools/verifyBaseline.py
```

That command checks every evidence-manifest byte count and SHA-256 digest, all
retained correctness/cleanup gates, and the HTTP/browser summary medians. Full
rerun boundaries and commands are in [the Baseline v1 report](docs/baseline-v1.md).

## Evidence rule

An arm that returns the wrong values, order, multiplicity, terminal status, or
required cleanup state has no ranked timing. Failed, unsupported, and
resource-bounded outcomes stay visible rather than being silently dropped.

## Public versus internal results

The public caveman lane is pure Rust through Yosoi's public Rust surface or a
small release binary. Python and future Node bindings belong in a separate
Yosoi-versus-Yosoi overhead suite; their timings are never averaged into or
substituted for the Rust result.

## Repository map

- `docs/`: scope, taxonomy, methodology, decisions, and the closeout report.
- `specs/`: machine-readable benchmark and competitor contracts.
- `schemas/`: JSON Schemas for specifications and result envelopes.
- `fixtures/`: deterministic offline parser corpora and manifests.
- `adapters/`: isolated competitor and Yosoi benchmark surfaces.
- `tools/`: fixture generation, runners, builders, reporting, and verification.
- `evidence/`: retained raw records, summaries, and sealed manifests.
- `results/`: ignored scratch output for reruns.

## Closeout boundary

Baseline v1 records where Yosoi started. Optimization, replacement evidence,
and any future headline graph belong to the separate Yosoi Optimization project.
Format/query/extraction breadth is retained in internal Diagnostic Baseline v2
and does not change the public KPI. This repository remains the independent
harness and historical evidence source.
