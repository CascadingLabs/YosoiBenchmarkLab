from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


def directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--yosoi-repository", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repository = Path(__file__).resolve().parents[1]
    source = repository / "adapters" / "yosoi-rust"
    crate = args.yosoi_repository / "crates" / "yosoi"
    if not crate.is_dir():
        raise SystemExit(f"Yosoi crate does not exist: {crate}")

    build = args.work / "yosoiRust"
    (build / "src").mkdir(parents=True, exist_ok=True)
    (build / "benches").mkdir(parents=True, exist_ok=True)
    manifest = (source / "Cargo.toml.template").read_text(encoding="utf-8").replace(
        "__YOSOI_CRATE_PATH__", str(crate)
    )
    (build / "Cargo.toml").write_text(manifest, encoding="utf-8")
    shutil.copy2(source / "src" / "main.rs", build / "src" / "main.rs")
    shutil.copy2(source / "benches" / "caveman.rs", build / "benches" / "caveman.rs")

    revision = subprocess.check_output(
        ["jj", "-R", str(args.yosoi_repository), "log", "-r", "@-", "--no-graph", "-T", "commit_id"],
        text=True,
    ).strip()
    environment = os.environ.copy()
    environment["CARGO_BUILD_JOBS"] = "1"
    environment["YOSOI_SOURCE_REVISION"] = revision
    subprocess.run(["cargo", "generate-lockfile"], cwd=build, env=environment, check=True)
    subprocess.run(["cargo", "build", "--release", "--locked"], cwd=build, env=environment, check=True)

    binary = build / "target" / "release" / "yosoi-benchmark-yosoi-rust"
    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output / "yosoiRust"
    shutil.copy2(binary, destination)
    shutil.copy2(build / "Cargo.lock", args.output / "yosoiRust.Cargo.lock")
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    identity = {
        "armId": "yosoiRust",
        "sourceRevision": revision,
        "sha256": digest,
        "artifactBytes": destination.stat().st_size,
        "buildTreeBytes": directory_size(build / "target"),
    }
    (args.output / "yosoiRust.identity.json").write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(identity))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
