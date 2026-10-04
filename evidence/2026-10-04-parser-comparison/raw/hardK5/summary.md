# Exploratory parser/selector results

Correctness-gated local run. Lower is better for latency and RSS; higher is better for throughput.

## Hard catalog end-to-end

| Arm | Median ms | P95 ms | Input MB/s |
| --- | --- | --- | --- |
| yosoiRust | 10.141 | 13.963 | 1694.74 |
| scraplingParser | 146.119 | 182.473 | 117.62 |
| selectolaxLexbor | 148.833 | 182.562 | 115.48 |
| parsel | 149.382 | 183.593 | 115.05 |
| lxml | 173.672 | 205.999 | 98.96 |
| rustScraper | 191.265 | 202.094 | 89.86 |
| goquery | 242.281 | 337.086 | 70.94 |
