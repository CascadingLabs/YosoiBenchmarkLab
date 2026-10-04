# HTTP acquisition and extraction — 2026-10-04

All 150 runs passed exact ordered output for 64 loopback pages. Five fresh-process campaigns per workload, arm, and concurrency cell.

## Immediate responses

| Arm | c1 req/s | c4 req/s | c8 req/s | c8 wall ms | c8 sampled peak RSS MiB |
| --- | --- | --- | --- | --- | --- |
| colly | 1790.5 | 2258.9 | 2295.4 | 27.9 | 20.0 |
| yosoiRequest | 1456.3 | 1281.2 | 1613.0 | 39.7 | 13.7 |
| scraplingFetcher | 433.8 | 505.9 | 671.0 | 95.4 | 54.2 |
| scrapy | 159.4 | 190.7 | 192.8 | 332.0 | 85.6 |
| crawleeCheerio | 131.7 | 133.6 | 112.6 | 568.4 | 186.2 |

## Fixed 20 ms response delay

| Arm | c1 req/s | c4 req/s | c8 req/s | c8 wall ms | c8 sampled peak RSS MiB |
| --- | --- | --- | --- | --- | --- |
| colly | 47.1 | 187.2 | 365.5 | 175.1 | 22.0 |
| yosoiRequest | 45.9 | 177.2 | 320.0 | 200.0 | 13.6 |
| scraplingFetcher | 42.4 | 141.5 | 243.1 | 263.3 | 54.2 |
| crawleeCheerio | 32.7 | 79.6 | 136.1 | 470.4 | 186.4 |
| scrapy | 35.1 | 98.7 | 135.4 | 472.6 | 89.7 |

## Measurement boundary

Each ordinary adapter fetches, parses, selects one value, restores input order, and verifies all 64 values. The deterministic server uses immediate or fixed-delay approximately 32 KiB HTML responses, `Connection: close`, and an accept backlog of 128. RSS is the adapter process tree sampled at a nominal 10 ms interval; server memory is excluded. Internal and fresh-process outer wall clocks are retained separately.

## Source and evidence

Yosoi source snapshot: `2d9269fe045149b2b2289dc4d3d47a354a92c8b4`. This is an immutable local source build, not a published release. Artifact and dependency identities, native records, environment metadata, and digest manifests are retained in this bundle. These are current-host observations, with no universal performance or allocation claim.
