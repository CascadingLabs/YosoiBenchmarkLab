# Exploratory parser/selector results

Correctness-gated local run. Lower is better for latency and RSS; higher is better for throughput.

## Caveman end-to-end

| Arm | Median ms | P95 ms | Input MB/s |
| --- | --- | --- | --- |
| parsel | 0.802 | 0.802 | 109.63 |
| lxml | 0.818 | 0.818 | 107.47 |
| scraplingParser | 0.914 | 0.914 | 96.19 |
| rustScraper | 0.982 | 0.982 | 89.52 |
| selectolaxLexbor | 0.993 | 0.993 | 88.52 |
| yosoiRust | 1.188 | 1.188 | 73.98 |
| goquery | 1.347 | 1.347 | 65.30 |
| beautifulSoupLxml | 14.924 | 14.924 | 5.89 |
| beautifulSoupHtmlParser | 19.681 | 19.681 | 4.47 |

## Hard catalog end-to-end

| Arm | Median ms | P95 ms | Input MB/s |
| --- | --- | --- | --- |
| scraplingParser | 185.696 | 185.696 | 92.55 |
| parsel | 186.388 | 186.388 | 92.21 |
| rustScraper | 192.464 | 192.464 | 89.30 |
| selectolaxLexbor | 193.526 | 193.526 | 88.81 |
| goquery | 202.728 | 202.728 | 84.78 |
| lxml | 225.476 | 225.476 | 76.22 |
| yosoiRust | 330.913 | 330.913 | 51.94 |
| beautifulSoupLxml | 6240.615 | 6240.615 | 2.75 |
| beautifulSoupHtmlParser | 7681.558 | 7681.558 | 2.24 |

## Caveman cold process

| Arm | Median ms |
| --- | --- |
| rustScraper | 3.111 |
| goquery | 3.235 |
| yosoiRust | 4.179 |
| selectolaxLexbor | 45.752 |
| lxml | 49.846 |
| scraplingParser | 65.245 |
| parsel | 67.945 |
| beautifulSoupLxml | 84.108 |
| beautifulSoupHtmlParser | 91.651 |

## Hard-catalog resource pass

| Arm | Peak RSS MiB | Mean RSS MiB | Installed MiB | Language | Streaming |
| --- | --- | --- | --- | --- | --- |
| yosoiRust | 256.4 | 178.5 | 4.8 | rust | fullBuffer |
| rustScraper | 272.8 | 170.5 | 2.6 | rust | fullBuffer |
| goquery | 290.3 | 170.3 | 4.9 | go | fullBuffer |
| parsel | 346.4 | 236.1 | 11.4 | python | fullBuffer |
| scraplingParser | 347.7 | 240.7 | 13.4 | python | fullBuffer |
| lxml | 353.0 | 241.0 | 11.2 | python | fullBuffer |
| selectolaxLexbor | 391.2 | 237.6 | 13.8 | python | fullBuffer |
| beautifulSoupLxml | 878.0 | 629.5 | 0.7 | python | fullBuffer |
| beautifulSoupHtmlParser | 1057.0 | 735.9 | 0.7 | python | fullBuffer |

Package numbers for Python are installed distribution closures in the shared benchmark environment; compressed wheel sizes were not retained in this exploratory run.
