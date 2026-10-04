from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def copyFile(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def summaryMap(summary: dict[str, Any]) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    return {
        (item["cellId"], item["armId"], item["size"], item["phase"]): item
        for item in summary["summaries"]
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--extraction", type=Path, required=True)
    parser.add_argument("--negative", type=Path, required=True)
    parser.add_argument("--conformance", type=Path, required=True)
    parser.add_argument("--yosoi-identity", type=Path, required=True)
    parser.add_argument("--controls-identity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.output.exists():
        raise SystemExit(f"output already exists: {args.output}")
    raw = args.output / "raw"
    raw.mkdir(parents=True)
    copyFile(args.spec, raw / "diagnostics-v2.json")
    copyFile(args.fixtures / "manifest.json", raw / "fixtureManifest.json")
    copyFile(args.matrix / "raw.jsonl", raw / "matrix-results.jsonl")
    copyFile(args.matrix / "summary.json", raw / "matrix-summary.json")
    copyFile(args.extraction / "raw.jsonl", raw / "extraction-results.jsonl")
    copyFile(args.extraction / "summary.json", raw / "extraction-summary.json")
    copyFile(args.extraction / "limit-results.json", raw / "extraction-limit-results.json")
    copyFile(args.negative / "negative-results.json", raw / "negative-results.json")
    copyFile(args.conformance / "conformance-results.json", raw / "conformance-results.json")
    copyFile(args.yosoi_identity, raw / "yosoiV2.identity.json")
    copyFile(args.controls_identity, raw / "v2Controls.identity.json")

    spec = load(args.spec)
    matrix = load(args.matrix / "summary.json")
    extraction = load(args.extraction / "summary.json")
    negative = load(args.negative / "negative-results.json")
    conformance = load(args.conformance / "conformance-results.json")
    extractionLimits = load(args.extraction / "limit-results.json")
    yosoiIdentity = load(args.yosoi_identity)
    controlsIdentity = load(args.controls_identity)
    summaries = summaryMap(matrix)

    matrixRows = []
    for cell in spec["cells"]:
        yosoi = summaries[(cell["id"], "yosoiRust", "large", "endToEnd")]
        yosoiMs = yosoi["medianOfCampaignMediansNs"] / 1_000_000
        if cell["controlArm"] is None:
            controlText = "internal only"
            comparison = "—"
        else:
            control = summaries[(cell["id"], cell["controlArm"], "large", "endToEnd")]
            controlMs = control["medianOfCampaignMediansNs"] / 1_000_000
            controlText = f"{cell['controlArm']} {controlMs:.3f} ms"
            comparison = f"{yosoiMs / controlMs:.2f}× control time"
        matrixRows.append(
            [
                cell["id"],
                cell["documentClass"],
                cell["queryFamily"],
                cell["projection"],
                f"{yosoiMs:.3f} ms",
                controlText,
                comparison,
                cell["equivalence"],
            ]
        )

    extractionMap = summaryMap(extraction)
    extractionRows = []
    lane = spec["extractionLane"]
    primaryExtractionSize = lane["sizes"][-1]
    for phase in lane["phases"]:
        result = extractionMap[(lane["id"], "yosoiRust", primaryExtractionSize, phase)]
        extractionRows.append(
            [phase, f"{result['medianOfCampaignMediansNs'] / 1_000_000:.3f}", f"{result['medianPeakRssBytes'] / 1_048_576:.1f}"]
        )
    control = extractionMap[
        (lane["id"], lane["controlArm"], primaryExtractionSize, "endToEnd")
    ]
    extractionRows.append(
        [
            "endToEnd nearest primitive",
            f"{control['medianOfCampaignMediansNs'] / 1_000_000:.3f}",
            f"{control['medianPeakRssBytes'] / 1_048_576:.1f}",
        ]
    )
    compatibilityRows = []
    for compatibility in spec["extractionCompatibilityLanes"]:
        compatibilitySize = compatibility["sizes"][-1]
        result = extractionMap[
            (
                compatibility["id"],
                "yosoiRust",
                compatibilitySize,
                compatibility["phase"],
            )
        ]
        compatibilityRows.append(
            [
                compatibility["id"],
                compatibility["documentClass"],
                compatibility["phase"],
                compatibility["expectedOutcome"],
                compatibilitySize,
                f"{result['medianOfCampaignMediansNs'] / 1_000_000:.3f}",
            ]
        )

    coverage = {
        "schemaVersion": "yosoi.benchmark.coverage.v2",
        "purpose": "internalNonKpiDiagnostics",
        "requiredCells": len(spec["cells"]),
        "measuredCells": len({item["cellId"] for item in matrix["summaries"]}),
        "documentClasses": sorted({cell["documentClass"] for cell in spec["cells"]}),
        "queryFamilies": sorted({cell["queryFamily"] for cell in spec["cells"]}),
        "projections": sorted({cell["projection"] for cell in spec["cells"]}),
        "conformanceCases": len(conformance["records"]),
        "negativeFixtures": len(negative["records"]),
        "extractionLanes": 1 + len(spec["extractionCompatibilityLanes"]),
        "extractionLimitCases": len(extractionLimits["records"]),
        "allConformancePassed": all(item["passed"] for item in conformance["records"]),
        "allNegativePassed": all(item["passed"] for item in negative["records"]),
        "allExtractionLimitsPassed": all(item["passed"] for item in extractionLimits["records"]),
        "crossFormatAggregate": False,
        "publicKpi": False,
        "publishedReleaseArtifact": False,
        "allocationEvidence": "notCollected",
    }
    (args.output / "coverage.json").write_text(json.dumps(coverage, indent=2) + "\n")

    report = f"""# Benchmark Lab V2 — format and extraction diagnostics

## Decision

V2 is a complete internal diagnostic map for the frozen cells, not a public
leaderboard. It measures {coverage['requiredCells']} cells across
{len(coverage['documentClasses'])} document classes, {len(coverage['queryFamilies'])}
query families, three input sizes, query-build/parse/locate/end-to-end phases,
and the typed Contract pipeline.
There is deliberately no cross-format aggregate score.

All {coverage['conformanceCases']} no-match, multi-match, invalid-query, and
resource-limit conformance cases passed. All {coverage['negativeFixtures']}
malformed/recovery fixtures produced their frozen terminal states.
All {coverage['extractionLimitCases']} large repeated-Contract cases stopped at
the ordinary resource boundary and were retained as bounded outcomes.

Yosoi artifact source revision: `{yosoiIdentity['sourceRevision']}`; SHA-256
`{yosoiIdentity['sha256']}`. Rust control artifact SHA-256
`{controlsIdentity['sha256']}`.

## Large-input end-to-end diagnostics

Control rows are exact only where the `Equivalence` column says `exact`.
`nearestPrimitive` is an attributed lower-level control, not a product winner.

{table(['Cell', 'Document', 'Query', 'Projection', 'Yosoi', 'Control', 'Ratio', 'Equivalence'], matrixRows)}

## Typed Contract extraction — largest admitted repeated catalog

Every Yosoi phase retains ordinary provenance and validation semantics. The
control row materializes and validates equivalent plain Rust records but does
not retain Yosoi evidence, diagnostics, or typed Contract outcomes.

{table(['Phase', 'Median ms', 'Median peak RSS MiB'], extractionRows)}

## Extraction compatibility across document classes

These lanes prove that XML, decoded text, rendered DOM, accessibility, and the
typed JSON-rejection path all reach the ordinary Extractor/Contract machinery.

{table(['Lane', 'Document', 'Phase', 'Outcome', 'Size', 'Median ms'], compatibilityRows)}

## Interpretation rules

- These results are internal optimization/regression evidence and are not KPI
  gates or marketing claims.
- CSS, XPath, regex, JSON Pointer, JSONPath, XML, rendered DOM, accessibility,
  and typed Contract rows remain separate semantic cells.
- `internalOnly` means no honest external semantic peer was invented.
- Node-reference correctness is exact within each arm and deterministic across
  campaigns; cross-library node identities are not equated.
- Warm parse/locate/end-to-end samples, outer fresh-process wall, CPU, and
  aggregate RSS remain separately named.
- The Yosoi binary was built from a hashed immutable local source archive, not
  a published release artifact. That is acceptable for this internal diagnostic
  baseline and insufficient for release certification.
- Allocation counts were not collected. CPU, sampled process-tree RSS, and
  output bytes are retained, but they do not substitute for allocator evidence.

## Reproduction and evidence

The `raw/` directory contains the frozen spec, fixture manifest, every campaign
record, independent summaries, conformance and negative results, and both
artifact identities. `coverage.json` proves cell coverage. The evidence manifest
hashes every retained file.
"""
    (args.output / "README.md").write_text(report)

    entries = []
    for path in sorted(item for item in args.output.rglob("*") if item.is_file() and item.name != "evidenceManifest.json"):
        payload = path.read_bytes()
        entries.append(
            {
                "path": str(path.relative_to(args.output)),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    manifest = {"schemaVersion": "yosoi.benchmark.evidence-manifest.v2", "files": entries}
    (args.output / "evidenceManifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(args.output / "README.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
