# Parser and selector methodology

Current evidence: [2026-10-04 benchmark results](current-results.md).
The latest run includes the ranked `lol_html` caveman control and retained
resource-stopped browser cells.

## Decision

The public parser story has one deliberately simple caveman benchmark backed by
a harder offline suite. The caveman number is memorable; the hard suite prevents
it from rewarding a parser that only succeeds on one tiny, friendly document.

No timing is rankable until the arm produces the exact frozen output.

## Neutral operation model

The benchmark does not force every library to accept one raw CSS or XPath
string. Instead, a task uses a small typed locator vocabulary:

- descend to an element with a specified HTML local name;
- require an attribute token, such as a class token;
- require an exact attribute value;
- preserve document order;
- project exact attribute value or normalized descendant text;
- return the first match or all matches as declared by the task.

Each adapter compiles that contract into the narrowest ordinary native public
operation. The adapter records its effective query and any unsupported
semantics. Hand-written shortcuts, precomputed offsets, fixture-specific scans,
and parser internals unavailable to normal callers are prohibited.

## Workload 1: caveman

Identifier: `parser.caveman.product-price.v1`.

Purpose: answer the five-second question, “How quickly does this tool turn HTML
bytes into the correct value?”

Contract:

- input: deterministic UTF-8 HTML catalog bytes, already resident in memory;
- size class: approximately 88 KiB after canonical generation;
- document: 128 product cards with repeated distractor structure;
- target: one product identified by exact SKU;
- projection: normalized descendant text from its price field;
- expected result: exactly one value, `USD 19.73`;
- locator plan/query construction: outside timing;
- timed end-to-end operation: parse input, evaluate locator, materialize the
  ordered value list;
- file I/O, process startup, fixture verification, and result comparison:
  outside the warm end-to-end timer;
- public Yosoi arm: pure Rust through the public Rust surface or a tiny release
  binary, never Python or Node bindings.

Separate rows report parse-only, locate-only on a pre-parsed document,
end-to-end, and cold process startup. Only end-to-end is eligible for the hero
chart.

Yosoi's end-to-end adapter uses ordinary `Document::locate`, including its
default routing for eligible plans. Explicit `Document::parse` and
`ParsedDocument::locate` measure the retained-tree path separately. Default
location can use a streaming evaluator on resident input, so end-to-end may
be faster than the explicit full-tree parse phase. Report that boundary;
do not add the phase timings or describe default byte-to-value latency as
universal full-DOM parsing speed. Standalone streaming controls still need
their own equivalent public-operation adapter and correctness proof.

## Workload 2: hard catalog

Identifier: `parser.hard.catalog.v1`.

Purpose: resist tiny-input specialization and expose scaling, recovery,
allocation, traversal, ordering, and output-materialization behavior.

Canonical generator contract:

- deterministic seed `0x594f534f49` (`YOSOI`);
- 25,000 product records in document order;
- at least 250,000 total HTML elements;
- generated size target between 12 MiB and 24 MiB, never above 32 MiB;
- repeated class and attribute distractors;
- UTF-8 text spanning ASCII, combining marks, non-Latin scripts, and emoji;
- tables with implied containers, optional end tags, comments, script/style
  text, character references, and bounded malformed fragments;
- HTML-namespace SVG islands and adjusted-name cases;
- 64 target records selected from the fixed seed;
- exact ordered projections for IDs, names, prices, and availability;
- an oracle manifest containing input digest, byte count, expected match count,
  and ordered-output digest.

Hard-catalog results are not compressed into the hero graph. They report
correctness, latency distribution, scaling per input byte and element, CPU,
peak/mean/p95 aggregate RSS, RSS area, and output size.

## Workload 3: publisher reproduction

Identifier: `parser.publisher.scrapling-nested.v1`.

