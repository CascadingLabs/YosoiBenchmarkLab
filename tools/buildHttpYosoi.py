from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--yosoi-repository", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    source = repository / "adapters" / "http" / "yosoi-rust"
    build = args.work / "yosoiHttp"
    (build / "src").mkdir(parents=True, exist_ok=True)
    manifest = (source / "Cargo.toml.template").read_text().replace(
        "__YOSOI_CRATE_PATH__", str(args.yosoi_repository / "crates" / "yosoi")
    )
    (build / "Cargo.toml").write_text(manifest)
    shutil.copy2(source / "src" / "main.rs", build / "src" / "main.rs")
    subprocess.run(["cargo", "generate-lockfile"], cwd=build, check=True)
    subprocess.run(["cargo", "build", "--release", "--locked"], cwd=build, check=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(build / "target" / "release" / "yosoi-benchmark-http", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
