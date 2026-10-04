from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def selector_for(task: str) -> str:
    if task == "caveman":
        return 'article.product-card[data-sku="sku-000073"] span.price'
    if task == "hard":
        return 'article.product-card[data-selected="true"] span.price'
    raise ValueError(f"unsupported task: {task}")


@dataclass(frozen=True)
class Arm:
    arm_id: str
    package: str
    parse: Callable[[bytes], Any]
    locate: Callable[[Any, str], list[str]]


def load_arm(arm_id: str, task: str) -> Arm:
    selector = selector_for(task)
    if arm_id == "lxml":
        from lxml import etree, html

        parser = html.HTMLParser(encoding="utf-8", recover=True)
        expression = (
            "//article[contains(concat(' ', normalize-space(@class), ' '), ' product-card ')][@data-sku='sku-000073']"
            "//span[contains(concat(' ', normalize-space(@class), ' '), ' price ')]"
            if task == "caveman"
            else "//article[contains(concat(' ', normalize-space(@class), ' '), ' product-card ')][@data-selected='true']"
            "//span[contains(concat(' ', normalize-space(@class), ' '), ' price ')]"
        )
        compiled = etree.XPath(expression)

        def parse(data: bytes) -> Any:
            return html.fromstring(data, parser=parser)

        def locate(document: Any, _task: str) -> list[str]:
            return [normalize_text(node.text_content()) for node in compiled(document)]

        return Arm(arm_id, "lxml", parse, locate)

    if arm_id == "parsel":
        from parsel import Selector

        def parse(data: bytes) -> Any:
            return Selector(body=data, type="html")

        def locate(document: Any, _task: str) -> list[str]:
            return [normalize_text(value) for value in document.css(f"{selector}::text").getall()]

        return Arm(arm_id, "parsel", parse, locate)

    if arm_id == "selectolaxLexbor":
        from selectolax.lexbor import LexborHTMLParser

        def parse(data: bytes) -> Any:
            return LexborHTMLParser(data)

        def locate(document: Any, _task: str) -> list[str]:
            return [normalize_text(node.text()) for node in document.css(selector)]

        return Arm(arm_id, "selectolax", parse, locate)

    if arm_id in {"beautifulSoupHtmlParser", "beautifulSoupLxml"}:
        from bs4 import BeautifulSoup

        backend = "html.parser" if arm_id == "beautifulSoupHtmlParser" else "lxml"

        def parse(data: bytes) -> Any:
            return BeautifulSoup(data, backend)

        def locate(document: Any, _task: str) -> list[str]:
            return [normalize_text(node.get_text(" ", strip=True)) for node in document.select(selector)]

        return Arm(arm_id, "beautifulsoup4", parse, locate)

    if arm_id == "scraplingParser":
        from scrapling.parser import Selector

        def parse(data: bytes) -> Any:
            return Selector(data)

        def locate(document: Any, _task: str) -> list[str]:
            return [normalize_text(value) for value in document.css(f"{selector}::text").getall()]

        return Arm(arm_id, "scrapling", parse, locate)

    raise ValueError(f"unsupported arm: {arm_id}")


def values_digest(values: list[str]) -> str:
    payload = json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def measure(arm: Arm, phase: str, data: bytes, task: str, samples: int, operations: int) -> tuple[list[str], list[int]]:
    parsed = arm.parse(data)
    expected_values = arm.locate(parsed, task)
    timings: list[int] = []

    for _ in range(samples):
        started = time.perf_counter_ns()
        last_values: list[str] = []
        if phase == "parse":
            for _ in range(operations):
                arm.parse(data)
            last_values = expected_values
        elif phase == "locate":
            for _ in range(operations):
                last_values = arm.locate(parsed, task)
        elif phase == "endToEnd":
            for _ in range(operations):
                last_values = arm.locate(arm.parse(data), task)
        else:
            raise ValueError(f"unsupported phase: {phase}")
        elapsed = time.perf_counter_ns() - started
        if phase != "parse" and last_values != expected_values:
            raise RuntimeError("measured output changed from correctness preflight")
        timings.append(elapsed // operations)
    return expected_values, timings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--task", choices=["caveman", "hard"], required=True)
    parser.add_argument("--phase", choices=["parse", "locate", "endToEnd"], required=True)
    parser.add_argument("--samples", type=int, required=True)
    parser.add_argument("--operations", type=int, required=True)
    args = parser.parse_args()

    if args.samples < 0 or args.operations < 1:
        parser.error("samples must be non-negative and operations must be positive")

    arm = load_arm(args.arm, args.task)
    data = args.fixture.read_bytes()
    values, samples_ns = measure(arm, args.phase, data, args.task, args.samples, args.operations)
    result = {
        "schemaVersion": "yosoi.benchmark.adapter.v1",
        "armId": arm.arm_id,
        "language": "python",
        "runtime": f"python-{__import__('platform').python_version()}",
        "productVersion": importlib.metadata.version(arm.package),
        "task": args.task,
        "phase": args.phase,
        "terminalStatus": "ok",
        "matchCount": len(values),
        "values": values,
        "outputSha256": values_digest(values),
        "samplesNs": samples_ns,
        "operationsPerSample": args.operations,
        "inputBytes": len(data),
    }
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
