# Exploratory parser/selector results

Correctness-gated local run. Lower is better for latency and RSS; higher is better for throughput.

## Caveman end-to-end

| Arm | Median ms | P95 ms | Input MB/s |
| --- | --- | --- | --- |
| parsel | 0.608 | 0.655 | 144.53 |
| scraplingParser | 0.679 | 0.712 | 129.48 |
| lxml | 0.681 | 0.715 | 129.12 |
| selectolaxLexbor | 0.786 | 0.821 | 111.84 |
| rustScraper | 0.829 | 0.862 | 106.06 |
| goquery | 0.976 | 1.084 | 90.07 |
| yosoiRust | 1.205 | 1.286 | 72.95 |
| beautifulSoupLxml | 13.703 | 17.362 | 6.42 |
| beautifulSoupHtmlParser | 19.044 | 23.365 | 4.62 |

## Caveman cold process

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
