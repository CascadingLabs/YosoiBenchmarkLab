from __future__ import annotations

import argparse
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
        campaigns = []
        for line in (directory / relativePath).read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if record["recordType"] == "campaign":
                campaigns.append(record)
            candidate = record.get("adapterResult", record)
            if "terminalStatus" not in candidate:
                continue
            expected = expectedByTask[candidate["task"]]
            if candidate["terminalStatus"] != "ok" or candidate["values"] != expected:
                raise RuntimeError(
                    f"parser correctness gate failed: {relativePath}/{candidate.get('armId')}"
                )
            if candidate.get("armId") == "lolHtml" and record["recordType"] == "preflight":
                parity = candidate.get("chunkParity", [])
                if {item["chunkSize"] for item in parity} != {1, 7, 65536} or not all(item["exactOutput"] for item in parity):
                    raise RuntimeError("lol_html chunk-boundary correctness evidence is incomplete")
            records += 1
        summary = loadJson((directory / relativePath).with_name("summary.json"))
        for row in summary["summaries"]:
            group = [record for record in campaigns if all(record[key] == row[key] for key in ("armId", "task", "phase"))]
            expectedCampaigns = summary["configuration"]["campaigns"]
            if len(group) != expectedCampaigns or row["campaigns"] != expectedCampaigns:
                raise RuntimeError("parser campaign count differs")
            sampleKey = "cavemanSamples" if row["task"] == "caveman" else "hardSamples"
            operationsKey = "cavemanOperations" if row["task"] == "caveman" else "hardOperations"
            if any(len(record["samplesNs"]) != summary["configuration"][sampleKey]
                   or record["operationsPerSample"] != summary["configuration"][operationsKey]
                   for record in group):
                raise RuntimeError("parser sample or operation count differs")
            expected = statistics.median(statistics.median(record["samplesNs"]) for record in group)
            if row["medianOfCampaignMediansNs"] != expected:
                raise RuntimeError("parser timing summary differs from raw samples")
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


def verifyBrowser(directory: Path, allowNonRanked: bool = False) -> int:
    records = [
        json.loads(line)
        for line in (directory / "raw/browser-results.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    expected = [f"value-{index}" for index in range(4)]
    for record in records:
        correct = record["terminalStatus"] == "ok" and record["values"] == expected
        cleaned = record["cleanupComplete"] and not record["residualChromiumPids"]
        retainedFailure = allowNonRanked and record["terminalStatus"] in (
            "resourceLimit", "timeout", "error", "wrongOutput"
        ) and record.get("admitted") is False
        if (not correct and not retainedFailure) or not cleaned:
            raise RuntimeError(f"browser correctness or cleanup gate failed: {record['armId']}")
    summary = loadJson(directory / "raw/summary.json")
    if allowNonRanked:
        for row in summary["summaries"]:
            group = [record for record in records if record["armId"] == row["armId"] and record["concurrency"] == row["concurrency"]]
            if len(group) != summary["campaigns"]:
                raise RuntimeError("browser campaign attempts are incomplete")
            allPassed = all(record["terminalStatus"] == "ok" for record in group)
            if row.get("rankable", True) != allPassed:
                raise RuntimeError("browser rankability does not match raw outcomes")
            if not allPassed and any(key.startswith("median") for key in row):
                raise RuntimeError("failed browser group contains ranked timing")
        if len(records) != 4 * 3 * summary["campaigns"] or len(summary["summaries"]) != 12:
            raise RuntimeError("browser matrix population is incomplete")
    verifyMedianSummary(
        records,
        [row for row in summary["summaries"] if row.get("rankable", True)],
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, default=REPOSITORY / "evidence/baseline-v1.json")
    args = parser.parse_args()
    baseline = loadJson(args.baseline)
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
        verifier = verifiers[quadrant["id"]]
        count = verifyBrowser(directory, baseline.get("allowNonRankedBrowserOutcomes", False)) if quadrant["id"] == "renderedAcquisition" else verifier(directory)
        results["quadrants"][quadrant["id"]] = {
            "manifestFiles": verifyManifest(directory),
            "retainedRecords": count,
        }
        if quadrant["id"] == "renderedAcquisition" and baseline.get("allowNonRankedBrowserOutcomes", False):
            records = [json.loads(line) for line in (directory / "raw/browser-results.jsonl").read_text().splitlines()]
            results["quadrants"][quadrant["id"]]["nonRankedRecords"] = sum(record["terminalStatus"] != "ok" for record in records)
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
