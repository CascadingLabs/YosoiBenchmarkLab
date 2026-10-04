# Baseline v1: what we ran, what failed, and what to optimize

This is the historical **2026-09-27** baseline. Its measurements and targets
describe the recorded source artifacts and environment. See
[Current benchmark results](current-results.md) for the latest rerun and
[Rerun the complete lab](rerunning.md) for reproducible commands.

## Plain English

This lab answers one question: where is Yosoi fast or slow before optimization?
It compares exact, local workloads against open-source tools and refuses to rank
an answer that is wrong. Baseline v1 is complete enough to guide optimization,
but it is deliberately not polished into a marketing claim.

## The three quadrants

### 1. Parser and selector engines

This is the fully offline CPU/memory lane. Nine adapters parse the same frozen
HTML bytes, compile an equivalent selector operation, and return the same
ordered values.

The caveman fixture is 87,928 bytes with one selected value. The hard fixture is
17,186,672 bytes with 64 selected values. The suite separates parse, locate,
end-to-end, cold-process, and resource measurements instead of treating them as
one interchangeable number.

Result: Parsel led both end-to-end workloads. Yosoi took 1.205 ms versus 0.608
ms on caveman and 315.984 ms versus 143.600 ms on hard. Yosoi's useful bright
spot was a 256.4 MiB hard-pass peak RSS, lower than the Rust `scraper`, GoQuery,
and Python parser controls in that pass.

### 2. HTTP acquisition and extraction

Five frameworks request 64 unique URLs from one deterministic loopback server,
parse the approximately 32 KiB response, select one value, restore input order,
and prove the exact 64-value oracle. The matrix uses concurrency 1, 4, and 8,
both immediate and fixed 20 ms server responses, and five fresh-process
campaigns per cell.

Result: Colly led. At 20 ms and concurrency 8, Yosoi reached 332.6 requests/s
versus Colly's 370.5. Yosoi scaled 7.26× from c1 to c8, which says concurrency
works; the next target is per-request setup and processing overhead. With an
immediate server, Yosoi was nearly flat across c1–c8 and reached 1,388.6
requests/s at c8 versus Colly's 2,644.9.

### 3. Rendered acquisition

Four unique loopback pages each load a deterministic delayed script and update
one DOM value. Yosoi browser Request, Scrapling DynamicFetcher,
Crawlee/Playwright, and a direct Playwright control run at concurrency 1, 2,
and 4 for three fresh-process campaigns. Every retained run returned all four
values and left zero new Chromium processes behind.

Result: Yosoi took 1.389 s and 5,916.2 MiB peak RSS at c4. Crawlee took 0.789 s
and 1,678.5 MiB by amortizing a browser pool. Direct Playwright took 0.487 s as
a lower-level pooled control. This is strong evidence that browser reuse and
bounded lifecycle ownership are the first rendered-acquisition optimization
targets.

## Coverage boundary

Baseline v1 is not a full document/extraction matrix. It does not independently
benchmark XPath, decoded-text literal search, regex/captures, JSON, XML,
accessibility trees, streaming evaluation, or the typed Contracts/Extractor
pipeline. Raw lxml happens to compile the neutral HTML task to XPath, but that
does not make V1 a CSS-versus-XPath comparison.

The exact measured/missing matrix and the implemented internal, non-KPI V2 are in
[Baseline v1 coverage gaps and Benchmark Lab V2](coverage-gaps.md).

## KPI scoreboard for optimization

Correctness remains non-negotiable for every target below.

| Area | Baseline | First target | Stretch target |
| --- | ---: | ---: | ---: |
| Caveman parser end-to-end | 1.205 ms | ≤0.829 ms (Rust `scraper`) | ≤0.608 ms (Parsel) |
| Hard parser end-to-end | 315.984 ms | ≤187.597 ms (Rust `scraper`) | ≤143.600 ms (Parsel) |
| Hard parser peak RSS | 256.4 MiB | Do not regress | Lower while improving latency |
| HTTP io20 c8 | 332.6 req/s | ≥370.5 req/s (Colly) | Preserve near-linear c1→c8 scaling |
| HTTP immediate c8 | 1,388.6 req/s | ≥1,795.8 req/s (Colly c1) | ≥2,644.9 req/s (Colly c8) |
| Rendered c4 wall | 1.389 s | ≤1.025 s (Scrapling) | ≤0.789 s (Crawlee) |
| Rendered c4 peak RSS | 5,916.2 MiB | <4,490.1 MiB (Scrapling) | ≤1,678.5 MiB (Crawlee) |
| Browser cleanup | zero residual PIDs | zero | zero |

