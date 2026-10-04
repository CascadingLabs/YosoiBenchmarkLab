from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def fixtureMap(manifest: dict[str, Any], root: Path) -> dict[str, Path]:
    return {
        fixture["documentClass"]: root / fixture["path"]
        for fixture in manifest["fixtures"]
        if fixture["size"] == "tiny"
    }


def observedStatus(completed: subprocess.CompletedProcess[str]) -> str:
    if completed.returncode == 0:
        return "ok"
    stderr = completed.stderr.lower()
    if "limit" in stderr or "exhausted" in stderr:
        return "limitFailed"
    return "queryRejected"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--yosoi", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    manifest = json.loads((args.fixtures / "manifest.json").read_text())
    fixtures = fixtureMap(manifest, args.fixtures)
    args.output.mkdir(parents=True, exist_ok=True)
    records = []

    for case in spec["correctnessCases"]:
        command = [
            str(args.yosoi),
            "--cell", f"conformance.{case['id']}",
            "--document-class", case["documentClass"],
            "--query-family", case["queryFamily"],
            "--expression", case["expression"],
            "--projection", case["projection"],
            "--phase", "endToEnd",
            "--fixture", str(fixtures[case["documentClass"]]),
            "--samples", "1",
            "--operations", "1",
        ]
        namespace = case.get("namespace")
        if namespace is not None:
            command.extend(
                ["--namespace-prefix", namespace["prefix"], "--namespace-uri", namespace["uri"]]
            )
        if case.get("maxMatches") is not None:
            command.extend(["--max-matches", str(case["maxMatches"])])
        completed = subprocess.run(command, capture_output=True, text=True, timeout=30)
        observed = observedStatus(completed)
        matchCount = None
        if completed.returncode == 0:
            lines = [line for line in completed.stdout.splitlines() if line.startswith("{")]
            if not lines:
                raise RuntimeError(f"conformance case emitted no JSON: {case['id']}")
            matchCount = json.loads(lines[-1])["matchCount"]
        passed = observed == case["expectedStatus"]
        if passed and observed == "ok":
            passed = matchCount == case["expectedMatchCount"]
        record = {
            "id": case["id"],
            "documentClass": case["documentClass"],
            "expectedStatus": case["expectedStatus"],
            "observedStatus": observed,
            "expectedMatchCount": case.get("expectedMatchCount"),
            "observedMatchCount": matchCount,
            "passed": passed,
            "exitCode": completed.returncode,
            "stdoutSha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
            "stderr": completed.stderr[-4096:],
        }
        records.append(record)
        if not passed:
            raise RuntimeError(f"conformance case failed: {record}")

    result = {
        "schemaVersion": "yosoi.benchmark.conformance-results.v2",
        "records": records,
    }
    path = args.output / "conformance-results.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
