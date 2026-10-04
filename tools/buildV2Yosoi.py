from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--yosoi-repository", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repository = Path(__file__).resolve().parents[1]
    source = repository / "adapters/v2/yosoi-rust"
    yosoiCrate = args.yosoi_repository / "crates/yosoi"
    if not yosoiCrate.is_dir():
        raise SystemExit(f"Yosoi crate does not exist: {yosoiCrate}")
    status = subprocess.check_output(
        ["jj", "-R", str(args.yosoi_repository), "status"], text=True
    )
    if "working copy has no changes" not in status.lower():
        raise SystemExit("Yosoi repository must be clean before building a V2 artifact")
    revision = subprocess.check_output(
        ["jj", "-R", str(args.yosoi_repository), "log", "-r", "@-", "--no-graph", "-T", "commit_id"],
        text=True,
    ).strip()

    sourceArchive = args.work / "yosoiSource.tar"
    sourceRoot = args.work / "yosoiSource"
    archived = subprocess.check_output(
        ["git", "-C", str(args.yosoi_repository), "archive", "--format=tar", revision]
    )
    sourceArchive.parent.mkdir(parents=True, exist_ok=True)
    sourceArchive.write_bytes(archived)
    if sourceRoot.exists():
        shutil.rmtree(sourceRoot)
    sourceRoot.mkdir()
    with tarfile.open(sourceArchive) as archive:
        archive.extractall(sourceRoot, filter="data")
    stagedYosoiCrate = sourceRoot / "crates/yosoi"
    if not stagedYosoiCrate.is_dir():
        raise SystemExit("staged Yosoi source artifact does not contain crates/yosoi")

    build = args.work / "yosoiV2"
    (build / "src").mkdir(parents=True, exist_ok=True)
    manifest = (source / "Cargo.toml.template").read_text().replace(
        "__YOSOI_CRATE_PATH__", str(stagedYosoiCrate)
    ).replace(
        "__YOSOI_DOCUMENTS_PATH__", str(sourceRoot / "crates/yosoi-documents")
    )
    (build / "Cargo.toml").write_text(manifest)
    shutil.copy2(source / "src/main.rs", build / "src/main.rs")
    environment = os.environ.copy()
    environment["CARGO_BUILD_JOBS"] = "1"
    environment["YOSOI_SOURCE_REVISION"] = revision
    subprocess.run(["cargo", "generate-lockfile"], cwd=build, env=environment, check=True)
    subprocess.run(
        ["cargo", "build", "--release", "--locked", "--jobs", "1"],
        cwd=build,
        env=environment,
        check=True,
    )

    args.output.mkdir(parents=True, exist_ok=True)
    binary = build / "target/release/yosoi-benchmark-v2"
    destination = args.output / "yosoiV2"
    shutil.copy2(binary, destination)
    lock = args.output / "yosoiV2.Cargo.lock"
    shutil.copy2(build / "Cargo.lock", lock)
    identity = {
        "armId": "yosoiRust",
        "sourceRevision": revision,
        "sha256": sha256(destination),
        "artifactBytes": destination.stat().st_size,
        "cargoLockSha256": sha256(lock),
        "sourceArchiveSha256": sha256(sourceArchive),
    }
    (args.output / "yosoiV2.identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    print(json.dumps(identity))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
