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


SEED = 0x594F534F4932


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def processTreeRss(rootPid: int) -> int:
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
    members = {rootPid}
    changed = True
    while changed:
        changed = False
        for pid, parent in parents.items():
            if parent in members and pid not in members:
                members.add(pid)
                changed = True
    return sum(rss.get(pid, 0) for pid in members)


def fixtureMap(manifest: dict[str, Any], root: Path) -> dict[tuple[str, str], Path]:
    return {
        (fixture["documentClass"], fixture["size"]): root / fixture["path"]
        for fixture in manifest["fixtures"]
    }


def command(
    args: argparse.Namespace,
    cell: dict[str, Any],
    arm: str,
    size: str,
    phase: str,
    fixture: Path,
    samples: int,
    operations: int,
) -> list[str]:
    binary = args.yosoi if arm == "yosoiRust" else args.controls
    value = [
        str(binary),
        "--cell", cell["id"],
        "--document-class", cell["documentClass"],
        "--query-family", cell["queryFamily"],
        "--expression", cell["expression"],
        "--projection", cell["projection"],
        "--phase", phase,
        "--fixture", str(fixture),
        "--samples", str(samples),
        "--operations", str(operations),
    ]
    if arm != "yosoiRust":
        value[1:1] = ["--arm", arm]
    namespace = cell.get("namespace")
    if arm == "yosoiRust" and namespace is not None:
        value.extend(["--namespace-prefix", namespace["prefix"], "--namespace-uri", namespace["uri"]])
    return value


def run(commandValue: list[str], cwd: Path) -> dict[str, Any]:
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.perf_counter_ns()
    process = subprocess.Popen(
        commandValue,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    rssSamples: list[int] = []
    while process.poll() is None:
        rssSamples.append(processTreeRss(process.pid))
        time.sleep(0.005)
    stdout, stderr = process.communicate()
    outerWall = time.perf_counter_ns() - started
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    if process.returncode != 0:
        raise RuntimeError(
            f"diagnostic arm failed: {' '.join(commandValue)}\n{stderr}\n{stdout}"
        )
    result = None
    for line in reversed(stdout.splitlines()):
        if line.startswith("{"):
            result = json.loads(line)
            break
    if result is None:
        raise RuntimeError(f"diagnostic arm emitted no JSON: {stdout}")
    samples = rssSamples or [0]
    result.update(
        {
            "outerWallNs": outerWall,
            "peakRssBytes": max(samples),
            "meanRssBytes": int(statistics.fmean(samples)),
            "p95RssBytes": int(percentile([float(value) for value in samples], 0.95)),
            "userCpuNs": int((after.ru_utime - before.ru_utime) * 1_000_000_000),
            "systemCpuNs": int((after.ru_stime - before.ru_stime) * 1_000_000_000),
            "stderr": stderr[-4096:],
        }
    )
    return result


def verifyResult(result: dict[str, Any], cell: dict[str, Any]) -> None:
    if result["terminalStatus"] != "ok":
        raise RuntimeError(f"terminal gate failed: {result['armId']}/{cell['id']}")
    if result["matchCount"] != cell["expectedMatchCount"]:
        raise RuntimeError(
            f"match-count gate failed: {result['armId']}/{cell['id']}: {result['matchCount']}"
        )
    expected = cell["expectedValues"]
    if expected is not None and result["values"] != expected:
        raise RuntimeError(
            f"value gate failed: {result['armId']}/{cell['id']}: {result['values']}"
        )


def summarize(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for record in records:
        key = (record["cellId"], record["armId"], record["size"], record["phase"])
        grouped.setdefault(key, []).append(record)
    summaries = []
    for (cell, arm, size, phase), group in sorted(grouped.items()):
        hashes = {record["outputSha256"] for record in group}
        if len(hashes) != 1:
            raise RuntimeError(f"output changed across campaigns: {cell}/{arm}/{size}/{phase}")
        campaignMedians = [statistics.median(record["samplesNs"]) for record in group]
        allSamples = [sample for record in group for sample in record["samplesNs"]]
        summaries.append(
            {
                "cellId": cell,
                "armId": arm,
                "size": size,
                "phase": phase,
                "campaigns": len(group),
                "medianOfCampaignMediansNs": statistics.median(campaignMedians),
                "campaignMedianMinimumNs": min(campaignMedians),
                "campaignMedianMaximumNs": max(campaignMedians),
                "p95AllSamplesNs": percentile([float(value) for value in allSamples], 0.95),
                "medianOuterWallNs": statistics.median(record["outerWallNs"] for record in group),
                "medianPeakRssBytes": statistics.median(record["peakRssBytes"] for record in group),
                "medianMeanRssBytes": statistics.median(record["meanRssBytes"] for record in group),
                "medianUserCpuNs": statistics.median(record["userCpuNs"] for record in group),
                "outputSha256": next(iter(hashes)),
            }
        )
    return summaries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--yosoi", type=Path, required=True)
    parser.add_argument("--controls", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--campaigns", type=int)
    parser.add_argument("--samples", type=int)
    parser.add_argument("--operations", type=int)
    parser.add_argument("--cells")
    parser.add_argument("--sizes")
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text())
    manifest = json.loads((args.fixtures / "manifest.json").read_text())
    fixtures = fixtureMap(manifest, args.fixtures)
    campaigns = args.campaigns or spec["campaigns"]
    samples = args.samples or spec["samplesPerCampaign"]
    operations = args.operations or spec["operationsPerSample"]
    selectedCells = set(args.cells.split(",")) if args.cells else None
    selectedSizes = args.sizes.split(",") if args.sizes else list(spec["sizes"])
    cells = [cell for cell in spec["cells"] if selectedCells is None or cell["id"] in selectedCells]
    if not cells:
        parser.error("no diagnostic cells selected")
    if any(size not in spec["sizes"] for size in selectedSizes):
        parser.error("sizes contains an unknown size")
    args.output.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    with (args.output / "raw.jsonl").open("w") as raw:
        for cellIndex, cell in enumerate(cells):
            for size in selectedSizes:
                fixture = fixtures[(cell["documentClass"], size)]
                for phaseIndex, phase in enumerate(cell["phases"]):
                    arms = ["yosoiRust"]
                    if cell["controlArm"] is not None and phase in cell["controlPhases"]:
                        arms.append(cell["controlArm"])
                    for campaign in range(campaigns):
                        order = list(arms)
                        random.Random(SEED + cellIndex * 1000 + phaseIndex * 100 + campaign).shuffle(order)
                        for arm in order:
                            result = run(
                                command(args, cell, arm, size, phase, fixture, samples, operations),
                                args.repository,
                            )
                            verifyResult(result, cell)
                            result.update(
                                {
                                    "size": size,
                                    "campaignIndex": campaign,
                                    "armOrder": order,
                                    "equivalence": "product" if arm == "yosoiRust" else cell["equivalence"],
                                }
                            )
                            records.append(result)
                            raw.write(json.dumps(result, separators=(",", ":")) + "\n")
                            raw.flush()

    output = {
        "schemaVersion": "yosoi.benchmark.diagnostic-summary.v2",
        "purpose": "internalNonKpiDiagnostics",
        "campaigns": campaigns,
        "samplesPerCampaign": samples,
        "operationsPerSample": operations,
        "cellCount": len(cells),
        "recordCount": len(records),
        "summaries": summarize(records),
        "artifacts": {
            "yosoiRustBytes": args.yosoi.stat().st_size,
            "controlsBytes": args.controls.stat().st_size,
        },
    }
    (args.output / "summary.json").write_text(json.dumps(output, indent=2) + "\n")
    print(args.output / "summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
