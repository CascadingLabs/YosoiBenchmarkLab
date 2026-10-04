# Exploratory parser and selector benchmark — 2026-10-04

## Decision

The lowest retained end-to-end medians are **yosoiRust** on caveman and **yosoiRust** on the repeated hard-catalog campaign. The tables below retain every admitted arm; these results apply to this source snapshot and host.

These are local exploratory results, not a public “fastest” claim.

## Inputs and correctness

cavemanCatalog 87,928 bytes SHA-256 `3a189573c0ab36b7e77b67a1a5b2a849133969c472067e16fae3f5c10ffcd4ef`, hardCatalog 17,186,672 bytes SHA-256 `139ee57c396ae07c3910295e705fcacb79b08b6a8faf74813e443e494bb6a163`.

All 10 caveman arms returned the exact ordered value before timing. The hard suite separately gated its nine admitted arms against all 64 exact ordered values. No incorrect arm was ranked.

## Caveman warm timings — five campaigns

Each arm ran five fresh-process campaigns, 100 samples per campaign, 10 operations per sample. Values are the median of campaign medians; p95 is retained across the raw native samples.

| Arm | Parse ms | Locate ms | End-to-end ms | P95 ms | Input MB/s |
| --- | --- | --- | --- | --- | --- |
| yosoiRust | 0.839 | 0.069 | 0.072 | 0.106 | 1221.07 |
| lolHtml | — | — | 0.170 | 0.300 | 517.87 |
| parsel | 0.508 | 0.067 | 0.650 | 0.691 | 135.34 |
| scraplingParser | 0.509 | 0.070 | 0.670 | 0.701 | 131.33 |
| lxml | 0.604 | 0.074 | 0.678 | 0.710 | 129.62 |
| selectolaxLexbor | 0.789 | 0.049 | 0.789 | 0.832 | 111.43 |
| rustScraper | 0.787 | 0.025 | 0.837 | 0.948 | 105.03 |
| goquery | 1.062 | 0.048 | 1.123 | 1.505 | 78.30 |
| beautifulSoupLxml | 11.526 | 1.930 | 13.565 | 17.845 | 6.48 |
| beautifulSoupHtmlParser | 17.026 | 1.928 | 19.183 | 24.750 | 4.58 |

## Hard-catalog end-to-end

Seven arms ran five campaigns with five samples per campaign. Beautiful Soup retains correctness-gated single exploratory samples under the established resource-bounded protocol.

| Arm | Median ms | P95 ms | Input MB/s | Evidence |
| --- | --- | --- | --- | --- |
| yosoiRust | 10.141 | 13.963 | 1694.74 | K=5 × 5 |
| scraplingParser | 146.119 | 182.473 | 117.62 | K=5 × 5 |
| selectolaxLexbor | 148.833 | 182.562 | 115.48 | K=5 × 5 |
| parsel | 149.382 | 183.593 | 115.05 | K=5 × 5 |
| lxml | 173.672 | 205.999 | 98.96 | K=5 × 5 |
| rustScraper | 191.265 | 202.094 | 89.86 | K=5 × 5 |
| goquery | 242.281 | 337.086 | 70.94 | K=5 × 5 |
| beautifulSoupLxml | 6091.615 | 6091.615 | 2.82 | single exploratory sample |
| beautifulSoupHtmlParser | 7559.362 | 7559.362 | 2.27 | single exploratory sample |

## Cold process

Fresh process start through one correctness-verified caveman output, five samples.

| Arm | Median ms |
| --- | --- |
| lolHtml | 1.573 |
| yosoiRust | 1.702 |
| rustScraper | 3.328 |
| goquery | 3.719 |
| selectolaxLexbor | 67.934 |
| lxml | 68.304 |
| parsel | 69.501 |
| scraplingParser | 80.643 |
| beautifulSoupLxml | 86.407 |
| beautifulSoupHtmlParser | 88.158 |

## Hard-catalog resources and package footprint

Resource evidence is one declared pass with 10 ms process-tree RSS sampling. Python installed sizes are distribution closures; the shared runnable environment includes Python 3.13. Compressed wheel sizes were not retained.

