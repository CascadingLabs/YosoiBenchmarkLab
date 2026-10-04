from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def verifyManifest(root: Path) -> int:
    manifest = load(root / "evidenceManifest.json")
    for item in manifest["files"]:
        path = root / item["path"]
        if not path.is_file():
            raise RuntimeError(f"evidence file is missing: {path}")
        if path.stat().st_size != item["bytes"]:
            raise RuntimeError(f"evidence byte count differs: {path}")
        if sha256(path) != item["sha256"]:
            raise RuntimeError(f"evidence digest differs: {path}")
    return len(manifest["files"])


def verifySummaries(
    raw: list[dict[str, Any]], summaries: list[dict[str, Any]], campaigns: int
) -> None:
    for summary in summaries:
        group = [
            item
            for item in raw
            if (
                item["cellId"],
                item["armId"],
                item["size"],
                item["phase"],
            )
            == (
                summary["cellId"],
                summary["armId"],
                summary["size"],
                summary["phase"],
            )
        ]
        if len(group) != campaigns:
            raise RuntimeError(f"campaign count differs: {summary}")
        campaignMedians = [statistics.median(item["samplesNs"]) for item in group]
        if summary["medianOfCampaignMediansNs"] != statistics.median(campaignMedians):
            raise RuntimeError(f"campaign median differs: {summary}")
        if summary["medianOuterWallNs"] != statistics.median(item["outerWallNs"] for item in group):
            raise RuntimeError(f"outer wall median differs: {summary}")
        if summary["medianPeakRssBytes"] != statistics.median(item["peakRssBytes"] for item in group):
            raise RuntimeError(f"peak RSS median differs: {summary}")
        if len({item["outputSha256"] for item in group}) != 1:
            raise RuntimeError(f"output identity differs across campaigns: {summary}")


def verifyMatrix(root: Path, spec: dict[str, Any]) -> tuple[int, int]:
    raw = records(root / "raw/matrix-results.jsonl")
    summary = load(root / "raw/matrix-summary.json")
    expectedRecords = 0
    cells = {cell["id"]: cell for cell in spec["cells"]}
    requiredGroups = set()
    for cell in spec["cells"]:
        for size in cell["sizes"]:
            for phase in cell["phases"]:
                arms = ["yosoiRust"]
                if cell["controlArm"] and phase in cell["controlPhases"]:
                    arms.append(cell["controlArm"])
                expectedRecords += len(arms) * spec["campaigns"]
                for arm in arms:
                    requiredGroups.add((cell["id"], arm, size, phase))
    if len(raw) != expectedRecords:
        raise RuntimeError(f"matrix record count differs: {len(raw)} != {expectedRecords}")
    observedGroups = set()
    for item in raw:
        cell = cells[item["cellId"]]
        if item["terminalStatus"] != "ok" or item["matchCount"] != cell["expectedMatchCount"]:
            raise RuntimeError(f"matrix correctness gate failed: {item}")
        if cell["expectedValues"] is not None and item["values"] != cell["expectedValues"]:
            raise RuntimeError(f"matrix values differ: {item}")
        observedGroups.add((item["cellId"], item["armId"], item["size"], item["phase"]))
    if observedGroups != requiredGroups:
        raise RuntimeError("matrix coverage differs from the frozen cell set")
    verifySummaries(raw, summary["summaries"], spec["campaigns"])
    return len(raw), len(requiredGroups)


def verifyExtraction(root: Path, spec: dict[str, Any]) -> tuple[int, int]:
    raw = records(root / "raw/extraction-results.jsonl")
    summary = load(root / "raw/extraction-summary.json")
    lane = spec["extractionLane"]
    requiredGroups = set()
    for size in lane["sizes"]:
        for phase in lane["phases"]:
            requiredGroups.add((lane["id"], "yosoiRust", size, phase))
            if phase in lane["controlPhases"]:
                requiredGroups.add((lane["id"], lane["controlArm"], size, phase))
    compatibilityById = {item["id"]: item for item in spec["extractionCompatibilityLanes"]}
    for compatibility in spec["extractionCompatibilityLanes"]:
        for size in compatibility["sizes"]:
            requiredGroups.add(
                (
                    compatibility["id"],
                    "yosoiRust",
                    size,
                    compatibility["phase"],
                )
            )
    expectedRecords = len(requiredGroups) * spec["campaigns"]
    if len(raw) != expectedRecords:
        raise RuntimeError(f"extraction record count differs: {len(raw)} != {expectedRecords}")
    observedGroups = set()
    for item in raw:
        count = item.get("recordCount")
        if count is None:
            count = item["values"][0]["value"]["count"]
        if item["cellId"] == lane["id"]:
            correct = count == spec["sizes"][item["size"]]
        else:
            compatibility = compatibilityById[item["cellId"]]
            expected = compatibility["expectedOutcome"]
            correct = (
                (expected == "fixtureRecordCount" and count == spec["sizes"][item["size"]])
                or (expected == "oneRecord" and count == 1)
                or (
                    expected == "oneValidationIssue"
                    and count == 0
                    and item["values"]
                    == [{"kind": "rejected_records", "value": {"records": 0, "issues": 1}}]
                )
            )
        if item["terminalStatus"] != "ok" or not correct:
            raise RuntimeError(f"extraction correctness gate failed: {item}")
        observedGroups.add((item["cellId"], item["armId"], item["size"], item["phase"]))
    if observedGroups != requiredGroups:
        raise RuntimeError("extraction coverage differs from the frozen phase set")
    verifySummaries(raw, summary["summaries"], spec["campaigns"])
    return len(raw), len(requiredGroups)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    root = args.evidence
    files = verifyManifest(root)
    spec = load(root / "raw/diagnostics-v2.json")
    matrixRecords, matrixGroups = verifyMatrix(root, spec)
    extractionRecords, extractionGroups = verifyExtraction(root, spec)
    conformance = load(root / "raw/conformance-results.json")
    negative = load(root / "raw/negative-results.json")
    extractionLimits = load(root / "raw/extraction-limit-results.json")
    if len(conformance["records"]) != len(spec["correctnessCases"]) or not all(
        item["passed"] for item in conformance["records"]
    ):
        raise RuntimeError("conformance evidence is incomplete or failed")
    if not all(item["passed"] for item in negative["records"]):
        raise RuntimeError("negative evidence contains a failure")
    if len(extractionLimits["records"]) != len(spec["extractionLimitLanes"]) or not all(
        item["passed"] for item in extractionLimits["records"]
    ):
        raise RuntimeError("extraction resource-bound evidence is incomplete or failed")
    coverage = load(root / "coverage.json")
    if coverage["requiredCells"] != len(spec["cells"]) or coverage["measuredCells"] != len(spec["cells"]):
        raise RuntimeError("coverage summary does not prove every V2 cell")
    result = {
        "schemaVersion": "yosoi.benchmark.verification.v2",
        "manifestFiles": files,
        "matrixRecords": matrixRecords,
        "matrixGroups": matrixGroups,
        "extractionRecords": extractionRecords,
        "extractionGroups": extractionGroups,
        "conformanceCases": len(conformance["records"]),
        "negativeFixtures": len(negative["records"]),
        "extractionLimitCases": len(extractionLimits["records"]),
        "status": "verified",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
