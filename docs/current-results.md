# Current benchmark results — 2026-10-04

The complete lab program ran against immutable local Yosoi source snapshot
`2d9269fe045149b2b2289dc4d3d47a354a92c8b4`. Its source archive SHA-256 is
`559ed881d47678c83320340d1c2dc0ce70a8df3ff4a36de48fa59a1842300129`. The build includes the frozen
working-copy code and is not a published Yosoi release artifact.

| Lane | Yosoi | Comparative result |
| --- | ---: | --- |
| Caveman byte-to-value | 0.072 ms | First of 10 arms; `lol_html` second (full ranking below) |
| Hard catalog byte-to-value | 10.141 ms | Lowest repeated median; next `scraplingParser` 146.119 ms |
| HTTP, 20 ms delay, c8 | 320.0 req/s | Colly 365.5 req/s |
| Rendered Requests, c4 | Resource-stopped | Yosoi and Scrapling unranked at the 3 GiB cap; Crawlee 0.928 s |


## How to read the parser numbers

The headline operation is **resident HTML bytes → exact materialized price
values**, through each arm's ordinary public surface. Plan construction, file
I/O, startup, and correctness checking stay outside the warm timer. Every ranked
arm passed exact values, order, and multiplicity. Five seeded campaigns retain
100 samples × 10 operations for caveman, or five samples × one operation for
the seven repeated hard arms. Beautiful Soup's hard observations stay single
samples under the resource-bounded protocol.

Yosoi's `Document::locate` uses default routing and can stream eligible plans.
Its explicit `Document::parse` and `ParsedDocument::locate` rows measure the
retained-tree path separately. End-to-end is consequently not the sum of those
phase timings. This ranking is evidence for these byte-to-value workloads,
not a universal full-DOM parser-speed claim.

`lol_html` 3.0.1 is ranked in caveman using public `HtmlRewriter` selector/text
handlers. It receives the same resident bytes in 64 KiB chunks, normalizes the
same descendant text, and passes 1-byte, 7-byte, and 64 KiB chunk-boundary
oracles. It has no invented parse-only or pre-parsed-locate row and no hard
catalog ranking in this rerun. The previous nine-arm caveman attempt was kept
separately; its samples were not pooled into the expanded ten-arm ranking.

[Parser timings, Criterion confirmation, cold starts, resources, and raw samples](../evidence/2026-10-04-parser-comparison/README.md)

## HTTP

All **150** records pass exact output for 64 unique loopback URLs, input order,
and ordinary acquisition/parsing/extraction. Immediate and fixed 20 ms response
workloads run at concurrency 1, 4, and 8, with five campaigns per cell. The
server uses `Connection: close` and backlog 128. Internal wall and fresh-process
outer wall are separate observations.

[HTTP result tables and evidence](../evidence/2026-10-04-http-e2e/README.md)

## Rendered browser Requests

All **36** campaigns were attempted. Thirty returned the exact four values and
cleaned up. Yosoi and Scrapling each reached the declared **3 GiB aggregate
sampled RSS cap** in all three c4 campaigns. Those six attempts were stopped,
retained as `resourceLimit`, and omitted from ranked timing. Every attempt has
zero residual owned browser processes; the sampler and stop path track owned
descendants rather than unrelated existing browsers.

Each arm uses regular Stable Chrome 154.0.8037.97, with sandboxing enabled, a
180-second adapter deadline, and nominal 20 ms process-tree RSS sampling.
Crawlee pools browsers; Yosoi and Scrapling perform one-shot acquisition.
Direct Playwright is a lower-level pooled control whose internal timer starts
after browser launch. Its outer process clock includes startup; it is not
ranked as a product-equivalent framework.

[Rendered result tables, resource outcomes, and identities](../evidence/2026-10-04-browser-requests/README.md)

## V2 diagnostics

All **36 cells** across HTML, XML, JSON, decoded text, rendered DOM, and
accessibility trees are covered. Verification passes for **3,105 matrix
records**, **135 extraction records**, **30 conformance cases**, **eight
malformed/security fixtures**, and **three expected extraction resource-bound
cases**. The 621 matrix groups and 27 extraction groups remain separate
semantic comparisons, with exact, nearest-primitive, and internal-only control
labels. There is no cross-format aggregate or public KPI score.

[V2 results and interpretation](../evidence/2026-10-04-diagnostics-v2/README.md)

## Environment, limitations, and verification

Rust 1.99.0; Python 3.13.1; Node 24.21.0; Go 1.27.1; Linux
7.2.5-3-omarchy on AMD Ryzen AI 9 HX 370. Python groups use `uv.lock`; Node arms
use quadrant-specific npm locks; Rust/Go control locks and every runnable
artifact digest are retained. Each bundle includes environment and harness
content identities. Builds and benchmark commands ran serially with one build
worker; workload concurrency is explicitly named in its matrix.

RSS is sampled aggregate resident memory and can miss short-lived peaks or
count shared pages more than once. It is neither PSS nor allocation evidence.
CPU, memory, latency, startup, and footprint remain different measurements.
Power/frequency and unrelated workstation activity were not controlled.
This is current-host exploratory evidence. September bundles retain different
source/compiler/dependency/browser identities and provide historical context,
not a controlled before/after performance trend. A successful benchmark does
not replace full browser compatibility or release certification.

```bash
python3 tools/verifyBaseline.py --baseline evidence/current.json
python3 tools/verifyV2.py --evidence evidence/2026-10-04-diagnostics-v2
```

The comparative verifier checks manifest bytes/digests, exact output, native
parser sample/operation counts and timing medians, HTTP/browser medians,
browser matrix completeness, cleanup, and rejection of ranked failed cells.
The V2 verifier checks all spec cells, records, summaries, and expected failure
boundaries. See [complete rerun instructions](rerunning.md).
