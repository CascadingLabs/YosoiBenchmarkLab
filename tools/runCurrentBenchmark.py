"""Run all frozen lab lanes serially against buildCurrentYosoi artifacts."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--python-parser", type=Path, required=True)
    parser.add_argument("--python-http", type=Path, required=True)
    parser.add_argument("--python-browser", type=Path, required=True)
    parser.add_argument("--chromium", type=Path, required=True)
    parser.add_argument("--sections", default="build,parser,criterion,http,browser,v2")
    args = parser.parse_args()
    if any(section not in ("build", "parser", "criterion", "http", "browser", "v2")
           for section in args.sections.split(",")):
        parser.error("unknown section")
    lab = Path(__file__).resolve().parents[1]
    work = args.work.resolve()
    artifacts = work / "artifacts"
    environment = os.environ.copy()
    environment.update(CARGO_BUILD_JOBS="1", CARGO_NET_OFFLINE="true",
                       RAYON_NUM_THREADS="1", GOMAXPROCS="1", RUSTUP_TOOLCHAIN="1.99.0",
                       CHROME=str(args.chromium), CARGO_TARGET_DIR=str(work / "target"))
    environment["YOSOI_BENCHMARK_RUST_VERSION"] = subprocess.check_output(
        ["rustc", "+1.99.0", "--version"], text=True,
    ).strip()
    sections = args.sections.split(",")
    def run(command: list[str | Path], cwd: Path = lab) -> None:
        print("Running: " + " ".join(map(str, command)), flush=True)
        subprocess.run(list(map(str, command)), cwd=cwd, env=environment, check=True)
    def tool(name: str, *arguments: str | Path) -> None:
        run([sys.executable, lab / "tools" / name, *arguments])
    if "build" in sections:
        run(["cargo", "+1.99.0", "build", "--release", "--locked", "--jobs", "1"], lab / "adapters/rust-scraper")
        shutil.copy2(work / "target/release/yosoi-benchmark-rust-scraper", artifacts / "rustScraper")
        run(["cargo", "+1.99.0", "build", "--release", "--locked", "--jobs", "1"], lab / "adapters/rust-lol-html")
        shutil.copy2(work / "target/release/yosoi-benchmark-lol-html", artifacts / "lolHtml")
        environment["GOCACHE"] = str(work / "goCache")
        run(["go", "build", "-p", "1", "-o", artifacts / "goquery", "."], lab / "adapters/goquery")
        run(["go", "build", "-p", "1", "-o", artifacts / "colly", "."], lab / "adapters/http/go-colly")
        tool("buildV2Controls.py", "--work", work, "--output", artifacts)
    if "parser" in sections:
        fixtures = work / "parserFixtures"
        tool("generateFixtures.py", "--output", fixtures)
        shared = ["--fixtures", fixtures, "--python", args.python_parser, "--artifacts", artifacts]
        for name, extra in (
            ("cavemanK5", ["--tasks", "caveman", "--skip-resource"]),
            ("hardK5", ["--tasks", "hard", "--hard-samples", "5", "--skip-resource",
                        "--arms", "lxml,parsel,scraplingParser,selectolaxLexbor,yosoiRust,rustScraper,goquery"]),
            ("hardSmokeAndResources", ["--campaigns", "1", "--caveman-samples", "1",
                                      "--hard-samples", "1", "--caveman-operations", "1"]),
        ):
            if not (work / name / "summary.json").exists():
                tool("runMatrix.py", *shared, "--output", work / name, *extra)
    if "criterion" in sections:
        for artifact, name in (("yosoiRust", "criterionYosoiRust"), ("rustScraper", "criterionRustScraper")):
            if not (work / name / "identity.json").exists():
                tool("runCriterionCampaigns.py", "--crate", work / artifact if artifact == "yosoiRust" else lab / "adapters/rust-scraper",
                     "--target", work / "target", "--group-prefix", artifact,
                     "--fixture", work / "parserFixtures/cavemanCatalog.html",
                     "--output", work / name)
    for section in ("http", "browser"):
        if section not in sections or (work / section / "summary.json").exists():
            continue
        server = subprocess.Popen([sys.executable, str(lab / "tools/httpFixtureServer.py"),
                                   "--identity", "current-benchmark"], stdout=subprocess.PIPE, text=True)
        try:
            if server.stdout is None:
                raise RuntimeError("fixture server stdout is missing")
            port = json.loads(server.stdout.readline())["port"]
            common = ["--repository", lab, "--base", f"http://127.0.0.1:{port}", "--output", work / section]
            if section == "http":
                tool("runHttpMatrix.py", *common, "--python", args.python_http, "--yosoi", artifacts / "yosoiHttp", "--colly", artifacts / "colly")
            else:
                tool("runBrowserMatrix.py", *common, "--python", args.python_browser, "--yosoi", artifacts / "yosoiBrowser", "--chromium", args.chromium)
        finally:
            server.terminate()
            server.wait(timeout=10)
    if "v2" in sections:
        spec = lab / "specs/diagnostics-v2.json"
        fixtures = work / "v2Fixtures"
        tool("generateV2Fixtures.py", "--output", fixtures, "--spec", spec)
        common = ["--spec", spec, "--fixtures", fixtures, "--yosoi", artifacts / "yosoiV2"]
        for name, tool_name, extra, completion in (
            ("v2Matrix", "runV2Matrix.py", ["--repository", lab, "--controls", artifacts / "v2Controls"], "summary.json"),
            ("v2Extraction", "runV2Extraction.py", ["--repository", lab, "--controls", artifacts / "v2Controls"], "summary.json"),
            ("v2Conformance", "runV2Conformance.py", [], "conformance-results.json"),
            ("v2Negative", "runV2Negative.py", [], "negative-results.json"),
        ):
            if not (work / name / completion).exists():
                arguments = common if name != "v2Negative" else ["--fixtures", fixtures, "--yosoi", artifacts / "yosoiV2"]
                tool(tool_name, *arguments, *extra, "--output", work / name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
