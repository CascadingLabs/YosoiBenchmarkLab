# Exploratory rendered browser Request benchmark — 2026-09-27

## Decision

Yosoi loses the current-host rendered Request comparison. Crawlee/Playwright is
fastest and most memory-efficient because its ordinary crawler surface
amortizes one browser pool across pages. Yosoi and Scrapling use fresh one-shot
browser launches, which is part of their measured product boundary.

All retained runs returned four exact rendered values and completed browser
cleanup with zero residual Chromium processes. Each cell contains three
fresh-process campaigns.

| Arm | c1 wall s | c2 wall s | c4 wall s | c1→c4 speedup | c4 peak RSS MiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| Direct Playwright control | 0.687 | 0.551 | 0.487 | 1.41× | 1,938.1 |
| Crawlee/Playwright | 1.165 | 0.942 | 0.789 | 1.48× | 1,678.5 |
| Scrapling DynamicFetcher | 3.326 | 1.557 | 1.025 | 3.24× | 4,490.1 |
| Yosoi browser Request | 2.977 | 1.960 | 1.389 | 2.14× | 5,916.2 |

## Method

- Four unique loopback pages each loaded a blocking external script delayed by
  exactly 20 ms, then wrote one exact rendered DOM value.
- Concurrency populations were 1, 2, and 4.
- Yosoi requested exact `RenderedDom`; Scrapling used `DynamicFetcher`; Crawlee
  used `PlaywrightCrawler`; direct Playwright used one browser with fresh
  contexts as a lower-level pooled control.
- Every arm used regular `/usr/bin/chromium` 152.0.7977.82, SHA-256
  `78f94ee05d5d6fd1bd8239b9700d3cf54d540911febad4c7cea01080273943f9`.
- The runner sampled adapter plus newly created Chromium process RSS every 20
  ms and required all new Chromium PIDs to disappear within five seconds.
- Crawlee initially returned the right value and cleaned Chromium but left its
  Node event loop alive. Explicit crawler teardown plus a final process exit was
  added only after verifying no Chromium child remained.

## Boundaries

- Chromium 152 is Yosoi's documented emergency rollback artifact, not its
  certified Chrome 153 tuple. These results are exploratory and cannot certify
  release browser performance.
- The ordinary products have different lifecycle semantics. The benchmark does
  not pretend a pooled Crawlee browser and fresh Yosoi browser are the same
  implementation; it records the user-visible consequence.
- No Actions, retained session, arbitrary JavaScript API, live site, hosted
  browser, proxy, or paid service participated.
