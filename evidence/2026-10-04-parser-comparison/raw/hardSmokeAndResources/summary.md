# Exploratory parser/selector results

Correctness-gated local run. Lower is better for latency and RSS; higher is better for throughput.

## Caveman end-to-end

| Arm | Median ms | P95 ms | Input MB/s |
| --- | --- | --- | --- |
| yosoiRust | 0.131 | 0.131 | 673.76 |
| lxml | 0.778 | 0.778 | 112.96 |
| parsel | 0.836 | 0.836 | 105.16 |
| scraplingParser | 0.860 | 0.860 | 102.24 |
| selectolaxLexbor | 0.992 | 0.992 | 88.62 |
| goquery | 1.333 | 1.333 | 65.96 |
| rustScraper | 2.048 | 2.048 | 42.94 |
| beautifulSoupLxml | 16.437 | 16.437 | 5.35 |
| beautifulSoupHtmlParser | 19.453 | 19.453 | 4.52 |

## Hard catalog end-to-end

| Arm | Median ms | P95 ms | Input MB/s |
| --- | --- | --- | --- |
| yosoiRust | 11.341 | 11.341 | 1515.42 |
| selectolaxLexbor | 180.756 | 180.756 | 95.08 |
| parsel | 181.163 | 181.163 | 94.87 |
| scraplingParser | 184.257 | 184.257 | 93.28 |
| goquery | 187.496 | 187.496 | 91.66 |
| rustScraper | 198.046 | 198.046 | 86.78 |
| lxml | 352.924 | 352.924 | 48.70 |
| beautifulSoupLxml | 6091.615 | 6091.615 | 2.82 |
| beautifulSoupHtmlParser | 7559.362 | 7559.362 | 2.27 |

## Caveman cold process

| Arm | Median ms |
| --- | --- |
| yosoiRust | 1.858 |
| rustScraper | 2.737 |
| goquery | 2.968 |
| lxml | 43.986 |
| selectolaxLexbor | 50.865 |
| scraplingParser | 68.105 |
| beautifulSoupLxml | 78.621 |
| parsel | 79.784 |
| beautifulSoupHtmlParser | 84.248 |

## Hard-catalog resource pass

| Arm | Peak RSS MiB | Mean RSS MiB | Installed MiB | Language | Streaming |
| --- | --- | --- | --- | --- | --- |
| yosoiRust | 39.7 | 38.5 | 5.1 | rust | fullBuffer |
| rustScraper | 272.7 | 162.2 | 2.6 | rust | fullBuffer |
| goquery | 333.8 | 174.7 | 7.2 | go | fullBuffer |
| parsel | 346.3 | 206.6 | 11.4 | python | fullBuffer |
| scraplingParser | 347.7 | 240.7 | 13.4 | python | fullBuffer |
| lxml | 353.0 | 252.0 | 11.2 | python | fullBuffer |
| selectolaxLexbor | 391.2 | 248.5 | 13.8 | python | fullBuffer |
| beautifulSoupLxml | 878.0 | 635.5 | 11.9 | python | fullBuffer |
| beautifulSoupHtmlParser | 1057.0 | 743.4 | 0.7 | python | fullBuffer |

Package numbers for Python are installed distribution closures in the shared benchmark environment; compressed wheel sizes were not retained in this exploratory run.
