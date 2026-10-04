from __future__ import annotations

import argparse
import unittest
from pathlib import Path

from tools.runV2Matrix import command
from tools.v2Catalog import specification


class V2ProtocolTests(unittest.TestCase):
    def testFrozenRecordPopulationAndNonKpiBoundary(self) -> None:
        spec = specification()
        controls = sum(1 for cell in spec["cells"] if cell["controlArm"] is not None)
        matrixRecords = (
            len(spec["cells"])
            * len(spec["sizes"])
            * 4
            * spec["campaigns"]
            + controls * len(spec["sizes"]) * 3 * spec["campaigns"]
        )
        extractionRecords = (
            len(spec["extractionLane"]["sizes"])
            * (len(spec["extractionLane"]["phases"]) + len(spec["extractionLane"]["controlPhases"]))
            * spec["campaigns"]
            + sum(len(lane["sizes"]) for lane in spec["extractionCompatibilityLanes"])
            * spec["campaigns"]
        )
        self.assertEqual(matrixRecords, 3105)
        self.assertEqual(extractionRecords, 135)
        self.assertFalse(spec["reporting"]["publicKpi"])
        self.assertFalse(spec["reporting"]["crossFormatAggregate"])

    def testCommandsPreserveArmAndNamespaceIdentity(self) -> None:
        spec = specification()
        cell = next(item for item in spec["cells"] if item["id"] == "xml.css.text")
        args = argparse.Namespace(
            yosoi=Path("/artifacts/yosoiV2"),
            controls=Path("/artifacts/v2Controls"),
        )
        yosoi = command(args, cell, "yosoiRust", "tiny", "locate", Path("/fixture.xml"), 2, 1)
        control = command(args, cell, "roxmltree", "tiny", "locate", Path("/fixture.xml"), 2, 1)
        self.assertEqual(yosoi[0], "/artifacts/yosoiV2")
        self.assertIn("--namespace-prefix", yosoi)
        self.assertIn("urn:product", yosoi)
        self.assertEqual(control[0:3], ["/artifacts/v2Controls", "--arm", "roxmltree"])
        self.assertNotIn("--namespace-prefix", control)


if __name__ == "__main__":
    unittest.main()
