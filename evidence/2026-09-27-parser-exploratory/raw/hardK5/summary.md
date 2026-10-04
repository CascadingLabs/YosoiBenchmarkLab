# Exploratory parser/selector results

Correctness-gated local run. Lower is better for latency and RSS; higher is better for throughput.

## Hard catalog end-to-end

| Arm | Median ms | P95 ms | Input MB/s |
| --- | --- | --- | --- |
| parsel | 143.600 | 183.703 | 119.68 |
| scraplingParser | 149.643 | 183.101 | 114.85 |
| selectolaxLexbor | 151.163 | 185.641 | 113.70 |
| lxml | 171.700 | 208.055 | 100.10 |
| goquery | 177.207 | 200.914 | 96.99 |
| rustScraper | 187.597 | 192.730 | 91.61 |
| yosoiRust | 315.984 | 347.270 | 54.39 |
