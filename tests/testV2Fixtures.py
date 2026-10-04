from __future__ import annotations

import json
import tempfile
import unittest
import xml.etree.ElementTree as ElementTree
from pathlib import Path

from tools.generateV2Fixtures import generate
from tools.v2Catalog import SIZES, diagnosticCells


class V2FixtureTests(unittest.TestCase):
    def testCatalogCoversEveryDocumentAndQueryFamily(self) -> None:
        cells = diagnosticCells()
        identifiers = [cell["id"] for cell in cells]
        self.assertEqual(len(identifiers), 36)
        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertEqual(
            {cell["documentClass"] for cell in cells},
            {
                "sourceHtml",
                "sourceXml",
                "sourceJson",
                "sourceText",
                "renderedDom",
                "accessibilityTree",
            },
        )
        self.assertEqual(
            {cell["queryFamily"] for cell in cells},
            {
                "css",
                "xpath",
                "treeText",
                "jsonPointer",
                "jsonPath",
                "textLiteral",
                "regex",
                "role",
                "accessibleName",
                "accessibilityText",
                "stateExpanded",
            },
        )
        self.assertEqual(
            {cell["projection"].split(":", 1)[0] for cell in cells},
            {"text", "attribute", "node", "value", "captures", "accessibleName", "accessibilityText"},
        )

    def testGenerationIsDeterministicAndStructurallyValid(self) -> None:
        with tempfile.TemporaryDirectory() as firstDirectory, tempfile.TemporaryDirectory() as secondDirectory:
            first = Path(firstDirectory)
            second = Path(secondDirectory)
            firstManifest = generate(first / "fixtures", first / "spec.json")
            secondManifest = generate(second / "fixtures", second / "spec.json")
            self.assertEqual(firstManifest, secondManifest)
            self.assertEqual((first / "spec.json").read_bytes(), (second / "spec.json").read_bytes())
            self.assertEqual(len(firstManifest["fixtures"]), len(SIZES) * 6)
            self.assertEqual(len(firstManifest["negativeFixtures"]), 8)

            root = first / "fixtures"
            for fixture in firstManifest["fixtures"]:
                path = root / fixture["path"]
                self.assertEqual(path.stat().st_size, fixture["bytes"])
                if fixture["documentClass"] in {"sourceJson", "renderedDom", "accessibilityTree"}:
                    json.loads(path.read_text())
                elif fixture["documentClass"] == "sourceXml":
                    ElementTree.fromstring(path.read_bytes())
                elif fixture["documentClass"] == "sourceText":
                    self.assertEqual(len(path.read_text().splitlines()), fixture["records"])
                elif fixture["documentClass"] == "sourceHtml":
                    self.assertIn("data-selected='true'", path.read_text())

            spec = json.loads((first / "spec.json").read_text())
            self.assertFalse(spec["reporting"]["publicKpi"])
            self.assertFalse(spec["reporting"]["crossFormatAggregate"])
            self.assertEqual(len(spec["cells"]), 36)
            self.assertEqual(len(spec["correctnessCases"]), 30)
            self.assertEqual(
                {case["expectedStatus"] for case in spec["correctnessCases"]},
                {"ok", "queryRejected", "limitFailed"},
            )


if __name__ == "__main__":
    unittest.main()
