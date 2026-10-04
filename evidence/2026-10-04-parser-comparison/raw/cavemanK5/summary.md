# Exploratory parser/selector results

Correctness-gated local run. Lower is better for latency and RSS; higher is better for throughput.

## Caveman end-to-end

| Arm | Median ms | P95 ms | Input MB/s |
| --- | --- | --- | --- |
| yosoiRust | 0.072 | 0.106 | 1221.07 |
| lolHtml | 0.170 | 0.300 | 517.87 |
| parsel | 0.650 | 0.691 | 135.34 |
| scraplingParser | 0.670 | 0.701 | 131.33 |
| lxml | 0.678 | 0.710 | 129.62 |
| selectolaxLexbor | 0.789 | 0.832 | 111.43 |
| rustScraper | 0.837 | 0.948 | 105.03 |
| goquery | 1.123 | 1.505 | 78.30 |
| beautifulSoupLxml | 13.565 | 17.845 | 6.48 |
| beautifulSoupHtmlParser | 19.183 | 24.750 | 4.58 |

## Caveman cold process

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
