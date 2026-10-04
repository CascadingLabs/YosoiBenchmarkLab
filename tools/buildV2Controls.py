from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    crate = repository / "adapters/v2/rust-controls"
    environment = os.environ.copy()
    environment["CARGO_BUILD_JOBS"] = "1"
    environment["CARGO_TARGET_DIR"] = str(args.work / "controlsTarget")
    environment["CARGO_NET_OFFLINE"] = "true"
    subprocess.run(
        ["cargo", "build", "--release", "--locked", "--jobs", "1"],
        cwd=crate,
        env=environment,
        check=True,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    binary = Path(environment["CARGO_TARGET_DIR"]) / "release/yosoi-benchmark-v2-controls"
    destination = args.output / "v2Controls"
    shutil.copy2(binary, destination)
    identity = {
        "armId": "v2Controls",
        "sha256": sha256(destination),
        "artifactBytes": destination.stat().st_size,
        "cargoLockSha256": sha256(crate / "Cargo.lock"),
    }
    (args.output / "v2Controls.identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    print(json.dumps(identity))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
