from __future__ import annotations

import argparse
import concurrent.futures
import json
import time


def fetch(index: int, target: str, executable: str) -> tuple[int, str]:
    from scrapling.fetchers import DynamicFetcher

    response = DynamicFetcher.fetch(
        target,
        executable_path=executable,
        headless=True,
        network_idle=False,
        disable_resources=False,
        timeout=45_000,
    )
    value = response.css("span.value::text").get()
    if value is None:
        raise RuntimeError("rendered value is missing")
    return index, value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--concurrency", type=int, required=True)
    parser.add_argument("--delay-ms", type=int, required=True)
    parser.add_argument("--executable", required=True)
    args = parser.parse_args()
    targets = [f"{args.base}/dynamic?id={index}&delayMs={args.delay_ms}" for index in range(args.count)]
    started = time.perf_counter_ns()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        results = list(executor.map(lambda pair: fetch(pair[0], pair[1], args.executable), enumerate(targets)))
    wall_ns = time.perf_counter_ns() - started
    results.sort()
    values = [value for _, value in results]
    correct = values == [f"value-{index}" for index in range(args.count)]
    print(json.dumps({"armId":"scraplingDynamicFetcher","language":"python","count":args.count,"concurrency":args.concurrency,"delayMs":args.delay_ms,"wallNs":wall_ns,"throughputRequestsPerSecond":args.count/(wall_ns/1e9),"terminalStatus":"ok" if correct else "wrongOutput","values":values},separators=(",", ":")))
    return 0 if correct else 2


if __name__ == "__main__":
    raise SystemExit(main())
