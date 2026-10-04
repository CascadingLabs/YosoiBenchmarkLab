from __future__ import annotations

import argparse
import importlib.metadata
import json
import re
import sys
from pathlib import Path


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def distribution_files(distribution: importlib.metadata.Distribution) -> set[Path]:
    result: set[Path] = set()
    for entry in distribution.files or []:
        path = Path(distribution.locate_file(entry))
        if path.is_file():
            result.add(path)
    return result


def closure(name: str) -> list[importlib.metadata.Distribution]:
    pending = [name]
    seen: set[str] = set()
    result: list[importlib.metadata.Distribution] = []
    while pending:
        candidate = pending.pop()
        normalized = canonical(candidate)
        if normalized in seen:
            continue
        seen.add(normalized)
        try:
            distribution = importlib.metadata.distribution(candidate)
        except importlib.metadata.PackageNotFoundError:
            continue
        result.append(distribution)
        for requirement in distribution.requires or []:
            if "extra ==" in requirement or "extra==" in requirement:
                continue
            match = re.match(r"[A-Za-z0-9_.-]+", requirement)
            if match:
                pending.append(match.group(0))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packages", required=True)
    args = parser.parse_args()

    environment = Path(sys.prefix)
    runtime = Path(sys.base_prefix)
    environment_bytes = directory_size(environment)
    runtime_bytes = directory_size(runtime)
    packages: dict[str, object] = {}
    for name in args.packages.split(","):
        direct = importlib.metadata.distribution(name)
        direct_files = distribution_files(direct)
        transitive = closure(name)
        transitive_files: set[Path] = set()
        for distribution in transitive:
            transitive_files.update(distribution_files(distribution))
        packages[name] = {
            "version": direct.version,
            "directInstalledBytes": sum(path.stat().st_size for path in direct_files),
            "installedPackageBytes": sum(path.stat().st_size for path in transitive_files),
            "distributions": sorted(
                f"{distribution.metadata['Name']}=={distribution.version}" for distribution in transitive
            ),
        }
    print(
        json.dumps(
            {
                "pythonVersion": sys.version.split()[0],
                "environmentBytes": environment_bytes,
                "pythonBaseRuntimeBytes": runtime_bytes,
                "runnableEnvironmentBytes": environment_bytes + runtime_bytes,
                "packages": packages,
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
