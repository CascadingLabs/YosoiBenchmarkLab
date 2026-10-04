from __future__ import annotations

from typing import Any


TARGET_INDEX = 17
SIZES = {"tiny": 32, "medium": 64, "large": 4096}
NAMESPACE = {"prefix": "p", "uri": "urn:product"}


def projectedText(value: str) -> dict[str, Any]:
    return {"kind": "text", "value": value}


def projectedAttribute(name: str, value: str) -> dict[str, Any]:
    return {"kind": "attribute", "value": {"name": name, "value": value}}


def projectedJson(value: Any) -> dict[str, Any]:
    return {"kind": "json", "value": value}


def projectedCapture(text: str, name: str, value: str) -> dict[str, Any]:
    return {
        "kind": "text_with_captures",
        "value": {"text": text, "captures": {name: value}},
    }


def cell(
    identifier: str,
    documentClass: str,
    queryFamily: str,
    expression: str,
    projection: str,
    expectedValues: list[dict[str, Any]] | None,
    controlArm: str | None,
    equivalence: str,
    *,
    namespace: dict[str, str] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": identifier,
        "documentClass": documentClass,
        "queryFamily": queryFamily,
        "expression": expression,
        "projection": projection,
        "expectedMatchCount": 1,
        "expectedValues": expectedValues,
        "controlArm": controlArm,
        "equivalence": equivalence,
        "sizes": list(SIZES),
        "phases": ["queryBuild", "parse", "locate", "endToEnd"],
        "controlPhases": ["parse", "locate", "endToEnd"],
    }
    if namespace is not None:
        result["namespace"] = namespace
    return result


