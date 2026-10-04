from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.generateFixtures import generate_fixture_set


class CompiledAdapterTests(unittest.TestCase):
    def test_compiled_arms_return_the_exact_caveman_value(self) -> None:
        artifacts_value = os.environ.get("YOSOI_BENCHMARK_ARTIFACTS")
        if artifacts_value is None:
            self.skipTest("YOSOI_BENCHMARK_ARTIFACTS is not set")
        artifacts = Path(artifacts_value)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = generate_fixture_set(root, hard_records=250)
            caveman = next(item for item in manifest["fixtures"] if item["id"] == "cavemanCatalog")
            fixture = root / caveman["path"]

            for arm in ("yosoiRust", "rustScraper", "goquery"):
                with self.subTest(arm=arm):
                    completed = subprocess.run(
                        [
                            str(artifacts / arm),
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
                    self.assertEqual(result["armId"], arm)
                    self.assertEqual(result["terminalStatus"], "ok")
                    self.assertEqual(result["values"], ["USD 19.73"])
                    self.assertEqual(result["matchCount"], 1)


if __name__ == "__main__":
    unittest.main()
