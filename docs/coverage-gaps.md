# Baseline v1 coverage gaps and Benchmark Lab V2

Current evidence: [2026-10-04 benchmark results](current-results.md).
The latest run includes the ranked `lol_html` caveman control and retained
resource-stopped browser cells.

Baseline v1 is a useful HTML/CSS-shaped optimization baseline. It is not a
general benchmark of every document, query, projection, or extraction path in
Yosoi.

## What Baseline v1 actually covers

| Capability | V1 state | Exact boundary |
| --- | --- | --- |
| Source HTML parsing | Measured | Two generated catalogs, warm/cold phases, full-buffered DOM |
| CSS-shaped tree location | Measured narrowly | One neutral product-price task compiled to ordinary native operations |
| XPath | Not independently measured | Raw lxml uses XPath for the neutral task; that is not a CSS-vs-XPath lane |
| Decoded-text literal search | Not measured | No plain-text fixture or result table |
| Regex and capture extraction | Not measured | Regex dependencies or JSONL output do not constitute a regex benchmark |
| JSON parsing/query | Not measured | JSON is only the evidence envelope in V1 |
| XML parsing/query | Not measured | The lxml arm runs in HTML recovery mode, not XML mode |
| Rendered DOM location | Measured narrowly | One CSS text projection after browser acquisition |
| Accessibility-tree extraction | Not measured | No immutable AX-tree lane |
| Streaming evaluation | Specified only | No ranked `lol_html` or time-to-first-output evidence |
| Typed Contracts/Extractor | Not measured | V1 stops at projected locator values |
| HTTP edge behavior | Tested, not timed as a matrix | Redirect, gzip, Latin-1, and error fixtures have correctness tests; timed runs use ordinary HTML pages |

The source-HTML fixture includes useful scale, Unicode, distractors, table
repair pressure, SVG islands, and bounded malformed fragments. It does not
prove complete HTML recovery conformance or broad selector-feature performance.

That table describes the historical September baseline. The current caveman
rerun also ranks `lol_html` for the exact byte-to-value task, with 1-byte,
7-byte, and 64 KiB chunk-boundary correctness checks. This adds a streaming
execution control; it does not add incremental-input memory scaling or
time-to-first-output measurements.

## Why these do not become one graph

Document format, query language, projection, and extraction layer are separate
axes. Regex over serialized JSON is not a faster JSON query. HTML recovery and
strict XML parsing do not have the same correctness contract. CSS and XPath
have different expressive power. Accessibility-tree text is not DOM text.

V2 therefore reports independent semantic cells. Correctness gates each cell,
but there is no cross-format aggregate score and no new public KPI.

## Required V2 surface

### Document classes

- source HTML;
- XML;
- JSON;
- decoded text;
- rendered DOM;
- accessibility tree.

### Query families

- CSS, XPath, and tree-text queries for compatible tree documents;
- JSON Pointer and bounded JSONPath;
- literal text and regex, including named captures;
- accessibility role, name, text, and state.

### Projections

- descendant text;
- attribute;
- node reference;
- native JSON value;
- matched text and matched text with captures;
- accessible name and accessibility text.

### Extraction layers

V2 attributes the cost of each public layer instead of assigning all overhead
to parsing:

1. document parsing;
2. locating on a parsed document;
3. `Document::locate` convenience;
4. Contract plan construction and cached reuse;
5. Contract location;
6. Extractor candidate grouping and evidence retention;
7. runtime cardinality and semantic validation;
8. typed derive output and strict `require_all`;
9. full bytes-to-record end-to-end extraction.

## V2 implementation and Linear ownership

[Benchmark Lab V2 — Format & Extraction Diagnostics](https://linear.app/cascadinglabs/project/yosoi-benchmark-lab-v2-format-and-extraction-diagnostics-44118b3a45cb)
owns the implemented internal diagnostic baseline under Oxidation. The sealed
The [historical V2 evidence](../evidence/2026-09-27-diagnostics-v2/README.md) covers every
frozen compatible cell and remains separate from headline KPI gates.

- CAS-476 freezes the semantic cells and non-KPI protocol.
- CAS-477 covers source HTML and rendered DOM with CSS, XPath, tree text, and projections.
- CAS-478 covers decoded-text literal and regex/capture extraction.
- CAS-479 covers JSON parsing, JSON Pointer, JSONPath, and native values.
- CAS-480 covers strict XML, CSS/XPath, namespaces, and security boundaries.
- CAS-481 covers accessibility role, name, text, and state extraction.
- CAS-482 measures every layer from parsed document through typed Contract output.
- CAS-483 seals and independently verifies the V2 diagnostic bundle.

Product optimizations found by these cells belong in Yosoi Optimization or a
later owning project. Baseline v1 remains immutable historical evidence.
