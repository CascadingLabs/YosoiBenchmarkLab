"""Build lab adapters from one immutable JJ source snapshot, outside both repos."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

ARMS = {
    "parser": ("yosoi-rust", "yosoi-benchmark-yosoi-rust", "yosoiRust"),
    "http": ("http/yosoi-rust", "yosoi-benchmark-http", "yosoiHttp"),
    "browser": ("browser/yosoi-rust", "yosoi-benchmark-browser", "yosoiBrowser"),
    "v2": ("v2/yosoi-rust", "yosoi-benchmark-v2", "yosoiV2"),
}


def digest(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yosoi-repository", type=Path, required=True)
    parser.add_argument("--revision", default="@")
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--arms", default=",".join(ARMS))
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--previous-source", type=Path)
    args = parser.parse_args()
    lab = Path(__file__).resolve().parents[1]
    work = args.work.resolve()
    for repository in (lab, args.yosoi_repository.resolve()):
        if work.is_relative_to(repository):
            parser.error("--work must be outside the lab and Yosoi repositories")
    arms = args.arms.split(",")
    if any(arm not in ARMS for arm in arms):
        parser.error("unknown arm")
    revision = subprocess.check_output(
        ["jj", "-R", str(args.yosoi_repository), "log", "-r", args.revision,
         "--no-graph", "-T", "commit_id"], text=True,
    ).strip()
    work.mkdir(parents=True, exist_ok=True)
    archive_path = work / "yosoiSource.tar"
    source = work / "yosoiSource"
    source_identity = work / "sourceIdentity.json"
    if source_identity.exists():
        identity = json.loads(source_identity.read_text())
        if identity["sourceRevision"] != revision:
            parser.error("work directory already contains a different source snapshot")
    else:
        with archive_path.open("wb") as destination:
            subprocess.run(
                ["git", "-C", str(args.yosoi_repository), "archive", revision],
                stdout=destination, check=True,
            )
        source.mkdir()
        with tarfile.open(archive_path) as archive:
            archive.extractall(source, filter="data")
        if args.previous_source:
            # Preserve mtimes only for identical bytes so Cargo can reuse
            # unchanged local dependencies after a failed snapshot attempt.
            for path in source.rglob("*"):
                previous = args.previous_source / path.relative_to(source)
                if path.is_file() and previous.is_file() and digest(path) == digest(previous):
                    stat = previous.stat()
                    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        identity = {"sourceRevision": revision, "sourceArchiveSha256": digest(archive_path)}
        source_identity.write_text(json.dumps(identity, indent=2) + "\n")
    environment = os.environ.copy()
    environment["CARGO_BUILD_JOBS"] = "1"
    environment["CARGO_TARGET_DIR"] = str(work / "target")
    environment["YOSOI_SOURCE_REVISION"] = revision
    environment["YOSOI_BENCHMARK_RUST_VERSION"] = subprocess.check_output(
        ["rustc", "+1.99.0", "--version"], text=True,
    ).strip()
    if args.offline:
        environment["CARGO_NET_OFFLINE"] = "true"
    args.output.mkdir(parents=True, exist_ok=True)
    for arm in arms:
        adapter, binary, artifact = ARMS[arm]
        original = lab / "adapters" / adapter
        build = work / artifact
        shutil.copytree(original, build, dirs_exist_ok=True)
        manifest = (build / "Cargo.toml.template").read_text().replace(
            "__YOSOI_CRATE_PATH__", str(source / "crates/yosoi")
        ).replace("__YOSOI_DOCUMENTS_PATH__", str(source / "crates/yosoi-documents"))
        (build / "Cargo.toml").write_text(manifest)
        if not (build / "Cargo.lock").exists():
            shutil.copy2(source / "Cargo.lock", build / "Cargo.lock")
            subprocess.run(["cargo", "+1.99.0", "build", "--release", "--jobs", "1"],
                           cwd=build, env=environment, check=True)
        else:
            subprocess.run(["cargo", "+1.99.0", "build", "--release", "--locked", "--jobs", "1"],
                           cwd=build, env=environment, check=True)
        destination = args.output / artifact
        shutil.copy2(work / "target/release" / binary, destination)
        lock = args.output / f"{artifact}.Cargo.lock"
        shutil.copy2(build / "Cargo.lock", lock)
        result = {**identity, "armId": "yosoiRust" if arm == "v2" else artifact,
                  "sha256": digest(destination), "artifactBytes": destination.stat().st_size,
                  "cargoLockSha256": digest(lock)}
        (args.output / f"{artifact}.identity.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
