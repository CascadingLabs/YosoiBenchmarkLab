# Exploratory parser and selector benchmark — 2026-09-27

## Decision

Yosoi is **not currently the fastest parser/selector arm** on these frozen exploratory workloads. Parsel leads both the 87,928-byte caveman task and the 17,186,672-byte hard catalog. Yosoi's clearest current advantage is lower hard-pass peak RSS than the other compiled Rust/Go controls, not latency.

These are local exploratory results, not a public “fastest” claim.

## Inputs and correctness

cavemanCatalog 87,928 bytes SHA-256 `3a189573c0ab36b7e77b67a1a5b2a849133969c472067e16fae3f5c10ffcd4ef`, hardCatalog 17,186,672 bytes SHA-256 `139ee57c396ae07c3910295e705fcacb79b08b6a8faf74813e443e494bb6a163`.

All nine arms returned the exact ordered caveman value and all 64 exact ordered hard-catalog values before timing. No incorrect arm was ranked.

## Caveman warm timings — five campaigns

Each arm ran five fresh-process campaigns, 100 samples per campaign, 10 operations per sample. Values are the median of campaign medians; p95 is retained across the raw native samples.

| Arm | Parse ms | Locate ms | End-to-end ms | P95 ms | Input MB/s |
| --- | --- | --- | --- | --- | --- |
| parsel | 0.507 | 0.067 | 0.608 | 0.655 | 144.53 |
| scraplingParser | 0.601 | 0.069 | 0.679 | 0.712 | 129.48 |
| lxml | 0.599 | 0.074 | 0.681 | 0.715 | 129.12 |
| selectolaxLexbor | 0.796 | 0.049 | 0.786 | 0.821 | 111.84 |
| rustScraper | 0.785 | 0.025 | 0.829 | 0.862 | 106.06 |
| goquery | 0.933 | 0.069 | 0.976 | 1.084 | 90.07 |
| yosoiRust | 1.085 | 0.104 | 1.205 | 1.286 | 72.95 |
| beautifulSoupLxml | 11.525 | 1.895 | 13.703 | 17.362 | 6.42 |
| beautifulSoupHtmlParser | 16.810 | 1.911 | 19.044 | 23.365 | 4.62 |

## Hard-catalog end-to-end

The seven sub-400 MiB arms ran five campaigns with five samples per campaign. Beautiful Soup retains its correctness-gated single exploratory sample because repeatedly allocating 878 MiB–1.0 GiB increased workstation swap pressure.

| Arm | Median ms | P95 ms | Input MB/s | Evidence |
| --- | --- | --- | --- | --- |
| parsel | 143.600 | 183.703 | 119.68 | K=5 × 5 |
| scraplingParser | 149.643 | 183.101 | 114.85 | K=5 × 5 |
| selectolaxLexbor | 151.163 | 185.641 | 113.70 | K=5 × 5 |
| lxml | 171.700 | 208.055 | 100.10 | K=5 × 5 |
| goquery | 177.207 | 200.914 | 96.99 | K=5 × 5 |
| rustScraper | 187.597 | 192.730 | 91.61 | K=5 × 5 |
| yosoiRust | 315.984 | 347.270 | 54.39 | K=5 × 5 |
| beautifulSoupLxml | 6240.615 | 6240.615 | 2.75 | single exploratory sample |
| beautifulSoupHtmlParser | 7681.558 | 7681.558 | 2.24 | single exploratory sample |

## Cold process

Fresh process start through one correctness-verified caveman output, five samples.

| Arm | Median ms |
| --- | --- |
| rustScraper | 3.202 |
| goquery | 4.332 |
| yosoiRust | 4.742 |
| lxml | 50.355 |
| selectolaxLexbor | 52.523 |
| parsel | 66.178 |
| scraplingParser | 69.880 |
| beautifulSoupLxml | 80.299 |
| beautifulSoupHtmlParser | 91.637 |

## Hard-catalog resources and package footprint