def diagnosticCells() -> list[dict[str, Any]]:
    targetId = f"p-{TARGET_INDEX:06d}"
    targetName = f"Unique target {TARGET_INDEX:06d}"
    targetPrice = f"${TARGET_INDEX}.{TARGET_INDEX:02d}"
    htmlProduct = "//article[@data-selected='true']"

    cells = [
        cell("html.css.text", "sourceHtml", "css", "article.product[data-selected='true'] span.name", "text", [projectedText(targetName)], "rustScraper", "exact"),
        cell("html.css.attribute", "sourceHtml", "css", "article.product[data-selected='true']", "attribute:data-id", [projectedAttribute("data-id", targetId)], "rustScraper", "exact"),
        cell("html.css.node", "sourceHtml", "css", "article.product[data-selected='true']", "node", None, "rustScraper", "nearestPrimitive"),
        cell("html.xpath.text", "sourceHtml", "xpath", f"{htmlProduct}//span[@class='name']", "text", [projectedText(targetName)], "rustScraper", "nearestPrimitive"),
        cell("html.xpath.attribute", "sourceHtml", "xpath", htmlProduct, "attribute:data-id", [projectedAttribute("data-id", targetId)], "rustScraper", "nearestPrimitive"),
        cell("html.xpath.node", "sourceHtml", "xpath", htmlProduct, "node", None, "rustScraper", "nearestPrimitive"),
        cell("html.treeText.text", "sourceHtml", "treeText", targetName, "text", [projectedText(targetName)], "rustScraper", "nearestPrimitive"),
        cell("html.treeText.node", "sourceHtml", "treeText", targetName, "node", None, "rustScraper", "nearestPrimitive"),
        cell("xml.css.text", "sourceXml", "css", "p|product[data-selected='true'] p|name", "text", [projectedText(targetName)], "roxmltree", "exact", namespace=NAMESPACE),
        cell("xml.css.attribute", "sourceXml", "css", "p|product[data-selected='true']", "attribute:data-id", [projectedAttribute("data-id", targetId)], "roxmltree", "nearestPrimitive", namespace=NAMESPACE),
        cell("xml.css.node", "sourceXml", "css", "p|product[data-selected='true']", "node", None, "roxmltree", "nearestPrimitive", namespace=NAMESPACE),
        cell("xml.xpath.text", "sourceXml", "xpath", "/catalog/p:product[@data-selected='true']/p:name", "text", [projectedText(targetName)], "roxmltree", "nearestPrimitive", namespace=NAMESPACE),
        cell("xml.xpath.attribute", "sourceXml", "xpath", "/catalog/p:product[@data-selected='true']", "attribute:data-id", [projectedAttribute("data-id", targetId)], "roxmltree", "nearestPrimitive", namespace=NAMESPACE),
        cell("xml.xpath.node", "sourceXml", "xpath", "/catalog/p:product[@data-selected='true']", "node", None, "roxmltree", "nearestPrimitive", namespace=NAMESPACE),
        cell("xml.treeText.text", "sourceXml", "treeText", targetName, "text", [projectedText(targetName)], "roxmltree", "nearestPrimitive"),
        cell("xml.treeText.node", "sourceXml", "treeText", targetName, "node", None, "roxmltree", "nearestPrimitive"),
        cell("json.pointer.value", "sourceJson", "jsonPointer", f"/products/{TARGET_INDEX}/price", "value", [projectedJson(targetPrice)], "serdeJson", "exact"),
        cell("json.path.value", "sourceJson", "jsonPath", f"$.products[{TARGET_INDEX}].price", "value", [projectedJson(targetPrice)], "serdeJson", "nearestPrimitive"),
        cell("text.literal.text", "sourceText", "textLiteral", f"ORDER-{TARGET_INDEX:06d}", "text", [projectedText(f"ORDER-{TARGET_INDEX:06d}")], "stdString", "exact"),
        cell("text.regex.text", "sourceText", "regex", rf"ORDER-{TARGET_INDEX:06d} TOTAL=\${TARGET_INDEX}\.{TARGET_INDEX:02d}", "text", [projectedText(f"ORDER-{TARGET_INDEX:06d} TOTAL={targetPrice}")], "rustRegex", "exact"),
        cell("text.regex.captures", "sourceText", "regex", rf"ORDER-(?P<id>{TARGET_INDEX:06d}) TOTAL=\${TARGET_INDEX}\.{TARGET_INDEX:02d}", "captures:id", [projectedCapture(f"ORDER-{TARGET_INDEX:06d} TOTAL={targetPrice}", "id", f"{TARGET_INDEX:06d}")], "rustRegex", "exact"),
        cell("dom.css.text", "renderedDom", "css", "article.product[data-selected='true'] span.name", "text", [projectedText(targetName)], None, "internalOnly"),
        cell("dom.css.attribute", "renderedDom", "css", "article.product[data-selected='true']", "attribute:data-id", [projectedAttribute("data-id", targetId)], None, "internalOnly"),
        cell("dom.css.node", "renderedDom", "css", "article.product[data-selected='true']", "node", None, None, "internalOnly"),
        cell("dom.xpath.text", "renderedDom", "xpath", f"{htmlProduct}//span[@class='name']", "text", [projectedText(targetName)], None, "internalOnly"),
        cell("dom.xpath.attribute", "renderedDom", "xpath", htmlProduct, "attribute:data-id", [projectedAttribute("data-id", targetId)], None, "internalOnly"),
        cell("dom.xpath.node", "renderedDom", "xpath", htmlProduct, "node", None, None, "internalOnly"),
        cell("dom.treeText.text", "renderedDom", "treeText", targetName, "text", [projectedText(targetName)], None, "internalOnly"),
        cell("dom.treeText.node", "renderedDom", "treeText", targetName, "node", None, None, "internalOnly"),
        cell("ax.role.name", "accessibilityTree", "role", "target-button", "accessibleName", [projectedText(f"Buy {targetId}")], None, "internalOnly"),
        cell("ax.role.node", "accessibilityTree", "role", "target-button", "node", None, None, "internalOnly"),
        cell("ax.name.node", "accessibilityTree", "accessibleName", f"Buy {targetId}", "node", None, None, "internalOnly"),
        cell("ax.name.name", "accessibilityTree", "accessibleName", f"Buy {targetId}", "accessibleName", [projectedText(f"Buy {targetId}")], None, "internalOnly"),
        cell("ax.text.text", "accessibilityTree", "accessibilityText", f"Buy {targetId}", "accessibilityText", [projectedText(f"Buy {targetId}")], None, "internalOnly"),
        cell("ax.text.node", "accessibilityTree", "accessibilityText", f"Buy {targetId}", "node", None, None, "internalOnly"),
        cell("ax.state.node", "accessibilityTree", "stateExpanded", "true", "node", None, None, "internalOnly"),
    ]
    return cells


