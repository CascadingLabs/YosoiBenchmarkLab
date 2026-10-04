from __future__ import annotations

import argparse
import asyncio
import json
import time
from typing import Any


def urls(base: str, count: int, delay_ms: int) -> list[str]:
    return [f"{base}/page?id={index}&delayMs={delay_ms}" for index in range(count)]


def expected(count: int) -> list[str]:
    return [f"value-{index}" for index in range(count)]


async def scrapling_values(targets: list[str], concurrency: int) -> list[str]:
    from scrapling.fetchers import AsyncFetcher

    semaphore = asyncio.Semaphore(concurrency)

    async def one(index: int, target: str) -> tuple[int, str]:
        async with semaphore:
            response = await AsyncFetcher.get(target, retries=0, stealthy_headers=False, timeout=30)
            value = response.css("span.value::text").get()
            if value is None:
                raise RuntimeError("Scrapling response has no value")
            return index, value

    results = await asyncio.gather(*(one(index, target) for index, target in enumerate(targets)))
    return [value for _, value in sorted(results)]


def scrapy_values(targets: list[str], concurrency: int) -> list[str]:
    import scrapy
    from scrapy.crawler import CrawlerProcess

    values: dict[int, str] = {}

    class BenchmarkSpider(scrapy.Spider):
        name = "yosoiBenchmark"
        start_urls = targets
        custom_settings = {
            "CONCURRENT_REQUESTS": concurrency,
            "CONCURRENT_REQUESTS_PER_DOMAIN": concurrency,
            "RETRY_ENABLED": False,
            "LOG_ENABLED": True,
            "LOG_LEVEL": "ERROR",
            "TELNETCONSOLE_ENABLED": False,
            "HTTPPROXY_ENABLED": False,
            "ROBOTSTXT_OBEY": False,
            "DOWNLOAD_TIMEOUT": 30,
        }

        def parse(self, response: Any):
            from urllib.parse import parse_qs, urlparse

            index = int(parse_qs(urlparse(response.url).query)["id"][0])
            value = response.css("span.value::text").get()
            if value is None:
                raise RuntimeError("Scrapy response has no value")
            values[index] = value

    process = CrawlerProcess(settings={"LOG_ENABLED": True, "LOG_LEVEL": "ERROR"})
    process.crawl(BenchmarkSpider)
    process.start()
    return [values[index] for index in range(len(targets))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=["scrapy", "scraplingFetcher"], required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--concurrency", type=int, required=True)
    parser.add_argument("--delay-ms", type=int, default=0)
    args = parser.parse_args()
    targets = urls(args.base, args.count, args.delay_ms)
    started = time.perf_counter_ns()
    if args.arm == "scraplingFetcher":
        values = asyncio.run(scrapling_values(targets, args.concurrency))
    else:
        values = scrapy_values(targets, args.concurrency)
    wall_ns = time.perf_counter_ns() - started
    status = "ok" if values == expected(args.count) else "wrongOutput"
    print(json.dumps({
        "armId": args.arm,
        "language": "python",
        "count": args.count,
        "concurrency": args.concurrency,
        "delayMs": args.delay_ms,
        "wallNs": wall_ns,
        "throughputRequestsPerSecond": args.count / (wall_ns / 1_000_000_000),
        "terminalStatus": status,
        "values": values,
    }, separators=(",", ":")))
    return 0 if status == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
