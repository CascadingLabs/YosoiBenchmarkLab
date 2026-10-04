# Benchmark Lab V2 — format and extraction diagnostics

## Decision

V2 is a complete internal diagnostic map for the frozen cells, not a public
leaderboard. It measures 36 cells across
6 document classes, 11
query families, three input sizes, query-build/parse/locate/end-to-end phases,
and the typed Contract pipeline.
There is deliberately no cross-format aggregate score.

All 30 no-match, multi-match, invalid-query, and
resource-limit conformance cases passed. All 8
malformed/recovery fixtures produced their frozen terminal states.
All 3 large repeated-Contract cases stopped at
the ordinary resource boundary and were retained as bounded outcomes.

Yosoi artifact source revision: `2d9269fe045149b2b2289dc4d3d47a354a92c8b4`; SHA-256
`ce15e7204c0c1df7bcabd1530266f4133320370fdd72e10a53db6763c91c1b9d`. Rust control artifact SHA-256
`9c1f9bb6e16c6bd4d6965a3d1a45a607bceaaf19a89a354449527ae008867c48`.

## Large-input end-to-end diagnostics

Control rows are exact only where the `Equivalence` column says `exact`.
`nearestPrimitive` is an attributed lower-level control, not a product winner.

| Cell | Document | Query | Projection | Yosoi | Control | Ratio | Equivalence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| html.css.text | sourceHtml | css | text | 1.080 ms | rustScraper 15.910 ms | 0.07× control time | exact |
| html.css.attribute | sourceHtml | css | attribute:data-id | 1.174 ms | rustScraper 15.778 ms | 0.07× control time | exact |
| html.css.node | sourceHtml | css | node | 1.516 ms | rustScraper 14.446 ms | 0.10× control time | nearestPrimitive |
| html.xpath.text | sourceHtml | xpath | text | 1.539 ms | rustScraper 17.837 ms | 0.09× control time | nearestPrimitive |
| html.xpath.attribute | sourceHtml | xpath | attribute:data-id | 1.438 ms | rustScraper 15.539 ms | 0.09× control time | nearestPrimitive |
| html.xpath.node | sourceHtml | xpath | node | 1.416 ms | rustScraper 14.953 ms | 0.09× control time | nearestPrimitive |
| html.treeText.text | sourceHtml | treeText | text | 2.412 ms | rustScraper 16.298 ms | 0.15× control time | nearestPrimitive |
| html.treeText.node | sourceHtml | treeText | node | 1.736 ms | rustScraper 14.346 ms | 0.12× control time | nearestPrimitive |
| xml.css.text | sourceXml | css | text | 2.608 ms | roxmltree 1.634 ms | 1.60× control time | exact |
| xml.css.attribute | sourceXml | css | attribute:data-id | 2.408 ms | roxmltree 2.170 ms | 1.11× control time | nearestPrimitive |
| xml.css.node | sourceXml | css | node | 2.641 ms | roxmltree 2.532 ms | 1.04× control time | nearestPrimitive |
| xml.xpath.text | sourceXml | xpath | text | 1.705 ms | roxmltree 2.302 ms | 0.74× control time | nearestPrimitive |
| xml.xpath.attribute | sourceXml | xpath | attribute:data-id | 2.825 ms | roxmltree 2.310 ms | 1.22× control time | nearestPrimitive |
| xml.xpath.node | sourceXml | xpath | node | 2.656 ms | roxmltree 1.753 ms | 1.51× control time | nearestPrimitive |
| xml.treeText.text | sourceXml | treeText | text | 2.807 ms | roxmltree 1.536 ms | 1.83× control time | nearestPrimitive |
| xml.treeText.node | sourceXml | treeText | node | 5.225 ms | roxmltree 1.659 ms | 3.15× control time | nearestPrimitive |
| json.pointer.value | sourceJson | jsonPointer | value | 1.834 ms | serdeJson 1.566 ms | 1.17× control time | exact |
| json.path.value | sourceJson | jsonPath | value | 1.860 ms | serdeJson 3.061 ms | 0.61× control time | nearestPrimitive |
| text.literal.text | sourceText | textLiteral | text | 0.016 ms | stdString 0.029 ms | 0.56× control time | exact |
| text.regex.text | sourceText | regex | text | 0.019 ms | rustRegex 0.030 ms | 0.62× control time | exact |
| text.regex.captures | sourceText | regex | captures:id | 0.019 ms | rustRegex 0.055 ms | 0.35× control time | exact |
| dom.css.text | renderedDom | css | text | 18.242 ms | internal only | — | internalOnly |
| dom.css.attribute | renderedDom | css | attribute:data-id | 17.411 ms | internal only | — | internalOnly |
| dom.css.node | renderedDom | css | node | 18.419 ms | internal only | — | internalOnly |
| dom.xpath.text | renderedDom | xpath | text | 18.968 ms | internal only | — | internalOnly |
| dom.xpath.attribute | renderedDom | xpath | attribute:data-id | 18.305 ms | internal only | — | internalOnly |
| dom.xpath.node | renderedDom | xpath | node | 18.400 ms | internal only | — | internalOnly |
| dom.treeText.text | renderedDom | treeText | text | 18.778 ms | internal only | — | internalOnly |
| dom.treeText.node | renderedDom | treeText | node | 18.726 ms | internal only | — | internalOnly |
| ax.role.name | accessibilityTree | role | accessibleName | 2.425 ms | internal only | — | internalOnly |
| ax.role.node | accessibilityTree | role | node | 2.590 ms | internal only | — | internalOnly |
| ax.name.node | accessibilityTree | accessibleName | node | 2.083 ms | internal only | — | internalOnly |
| ax.name.name | accessibilityTree | accessibleName | accessibleName | 2.035 ms | internal only | — | internalOnly |
| ax.text.text | accessibilityTree | accessibilityText | accessibilityText | 3.142 ms | internal only | — | internalOnly |
| ax.text.node | accessibilityTree | accessibilityText | node | 3.016 ms | internal only | — | internalOnly |
| ax.state.node | accessibilityTree | stateExpanded | node | 3.032 ms | internal only | — | internalOnly |

