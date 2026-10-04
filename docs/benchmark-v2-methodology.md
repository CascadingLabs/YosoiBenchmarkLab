# Benchmark Lab V2 methodology

Current evidence: [2026-10-04 benchmark results](current-results.md).
The latest run includes the ranked `lol_html` caveman control and retained
resource-stopped browser cells.

## Plain English

V2 answers “which internal document or extraction path is expensive?” It does
not answer “which product is fastest?” Every result stays inside its own
document/query/projection cell, and external packages are lower-level controls
only when their semantics genuinely match.

## Coverage

The frozen catalog contains 36 timed cells across:

- source HTML, XML, JSON, decoded text, rendered DOM, and accessibility trees;
- CSS, XPath, tree-text, JSON Pointer, bounded JSONPath, literal text, regex,
  accessibility role/name/text/state queries;
- descendant text, attribute, node-reference, native JSON, matched-text,
  capture, accessible-name, and accessibility-text projections;
- parse, locate on a pre-parsed document, and end-to-end phases;
- tiny (32 records), medium (64), and large (4,096) deterministic fixtures.

The typed extraction lane separately measures cached Contract plan access,
Contract location, candidate assembly, candidate-plus-validation,
validation-plus-strict-record materialization, and complete bytes-to-record
execution.

Repeated Contract timing stops at the ordinary 64-region default. The 4,096
record HTML, XML, and rendered-DOM lanes are retained as expected
resource-bounded outcomes instead of weakening the product limit for a graph.

## Controls

Controls are deliberately small public packages rather than hosted products:

- Rust `scraper` for HTML parsing and CSS-shaped selection;
- Rust `regex` for decoded-text regex and capture work;
- `serde_json` for JSON parsing and Pointer/manual-equivalent path access;
- `roxmltree` for strict XML parsing and equivalent semantic traversal.

`exact` means the control executes the same semantic operation and returns the
same normalized value. `nearestPrimitive` means it is a useful lower bound but
does less query-language, provenance, or product work. Rendered DOM,
accessibility, and typed Contracts are `internalOnly`; V2 does not invent a fake
competitor.

## Correctness before timing

Every timed record must return the exact frozen terminal state, match count,
and scalar projected values. Node references retain deterministic per-arm
identity but are not equated across unrelated tree representations.

The separate conformance suite covers no-match, multi-match, invalid-query, and
match-limit behavior for every document class. The negative fixture suite
covers recoverable malformed HTML and rejected malformed XML, JSON, decoded
text, rendered DOM, and accessibility inputs.

## Sampling and resources

- five fresh-process campaigns per arm/cell/size/phase;
- five warm samples per campaign;
- one operation per sample;
- seeded arm order;
- no outlier deletion;
- one arm process at a time;
- internal monotonic samples plus outer process wall time;
- process-tree peak, mean, and p95 RSS sampled every 5 ms;
- child user and system CPU time;
- full raw distributions and deterministic output digests.

These are internal diagnostics, so no confidence interval or ratio is promoted
to a release KPI. The frozen medians exist to find and prevent regressions.
Allocation instrumentation is not available in Baseline v2; CPU and sampled
process-tree RSS remain separate evidence and are not described as allocations.

## Artifact boundary

Yosoi is compiled into a temporary immutable binary from one exact clean source
revision. The lab stores the source revision, binary SHA-256, binary bytes, and
generated Cargo lock digest. Competitor code and dependencies remain in the
Benchmark Lab; Yosoi's checkout remains unchanged.

## Reproduction shape

All benchmark inputs are generated offline and all timed work is local. Only
initial dependency resolution may contact package registries.

```bash
diagnosticWork=$(mktemp -d "$PWD/../.yosoi-v2.XXXXXX")
python3 tools/generateV2Fixtures.py \
  --output "$diagnosticWork/fixtures" \
  --spec specs/diagnostics-v2.json

CARGO_BUILD_JOBS=1 python3 tools/buildV2Controls.py \
  --work "$diagnosticWork/build" \
  --output "$diagnosticWork/artifacts"

CARGO_BUILD_JOBS=1 python3 tools/buildCurrentYosoi.py \
  --yosoi-repository /path/to/Yosoi \
  --revision @ --arms v2 \
  --work "$diagnosticWork/build" \
  --output "$diagnosticWork/artifacts" --offline
```

Run `tools/runV2Matrix.py`, `tools/runV2Extraction.py`,
`tools/runV2Conformance.py`, and `tools/runV2Negative.py` serially. Then use
`tools/compileV2Report.py` to seal the evidence and `tools/verifyV2.py` to
recompute coverage, correctness, summaries, and hashes offline.

## Interpretation boundary

V2 does not change the Baseline v1 KPI scoreboard. Any product optimization
suggested by V2 belongs to Yosoi Optimization. A specific V2 cell can become a
future public claim only through a separate explicit decision and
release-artifact rerun.