These targets are optimization gates, not promises. A faster result does not
replace Baseline v1; it becomes a new evidence bundle with a new manifest.

## Metrics and their boundaries

- **Correctness:** exact values, order, multiplicity, terminal status, and for
  browser runs, cleanup. This gates every timing.
- **Internal wall:** the adapter's own monotonic timer around its declared
  operation. Different products expose different lifecycle boundaries.
- **Outer wall:** fresh child-process launch through exit. This retains startup
  and module-loading cost that internal wall may exclude.
- **Throughput:** completed correct requests divided by internal wall. It is
  derived only where the runner records both inputs.
- **RSS:** sampled resident physical memory, aggregated across the relevant
  process tree. VSZ is not treated as RAM.
- **CPU:** child user/system CPU where the runner captures it.
- **Footprint:** binary bytes or dependency-environment bytes. These are kept
  distinct because they are not equivalent packaging formats.
- **Concurrency scaling:** c1 versus higher bounded populations.
- **Streaming:** recorded as a capability/mode; the parser workload itself is a
  full-DOM equivalence task and does not manufacture a streaming ranking.

## Campaign design

Parser warm results use five independently shuffled campaigns; the main
caveman lane contains 100 samples with 10 operations per sample. Criterion adds
five Rust-only campaigns. HTTP uses five fresh-process campaigns per cell.
Rendered acquisition uses three because each arm launches substantially more
processes and memory.

Randomized arm order reduces simple thermal/order bias. Medians are calculated
from retained raw records. `python3 tools/verifyBaseline.py` recomputes the
HTTP/browser medians and verifies every evidence digest.

## Dependency environments with uv

The root `pyproject.toml` divides Python competitors into `parser`, `http`, and
`browser` groups; `uv.lock` fixes the transitive resolution for reruns.

```bash
uv sync --only-group parser
uv sync --only-group http
uv sync --only-group browser
```

Node arms use their quadrant-local `package-lock.json`. Go arms use `go.sum`.
Rust adapters use locked temporary crates and one Cargo build job.

## Reproduction shape

All measured traffic is offline or loopback. Dependency installation is the
only step that may contact a package registry.

Start by creating scratch space outside both repositories:

```bash
benchmarkWork=$(mktemp -d /tmp/yosoi-benchmark.XXXXXX)
python3 tools/verifyBaseline.py
```

For parser runs, generate the deterministic fixtures, build immutable adapter
artifacts into the scratch directory, and invoke `tools/runMatrix.py`. The exact
historic Criterion and report compilers are `tools/runCriterionCampaigns.py`
and `tools/compileExploratoryReport.py`.

For HTTP and rendered runs:

1. install only the applicable uv group;
2. run `npm ci` in the applicable `adapters/*/node-crawlee` directory;
3. build Colly with one Go build worker for HTTP;
4. place the Yosoi release binary and every competitor artifact under the
   scratch directory;
5. start `tools/httpFixtureServer.py`, read its emitted JSON port, and pass that
   loopback base URL to `tools/runHttpMatrix.py` or `tools/runBrowserMatrix.py`;
6. write output beneath scratch space, then seal a new evidence directory by
   byte count and SHA-256.

The runners expose every path, count, and campaign setting through `--help`.
The HTTP Crawlee arm now runs with its adapter directory as its working
directory, so its ignored local storage cannot contaminate Yosoi or the caller's
checkout.

## What Baseline v1 does not prove

- HTTP and rendered Yosoi source revisions were not retained at run time. Their
  surviving binary SHA-256 identities are recorded, but the runs cannot be
  promoted to release evidence retroactively.
- Those Yosoi binaries were local source builds, not published release
  artifacts.
- `uv.lock` defines future reruns; the original HTTP/browser runs recorded
  direct versions but not a complete Python transitive freeze.
- Rendered acquisition used regular Chromium 152, the documented emergency
  rollback artifact, rather than the certified Chrome 153 tuple.
- One workstation cannot establish universal performance, and sampled RSS is
  not an allocator-level measurement.
- The direct Playwright timer begins after browser launch. It is a pooled
  control and optimization clue, not a framework-equivalent winner.

## Closeout decision

The lab has done its job: it froze the taxonomy and correctness rules, ran all
three required quadrants, retained raw losing evidence, exposed browser-pool
potential, and produced concrete optimization targets. Public hero graphs and
“fastest” copy must wait for a separately versioned, release-artifact rerun
after optimization.
