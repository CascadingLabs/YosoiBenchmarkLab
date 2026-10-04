# Measurement contract

Current evidence: [2026-10-04 benchmark results](current-results.md).
The latest run includes the ranked `lol_html` caveman control and retained
resource-stopped browser cells.

## Principle

Measure facts that answer different questions. Do not publish several names for
the same number, and do not infer process, memory, or package facts from a
microbenchmark timer.

Correctness is the admission gate for every performance result. Language,
runtime, backend, and streaming model are identity metadata used to interpret a
result; they are not scores by themselves.

## Required measurements

| Measurement | Exact meaning | Primary report |
| --- | --- | --- |
| Warm latency | Per-operation monotonic wall time in a long-lived process | median, p95, mean, 95% confidence interval, full samples |
| Cold latency | Fresh process start through verified output and clean exit | median, p95, full samples |
| Campaign wall time | Elapsed wall time for one complete benchmark campaign | exact duration; diagnostic, not a substitute for latency |
| Throughput | Verified input work divided by measured wall time | input bytes/s primary; elements/s and records/s when the fixture defines them |
| Peak aggregate RSS | Maximum summed resident bytes across the arm's process tree | bytes plus sampler and interval |
| Mean aggregate RSS | Time-weighted mean of summed process-tree RSS samples | bytes plus sample count and interval |
| P95 aggregate RSS | 95th percentile of process-tree RSS samples | bytes |
| RSS area | Integral of aggregate RSS over wall time | byte-nanoseconds; exposes memory held for a long time |
| CPU time | User and system CPU consumed by the declared process tree | user ns, system ns, and CPU/wall ratio |
| Package footprint | Size of what is distributed and what must exist to run | compressed artifact, installed package, complete runnable environment |
| Output size | Materialized result bytes produced by the frozen operation | bytes |
| Startup/import | Runtime/module initialization before the first callable operation | separate cold measurement where observable |
| Terminal outcome | Exact success, wrong output, unsupported, error, timeout, or resource limit | count and retained diagnostics |

Latency and wall time are related but not duplicate report labels: latency is
the normalized time for the operation users care about, while campaign wall
time tells us how long the entire evidence collection took.

## Package-size boundaries

Report all three; never choose the smallest one after seeing results:

1. `artifactBytes`: compressed wheel, crate/package archive, module archive, or
   release binary as distributed.
2. `installedPackageBytes`: installed product plus its product dependencies,
   excluding caches and benchmark fixtures.
3. `runnableEnvironmentBytes`: everything unique that must be present to run
   the arm, including language runtime and native shared libraries where they
   are not part of the declared base operating system.

Container layers may be reported as an additional deployment fact, but layer
deduplication must not replace the three portable boundaries above.

## Streaming proof

An arm may declare `none`, `incremental`, or `fullBuffer` behavior. A ranked
streaming claim additionally requires:

- exact output parity across multiple input chunk boundaries;
- `timeToFirstOutputNs`;
- `inputBytesBeforeFirstOutput`;
- peak and mean aggregate RSS across increasing input sizes;
- explicit end-of-input and backpressure behavior;
- no hidden full-input buffering in the adapter.

The `lol_html` control is included in the caveman byte-to-value ranking after
passing the same frozen oracle and chunk-boundary checks. Its public
`HtmlRewriter` selector/text handlers do not provide a retained queryable DOM,
so parse-only and pre-parsed-locate columns are unavailable for that arm.
No queryable-DOM equivalence or time-to-first-output result is inferred.

The current Yosoi byte-to-value arm uses default `Document::locate` routing,
which may stream eligible plans over already resident bytes. Its explicit
parse and pre-parsed locate rows remain separate retained-tree operations.
The V1 `streamingMode: fullBuffer` package field describes complete input
delivery, not a claim that every operation constructs a DOM. This suite has
no incremental-input or time-to-first-output evidence.

## Scaling curve

The comparative parser suite measures the caveman and hard sizes; V2 measures
32, 64, and 4,096 records separately per semantic cell. The following four-point
scaling curve is a desired extension, not evidence already collected by those suites.

Run the same semantic task over at least four frozen size classes: approximately 88 KiB caveman,
approximately 1 MiB, approximately 8 MiB, and the 12–24 MiB hard catalog. Report
latency and RSS at every point rather than only a single throughput number.

The analysis records the observed latency/byte and RSS/byte curve. It does not
claim an asymptotic complexity class from four empirical points.

## Secondary diagnostics

Collect when the runtime supports them without changing the primary operation:

- allocation count, total allocated bytes, and maximum live allocated bytes;
- hardware instructions, cycles, cache misses, and branch misses;
- query/plan construction time;
- dependency count and installation/build time;
- binary sections or dependency-level size attribution.

These diagnostics remain separately named and are not required for cross-arm
ranking because instrumentation support differs by language and runtime.

## Five-campaign protocol

`K = 5` means five independent benchmark campaigns, not machine-learning
cross-validation:

1. Start each campaign from a fresh arm process.
2. Run a correctness preflight before measurement.
3. Use a recorded, seeded arm order per campaign so thermal and background
   drift are not perfectly correlated with product identity.
4. For the Rust warm phases, run Criterion inside each campaign with the frozen
   configuration in the benchmark specification.
5. For non-Rust warm phases, use an equivalent in-process monotonic timer and
   sampling contract; do not benchmark another language by spawning it inside a
   Criterion iteration.
6. Measure cold process, process-tree RSS, CPU, package size, and streaming in
   their own runs.
7. Retain Criterion/native raw samples and every campaign summary.

Report each campaign independently. The headline warm result is the median of
the five campaign medians, accompanied by the full campaign range. Criterion's
within-campaign confidence interval remains visible; it is not treated as an
across-day or across-machine confidence interval.

## Criterion boundary

Criterion is the reference Rust warm-microbenchmark harness. It measures
`parse`, `locate`, and `endToEnd` for the Rust arm. It does not measure:

- package or installed size;
- cold process startup;
- peak or mean process-tree RSS;
- CPU time for an external process tree;
- streaming time-to-first-output;
- another language through subprocess startup.

Those boundaries use the common black-box result protocol so the final report
can compare like with like without pretending one tool measured everything.