The pinned Scrapling 5,000-nested-element benchmark is executed unchanged in
its own environment and retained as publisher-exact evidence. A separate
semantic-parity task may place Yosoi beside it only after output meaning and
timed boundaries are made identical. Publisher-exact and corrected results are
never merged.

## Workload 4: deep and malformed stress

Identifier: `parser.hard.recovery.v1`.

This bounded negative suite contains deep nesting, misnested formatting
elements, incomplete tables, duplicate attributes, invalid-but-decodable byte
sequences after the declared decoding step, and namespace edges. It is primarily
a correctness and termination gate. A tool that rejects a case may report
`unsupported` if rejection is its documented behavior; it may not report a fast
successful parse.

## Measurement phases

Every arm reports these phases independently when supported:

1. `parse`: resident bytes to the tool's ordinary parsed representation.
2. `locate`: pre-parsed representation plus prebuilt query to ordered matches.
3. `endToEnd`: resident bytes to materialized ordered values.
4. `coldProcess`: fresh process invocation, parse, locate, output, clean exit.
5. `resource`: CPU and aggregate RSS for a declared operation count.

Allocation or instruction evidence is optional and language/tool specific. It
must never be inferred from timing or RSS.

## Sampling contract

- Run one arm and one measurement class at a time.
- Run five independent campaigns from fresh arm processes. This is `K = 5`
  repeated evidence, not machine-learning cross-validation.
- Run a correctness preflight before every campaign.
- Use a recorded seeded arm order per campaign.
- For Rust warm phases, use Criterion with the frozen configuration in the
  machine-readable specification. Do not use Criterion to time subprocess calls
  into other languages.
- For other languages, use an equivalent in-process monotonic timer and emit the
  same raw sample envelope.
- Caveman campaigns target 100 samples; hard-suite campaigns target 30 samples.
- If calibration changes operations per sample, freeze and record that count
  before the comparative run and normalize only within that named phase.
- Retain every raw sample. Report median, p95, minimum, maximum, arithmetic
  mean, standard deviation, 95% confidence interval where the harness supports
  it, and the full distribution.
- Report all five campaign summaries. The headline warm result is the median of
  the five campaign medians plus the full campaign range.
- Do not remove outliers after seeing product identity or results.
- Record CPU model, topology, installed and available memory, swap state,
  kernel/OS, runtime/toolchain, power/frequency facts when available, and exact
  commands.

The complete required and secondary metric definitions live in
`docs/metrics.md`.

## Correctness gate

Before timing, the arm must return:

- the exact terminal status;
- the exact ordered UTF-8 values;
- the exact match count;
- the expected output digest;
- no extra values;
- no mutation of the input fixture.

Each measured sample rechecks a bounded checksum/count assertion outside the
timer. A mismatch invalidates the workload's timing bundle for that arm but
remains a published failure.

## Fairness rules

- Use ordinary documented public APIs.
- Name every backend and meaningful parser option.
- Preserve product defaults in one named lane; common tuned settings, if any,
  are a separate lane.
- Prebuild the neutral locator for all arms; do not include query parsing for
  only some arms in the warm locate or end-to-end phase.
- Do not compare a streaming scan with a queryable DOM without a separate,
  explicitly equivalent streaming task.
- Do not make Yosoi drop provenance, validation, or output semantics solely to
  win a primitive comparison. If a nearest-primitive control is useful, name it
  separately from the public Yosoi result.
- Publish losses and unsupported cases.

## Implementation sequence

1. Review and freeze `specs/parser-selector-v1.json`.
2. Implement the deterministic fixture generator and oracle verifier.
3. Implement fake success, wrong-output, unsupported, timeout, and oversize
   arms against the result protocol.
4. Add the pure-Rust Yosoi arm.
5. Add competitors one isolated arm at a time.

The current lab includes real parser adapters, shared correctness/resource
runners, Criterion confirmation, and retained evidence. The complete rerun
commands and frozen-source build procedure are in [Rerun the complete lab](rerunning.md).
