from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.generateFixtures import generate_fixture_set


class PythonAdapterTests(unittest.TestCase):
    def test_every_python_arm_returns_the_exact_caveman_value(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        adapter = repository / "adapters" / "python" / "adapter.py"
        arms = [
            "beautifulSoupHtmlParser",
            "beautifulSoupLxml",
            "lxml",
            "parsel",
            "scraplingParser",
            "selectolaxLexbor",
        ]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = generate_fixture_set(root, hard_records=250)
            caveman = next(item for item in manifest["fixtures"] if item["id"] == "cavemanCatalog")
            fixture = root / caveman["path"]

            for arm in arms:
                with self.subTest(arm=arm):
                    completed = subprocess.run(
                        [
                            sys.executable,
                            str(adapter),
                            "--arm",
                            arm,
                            "--fixture",
                            str(fixture),
                            "--task",
                            "caveman",
                            "--phase",
                            "endToEnd",
                            "--samples",
                            "1",
                            "--operations",
                            "1",
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    result = json.loads(completed.stdout)
                    self.assertEqual(result["terminalStatus"], "ok")
                    self.assertEqual(result["values"], ["USD 19.73"])
                    self.assertEqual(result["matchCount"], 1)
                    self.assertEqual(len(result["samplesNs"]), 1)
                    self.assertGreater(result["samplesNs"][0], 0)


if __name__ == "__main__":
    unittest.main()
