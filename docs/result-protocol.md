# Arm result protocol

Current evidence: [2026-10-04 benchmark results](current-results.md).
The latest run includes the ranked `lol_html` caveman control and retained
resource-stopped browser cells.

## Boundary

An arm is a black-box executable inside its own locked environment. The lab
provides a benchmark specification and immutable input paths. The arm writes
newline-delimited JSON records conforming to `schemas/arm-result.schema.json`.

No arm imports another arm. The orchestrator never imports competitor packages.

The comparative V1 runners currently retain adapter-specific JSON records in
their quadrant schemas; V2 uses its separate diagnostic result envelope. The
record classes below define the measurement contract, rather than claiming
that every existing adapter emits the same wire schema. See the exact native
records and verifier for each sealed evidence bundle.

## Required record classes

- `identity`: product, release/source revision, runtime, lock/container digest,
  adapter revision, platform, and declared backend.
- `correctness`: task, terminal status, match count, ordered-output digest, and
  bounded diagnostics.
- `sample`: task, phase, sample index, operations, wall nanoseconds, optional
  CPU nanoseconds, throughput inputs, and output checksum.
- `resource`: task, phase, aggregate peak/mean/p95 RSS, RSS area, process count,
  CPU time, and collection method.
- `identity`: also records language, runtime, backend, artifact/package/runnable
  environment sizes, and streaming mode.
- `summary`: planned and observed sample counts plus terminal completeness.

## Terminal statuses

- `ok`: exact output and lifecycle completed.
- `wrongOutput`: process succeeded but the oracle did not match.
- `unsupported`: the ordinary public API cannot express the frozen task.
- `error`: typed product or adapter error.
- `timeout`: the bounded operation did not finish.
- `resourceLimit`: the arm crossed a declared limit and was stopped.

Only `ok` correctness records admit timing samples to a ranking.

Every sample and resource record belongs to a numbered campaign. The required
parser protocol uses five independent campaigns. Raw within-campaign samples
must remain recoverable; a precomputed summary alone is insufficient evidence.

## Redaction

Parser fixtures contain no secrets or network targets. Later quadrants must not
place credentials, full environments, identifying host paths, or unrelated
process command lines in publishable results.

## Result identity

A sealed bundle identity covers the benchmark spec digest, fixture manifest and
input digests, arm identity records, raw records, exact commands, environment
manifest, and analysis version. A chart without that identity is illustrative,
not benchmark evidence.
