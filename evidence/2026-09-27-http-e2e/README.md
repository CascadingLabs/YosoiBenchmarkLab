# Exploratory HTTP end-to-end benchmark — 2026-09-27

## Decision

Yosoi is second to Colly across the deterministic loopback workloads. Its
bounded concurrency scales well under I/O latency, but zero-delay throughput is
flat from concurrency 1 through 8, indicating per-request setup and processing
overhead rather than scheduler capacity is the current limit.

All five arms returned the exact ordered values for 64 unique URLs before a
result was retained. Each cell contains five fresh-process campaigns.

## Immediate response

| Arm | c1 req/s | c4 req/s | c8 req/s | c8 wall ms | c8 peak RSS MiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| Colly | 1,795.8 | 2,756.4 | 2,644.9 | 24.2 | 24.5 |
| Yosoi Request | 1,348.3 | 1,413.6 | 1,388.6 | 46.1 | 13.5 |
| Scrapling Fetcher | 414.9 | 592.4 | 666.2 | 96.1 | 54.1 |
| Scrapy | 148.6 | 202.4 | 194.8 | 328.5 | 85.3 |
| Crawlee/Cheerio | 107.8 | 199.0 | 118.2 | 541.3 | 183.3 |

## Deterministic 20 ms response delay

| Arm | c1 req/s | c4 req/s | c8 req/s | c1→c8 speedup | c8 wall ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Colly | 47.1 | 187.5 | 370.5 | 7.87× | 172.8 |
| Yosoi Request | 45.8 | 174.5 | 332.6 | 7.26× | 192.4 |
| Scrapling Fetcher | 42.5 | 145.6 | 230.0 | 5.41× | 278.2 |
| Scrapy | 35.7 | 92.2 | 125.5 | 3.52× | 510.1 |
| Crawlee/Cheerio | 32.7 | 84.1 | 111.4 | 3.41× | 574.7 |

## Method

- One deterministic local server returned an approximately 32 KiB HTML page
  containing one exact value per URL.
- Workloads used 64 unique URLs and concurrency 1, 4, and 8.
- `fast` returned immediately; `io20` delayed every response by exactly 20 ms.
- Every adapter performed HTTP acquisition, HTML parsing, selector evaluation,
  ordered materialization, and correctness verification.
- Server `Connection: close` removed connection-pool reuse as a hidden advantage.
- The server accept backlog was fixed at 128. An earlier run with the standard
  backlog of five caused one-second TCP retransmission stalls at concurrency 8
  and was discarded rather than used as a Yosoi win.
- RSS is the aggregate adapter process tree sampled every 10 ms. Server memory
  is outside every arm and is not attributed to a competitor.

## Boundaries

- Results are current-host exploratory evidence from local source artifacts,
  not public release artifacts.
- The internal wall timer excludes different amounts of process/module startup;
  raw records also retain outer process wall time.
- This is one-shot URL-to-value, not multi-page crawl orchestration.
- No live site, proxy, hosted API, or paid service participated.
