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
from collections import defaultdict
from pathlib import Path
from typing import Any

SEED = 0x594F534F49
PYTHON_ARMS = {
    "beautifulSoupHtmlParser": "beautifulsoup4",
    "beautifulSoupLxml": "beautifulsoup4",
    "lxml": "lxml",
    "parsel": "parsel",
    "scraplingParser": "scrapling",
    "selectolaxLexbor": "selectolax",
}
BINARY_ARMS = ["yosoiRust", "rustScraper", "goquery", "lolHtml"]
PHASES = ["parse", "locate", "endToEnd"]


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def command_for(
    repository: Path,
    python: Path,
    artifacts: Path,
    arm: str,
    fixture: Path,
    task: str,
    phase: str,
    samples: int,
    operations: int,
) -> list[str]:
    common = [
        "--fixture",
        str(fixture),
        "--task",
        task,
        "--phase",
        phase,
        "--samples",
        str(samples),
        "--operations",
        str(operations),
    ]
    if arm in PYTHON_ARMS:
        return [str(python), str(repository / "adapters" / "python" / "adapter.py"), "--arm", arm, *common]
    if arm == "lolHtml":
        return [str(artifacts / arm), *common, "--manifest", str(fixture.parent / "manifest.json"), "--chunk-size", "65536"]
    return [str(artifacts / arm), *common]


def run_json(command: list[str], timeout: int = 900) -> tuple[dict[str, Any], int]:
    started = time.perf_counter_ns()
    completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout)
    elapsed = time.perf_counter_ns() - started
    return json.loads(completed.stdout), elapsed


def process_tree_rss(root_pid: int) -> tuple[int, int]:
    parent_by_pid: dict[int, int] = {}
    rss_by_pid: dict[int, int] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            status = (entry / "status").read_text(encoding="utf-8")
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        parent = None
        rss_kib = 0
        for line in status.splitlines():
            if line.startswith("PPid:"):
                parent = int(line.split()[1])
            elif line.startswith("VmRSS:"):
                rss_kib = int(line.split()[1])
        if parent is not None:
            pid = int(entry.name)
            parent_by_pid[pid] = parent
            rss_by_pid[pid] = rss_kib * 1024

    members = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, parent in parent_by_pid.items():
            if parent in members and pid not in members:
                members.add(pid)
                changed = True
    return sum(rss_by_pid.get(pid, 0) for pid in members), len(members)


def run_resource(command: list[str], interval_seconds: float = 0.01) -> dict[str, Any]:
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.perf_counter_ns()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    samples: list[int] = []
    max_processes = 1
    while process.poll() is None:
        rss, process_count = process_tree_rss(process.pid)
        samples.append(rss)
        max_processes = max(max_processes, process_count)
        time.sleep(interval_seconds)
    stdout, stderr = process.communicate()
    elapsed = time.perf_counter_ns() - started
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    if process.returncode != 0:
        raise RuntimeError(f"resource command failed: {stderr.strip()}")
    result = json.loads(stdout)
    if not samples:
        samples.append(0)
    interval_ns = int(interval_seconds * 1_000_000_000)
    return {
        "adapterResult": result,
        "wallNs": elapsed,
        "aggregatePeakRssBytes": max(samples),
        "aggregateMeanRssBytes": int(statistics.fmean(samples)),
        "aggregateP95RssBytes": int(percentile([float(value) for value in samples], 0.95)),
        "rssAreaByteNs": sum(samples) * interval_ns,
        "rssSampleCount": len(samples),
        "rssSampleIntervalNs": interval_ns,
        "processCount": max_processes,
        "userCpuNs": int((after.ru_utime - before.ru_utime) * 1_000_000_000),
        "systemCpuNs": int((after.ru_stime - before.ru_stime) * 1_000_000_000),
    }


def directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def summarize_campaigns(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[(record["armId"], record["task"], record["phase"])].append(record)
    summaries = []
    for (arm, task, phase), group in sorted(grouped.items()):
        campaign_medians = [statistics.median(item["samplesNs"]) for item in group]
        all_samples = [value for item in group for value in item["samplesNs"]]
        input_bytes = group[0]["inputBytes"]
        median_ns = statistics.median(campaign_medians)
        summaries.append(
            {
                "armId": arm,
                "task": task,
                "phase": phase,
                "campaigns": len(group),
                "medianOfCampaignMediansNs": median_ns,
                "campaignMedianMinimumNs": min(campaign_medians),
                "campaignMedianMaximumNs": max(campaign_medians),
                "p95AllSamplesNs": percentile([float(value) for value in all_samples], 0.95),
                "meanAllSamplesNs": statistics.fmean(all_samples),
                "throughputInputBytesPerSecond": input_bytes / (median_ns / 1_000_000_000),
            }
        )
    return summaries


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--campaigns", type=int, default=5)
    parser.add_argument("--caveman-samples", type=int, default=100)
    parser.add_argument("--hard-samples", type=int, default=30)
    parser.add_argument("--caveman-operations", type=int, default=10)
    parser.add_argument("--hard-operations", type=int, default=1)
    parser.add_argument("--tasks", default="caveman,hard")
    parser.add_argument("--arms")
    parser.add_argument("--skip-resource", action="store_true")
    args = parser.parse_args()

    repository = Path(__file__).resolve().parents[1]
    manifest = json.loads((args.fixtures / "manifest.json").read_text(encoding="utf-8"))
    all_fixtures = {
        "caveman": next(item for item in manifest["fixtures"] if item["id"] == "cavemanCatalog"),
        "hard": next(item for item in manifest["fixtures"] if item["id"] == "hardCatalog"),
    }
    selected_tasks = [item.strip() for item in args.tasks.split(",") if item.strip()]
    if not selected_tasks or any(item not in all_fixtures for item in selected_tasks):
        parser.error("tasks must be a comma-separated subset of caveman,hard")
    fixture_by_task = {task: all_fixtures[task] for task in selected_tasks}
    all_arms = [*PYTHON_ARMS, *BINARY_ARMS]
    default_arms = all_arms if selected_tasks == ["caveman"] else [arm for arm in all_arms if arm != "lolHtml"]
    arms = [item.strip() for item in args.arms.split(",") if item.strip()] if args.arms else default_arms
    if not arms or any(item not in all_arms for item in arms):
        parser.error("arms contains an unknown or empty arm")
    args.output.mkdir(parents=True, exist_ok=True)
    raw_path = args.output / "raw.jsonl"
    campaign_records: list[dict[str, Any]] = []
    cold_records: list[dict[str, Any]] = []
    resource_records: list[dict[str, Any]] = []
    identities: dict[str, dict[str, Any]] = {}

    with raw_path.open("w", encoding="utf-8") as raw:
        for arm in arms:
            for task, fixture in fixture_by_task.items():
                command = command_for(
                    repository,
                    args.python,
                    args.artifacts,
                    arm,
                    args.fixtures / fixture["path"],
                    task,
                    "endToEnd",
                    0,
                    1,
                )
                if arm == "lolHtml":
                    command.extend(["--check-chunk-sizes", "1,7,65536"])
                result, outer_wall = run_json(command)
                if result["values"] != fixture["expectedValues"]:
                    raise RuntimeError(f"correctness failure for {arm}/{task}")
                identities[arm] = {
                    key: result.get(key)
                    for key in ("armId", "language", "runtime", "productVersion", "sourceRevision")
                    if result.get(key) is not None
                }
                record = {"recordType": "preflight", "outerWallNs": outer_wall, **result}
                raw.write(json.dumps(record, separators=(",", ":")) + "\n")

        for campaign in range(args.campaigns):
            order = list(arms)
            random.Random(SEED + campaign).shuffle(order)
            for arm in order:
                for task, fixture in fixture_by_task.items():
                    samples = args.caveman_samples if task == "caveman" else args.hard_samples
                    operations = args.caveman_operations if task == "caveman" else args.hard_operations
                    for phase in (["endToEnd"] if arm == "lolHtml" else PHASES):
                        command = command_for(
                            repository,
                            args.python,
                            args.artifacts,
                            arm,
                            args.fixtures / fixture["path"],
                            task,
                            phase,
                            samples,
                            operations,
                        )
                        result, outer_wall = run_json(command)
                        if result["values"] != fixture["expectedValues"]:
                            raise RuntimeError(f"measured correctness failure for {arm}/{task}/{phase}")
                        record = {
                            "recordType": "campaign",
                            "campaignIndex": campaign,
                            "armOrder": order,
                            "outerWallNs": outer_wall,
                            **result,
                        }
                        campaign_records.append(record)
                        raw.write(json.dumps(record, separators=(",", ":")) + "\n")
                        raw.flush()

        if "caveman" in fixture_by_task:
            caveman = fixture_by_task["caveman"]
            for arm in arms:
                samples = []
                for campaign in range(args.campaigns):
                    command = command_for(
                        repository,
                        args.python,
                        args.artifacts,
                        arm,
                        args.fixtures / caveman["path"],
                        "caveman",
                        "endToEnd",
                        0,
                        1,
                    )
                    result, outer_wall = run_json(command)
                    if result["values"] != caveman["expectedValues"]:
                        raise RuntimeError(f"cold correctness failure for {arm}")
                    samples.append(outer_wall)
                record = {"recordType": "cold", "armId": arm, "task": "caveman", "samplesNs": samples}
                cold_records.append(record)
                raw.write(json.dumps(record, separators=(",", ":")) + "\n")

        if "hard" in fixture_by_task and not args.skip_resource:
            hard = fixture_by_task["hard"]
            for arm in arms:
                command = command_for(
                    repository,
                    args.python,
                    args.artifacts,
                    arm,
                    args.fixtures / hard["path"],
                    "hard",
                    "endToEnd",
                    1,
                    2,
                )
                record = {"recordType": "resource", "armId": arm, "task": "hard", **run_resource(command)}
                if record["adapterResult"]["values"] != hard["expectedValues"]:
                    raise RuntimeError(f"resource correctness failure for {arm}")
                resource_records.append(record)
                raw.write(json.dumps(record, separators=(",", ":")) + "\n")

    package_names = {PYTHON_ARMS[arm] for arm in arms if arm in PYTHON_ARMS}
    if "beautifulSoupLxml" in arms:
        package_names.add("lxml")
    package_command = [
        str(args.python),
        str(repository / "adapters" / "python" / "packageSize.py"),
        "--packages",
        ",".join(sorted(package_names)),
    ]
    python_packages = {"packages": {}}
    if any(arm in PYTHON_ARMS for arm in arms):
        python_packages, _ = run_json(package_command)
    package_records: dict[str, dict[str, Any]] = {}
    for arm, package in PYTHON_ARMS.items():
        if arm not in arms:
            continue
        installed_bytes = python_packages["packages"][package]["installedPackageBytes"]
        distributions = list(python_packages["packages"][package]["distributions"])
        if arm == "beautifulSoupLxml":
            installed_bytes += python_packages["packages"]["lxml"]["installedPackageBytes"]
            distributions.extend(python_packages["packages"]["lxml"]["distributions"])
        package_records[arm] = {
            **python_packages["packages"][package],
            "installedPackageBytes": installed_bytes,
            "distributions": sorted(set(distributions)),
            "runnableEnvironmentBytes": python_packages["runnableEnvironmentBytes"],
            "artifactBytes": None,
            "streamingMode": "fullBuffer",
        }
    for arm in BINARY_ARMS:
        if arm not in arms:
            continue
        size = (args.artifacts / arm).stat().st_size
        package_records[arm] = {
            "directInstalledBytes": size,
            "installedPackageBytes": size,
            "runnableEnvironmentBytes": size,
            "artifactBytes": size,
            "streamingMode": "incremental" if arm == "lolHtml" else "fullBuffer",
        }

    summaries = summarize_campaigns(campaign_records)
    result = {
        "schemaVersion": "yosoi.benchmark.exploratory-results.v1",
        "fixtureManifest": manifest,
        "configuration": {
            "campaigns": args.campaigns,
            "cavemanSamples": args.caveman_samples,
            "hardSamples": args.hard_samples,
            "cavemanOperations": args.caveman_operations,
            "hardOperations": args.hard_operations,
        },
        "identities": identities,
        "summaries": summaries,
        "cold": cold_records,
        "resources": resource_records,
        "packages": package_records,
    }
    (args.output / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def summary_for(task: str, phase: str) -> list[dict[str, Any]]:
        return sorted(
            (item for item in summaries if item["task"] == task and item["phase"] == phase),
            key=lambda item: item["medianOfCampaignMediansNs"],
        )

    lines = ["# Exploratory parser/selector results", "", "Correctness-gated local run. Lower is better for latency and RSS; higher is better for throughput.", ""]
    for task, title in (("caveman", "Caveman end-to-end"), ("hard", "Hard catalog end-to-end")):
        if task not in fixture_by_task:
            continue
        lines.extend([f"## {title}", ""])
        rows = []
        for item in summary_for(task, "endToEnd"):
            rows.append(
                [
                    item["armId"],
                    f"{item['medianOfCampaignMediansNs'] / 1_000_000:.3f}",
                    f"{item['p95AllSamplesNs'] / 1_000_000:.3f}",
                    f"{item['throughputInputBytesPerSecond'] / 1_000_000:.2f}",
                ]
            )
        lines.extend([markdown_table(["Arm", "Median ms", "P95 ms", "Input MB/s"], rows), ""])

    if cold_records:
        lines.extend(["## Caveman cold process", ""])
        cold_rows = []
        for item in sorted(cold_records, key=lambda value: statistics.median(value["samplesNs"])):
            cold_rows.append([item["armId"], f"{statistics.median(item['samplesNs']) / 1_000_000:.3f}"])
        lines.extend([markdown_table(["Arm", "Median ms"], cold_rows), ""])

    if resource_records:
        lines.extend(["## Hard-catalog resource pass", ""])
        resource_rows = []
        by_resource = {item["armId"]: item for item in resource_records}
        for arm in sorted(arms, key=lambda value: by_resource[value]["aggregatePeakRssBytes"]):
            item = by_resource[arm]
            package = package_records[arm]
            resource_rows.append(
                [
                    arm,
                    f"{item['aggregatePeakRssBytes'] / 1_048_576:.1f}",
                    f"{item['aggregateMeanRssBytes'] / 1_048_576:.1f}",
                    f"{package['installedPackageBytes'] / 1_048_576:.1f}",
                    identities[arm]["language"],
                    package["streamingMode"],
                ]
            )
        lines.extend(
            [
                markdown_table(
                    ["Arm", "Peak RSS MiB", "Mean RSS MiB", "Installed MiB", "Language", "Streaming"],
                    resource_rows,
                ),
                "",
                "Package numbers for Python are installed distribution closures in the shared benchmark environment; compressed wheel sizes were not retained in this exploratory run.",
                "",
            ]
        )
    (args.output / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(args.output / "summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
