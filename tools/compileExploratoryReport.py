from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import statistics
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def summary_map(data: dict[str, Any], task: str) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (item["armId"], item["phase"]): item
        for item in data["summaries"]
        if item["task"] == task
    }


def criterion_summary(root: Path) -> list[dict[str, Any]]:
    results = []
    for group in sorted(path for path in root.iterdir() if path.is_dir()):
        values = []
        for estimates in sorted(group.glob("campaign*/estimates.json")):
            values.append(load(estimates)["median"]["point_estimate"])
        if values:
            arm, phase = group.name.split("_", 1)
            results.append(
                {
                    "armId": arm,
                    "phase": phase,
                    "campaigns": len(values),
                    "medianNs": statistics.median(values),
                    "minimumNs": min(values),
                    "maximumNs": max(values),
                }
            )
    return results


def copy_evidence(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--caveman", type=Path, required=True)
    parser.add_argument("--hard", type=Path, required=True)
    parser.add_argument("--smoke", type=Path, required=True)
    parser.add_argument("--criterion-yosoi", type=Path, required=True)
    parser.add_argument("--criterion-scraper", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--yosoi-identity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--captured-on", default="2026-09-27")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    raw = args.output / "raw"
    raw.mkdir(exist_ok=True)
    copy_evidence(args.caveman, raw / "cavemanK5")
    copy_evidence(args.hard, raw / "hardK5")
    copy_evidence(args.smoke, raw / "hardSmokeAndResources")
    copy_evidence(args.criterion_yosoi, raw / "criterionYosoiRust")
    copy_evidence(args.criterion_scraper, raw / "criterionRustScraper")
    shutil.copy2(args.fixtures / "manifest.json", raw / "fixtureManifest.json")
    shutil.copy2(args.yosoi_identity, raw / "yosoiRust.identity.json")

    caveman = load(args.caveman / "summary.json")
    hard = load(args.hard / "summary.json")
    smoke = load(args.smoke / "summary.json")
    caveman_map = summary_map(caveman, "caveman")
    hard_map = summary_map(hard, "hard")
    smoke_hard_map = summary_map(smoke, "hard")
    identities = caveman["identities"]
    packages = caveman["packages"]

    arms = sorted(identities)
    caveman_rows = []
    for arm in sorted(arms, key=lambda value: caveman_map[(value, "endToEnd")]["medianOfCampaignMediansNs"]):
        parse = f"{caveman_map[(arm, 'parse')]['medianOfCampaignMediansNs'] / 1_000_000:.3f}" if (arm, "parse") in caveman_map else "—"
        locate = f"{caveman_map[(arm, 'locate')]['medianOfCampaignMediansNs'] / 1_000_000:.3f}" if (arm, "locate") in caveman_map else "—"
        end_to_end = caveman_map[(arm, "endToEnd")]["medianOfCampaignMediansNs"] / 1_000_000
        p95 = caveman_map[(arm, "endToEnd")]["p95AllSamplesNs"] / 1_000_000
        throughput = caveman_map[(arm, "endToEnd")]["throughputInputBytesPerSecond"] / 1_000_000
        caveman_rows.append([arm, parse, locate, f"{end_to_end:.3f}", f"{p95:.3f}", f"{throughput:.2f}"])

    hard_rows = []
    all_hard = set(arm for arm, phase in hard_map if phase == "endToEnd") | {
        "beautifulSoupHtmlParser",
        "beautifulSoupLxml",
    }
    for arm in sorted(
        all_hard,
        key=lambda value: (hard_map.get((value, "endToEnd")) or smoke_hard_map[(value, "endToEnd")])["medianOfCampaignMediansNs"],
    ):
        item = hard_map.get((arm, "endToEnd")) or smoke_hard_map[(arm, "endToEnd")]
        label = "K=5 × 5" if (arm, "endToEnd") in hard_map else "single exploratory sample"
        hard_rows.append(
            [
                arm,
                f"{item['medianOfCampaignMediansNs'] / 1_000_000:.3f}",
                f"{item['p95AllSamplesNs'] / 1_000_000:.3f}",
                f"{item['throughputInputBytesPerSecond'] / 1_000_000:.2f}",
                label,
            ]
        )

    cold_rows = []
    for item in sorted(caveman["cold"], key=lambda value: statistics.median(value["samplesNs"])):
        cold_rows.append([item["armId"], f"{statistics.median(item['samplesNs']) / 1_000_000:.3f}"])

    resource_rows = []
    for item in sorted(smoke["resources"], key=lambda value: value["aggregatePeakRssBytes"]):
        arm = item["armId"]
        package = packages[arm]
        resource_rows.append(
            [
                arm,
                f"{item['aggregatePeakRssBytes'] / 1_048_576:.1f}",
                f"{item['aggregateMeanRssBytes'] / 1_048_576:.1f}",
                f"{item['aggregateP95RssBytes'] / 1_048_576:.1f}",
                f"{item['userCpuNs'] / 1_000_000_000:.3f}",
                f"{package['installedPackageBytes'] / 1_048_576:.2f}",
                f"{package['runnableEnvironmentBytes'] / 1_048_576:.2f}",
                identities[arm]["language"],
                package["streamingMode"],
            ]
        )

    criterion_rows = []
    criterion_data = criterion_summary(args.criterion_yosoi / "criterion") + criterion_summary(
        args.criterion_scraper / "criterion"
    )
    phase_order = {"parse": 0, "locate": 1, "endToEnd": 2}
    for item in sorted(criterion_data, key=lambda value: (value["armId"], phase_order[value["phase"]])):
        criterion_rows.append(
            [
                item["armId"],
                item["phase"],
                f"{item['medianNs'] / 1_000_000:.3f}",
                f"{item['minimumNs'] / 1_000_000:.3f}",
                f"{item['maximumNs'] / 1_000_000:.3f}",
                str(item["campaigns"]),
            ]
        )

    yosoi_caveman = caveman_map[("yosoiRust", "endToEnd")]["medianOfCampaignMediansNs"]
    parsel_caveman = caveman_map[("parsel", "endToEnd")]["medianOfCampaignMediansNs"]
    scraper_caveman = caveman_map[("rustScraper", "endToEnd")]["medianOfCampaignMediansNs"]
    yosoi_hard = hard_map[("yosoiRust", "endToEnd")]["medianOfCampaignMediansNs"]
    parsel_hard = hard_map[("parsel", "endToEnd")]["medianOfCampaignMediansNs"]
    scraper_hard = hard_map[("rustScraper", "endToEnd")]["medianOfCampaignMediansNs"]
    resource_by_arm = {item["armId"]: item for item in smoke["resources"]}

    fixture_manifest = load(args.fixtures / "manifest.json")
    fixture_text = ", ".join(
        f"{item['id']} {item['bytes']:,} bytes SHA-256 `{item['sha256']}`" for item in fixture_manifest["fixtures"]
    )

    best_caveman = min(arms, key=lambda arm: caveman_map[(arm, "endToEnd")]["medianOfCampaignMediansNs"])
    best_hard = min((arm for arm, phase in hard_map if phase == "endToEnd"),
                    key=lambda arm: hard_map[(arm, "endToEnd")]["medianOfCampaignMediansNs"])
    report = f"""# Exploratory parser and selector benchmark — {args.captured_on}

## Decision

The lowest retained end-to-end medians are **{best_caveman}** on caveman and **{best_hard}** on the repeated hard-catalog campaign. The tables below retain every admitted arm; these results apply to this source snapshot and host.

These are local exploratory results, not a public “fastest” claim.

## Inputs and correctness

{fixture_text}.

All {len(arms)} caveman arms returned the exact ordered value before timing. The hard suite separately gated its nine admitted arms against all 64 exact ordered values. No incorrect arm was ranked.

## Caveman warm timings — five campaigns

Each arm ran five fresh-process campaigns, 100 samples per campaign, 10 operations per sample. Values are the median of campaign medians; p95 is retained across the raw native samples.

{table(['Arm', 'Parse ms', 'Locate ms', 'End-to-end ms', 'P95 ms', 'Input MB/s'], caveman_rows)}

## Hard-catalog end-to-end

Seven arms ran five campaigns with five samples per campaign. Beautiful Soup retains correctness-gated single exploratory samples under the established resource-bounded protocol.

{table(['Arm', 'Median ms', 'P95 ms', 'Input MB/s', 'Evidence'], hard_rows)}

## Cold process

Fresh process start through one correctness-verified caveman output, five samples.

{table(['Arm', 'Median ms'], cold_rows)}

## Hard-catalog resources and package footprint

Resource evidence is one declared pass with 10 ms process-tree RSS sampling. Python installed sizes are distribution closures; the shared runnable environment includes Python 3.13. Compressed wheel sizes were not retained.

{table(['Arm', 'Peak RSS MiB', 'Mean RSS MiB', 'P95 RSS MiB', 'User CPU s', 'Installed MiB', 'Runnable MiB', 'Language', 'Streaming'], resource_rows)}

## Criterion confirmation for Rust

Five independent Criterion 0.7 campaigns per Rust arm, each with 3 s warm-up, 5 s measurement, and 100 samples.

{table(['Arm', 'Phase', 'Median ms', 'Campaign min ms', 'Campaign max ms', 'K'], criterion_rows)}

## What happened

- Parsel's caveman end-to-end median was {parsel_caveman / 1_000_000:.3f} ms versus Yosoi's {yosoi_caveman / 1_000_000:.3f} ms; Yosoi took {yosoi_caveman / parsel_caveman:.2f}× as long.
- Rust `scraper` completed caveman end-to-end in {scraper_caveman / 1_000_000:.3f} ms; Yosoi took {yosoi_caveman / scraper_caveman:.2f}× as long.
- On the hard catalog, Parsel was {parsel_hard / 1_000_000:.3f} ms, Rust `scraper` was {scraper_hard / 1_000_000:.3f} ms, and Yosoi was {yosoi_hard / 1_000_000:.3f} ms.
- Yosoi peak RSS was {resource_by_arm['yosoiRust']['aggregatePeakRssBytes'] / 1_048_576:.1f} MiB versus Rust `scraper` {resource_by_arm['rustScraper']['aggregatePeakRssBytes'] / 1_048_576:.1f} MiB and GoQuery {resource_by_arm['goquery']['aggregatePeakRssBytes'] / 1_048_576:.1f} MiB.
- All input bytes are resident before timing. Yosoi's end-to-end arm calls ordinary `Document::locate`, whose default dispatcher can stream eligible plans; its explicit parse and pre-parsed locate phases use a retained tree. End-to-end latency therefore need not equal parse plus locate. The tables compare exact URL-free byte-to-value operations, not universal full-DOM parser speed.
- The package table's `fullBuffer` label describes resident input delivery. The `lol_html` caveman control uses ordinary selector/text handlers with 64 KiB chunks over resident input; exact output is checked with 1-byte, 7-byte, and 64 KiB chunk boundaries. It is ranked for this byte-to-value task, with no invented parse-only or pre-parsed-locate timings. Time-to-first-output was not measured.

## Evidence boundaries

- Yosoi was built into an immutable local binary from source revision `{identities['yosoiRust']['sourceRevision']}`. This is not yet a published release artifact, so the result is exploratory.
- The common cross-language warm harness uses each language's in-process monotonic timer. Criterion confirms only the two Rust arms.
- The hard K=5 campaign excludes the two Beautiful Soup arms under the established resource-bounded protocol. Their retained rows are single-sample observations.
- RSS is aggregate process-tree resident memory. VSZ is not reported as RAM.
- Results apply only to these fixtures, exact versions, machine, and command boundaries. They do not establish general accuracy or universal speed.

## Reproduction

The `raw/` directory contains native samples, Criterion estimates, console output, fixture identity, and the Yosoi artifact identity. `evidenceManifest.json` hashes every retained file.
"""
    (args.output / "README.md").write_text(report, encoding="utf-8")

    manifest_entries = []
    for path in sorted(item for item in args.output.rglob("*") if item.is_file() and item.name != "evidenceManifest.json"):
        manifest_entries.append(
            {
                "path": str(path.relative_to(args.output)),
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    evidence_manifest = {
        "schemaVersion": "yosoi.benchmark.evidence-manifest.v1",
        "files": manifest_entries,
    }
    (args.output / "evidenceManifest.json").write_text(
        json.dumps(evidence_manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output / "README.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
