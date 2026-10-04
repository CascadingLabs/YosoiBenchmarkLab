from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path
from typing import Any


REPOSITORY = Path(__file__).resolve().parents[1]


def loadJson(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verifyManifest(directory: Path) -> int:
    manifestPath = directory / "evidenceManifest.json"
    manifest = loadJson(manifestPath)
    for item in manifest["files"]:
        path = directory / item["path"]
        if not path.is_file():
            raise RuntimeError(f"manifest file is missing: {path}")
        if path.stat().st_size != item["bytes"]:
            raise RuntimeError(f"manifest byte count differs: {path}")
        if sha256(path) != item["sha256"]:
            raise RuntimeError(f"manifest digest differs: {path}")
    return len(manifest["files"])


def verifyParser(directory: Path) -> int:
    fixtureManifest = loadJson(directory / "raw/fixtureManifest.json")
    expectedByTask = {
        "caveman": next(item for item in fixtureManifest["fixtures"] if item["id"] == "cavemanCatalog")["expectedValues"],
        "hard": next(item for item in fixtureManifest["fixtures"] if item["id"] == "hardCatalog")["expectedValues"],
    }
    records = 0
    for relativePath in (
        "raw/cavemanK5/raw.jsonl",
        "raw/hardK5/raw.jsonl",
        "raw/hardSmokeAndResources/raw.jsonl",
    ):
        for line in (directory / relativePath).read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            candidate = record.get("adapterResult", record)
            if "terminalStatus" not in candidate:
                continue
            expected = expectedByTask[candidate["task"]]
            if candidate["terminalStatus"] != "ok" or candidate["values"] != expected:
                raise RuntimeError(
                    f"parser correctness gate failed: {relativePath}/{candidate.get('armId')}"
                )
            records += 1
    return records


def verifyMedianSummary(
    records: list[dict[str, Any]],
    summaries: list[dict[str, Any]],
    groupKeys: tuple[str, ...],
    metricKeys: dict[str, str],
    campaigns: int,
) -> None:
    for summary in summaries:
        group = [
            record
            for record in records
            if all(record[key] == summary[key] for key in groupKeys)
        ]
        if len(group) != campaigns:
            identity = "/".join(str(summary[key]) for key in groupKeys)
            raise RuntimeError(f"campaign count differs for {identity}: {len(group)}")
        for summaryKey, recordKey in metricKeys.items():
            expected = statistics.median(record[recordKey] for record in group)
            if summary[summaryKey] != expected:
                raise RuntimeError(f"summary median differs for {summaryKey}: {summary}")


def verifyHttp(directory: Path) -> int:
    records = [
        json.loads(line)
        for line in (directory / "raw/http-results.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    expected = [f"value-{index}" for index in range(64)]
    for record in records:
        if record["terminalStatus"] != "ok" or record["values"] != expected:
            raise RuntimeError(f"HTTP correctness gate failed: {record['armId']}")
    summary = loadJson(directory / "raw/summary.json")
    verifyMedianSummary(
        records,
        summary["summaries"],
        ("armId", "workload", "concurrency"),
        {
            "medianWallNs": "wallNs",
            "medianOuterWallNs": "outerWallNs",
            "medianThroughputRequestsPerSecond": "throughputRequestsPerSecond",
            "medianPeakRssBytes": "peakRssBytes",
            "medianMeanRssBytes": "meanRssBytes",
            "medianUserCpuNs": "userCpuNs",
        },
        summary["campaigns"],
    )
    return len(records)


def verifyBrowser(directory: Path) -> int:
    records = [
        json.loads(line)
        for line in (directory / "raw/browser-results.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    expected = [f"value-{index}" for index in range(4)]
    for record in records:
        correct = record["terminalStatus"] == "ok" and record["values"] == expected
        cleaned = record["cleanupComplete"] and not record["residualChromiumPids"]
        if not correct or not cleaned:
            raise RuntimeError(f"browser correctness or cleanup gate failed: {record['armId']}")
    summary = loadJson(directory / "raw/summary.json")
    verifyMedianSummary(
        records,
        summary["summaries"],
        ("armId", "concurrency"),
        {
            "medianWallNs": "wallNs",
            "medianOuterWallNs": "outerWallNs",
            "medianThroughputRequestsPerSecond": "throughputRequestsPerSecond",
            "medianPeakRssBytes": "peakRssBytes",
            "medianMeanRssBytes": "meanRssBytes",
        },
        summary["campaigns"],
    )
    return len(records)


def main() -> int:
    baseline = loadJson(REPOSITORY / "evidence/baseline-v1.json")
    results: dict[str, Any] = {"schemaVersion": baseline["schemaVersion"], "quadrants": {}}
    verifiers = {
        "parserSelector": verifyParser,
        "httpAcquisition": verifyHttp,
        "renderedAcquisition": verifyBrowser,
    }
    for quadrant in baseline["quadrants"]:
        directory = REPOSITORY / quadrant["evidenceDirectory"]
        manifestPath = directory / "evidenceManifest.json"
        if sha256(manifestPath) != quadrant["evidenceManifestSha256"]:
            raise RuntimeError(f"baseline manifest digest differs: {manifestPath}")
        results["quadrants"][quadrant["id"]] = {
            "manifestFiles": verifyManifest(directory),
            "correctnessRecords": verifiers[quadrant["id"]](directory),
        }
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
