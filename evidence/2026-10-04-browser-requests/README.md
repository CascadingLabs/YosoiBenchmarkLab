# Rendered browser Requests — 2026-10-04

All 36 campaigns were attempted. Thirty passed exact four-value output and cleanup. All three c4 campaigns for Yosoi and Scrapling hit the declared 3 GiB aggregate RSS cap, were stopped with their owned descendants, and remain unranked. All 36 attempts have zero residual owned browser processes.

| Arm | c1 wall s | c2 wall s | c4 wall s | c4 sampled peak RSS MiB |
| --- | --- | --- | --- | --- |
| yosoiBrowserRequest | 2.602 | 1.563 | resource-stopped | unranked |
| scraplingDynamicFetcher | 2.844 | 1.457 | resource-stopped | unranked |
| crawleePlaywright | 1.119 | 0.953 | 0.928 | 1426.5 |
| directPlaywright | 0.679 | 0.598 | 0.503 | 1594.3 |

## Measurement boundary

Four unique loopback pages load a blocking external script with a fixed 20 ms delay and produce exact ordered values. Each concurrency cell has three fresh-process campaigns. A cell receives timing medians only when every campaign passes output and cleanup. Each adapter has a 180-second deadline and 3 GiB sampled aggregate RSS cap. The sampler tracks owned descendants, including browser and helper processes, at a nominal 20 ms interval. Sampled RSS sums resident pages and does not deduplicate shared pages or measure PSS.

All arms use regular Stable Google Chrome 154.0.8037.97, executable SHA-256 `6c792041b07547a662e1b17974d1dc34a3db630379b45d9d89ddd7e3e68cc587`, with browser sandboxing enabled. This M154 package is a benchmark identity, not full Yosoi browser compatibility certification.

Yosoi and Scrapling use one-shot browser acquisition. Crawlee amortizes a browser pool. Direct Playwright is a lower-level pooled control whose internal timer begins after browser launch; it is not a product-equivalent framework winner. Outer process wall times include its browser startup and are retained separately.

## Source and evidence

Yosoi source snapshot: `2d9269fe045149b2b2289dc4d3d47a354a92c8b4`. This is an immutable local source build, not a published release. Artifact and dependency identities, native records, environment metadata, and digest manifests are retained in this bundle. These are current-host observations, with no universal performance or allocation claim.
