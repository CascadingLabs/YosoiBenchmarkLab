from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crate", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--campaigns", type=int, default=5)
    parser.add_argument("--group-prefix")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["CARGO_BUILD_JOBS"] = "1"
    environment["CARGO_TARGET_DIR"] = str(args.target)
    environment["CARGO_NET_OFFLINE"] = "true"
    environment["YOSOI_BENCHMARK_FIXTURE"] = str(args.fixture)

    for campaign in range(args.campaigns):
        baseline = f"campaign{campaign}"
        command = [
            "cargo",
            "bench",
            "--locked",
            "--bench",
            "caveman",
            "--",
            "--warm-up-time",
            "3",
            "--measurement-time",
            "5",
            "--sample-size",
            "100",
            "--noplot",
            "--save-baseline",
            baseline,
        ]
        completed = subprocess.run(
            command,
            cwd=args.crate,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        (args.output / f"{baseline}.stdout.txt").write_text(completed.stdout, encoding="utf-8")
        (args.output / f"{baseline}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
        if completed.returncode:
            print(completed.stderr[-4000:], flush=True)
            completed.check_returncode()
        print(f"completed {baseline}")

    criterion_root = args.target / "criterion"
    evidence_root = args.output / "criterion"
    if evidence_root.exists():
        shutil.rmtree(evidence_root)
    if args.group_prefix:
        evidence_root.mkdir()
        for group in criterion_root.iterdir():
            if group.is_dir() and group.name.startswith(args.group_prefix):
                shutil.copytree(group, evidence_root / group.name)
    else:
        shutil.copytree(criterion_root, evidence_root)
    identity = {
        "campaigns": args.campaigns,
        "fixture": str(args.fixture),
        "fixtureBytes": args.fixture.stat().st_size,
        "command": "cargo bench --locked --bench caveman -- --warm-up-time 3 --measurement-time 5 --sample-size 100 --noplot --save-baseline <campaign>",
    }
    (args.output / "identity.json").write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
