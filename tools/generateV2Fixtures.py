from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

if __package__:
    from tools.v2Catalog import SIZES, TARGET_INDEX, specification
else:
    from v2Catalog import SIZES, TARGET_INDEX, specification


HTML_NAMESPACE = "http://www.w3.org/1999/xhtml"


def targetName(index: int) -> str:
    if index == TARGET_INDEX:
        return f"Unique target {index:06d}"
    return f"Product {index:06d}"


def targetId(index: int) -> str:
    return f"p-{index:06d}"


def price(index: int) -> str:
    return f"${index}.{index % 100:02d}"


def renderHtml(records: int) -> bytes:
    parts = ["<!doctype html><html><body><main id='catalog'>"]
    for index in range(records):
        selected = " data-selected='true'" if index == TARGET_INDEX else ""
        identifier = targetId(index)
        name = targetName(index)
        parts.append(
            f"<article class='product' data-id='{identifier}'{selected}>"
            f"<h2><span class='name' data-id='{identifier}'>{name}</span></h2>"
            f"<span class='price'>{price(index)}</span>"
            f"<span class='subtitle'>Description {index:06d}</span>"
            f"<span class='category'>category-{index % 7}</span>"
            f"<span class='category'>bucket-{index % 13}</span>"
            f"<p>café 東京 🦀 repeated payload {index:06d}</p>"
            "</article>"
        )
    parts.append("</main></body></html>")
    return "".join(parts).encode("utf-8")


def renderXml(records: int) -> bytes:
    parts = ["<?xml version='1.0' encoding='UTF-8'?><catalog xmlns:p='urn:product'>"]
    for index in range(records):
        selected = " data-selected='true'" if index == TARGET_INDEX else ""
        identifier = targetId(index)
        parts.append(
            f"<p:product data-id='{identifier}'{selected}>"
            f"<p:name data-id='{identifier}'>{targetName(index)}</p:name>"
            f"<p:price>{price(index)}</p:price>"
            f"<p:category>category-{index % 7}</p:category>"
            "</p:product>"
        )
    parts.append("</catalog>")
    return "".join(parts).encode("utf-8")


