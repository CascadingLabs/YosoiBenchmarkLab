from __future__ import annotations

import argparse
import json
import math
import os
import random
import resource
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any

ARMS = ["yosoiRequest", "colly", "scraplingFetcher", "scrapy", "crawleeCheerio"]
SEED = 0x594F534F49


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1))]


def process_tree_rss(root_pid: int) -> int:
    parents: dict[int, int] = {}
    rss: dict[int, int] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            status = (entry / "status").read_text()
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        parent = None
        resident = 0
        for line in status.splitlines():
            if line.startswith("PPid:"):
                parent = int(line.split()[1])
            elif line.startswith("VmRSS:"):
                resident = int(line.split()[1]) * 1024
        if parent is not None:
            parents[int(entry.name)] = parent
            rss[int(entry.name)] = resident
    members = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, parent in parents.items():
            if parent in members and pid not in members:
                members.add(pid)
                changed = True
    return sum(rss.get(pid, 0) for pid in members)


def command(args: argparse.Namespace, arm: str, concurrency: int, delay_ms: int) -> tuple[list[str], Path]:
    common = ["--base", args.base, "--count", str(args.count), "--concurrency", str(concurrency), "--delay-ms", str(delay_ms)]
    if arm == "yosoiRequest":
        return [str(args.yosoi), *common], args.repository
    if arm == "colly":
        return [str(args.colly), *common], args.repository
    if arm in {"scrapy", "scraplingFetcher"}:
        return [str(args.python), str(args.repository / "adapters/http/python/adapter.py"), "--arm", arm, *common], args.repository
    return ["node", "adapter.mjs", *common], args.repository / "adapters/http/node-crawlee"


def run(command_value: list[str], cwd: Path) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["NODE_OPTIONS"] = "--max-old-space-size=1536"
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.perf_counter_ns()
    process = subprocess.Popen(command_value, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=environment)
    rss_samples: list[int] = []
    while process.poll() is None:
        rss_samples.append(process_tree_rss(process.pid))
        time.sleep(0.01)
    stdout, stderr = process.communicate()
    outer_wall = time.perf_counter_ns() - started
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    if process.returncode != 0:
        raise RuntimeError(f"adapter failed: {' '.join(command_value)}\n{stderr}\n{stdout}")
    result = None
    for line in reversed(stdout.splitlines()):
        if line.startswith("{"):
            result = json.loads(line)
            break
    if result is None:
        raise RuntimeError(f"adapter emitted no JSON: {stdout}")
    if not rss_samples:
        rss_samples = [0]
    result.update(
        {
            "outerWallNs": outer_wall,
            "peakRssBytes": max(rss_samples),
            "meanRssBytes": int(statistics.fmean(rss_samples)),
            "p95RssBytes": int(percentile([float(value) for value in rss_samples], 0.95)),
            "userCpuNs": int((after.ru_utime - before.ru_utime) * 1e9),
            "systemCpuNs": int((after.ru_stime - before.ru_stime) * 1e9),
            "stderr": stderr[-4096:],
        }
    )
    return result


def directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--yosoi", type=Path, required=True)
    parser.add_argument("--colly", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=64)
    parser.add_argument("--campaigns", type=int, default=5)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    with (args.output / "raw.jsonl").open("w") as raw:
        for delay_ms, workload in ((0, "fast"), (20, "io20")):
            for concurrency in (1, 4, 8):
                for campaign in range(args.campaigns):
                    order = list(ARMS)
                    random.Random(SEED + delay_ms * 100 + concurrency * 10 + campaign).shuffle(order)
                    for arm in order:
                        command_value, cwd = command(args, arm, concurrency, delay_ms)
                        result = run(command_value, cwd)
                        expected = [f"value-{index}" for index in range(args.count)]
                        if result["terminalStatus"] != "ok" or result["values"] != expected:
                            raise RuntimeError(f"correctness failure: {arm}/{workload}/c{concurrency}")
                        result.update({"workload": workload, "campaignIndex": campaign, "armOrder": order})
                        records.append(result)
                        raw.write(json.dumps(result, separators=(",", ":")) + "\n")
                        raw.flush()
    grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault((record["armId"], record["workload"], record["concurrency"]), []).append(record)
    summaries = []
    for (arm, workload, concurrency), group in sorted(grouped.items()):
        summaries.append(
            {
                "armId": arm,
                "workload": workload,
                "concurrency": concurrency,
                "campaigns": len(group),
                "medianWallNs": statistics.median(item["wallNs"] for item in group),
                "medianOuterWallNs": statistics.median(item["outerWallNs"] for item in group),
                "medianThroughputRequestsPerSecond": statistics.median(item["throughputRequestsPerSecond"] for item in group),
                "medianPeakRssBytes": statistics.median(item["peakRssBytes"] for item in group),
                "medianMeanRssBytes": statistics.median(item["meanRssBytes"] for item in group),
                "medianUserCpuNs": statistics.median(item["userCpuNs"] for item in group),
            }
        )
    package_sizes = {
        "yosoiRequest": args.yosoi.stat().st_size,
        "colly": args.colly.stat().st_size,
        "pythonEnvironment": directory_size(args.python.parents[1]),
        "crawleeNodeModules": directory_size(args.repository / "adapters/http/node-crawlee/node_modules"),
    }
    output = {"schemaVersion":"yosoi.benchmark.http-results.v1","count":args.count,"campaigns":args.campaigns,"summaries":summaries,"packageSizes":package_sizes}
    (args.output / "summary.json").write_text(json.dumps(output, indent=2) + "\n")
    print(args.output / "summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
