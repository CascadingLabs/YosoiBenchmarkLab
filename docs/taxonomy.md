# Benchmark taxonomy

Current evidence: [2026-10-04 benchmark results](current-results.md).
The latest run includes the ranked `lol_html` caveman control and retained
resource-stopped browser cells.

## Admission rule

A ranked competitor must be open source and runnable locally or self-hosted
without paid API access. Its exact release or source revision, license, runtime,
dependency lock, and execution boundary must be recorded before measurement.

Popularity helps choose candidates; it does not excuse an incomparable workload.

## Quadrant 1: parser and selector engines

This is the first required quadrant. All inputs are immutable local bytes.
No arm fetches a URL or starts a browser.

| Candidate | Native role | Initial status | Notes |
| --- | --- | --- | --- |
| Yosoi Rust Documents/Locators | Typed document parsing and location | Required | Public Rust surface; headline Yosoi arm |
| Scrapling parser | Python selector/parser layer | Required | Reproduce its publisher benchmark separately before semantic-parity ranking |
| Parsel | Python CSS/XPath/JSON selector API over lxml | Required | Do not merge with raw lxml |
| lxml | Python binding over libxml2/libxslt | Required | Lower-level control; exact parser flags must be pinned |
| selectolax Lexbor | Python HTML5 parser with CSS selectors | Required | Pin Lexbor backend explicitly |
| Beautiful Soup + `html.parser` | Python navigation API and stdlib parser | Required | Separate arm from every other backend |
| Beautiful Soup + lxml | Python navigation API and lxml backend | Required | Measures wrapper plus named backend |
| Rust `scraper` | Rust html5ever/selectors interface | Required | Same-language ecosystem control |
| GoQuery | Go net/html plus Cascadia selector interface | Required | Go ecosystem control |
| raw html5ever | Rust parser control | Secondary | Parse-only unless an equivalent query layer is added |
| `lol_html` | Streaming HTML parser/rewriter | Caveman ranked control | Exact same byte-to-value oracle; no queryable-DOM or pre-parsed-locate claim |

“Required” means required by the first parser release unless method audit shows
that the arm cannot perform the frozen operation or cannot be installed under
its license. Such a decision is recorded as an explicit exclusion, not a
missing row.

## Quadrant 2: HTTP scraping frameworks

This runs after the parser quadrant. The implemented common task requests 64
deterministic loopback URLs, extracts one exact value per page, and restores
input order at concurrency 1, 4, and 8 with immediate or fixed-delay responses.

Measured arms: Yosoi Request, Scrapy, Scrapling Fetcher, Crawlee with
Cheerio, and Colly. Multi-page crawl behavior is a later sub-lane and exists
only when Yosoi Crawl has a comparable public artifact.

## Quadrant 3: rendered browser Requests

This begins after the HTTP quadrant. The shared boundary is one bounded
browser-backed Request that returns immutable rendered evidence and cleans up.

Measured arms: Yosoi browser-backed Request, Scrapling DynamicFetcher,
Crawlee/PlaywrightCrawler, and a direct Playwright control. The matrix requests
four unique delayed-script pages at concurrency 1, 2, and 4. Crawl4AI remains
outside the measured population. Every ranked arm must use regular Chrome/Chromium Stable
intended for normal browsing.

Persistent sessions, Actions, arbitrary JavaScript, multi-step interaction,
and general browser automation are not benchmarked.

## Optional research, not a fourth quadrant

Self-hosted product suites such as Firecrawl or Crawl4AI-as-a-service, and
adaptive/AI algorithms, are optional appendices. They do not block the three
quadrants, the public charts, or release closure.

## Excluded population

- hosted APIs and hosted-only features;
- paid proxy, extraction, search, or browser services;
- systems whose required benchmark path cannot run locally;
- browser-automation breadth unrelated to a single rendered Request;
- a result whose output is not equivalent to the frozen task;
- a testing-only browser distribution.