| Arm | Peak RSS MiB | Mean RSS MiB | P95 RSS MiB | User CPU s | Installed MiB | Runnable MiB | Language | Streaming |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| yosoiRust | 39.7 | 38.5 | 39.7 | 0.166 | 5.09 | 5.09 | rust | fullBuffer |
| rustScraper | 272.7 | 162.2 | 271.6 | 0.689 | 2.60 | 2.60 | rust | fullBuffer |
| goquery | 333.8 | 174.7 | 320.2 | 0.587 | 7.24 | 7.24 | go | fullBuffer |
| parsel | 346.3 | 206.6 | 346.3 | 0.704 | 11.40 | 153.71 | python | fullBuffer |
| scraplingParser | 347.7 | 240.7 | 347.7 | 0.616 | 13.42 | 153.71 | python | fullBuffer |
| lxml | 353.0 | 252.0 | 353.0 | 0.650 | 11.16 | 153.71 | python | fullBuffer |
| selectolaxLexbor | 391.2 | 248.5 | 391.2 | 0.704 | 13.79 | 153.71 | python | fullBuffer |
| beautifulSoupLxml | 878.0 | 635.5 | 878.0 | 21.907 | 11.86 | 153.71 | python | fullBuffer |
| beautifulSoupHtmlParser | 1057.0 | 743.4 | 1057.0 | 26.784 | 0.70 | 153.71 | python | fullBuffer |

## Criterion confirmation for Rust

Five independent Criterion 0.7 campaigns per Rust arm, each with 3 s warm-up, 5 s measurement, and 100 samples.

| Arm | Phase | Median ms | Campaign min ms | Campaign max ms | K |
| --- | --- | --- | --- | --- | --- |
| rustScraper | parse | 0.790 | 0.784 | 0.829 | 5 |
| rustScraper | locate | 0.025 | 0.025 | 0.026 | 5 |
| rustScraper | endToEnd | 0.840 | 0.831 | 0.840 | 5 |
| yosoiRust | parse | 0.862 | 0.848 | 1.276 | 5 |
| yosoiRust | locate | 0.034 | 0.033 | 0.035 | 5 |
| yosoiRust | endToEnd | 0.076 | 0.065 | 0.084 | 5 |

## What happened

- Parsel's caveman end-to-end median was 0.650 ms versus Yosoi's 0.072 ms; Yosoi took 0.11× as long.
- Rust `scraper` completed caveman end-to-end in 0.837 ms; Yosoi took 0.09× as long.
- On the hard catalog, Parsel was 149.382 ms, Rust `scraper` was 191.265 ms, and Yosoi was 10.141 ms.
- Yosoi peak RSS was 39.7 MiB versus Rust `scraper` 272.7 MiB and GoQuery 333.8 MiB.
- All input bytes are resident before timing. Yosoi's end-to-end arm calls ordinary `Document::locate`, whose default dispatcher can stream eligible plans; its explicit parse and pre-parsed locate phases use a retained tree. End-to-end latency therefore need not equal parse plus locate. The tables compare exact URL-free byte-to-value operations, not universal full-DOM parser speed.
- The package table's `fullBuffer` label describes resident input delivery. The `lol_html` caveman control uses ordinary selector/text handlers with 64 KiB chunks over resident input; exact output is checked with 1-byte, 7-byte, and 64 KiB chunk boundaries. It is ranked for this byte-to-value task, with no invented parse-only or pre-parsed-locate timings. Time-to-first-output was not measured.

## Evidence boundaries

- Yosoi was built into an immutable local binary from source revision `2d9269fe045149b2b2289dc4d3d47a354a92c8b4`. This is not yet a published release artifact, so the result is exploratory.
- The common cross-language warm harness uses each language's in-process monotonic timer. Criterion confirms only the two Rust arms.
- The hard K=5 campaign excludes the two Beautiful Soup arms under the established resource-bounded protocol. Their retained rows are single-sample observations.
- RSS is aggregate process-tree resident memory. VSZ is not reported as RAM.
- Results apply only to these fixtures, exact versions, machine, and command boundaries. They do not establish general accuracy or universal speed.

## Reproduction

The `raw/` directory contains native samples, Criterion estimates, console output, fixture identity, and the Yosoi artifact identity. `evidenceManifest.json` hashes every retained file.