## Typed Contract extraction — largest admitted repeated catalog

Every Yosoi phase retains ordinary provenance and validation semantics. The
control row materializes and validates equivalent plain Rust records but does
not retain Yosoi evidence, diagnostics, or typed Contract outcomes.

| Phase | Median ms | Median peak RSS MiB |
| --- | --- | --- |
| planCached | 0.000 | 0.0 |
| locate | 1.682 | 5.6 |
| extract | 0.204 | 0.0 |
| extractValidate | 0.215 | 0.0 |
| extractValidateRequireAll | 0.212 | 0.0 |
| endToEnd | 1.727 | 6.0 |
| endToEnd nearest primitive | 0.419 | 0.0 |

## Extraction compatibility across document classes

These lanes prove that XML, decoded text, rendered DOM, accessibility, and the
typed JSON-rejection path all reach the ordinary Extractor/Contract machinery.

| Lane | Document | Phase | Outcome | Size | Median ms |
| --- | --- | --- | --- | --- | --- |
| contracts.xml.products | sourceXml | endToEnd | fixtureRecordCount | medium | 0.604 |
| contracts.text.summary | sourceText | endToEnd | oneRecord | large | 0.012 |
| contracts.dom.products | renderedDom | endToEnd | fixtureRecordCount | medium | 0.688 |
| contracts.ax.summary | accessibilityTree | endToEnd | oneRecord | large | 2.066 |
| contracts.json.rejection | sourceJson | endToEndRejected | oneValidationIssue | large | 3.792 |

## Interpretation rules

- These results are internal optimization/regression evidence and are not KPI
  gates or marketing claims.
- CSS, XPath, regex, JSON Pointer, JSONPath, XML, rendered DOM, accessibility,
  and typed Contract rows remain separate semantic cells.
- `internalOnly` means no honest external semantic peer was invented.
- Node-reference correctness is exact within each arm and deterministic across
  campaigns; cross-library node identities are not equated.
- Warm parse/locate/end-to-end samples, outer fresh-process wall, CPU, and
  aggregate RSS remain separately named.
- The Yosoi binary was built from a hashed immutable local source archive, not
  a published release artifact. That is acceptable for this internal diagnostic
  baseline and insufficient for release certification.
- Allocation counts were not collected. CPU, sampled process-tree RSS, and
  output bytes are retained, but they do not substitute for allocator evidence.

## Reproduction and evidence

The `raw/` directory contains the frozen spec, fixture manifest, every campaign
record, independent summaries, conformance and negative results, and both
artifact identities. `coverage.json` proves cell coverage. The evidence manifest
hashes every retained file.
