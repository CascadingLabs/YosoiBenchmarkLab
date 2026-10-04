# Yosoi Benchmark Lab

Independent, correctness-gated comparisons of [Yosoi](https://github.com/CascadingLabs/Yosoi)
with open-source tools that run locally. Competitor dependencies stay in this lab;
Yosoi is consumed as immutable built artifacts.

## Current rerun — 2026-10-04

Source snapshot: `2d9269fe045149b2b2289dc4d3d47a354a92c8b4`.
This is a local working-copy source build, not a published Yosoi release.
Rust 1.99.0; AMD Ryzen AI 9 HX 370; Linux x86-64. Rendered arms use regular
Stable Chrome 154.0.8037.97 with sandboxing enabled.

All comparative lanes and V2 diagnostics were rerun and verified. Browser
verification covers **30 successful runs and six retained resource stops**;
those six c4 runs have no ranked timing.

| Lane | Yosoi | Comparative result |
| --- | ---: | --- |
| Caveman byte-to-value | 0.072 ms | First of 10 arms; `lol_html` second (full ranking below) |
| Hard catalog byte-to-value | 10.141 ms | Lowest repeated median; next `scraplingParser` 146.119 ms |
| HTTP, 20 ms delay, c8 | 320.0 req/s | Colly 365.5 req/s |
| Rendered Requests, c4 | Resource-stopped | Yosoi and Scrapling unranked at the 3 GiB cap; Crawlee 0.928 s |

[Full current results](docs/current-results.md) · [Evidence register](evidence/current.json)


## Caveman ranking: HTML bytes → the correct price

Every arm reads the same **87,928-byte** catalog, runs the same selector, and
returns exactly **`USD 19.73`**. Lower end-to-end latency is better.

| Rank | Arm | End-to-end ms | Execution path |
| --- | --- | ---: | --- |
| 1 | Yosoi | 0.072 | Default locator: eligible streaming, tree fallback |
| 2 | lol_html 3.0.1 | 0.170 | Streaming rewriter |
| 3 | Parsel | 0.650 | Retained tree |
| 4 | Scrapling parser | 0.670 | Retained tree |
| 5 | lxml | 0.678 | Retained tree |
| 6 | selectolax / Lexbor | 0.789 | Retained tree |
| 7 | Rust scraper | 0.837 | Retained tree |
| 8 | GoQuery | 1.123 | Retained tree |
| 9 | Beautiful Soup / lxml | 13.565 | Retained tree |
| 10 | Beautiful Soup / html.parser | 19.183 | Retained tree |

Five independent campaigns, 100 samples per campaign, 10 operations per sample.
The table ranks the **median of the five campaign medians**. All input bytes and
locator setup are prepared before timing. File I/O, process startup, and result
checking are outside the warm timer. Raw samples and losing results are retained.

## Why end-to-end can be faster than parse-only

The caveman task asks for the price value. Full-tree construction is measured
separately. Yosoi's ordinary default locator can stream supported queries and
fall back to a retained tree. `lol_html` uses its public CSS/text handlers on
64 KiB chunks of the same resident input.

| Measurement | What we time, simply | Yosoi ms |
| --- | --- | ---: |
| Parse-only | Build the full parsed tree | 0.839 |
| Locate-only | Find the price in an already parsed tree | 0.069 |
| End-to-end | Get the price from HTML bytes through the default locator | 0.072 |

These are separate paths: **do not add parse-only and locate-only to predict
end-to-end**. The ranking describes this exact byte-to-value task, rather than
universal full-DOM parsing speed. `lol_html` has no retained-tree parse-only or
pre-parsed-locate row. Its output also passed 1-byte, 7-byte, and 64 KiB chunk
boundary checks. Time-to-first-output and allocation counts were not measured.

## What the complete suite measures

| Lane | Workload | How we measure it |
| --- | --- | --- |
| Parser / selector | Small catalog; 17.2 MB hard catalog | Warm phase timings, separate cold starts, sampled process RSS and CPU |
| HTTP | 64 loopback pages; immediate or 20 ms delay | Five campaigns at concurrency 1, 4, 8; exact ordered values |
| Rendered browser Request | Four delayed-script loopback pages | Three campaigns at concurrency 1, 2, 4; exact values and browser cleanup |
| V2 diagnostics | 36 document/query/projection cells plus typed extraction | Separate five-campaign cells, conformance, malformed-input, and resource-bound checks |

V2 covers HTML, XML, JSON, decoded text, rendered DOM, and accessibility trees.
It has no cross-format aggregate or public KPI score. Browser automation,
hosted APIs, paid services, persistent sessions, and Actions are outside this lab.

## Reproduce and inspect

See [complete rerun instructions](docs/rerunning.md),
[parser methodology](docs/parser-selector-methodology.md),
[V2 methodology](docs/benchmark-v2-methodology.md),
[metric definitions](docs/metrics.md), and [coverage boundaries](docs/coverage-gaps.md).

Earlier results remain preserved in [the historical September baseline](docs/baseline-v1.md)
and [its evidence register](evidence/baseline-v1.json). They describe their own
source, compiler, dependency, and browser identities.

This is one workstation and a frozen workload, with exact output required before
ranking. Sampled RSS, CPU time, warm latency, startup, and package size are
separate measurements; none substitutes for another.