def renderJson(records: int) -> bytes:
    payload = {
        "products": [
            {
                "id": targetId(index),
                "name": targetName(index),
                "price": price(index),
                "selected": index == TARGET_INDEX,
                "categories": [f"category-{index % 7}", f"bucket-{index % 13}"],
            }
            for index in range(records)
        ]
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def renderText(records: int) -> bytes:
    lines = [
        f"ORDER-{index:06d} TOTAL={price(index)} NAME={targetName(index)}"
        for index in range(records)
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def renderDom(records: int) -> bytes:
    nodes: list[dict[str, Any]] = [
        {"kind": "document", "id": 1, "parent": None, "children": [2]},
        {
            "kind": "element",
            "id": 2,
            "parent": 1,
            "children": [],
            "namespace_uri": HTML_NAMESPACE,
            "tag_name": "body",
            "attributes": [],
        },
    ]
    articleIds: list[int] = []
    nextId = 3
    for index in range(records):
        articleId = nextId
        nameId = nextId + 1
        nameTextId = nextId + 2
        priceId = nextId + 3
        priceTextId = nextId + 4
        nextId += 5
        articleIds.append(articleId)
        identifier = targetId(index)
        attributes = [
            {"namespace_uri": "", "name": "class", "value": "product"},
            {"namespace_uri": "", "name": "data-id", "value": identifier},
        ]
        if index == TARGET_INDEX:
            attributes.append(
                {"namespace_uri": "", "name": "data-selected", "value": "true"}
            )
        nodes.extend(
            [
                {
                    "kind": "element",
                    "id": articleId,
                    "parent": 2,
                    "children": [nameId, priceId],
                    "namespace_uri": HTML_NAMESPACE,
                    "tag_name": "article",
                    "attributes": attributes,
                },
                {
                    "kind": "element",
                    "id": nameId,
                    "parent": articleId,
                    "children": [nameTextId],
                    "namespace_uri": HTML_NAMESPACE,
                    "tag_name": "span",
                    "attributes": [
                        {"namespace_uri": "", "name": "class", "value": "name"},
                        {"namespace_uri": "", "name": "data-id", "value": identifier},
                    ],
                },
                {
                    "kind": "text",
                    "id": nameTextId,
                    "parent": nameId,
                    "children": [],
                    "value": targetName(index),
                },
                {
                    "kind": "element",
                    "id": priceId,
                    "parent": articleId,
                    "children": [priceTextId],
                    "namespace_uri": HTML_NAMESPACE,
                    "tag_name": "span",
                    "attributes": [
                        {"namespace_uri": "", "name": "class", "value": "price"}
                    ],
                },
                {
                    "kind": "text",
                    "id": priceTextId,
                    "parent": priceId,
                    "children": [],
                    "value": price(index),
                },
            ]
        )
    nodes[1]["children"] = articleIds
    payload = {
        "schema": "yosoi.rendered-dom.v1",
        "document_epoch": 1,
        "tree_model": "document_light_dom",
        "root": 1,
        "nodes": nodes,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def renderAccessibility(records: int) -> bytes:
    children = [f"ax-{index}" for index in range(records)]
    nodes: list[dict[str, Any]] = [
        {
            "id": "root",
            "parent": None,
            "children": children,
            "ignored": False,
            "role": "document",
            "accessible_name": "Orders",
            "text": None,
            "states": {},
        }
    ]
    for index in range(records):
        selected = index == TARGET_INDEX
        nodes.append(
            {
                "id": f"ax-{index}",
                "parent": "root",
                "children": [],
                "ignored": False,
                "role": "target-button" if selected else "button",
                "accessible_name": f"Buy {targetId(index)}",
                "text": f"Buy {targetId(index)}",
                "states": {"expanded": selected, "focused": False},
            }
        )
    payload = {
        "schema": "yosoi.accessibility-tree.v1",
        "document_epoch": 1,
        "root": "root",
        "completeness": {"status": "complete"},
        "nodes": nodes,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def record(path: Path, root: Path, *, documentClass: str, size: str, records: int) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "documentClass": documentClass,
        "size": size,
        "records": records,
        "path": str(path.relative_to(root)),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def generate(output: Path, specPath: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    specPath.parent.mkdir(parents=True, exist_ok=True)
    specPath.write_text(json.dumps(specification(), indent=2) + "\n", encoding="utf-8")
    renderers = {
        "sourceHtml": ("html", renderHtml),
        "sourceXml": ("xml", renderXml),
        "sourceJson": ("json", renderJson),
        "sourceText": ("txt", renderText),
        "renderedDom": ("dom.json", renderDom),
        "accessibilityTree": ("ax.json", renderAccessibility),
    }
    fixtures = []
    for size, records in SIZES.items():
        for documentClass, (extension, renderer) in renderers.items():
            path = output / f"{size}.{extension}"
            path.write_bytes(renderer(records))
            fixtures.append(record(path, output, documentClass=documentClass, size=size, records=records))

    negative = output / "negative"
    negative.mkdir(exist_ok=True)
    negativeFixtures = {
        "invalidXml": ("sourceXml", b"<catalog><product></catalog>", "parseFailed"),
        "xmlDoctype": (
            "sourceXml",
            b"<!DOCTYPE catalog [<!ELEMENT catalog ANY>]><catalog/>",
            "parseFailed",
        ),
        "xmlExternalEntity": (
            "sourceXml",
            b"<!DOCTYPE catalog [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]><catalog>&xxe;</catalog>",
            "parseFailed",
        ),
        "invalidJson": ("sourceJson", b'{"products":[}', "parseFailed"),
        "invalidTextUtf8": ("sourceText", b"order-1\xff", "parseFailed"),
        "invalidRenderedDom": ("renderedDom", b'{"schema":"wrong","nodes":[]}', "parseFailed"),
        "invalidAccessibility": ("accessibilityTree", b'{"schema":"wrong","nodes":[]}', "parseFailed"),
        "recoverableHtml": ("sourceHtml", b"<article><b>alpha<i>beta</b>gamma</i>", "ok"),
    }
    negativeRecords = []
    for identifier, (documentClass, payload, expectedStatus) in negativeFixtures.items():
        path = negative / identifier
        path.write_bytes(payload)
        negativeRecords.append(
            {
                "id": identifier,
                "documentClass": documentClass,
                "expectedStatus": expectedStatus,
                "path": str(path.relative_to(output)),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    manifest = {
        "schemaVersion": "yosoi.benchmark.fixtures.v2",
        "targetIndex": TARGET_INDEX,
        "fixtures": fixtures,
        "negativeFixtures": negativeRecords,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    args = parser.parse_args()
    manifest = generate(args.output, args.spec)
    print(json.dumps({"fixtures": len(manifest["fixtures"]), "negativeFixtures": len(manifest["negativeFixtures"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
