from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import subprocess
import time
from pathlib import Path

ARMS = ["yosoiBrowserRequest", "scraplingDynamicFetcher", "crawleePlaywright", "directPlaywright"]
SEED = 0x594F534F49


def chromium_pids() -> set[int]:
    result = set()
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            executable = os.readlink(entry / "exe")
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if Path(executable).name == "chromium":
            result.add(int(entry.name))
    return result


def tree_rss(pid: int) -> int:
    try:
        return int(next(line for line in Path(f"/proc/{pid}/status").read_text().splitlines() if line.startswith("VmRSS:")).split()[1]) * 1024
    except (FileNotFoundError, StopIteration, ProcessLookupError):
        return 0


def command(args: argparse.Namespace, arm: str, concurrency: int) -> tuple[list[str], Path]:
    common = ["--base", args.base, "--count", str(args.count), "--concurrency", str(concurrency), "--delay-ms", str(args.delay_ms)]
    if arm == "yosoiBrowserRequest":
        return [str(args.yosoi), *common], args.repository
    if arm == "scraplingDynamicFetcher":
        return [str(args.python), str(args.repository / "adapters/browser/python/adapter.py"), *common, "--executable", str(args.chromium)], args.repository
    script = "directPlaywright.mjs" if arm == "directPlaywright" else "adapter.mjs"
    return ["node", script, *common, "--executable", str(args.chromium)], args.repository / "adapters/browser/node-crawlee"


def run(command_value: list[str], cwd: Path) -> dict:
    baseline = chromium_pids()
    env = os.environ.copy(); env["NODE_OPTIONS"] = "--max-old-space-size=1536"
    started = time.perf_counter_ns()
    process = subprocess.Popen(command_value, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    rss = []
    while process.poll() is None:
        rss.append(tree_rss(process.pid) + sum(tree_rss(pid) for pid in chromium_pids() - baseline))
        time.sleep(0.02)
    stdout, stderr = process.communicate(timeout=5)
    outer = time.perf_counter_ns() - started
    if process.returncode != 0:
        raise RuntimeError(f"browser adapter failed: {stderr}\n{stdout}")
    result = next(json.loads(line) for line in reversed(stdout.splitlines()) if line.startswith("{"))
    deadline = time.monotonic() + 5
    residual = chromium_pids() - baseline
    while residual and time.monotonic() < deadline:
        time.sleep(0.1); residual = chromium_pids() - baseline
    result.update({"outerWallNs":outer,"peakRssBytes":max(rss or [0]),"meanRssBytes":int(statistics.fmean(rss or [0])),"cleanupComplete":not residual,"residualChromiumPids":sorted(residual),"stderr":stderr[-4096:]})
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, required=True); parser.add_argument("--base", required=True)
    parser.add_argument("--python", type=Path, required=True); parser.add_argument("--yosoi", type=Path, required=True)
    parser.add_argument("--chromium", type=Path, required=True); parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=4); parser.add_argument("--campaigns", type=int, default=3); parser.add_argument("--delay-ms", type=int, default=20)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    records = []
    with (args.output / "raw.jsonl").open("w") as raw:
        for concurrency in (1,2,4):
            for campaign in range(args.campaigns):
                order=list(ARMS); random.Random(SEED+concurrency*10+campaign).shuffle(order)
                for arm in order:
                    cmd,cwd=command(args,arm,concurrency); result=run(cmd,cwd)
                    expected=[f"value-{i}" for i in range(args.count)]
                    if result["terminalStatus"]!="ok" or result["values"]!=expected or not result["cleanupComplete"]:
                        raise RuntimeError(f"gate failed: {arm}/c{concurrency}: {result}")
                    result.update({"campaignIndex":campaign,"armOrder":order}); records.append(result); raw.write(json.dumps(result,separators=(",",":"))+"\n"); raw.flush()
    summaries=[]
    for arm in ARMS:
        for concurrency in (1,2,4):
            group=[r for r in records if r["armId"]==arm and r["concurrency"]==concurrency]
            summaries.append({"armId":arm,"concurrency":concurrency,"campaigns":len(group),"medianWallNs":statistics.median(r["wallNs"] for r in group),"medianOuterWallNs":statistics.median(r["outerWallNs"] for r in group),"medianThroughputRequestsPerSecond":statistics.median(r["throughputRequestsPerSecond"] for r in group),"medianPeakRssBytes":statistics.median(r["peakRssBytes"] for r in group),"medianMeanRssBytes":statistics.median(r["meanRssBytes"] for r in group)})
    (args.output/"summary.json").write_text(json.dumps({"schemaVersion":"yosoi.benchmark.browser-results.v1","count":args.count,"campaigns":args.campaigns,"chromium":str(args.chromium),"summaries":summaries},indent=2)+"\n")
    print(args.output/"summary.json"); return 0


if __name__ == "__main__": raise SystemExit(main())