Resource evidence is one declared pass with 10 ms process-tree RSS sampling. Python installed sizes are distribution closures; the shared runnable environment includes Python 3.13. Compressed wheel sizes were not retained.

| Arm | Peak RSS MiB | Mean RSS MiB | P95 RSS MiB | User CPU s | Installed MiB | Runnable MiB | Language | Streaming |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| yosoiRust | 256.4 | 178.5 | 253.8 | 0.982 | 4.85 | 4.85 | rust | fullBuffer |
| rustScraper | 272.8 | 170.5 | 267.1 | 0.491 | 2.62 | 2.62 | rust | fullBuffer |
| goquery | 290.3 | 170.3 | 290.3 | 0.752 | 4.89 | 4.89 | go | fullBuffer |
| parsel | 346.4 | 236.1 | 346.4 | 0.511 | 11.40 | 153.71 | python | fullBuffer |
| scraplingParser | 347.7 | 240.7 | 347.7 | 0.510 | 13.42 | 153.71 | python | fullBuffer |
| lxml | 353.0 | 241.0 | 353.0 | 0.576 | 11.16 | 153.71 | python | fullBuffer |
| selectolaxLexbor | 391.2 | 237.6 | 391.0 | 0.511 | 13.79 | 153.71 | python | fullBuffer |
| beautifulSoupLxml | 878.0 | 629.5 | 878.0 | 20.260 | 11.86 | 153.71 | python | fullBuffer |
| beautifulSoupHtmlParser | 1057.0 | 735.9 | 1057.0 | 24.620 | 0.70 | 153.71 | python | fullBuffer |

## Criterion confirmation for Rust

Five independent Criterion 0.7 campaigns per Rust arm, each with 3 s warm-up, 5 s measurement, and 100 samples.

| Arm | Phase | Median ms | Campaign min ms | Campaign max ms | K |
| --- | --- | --- | --- | --- | --- |
| rustScraper | parse | 0.779 | 0.773 | 0.781 | 5 |
| rustScraper | locate | 0.025 | 0.025 | 0.025 | 5 |
| rustScraper | endToEnd | 0.826 | 0.818 | 0.832 | 5 |
| yosoiRust | parse | 1.101 | 1.094 | 1.112 | 5 |
| yosoiRust | locate | 0.103 | 0.102 | 0.107 | 5 |
| yosoiRust | endToEnd | 1.185 | 1.178 | 1.186 | 5 |

## What happened

- Parsel's caveman end-to-end median was 0.608 ms versus Yosoi's 1.205 ms; Yosoi took 1.98× as long.
- Rust `scraper` completed caveman end-to-end in 0.829 ms; Yosoi took 1.45× as long.
- On the hard catalog, Parsel was 143.600 ms, Rust `scraper` was 187.597 ms, and Yosoi was 315.984 ms.
- Yosoi peak RSS was 256.4 MiB versus Rust `scraper` 272.8 MiB and GoQuery 290.3 MiB.
- Every measured parser is full-buffered for this DOM task. `lol_html` remains outside the DOM ranking until a semantically equivalent streaming task exists.

## Evidence boundaries

- Yosoi was built into an immutable local binary from source revision `d9b64106568b02e4960988ac5f18887301c576c4`. This is not yet a published release artifact, so the result is exploratory.
- The common cross-language warm harness uses each language's in-process monotonic timer. Criterion confirms only the two Rust arms.
- The hard K=5 campaign intentionally excludes the two Beautiful Soup arms because swap grew during the one-pass resource run. Their retained rows are single-sample observations.
- RSS is aggregate process-tree resident memory. VSZ is not reported as RAM.
- Results apply only to these fixtures, exact versions, machine, and command boundaries. They do not establish general accuracy or universal speed.

## Reproduction

The `raw/` directory contains native samples, Criterion estimates, console output, fixture identity, and the Yosoi artifact identity. `evidenceManifest.json` hashes every retained file.
