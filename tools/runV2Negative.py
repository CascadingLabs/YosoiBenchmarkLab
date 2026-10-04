from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


QUERY_BY_CLASS = {
    "sourceHtml": ("css", "article", "node"),
    "sourceXml": ("css", "product", "node"),
    "sourceJson": ("jsonPointer", "/", "value"),
    "sourceText": ("textLiteral", "a", "text"),
    "renderedDom": ("css", "body", "node"),
    "accessibilityTree": ("role", "button", "node"),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--yosoi", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.fixtures / "manifest.json").read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    for fixture in manifest["negativeFixtures"]:
        queryFamily, expression, projection = QUERY_BY_CLASS[fixture["documentClass"]]
        command = [
            str(args.yosoi),
            "--cell", f"negative.{fixture['id']}",
            "--document-class", fixture["documentClass"],
            "--query-family", queryFamily,
            "--expression", expression,
            "--projection", projection,
            "--phase", "parse",
            "--fixture", str(args.fixtures / fixture["path"]),
            "--samples", "1",
            "--operations", "1",
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=30)
        observed = "ok" if completed.returncode == 0 else "parseFailed"
        passed = observed == fixture["expectedStatus"]
        record = {
            "id": fixture["id"],
            "documentClass": fixture["documentClass"],
            "expectedStatus": fixture["expectedStatus"],
            "observedStatus": observed,
            "passed": passed,
            "exitCode": completed.returncode,
            "stdoutSha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
            "stderr": completed.stderr[-4096:],
        }
        records.append(record)
        if not passed:
            raise RuntimeError(f"negative fixture failed: {record}")
    result = {
        "schemaVersion": "yosoi.benchmark.negative-results.v2",
        "records": records,
    }
    path = args.output / "negative-results.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
