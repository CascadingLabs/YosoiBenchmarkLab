from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

if __package__:
    from tools.runV2Matrix import run, summarize
else:
    from runV2Matrix import run, summarize


SEED = 0x45585452414354


def fixtureMap(manifest: dict[str, Any], root: Path) -> dict[tuple[str, str], Path]:
    return {
        (fixture["documentClass"], fixture["size"]): root / fixture["path"]
        for fixture in manifest["fixtures"]
    }


def command(
    binary: Path,
    arm: str,
    phase: str,
    fixture: Path,
    samples: int,
    operations: int,
    *,
    cell: str = "contracts.html.products",
    documentClass: str = "contractHtml",
) -> list[str]:
    value = [
        str(binary),
        "--cell", cell,
        "--document-class", documentClass,
        "--query-family", "contract",
        "--expression", "products",
        "--projection", "records",
        "--phase", phase,
        "--fixture", str(fixture),
        "--samples", str(samples),
        "--operations", str(operations),
    ]
    if arm != "yosoiRust":
        value[1:1] = ["--arm", arm]
    return value


def recordCount(result: dict[str, Any]) -> int:
    if result.get("recordCount") is not None:
        return int(result["recordCount"])
    values = result.get("values", [])
    if len(values) != 1:
        raise RuntimeError(f"record control emitted unexpected values: {values}")
    return int(values[0]["value"]["count"])


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
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text())
    lane = spec["extractionLane"]
    manifest = json.loads((args.fixtures / "manifest.json").read_text())
    fixtures = fixtureMap(manifest, args.fixtures)
    counts = spec["sizes"]
    campaigns = args.campaigns or spec["campaigns"]
    samples = args.samples or spec["samplesPerCampaign"]
    operations = args.operations or spec["operationsPerSample"]
    args.output.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []

    with (args.output / "raw.jsonl").open("w") as raw:
        for sizeIndex, size in enumerate(lane["sizes"]):
            for phaseIndex, phase in enumerate(lane["phases"]):
                arms = ["yosoiRust"]
                if phase in lane["controlPhases"]:
                    arms.append(lane["controlArm"])
                for campaign in range(campaigns):
                    order = list(arms)
                    random.Random(SEED + sizeIndex * 1000 + phaseIndex * 100 + campaign).shuffle(order)
                    for arm in order:
                        binary = args.yosoi if arm == "yosoiRust" else args.controls
                        result = run(
                            command(
                                binary,
                                arm,
                                phase,
                                fixtures[("sourceHtml", size)],
                                samples,
                                operations,
                            ),
                            args.repository,
                        )
                        if result["terminalStatus"] != "ok" or recordCount(result) != counts[size]:
                            raise RuntimeError(
                                f"extraction correctness gate failed: {arm}/{size}/{phase}"
                            )
                        result.update(
                            {
                                "size": size,
                                "campaignIndex": campaign,
                                "armOrder": order,
                                "equivalence": "product" if arm == "yosoiRust" else "nearestPrimitive",
                            }
                        )
                        records.append(result)
                        raw.write(json.dumps(result, separators=(",", ":")) + "\n")
                        raw.flush()

        for laneIndex, compatibility in enumerate(spec["extractionCompatibilityLanes"]):
            for sizeIndex, size in enumerate(compatibility["sizes"]):
                for campaign in range(campaigns):
                    result = run(
                        command(
                            args.yosoi,
                            "yosoiRust",
                            compatibility["phase"],
                            fixtures[(compatibility["documentClass"], size)],
                            samples,
                            operations,
                            cell=compatibility["id"],
                            documentClass=compatibility["documentClass"],
                        ),
                        args.repository,
                    )
                    count = recordCount(result)
                    expectedOutcome = compatibility["expectedOutcome"]
                    passed = (
                        (expectedOutcome == "fixtureRecordCount" and count == counts[size])
                        or (expectedOutcome == "oneRecord" and count == 1)
                        or (
                            expectedOutcome == "oneValidationIssue"
                            and count == 0
                            and result["values"] == [
                                {"kind": "rejected_records", "value": {"records": 0, "issues": 1}}
                            ]
                        )
                    )
                    if result["terminalStatus"] != "ok" or not passed:
                        raise RuntimeError(
                            f"compatibility extraction gate failed: {compatibility['id']}/{size}"
                        )
                    result.update(
                        {
                            "size": size,
                            "campaignIndex": campaign,
                            "armOrder": ["yosoiRust"],
                            "equivalence": "product",
                            "laneOrder": laneIndex,
                        }
                    )
                    records.append(result)
                    raw.write(json.dumps(result, separators=(",", ":")) + "\n")
                    raw.flush()

    limitRecords = []
    for limit in spec["extractionLimitLanes"]:
        result = run(
            command(
                args.yosoi,
                "yosoiRust",
                "resourceBounded",
                fixtures[(limit["documentClass"], limit["size"])],
                1,
                1,
                cell=limit["id"],
                documentClass=limit["documentClass"],
            ),
            args.repository,
        )
        passed = (
            result["terminalStatus"] == "ok"
            and result.get("recordCount") == 0
            and len(result["values"]) == 1
            and result["values"][0].get("kind") == "resource_bounded"
        )
        limitRecord = {
            "id": limit["id"],
            "documentClass": limit["documentClass"],
            "size": limit["size"],
            "expectedStatus": limit["expectedStatus"],
            "observedStatus": "resourceBounded" if passed else "wrongOutcome",
            "passed": passed,
            "value": result["values"][0] if result["values"] else None,
        }
        limitRecords.append(limitRecord)
        if not passed:
            raise RuntimeError(f"extraction resource-bound gate failed: {limitRecord}")

    output = {
        "schemaVersion": "yosoi.benchmark.extraction-summary.v2",
        "purpose": "internalNonKpiDiagnostics",
        "campaigns": campaigns,
        "samplesPerCampaign": samples,
        "operationsPerSample": operations,
        "recordCount": len(records),
        "summaries": summarize(records),
    }
    (args.output / "summary.json").write_text(json.dumps(output, indent=2) + "\n")
    (args.output / "limit-results.json").write_text(
        json.dumps(
            {"schemaVersion": "yosoi.benchmark.extraction-limits.v2", "records": limitRecords},
            indent=2,
        )
        + "\n"
    )
    print(args.output / "summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