def specification() -> dict[str, Any]:
    conformanceCases = [
        {"id": "html.noMatch", "documentClass": "sourceHtml", "queryFamily": "css", "expression": ".missing", "projection": "node", "expectedStatus": "ok", "expectedMatchCount": 0},
        {"id": "xml.noMatch", "documentClass": "sourceXml", "queryFamily": "css", "expression": "missing", "projection": "node", "expectedStatus": "ok", "expectedMatchCount": 0},
        {"id": "json.noMatch", "documentClass": "sourceJson", "queryFamily": "jsonPointer", "expression": "/missing", "projection": "value", "expectedStatus": "ok", "expectedMatchCount": 0},
        {"id": "text.noMatch", "documentClass": "sourceText", "queryFamily": "textLiteral", "expression": "MISSING", "projection": "text", "expectedStatus": "ok", "expectedMatchCount": 0},
        {"id": "dom.noMatch", "documentClass": "renderedDom", "queryFamily": "css", "expression": ".missing", "projection": "node", "expectedStatus": "ok", "expectedMatchCount": 0},
        {"id": "ax.noMatch", "documentClass": "accessibilityTree", "queryFamily": "role", "expression": "missing", "projection": "node", "expectedStatus": "ok", "expectedMatchCount": 0},
        {"id": "html.multiMatch", "documentClass": "sourceHtml", "queryFamily": "css", "expression": "article.product", "projection": "node", "expectedStatus": "ok", "expectedMatchCount": SIZES["tiny"]},
        {"id": "xml.multiMatch", "documentClass": "sourceXml", "queryFamily": "css", "expression": "p|product", "projection": "node", "namespace": NAMESPACE, "expectedStatus": "ok", "expectedMatchCount": SIZES["tiny"]},
        {"id": "json.multiMatch", "documentClass": "sourceJson", "queryFamily": "jsonPath", "expression": "$.products[*].price", "projection": "value", "expectedStatus": "ok", "expectedMatchCount": SIZES["tiny"]},
        {"id": "text.multiMatch", "documentClass": "sourceText", "queryFamily": "regex", "expression": r"ORDER-\d{6}", "projection": "text", "expectedStatus": "ok", "expectedMatchCount": SIZES["tiny"]},
        {"id": "dom.multiMatch", "documentClass": "renderedDom", "queryFamily": "css", "expression": "article.product", "projection": "node", "expectedStatus": "ok", "expectedMatchCount": SIZES["tiny"]},
        {"id": "ax.multiMatch", "documentClass": "accessibilityTree", "queryFamily": "role", "expression": "button", "projection": "node", "expectedStatus": "ok", "expectedMatchCount": SIZES["tiny"] - 1},
        {"id": "html.invalidCss", "documentClass": "sourceHtml", "queryFamily": "css", "expression": "", "projection": "node", "expectedStatus": "queryRejected"},
        {"id": "html.invalidXpath", "documentClass": "sourceHtml", "queryFamily": "xpath", "expression": "//*[", "projection": "node", "expectedStatus": "queryRejected"},
        {"id": "xml.invalidXpath", "documentClass": "sourceXml", "queryFamily": "xpath", "expression": "//*[", "projection": "node", "expectedStatus": "queryRejected"},
        {"id": "json.invalidPath", "documentClass": "sourceJson", "queryFamily": "jsonPath", "expression": "$..products", "projection": "value", "expectedStatus": "queryRejected"},
        {"id": "text.invalidRegex", "documentClass": "sourceText", "queryFamily": "regex", "expression": "(?=a)", "projection": "text", "expectedStatus": "queryRejected"},
        {"id": "html.matchLimit", "documentClass": "sourceHtml", "queryFamily": "css", "expression": "article.product", "projection": "node", "maxMatches": 1, "expectedStatus": "limitFailed"},
        {"id": "xml.matchLimit", "documentClass": "sourceXml", "queryFamily": "css", "expression": "p|product", "projection": "node", "namespace": NAMESPACE, "maxMatches": 1, "expectedStatus": "limitFailed"},
        {"id": "json.matchLimit", "documentClass": "sourceJson", "queryFamily": "jsonPath", "expression": "$.products[*].price", "projection": "value", "maxMatches": 1, "expectedStatus": "limitFailed"},
        {"id": "text.matchLimit", "documentClass": "sourceText", "queryFamily": "regex", "expression": r"ORDER-\d{6}", "projection": "text", "maxMatches": 1, "expectedStatus": "limitFailed"},
        {"id": "dom.matchLimit", "documentClass": "renderedDom", "queryFamily": "css", "expression": "article.product", "projection": "node", "maxMatches": 1, "expectedStatus": "limitFailed"},
        {"id": "ax.matchLimit", "documentClass": "accessibilityTree", "queryFamily": "role", "expression": "button", "projection": "node", "maxMatches": 1, "expectedStatus": "limitFailed"},
        {"id": "html.treeTextAttributeUnsupported", "documentClass": "sourceHtml", "queryFamily": "treeText", "expression": "Unique target 000017", "projection": "attribute:data-id", "expectedStatus": "queryRejected", "classification": "unsupportedCombination"},
        {"id": "xml.treeTextAttributeUnsupported", "documentClass": "sourceXml", "queryFamily": "treeText", "expression": "Unique target 000017", "projection": "attribute:data-id", "expectedStatus": "queryRejected", "classification": "unsupportedCombination"},
        {"id": "dom.treeTextAttributeUnsupported", "documentClass": "renderedDom", "queryFamily": "treeText", "expression": "Unique target 000017", "projection": "attribute:data-id", "expectedStatus": "queryRejected", "classification": "unsupportedCombination"},
        {"id": "ax.stateNameUnsupported", "documentClass": "accessibilityTree", "queryFamily": "stateExpanded", "expression": "true", "projection": "accessibleName", "expectedStatus": "queryRejected", "classification": "unsupportedCombination"},
        {"id": "json.regexUnsupported", "documentClass": "sourceJson", "queryFamily": "regex", "expression": "price", "projection": "text", "expectedStatus": "queryRejected", "classification": "unsupportedCombination"},
        {"id": "text.jsonPointerUnsupported", "documentClass": "sourceText", "queryFamily": "jsonPointer", "expression": "/products/0", "projection": "value", "expectedStatus": "queryRejected", "classification": "unsupportedCombination"},
        {"id": "ax.cssUnsupported", "documentClass": "accessibilityTree", "queryFamily": "css", "expression": "button", "projection": "node", "expectedStatus": "queryRejected", "classification": "unsupportedCombination"},
    ]
    return {
        "schemaVersion": "yosoi.benchmark.diagnostics.v2",
        "status": "frozenForBaselineV2",
        "purpose": "internalNonKpiDiagnostics",
        "sourceRevisionPolicy": "immutableArtifactIdentityRequired",
        "sizes": SIZES,
        "targetIndex": TARGET_INDEX,
        "campaigns": 5,
        "samplesPerCampaign": 5,
        "operationsPerSample": 1,
        "correctnessGate": {
            "terminalStatus": "ok",
            "matchCount": "exact",
            "scalarValues": "exact",
            "nodeValues": "deterministicPerArm",
            "wrongOutputRanked": False,
        },
        "reporting": {
            "crossFormatAggregate": False,
            "publicKpi": False,
            "controlEquivalenceMustBeVisible": True,
        },
        "cells": diagnosticCells(),
        "correctnessCases": conformanceCases,
        "extractionLane": {
            "id": "contracts.html.products",
            "documentClass": "sourceHtml",
            "sizes": ["tiny", "medium"],
            "phases": [
                "planCached",
                "locate",
                "extract",
                "extractValidate",
                "extractValidateRequireAll",
                "endToEnd",
            ],
            "controlArm": "rustScraperRecords",
            "controlPhases": ["endToEnd"],
            "expectedRecordCount": "fixtureRecordCount",
            "publicKpi": False,
        },
        "extractionCompatibilityLanes": [
            {
                "id": "contracts.xml.products",
                "documentClass": "sourceXml",
                "phase": "endToEnd",
                "expectedOutcome": "fixtureRecordCount",
                "sizes": ["tiny", "medium"],
            },
            {
                "id": "contracts.text.summary",
                "documentClass": "sourceText",
                "phase": "endToEnd",
                "expectedOutcome": "oneRecord",
                "sizes": list(SIZES),
            },
            {
                "id": "contracts.dom.products",
                "documentClass": "renderedDom",
                "phase": "endToEnd",
                "expectedOutcome": "fixtureRecordCount",
                "sizes": ["tiny", "medium"],
            },
            {
                "id": "contracts.ax.summary",
                "documentClass": "accessibilityTree",
                "phase": "endToEnd",
                "expectedOutcome": "oneRecord",
                "sizes": list(SIZES),
            },
            {
                "id": "contracts.json.rejection",
                "documentClass": "sourceJson",
                "phase": "endToEndRejected",
                "expectedOutcome": "oneValidationIssue",
                "sizes": list(SIZES),
            },
        ],
        "extractionLimitLanes": [
            {
                "id": "contracts.html.products",
                "documentClass": "sourceHtml",
                "size": "large",
                "expectedStatus": "resourceBounded",
            },
            {
                "id": "contracts.xml.products",
                "documentClass": "sourceXml",
                "size": "large",
                "expectedStatus": "resourceBounded",
            },
            {
                "id": "contracts.dom.products",
                "documentClass": "renderedDom",
                "size": "large",
                "expectedStatus": "resourceBounded",
            },
        ],
    }
