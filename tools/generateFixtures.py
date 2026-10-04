from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

SEED = 0x594F534F49
CAVEMAN_RECORDS = 128
CAVEMAN_TARGET = 73
HARD_RECORDS = 25_000
HARD_SELECTED = 64


def price_for(index: int) -> str:
    return f"USD {12 + (index // 10) % 80}.{index % 100:02d}"


def selected_indexes(records: int, count: int) -> list[int]:
    if count > records:
        raise ValueError("selected record count exceeds catalog size")
    return sorted(random.Random(SEED).sample(range(records), count))


def render_catalog(*, records: int, selected_indexes: list[int]) -> tuple[bytes, list[str]]:
    selected = set(selected_indexes)
    expected: list[str] = []
    parts = ["<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>Catalog</title></head><body><main id=\"catalog\">"]

    for index in range(records):
        sku = f"sku-{index:06d}"
        price = price_for(index)
        marker = ' data-selected="true"' if index in selected else ""
        if index in selected:
            expected.append(price)
        unicode_text = ("café naïve 東京 Δοκιμή 🦀 " * 4).strip()
        parts.append(
            f'<article class="product-card card-{index % 17}" data-sku="{sku}"{marker}>'
            f'<header><h2>Product {index:06d}</h2></header>'
            f'<div class="meta"><span class="price">{price}</span>'
            f'<span class="availability">{"in stock" if index % 3 else "backorder"}</span></div>'
            f'<div class="body"><p>{unicode_text}</p><p data-copy="{index % 29}">{unicode_text}</p></div>'
            f'<ul class="tags"><li>tag-{index % 7}</li><li>tag-{index % 11}</li><li>tag-{index % 13}</li></ul>'
            f'<table><tr><td>{index}</td><td>{sku}</td></tr></table>'
        )
        if index % 991 == 0:
            parts.append(f'<svg viewBox="0 0 10 10"><title>icon-{index}</title><path d="M0 0L10 10"/></svg>')
        if index % 997 == 0:
            parts.append("<p class=\"recovery\"><b>alpha<i>beta</b>gamma</i>")
        parts.append("</article>")

    parts.append("</main></body></html>")
    return "".join(parts).encode("utf-8"), expected


def fixture_record(identifier: str, path: Path, expected_values: list[str], *, records: int, selected_records: int) -> dict[str, Any]:
    payload = path.read_bytes()
    encoded_values = json.dumps(expected_values, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {
        "id": identifier,
        "path": path.name,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "records": records,
        "selectedRecords": selected_records,
        "expectedValues": expected_values,
        "expectedValuesSha256": hashlib.sha256(encoded_values).hexdigest(),
    }


def generate_fixture_set(output: Path, *, hard_records: int = HARD_RECORDS) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)

    caveman_bytes, caveman_values = render_catalog(records=CAVEMAN_RECORDS, selected_indexes=[CAVEMAN_TARGET])
    caveman_path = output / "cavemanCatalog.html"
    caveman_path.write_bytes(caveman_bytes)

    hard_indexes = selected_indexes(hard_records, min(HARD_SELECTED, hard_records))
    hard_bytes, hard_values = render_catalog(records=hard_records, selected_indexes=hard_indexes)
    hard_path = output / "hardCatalog.html"
    hard_path.write_bytes(hard_bytes)

    manifest = {
        "schemaVersion": "yosoi.benchmark.fixtures.v1",
        "seed": f"0x{SEED:x}",
        "fixtures": [
            fixture_record("cavemanCatalog", caveman_path, caveman_values, records=CAVEMAN_RECORDS, selected_records=1),
            fixture_record("hardCatalog", hard_path, hard_values, records=hard_records, selected_records=len(hard_indexes)),
        ],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hard-records", type=int, default=HARD_RECORDS)
    args = parser.parse_args()
    manifest = generate_fixture_set(args.output, hard_records=args.hard_records)
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
