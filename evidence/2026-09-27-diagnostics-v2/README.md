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

Yosoi artifact source revision: `d9b64106568b02e4960988ac5f18887301c576c4`; SHA-256
`a2f39747f6ec26c7849a7f0f52338218d399521b31324dca57be325abd8079f7`. Rust control artifact SHA-256
`1dc1a3e97902e23744648378d47bfeafe07899a1dc4c9bc66a95a384bf14c566`.

## Large-input end-to-end diagnostics

Control rows are exact only where the `Equivalence` column says `exact`.
`nearestPrimitive` is an attributed lower-level control, not a product winner.

| Cell | Document | Query | Projection | Yosoi | Control | Ratio | Equivalence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| html.css.text | sourceHtml | css | text | 26.683 ms | rustScraper 17.123 ms | 1.56× control time | exact |
| html.css.attribute | sourceHtml | css | attribute:data-id | 31.887 ms | rustScraper 15.676 ms | 2.03× control time | exact |
| html.css.node | sourceHtml | css | node | 21.953 ms | rustScraper 15.229 ms | 1.44× control time | nearestPrimitive |
| html.xpath.text | sourceHtml | xpath | text | 23.576 ms | rustScraper 16.464 ms | 1.43× control time | nearestPrimitive |
| html.xpath.attribute | sourceHtml | xpath | attribute:data-id | 22.927 ms | rustScraper 15.712 ms | 1.46× control time | nearestPrimitive |
| html.xpath.node | sourceHtml | xpath | node | 21.239 ms | rustScraper 14.449 ms | 1.47× control time | nearestPrimitive |
| html.treeText.text | sourceHtml | treeText | text | 20.133 ms | rustScraper 15.625 ms | 1.29× control time | nearestPrimitive |
| html.treeText.node | sourceHtml | treeText | node | 20.017 ms | rustScraper 17.174 ms | 1.17× control time | nearestPrimitive |
| xml.css.text | sourceXml | css | text | 2.788 ms | roxmltree 2.210 ms | 1.26× control time | exact |
| xml.css.attribute | sourceXml | css | attribute:data-id | 1.838 ms | roxmltree 2.188 ms | 0.84× control time | nearestPrimitive |
| xml.css.node | sourceXml | css | node | 1.914 ms | roxmltree 2.225 ms | 0.86× control time | nearestPrimitive |
| xml.xpath.text | sourceXml | xpath | text | 2.246 ms | roxmltree 2.263 ms | 0.99× control time | nearestPrimitive |
| xml.xpath.attribute | sourceXml | xpath | attribute:data-id | 2.288 ms | roxmltree 1.518 ms | 1.51× control time | nearestPrimitive |
| xml.xpath.node | sourceXml | xpath | node | 1.726 ms | roxmltree 2.169 ms | 0.80× control time | nearestPrimitive |
| xml.treeText.text | sourceXml | treeText | text | 2.523 ms | roxmltree 2.256 ms | 1.12× control time | nearestPrimitive |
| xml.treeText.node | sourceXml | treeText | node | 3.890 ms | roxmltree 2.293 ms | 1.70× control time | nearestPrimitive |
| json.pointer.value | sourceJson | jsonPointer | value | 2.195 ms | serdeJson 2.408 ms | 0.91× control time | exact |
| json.path.value | sourceJson | jsonPath | value | 2.668 ms | serdeJson 1.749 ms | 1.53× control time | nearestPrimitive |
| text.literal.text | sourceText | textLiteral | text | 0.020 ms | stdString 0.023 ms | 0.86× control time | exact |
| text.regex.text | sourceText | regex | text | 0.027 ms | rustRegex 0.027 ms | 1.02× control time | exact |
| text.regex.captures | sourceText | regex | captures:id | 0.058 ms | rustRegex 0.056 ms | 1.04× control time | exact |
| dom.css.text | renderedDom | css | text | 19.218 ms | internal only | — | internalOnly |
| dom.css.attribute | renderedDom | css | attribute:data-id | 18.460 ms | internal only | — | internalOnly |
| dom.css.node | renderedDom | css | node | 18.070 ms | internal only | — | internalOnly |
| dom.xpath.text | renderedDom | xpath | text | 18.926 ms | internal only | — | internalOnly |
| dom.xpath.attribute | renderedDom | xpath | attribute:data-id | 19.379 ms | internal only | — | internalOnly |
| dom.xpath.node | renderedDom | xpath | node | 19.683 ms | internal only | — | internalOnly |
| dom.treeText.text | renderedDom | treeText | text | 18.633 ms | internal only | — | internalOnly |
| dom.treeText.node | renderedDom | treeText | node | 18.664 ms | internal only | — | internalOnly |
| ax.role.name | accessibilityTree | role | accessibleName | 2.452 ms | internal only | — | internalOnly |
| ax.role.node | accessibilityTree | role | node | 3.371 ms | internal only | — | internalOnly |
| ax.name.node | accessibilityTree | accessibleName | node | 2.257 ms | internal only | — | internalOnly |
| ax.name.name | accessibilityTree | accessibleName | accessibleName | 2.228 ms | internal only | — | internalOnly |
| ax.text.text | accessibilityTree | accessibilityText | accessibilityText | 3.247 ms | internal only | — | internalOnly |
| ax.text.node | accessibilityTree | accessibilityText | node | 2.210 ms | internal only | — | internalOnly |
| ax.state.node | accessibilityTree | stateExpanded | node | 2.601 ms | internal only | — | internalOnly |

## Typed Contract extraction — largest admitted repeated catalog

Every Yosoi phase retains ordinary provenance and validation semantics. The
control row materializes and validates equivalent plain Rust records but does
not retain Yosoi evidence, diagnostics, or typed Contract outcomes.

| Phase | Median ms | Median peak RSS MiB |
| --- | --- | --- |
| planCached | 0.000 | 0.6 |
| locate | 1.402 | 5.6 |
| extract | 0.300 | 5.4 |
| extractValidate | 0.198 | 5.4 |
| extractValidateRequireAll | 0.323 | 5.5 |
| endToEnd | 1.572 | 5.7 |
| endToEnd nearest primitive | 0.315 | 0.5 |

## Extraction compatibility across document classes

These lanes prove that XML, decoded text, rendered DOM, accessibility, and the
typed JSON-rejection path all reach the ordinary Extractor/Contract machinery.

| Lane | Document | Phase | Outcome | Size | Median ms |
| --- | --- | --- | --- | --- | --- |
| contracts.xml.products | sourceXml | endToEnd | fixtureRecordCount | medium | 0.860 |
| contracts.text.summary | sourceText | endToEnd | oneRecord | large | 0.029 |
| contracts.dom.products | renderedDom | endToEnd | fixtureRecordCount | medium | 0.967 |
| contracts.ax.summary | accessibilityTree | endToEnd | oneRecord | large | 4.447 |
| contracts.json.rejection | sourceJson | endToEndRejected | oneValidationIssue | large | 1.971 |

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
