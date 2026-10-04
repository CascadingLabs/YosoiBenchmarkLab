from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from tools.generateFixtures import generate_fixture_set, render_catalog


class FixtureContractTests(unittest.TestCase):
    def test_catalog_generation_is_byte_deterministic(self) -> None:
        first, first_oracle = render_catalog(records=128, selected_indexes=[73])
        second, second_oracle = render_catalog(records=128, selected_indexes=[73])

        self.assertEqual(first, second)
        self.assertEqual(first_oracle, second_oracle)
        self.assertEqual(first_oracle, ["USD 19.73"])
        self.assertEqual(hashlib.sha256(first).digest(), hashlib.sha256(second).digest())

    def test_generated_manifest_matches_materialized_bytes_and_oracles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = generate_fixture_set(root, hard_records=250)

            for fixture in manifest["fixtures"]:
                fixture_path = root / fixture["path"]
                payload = fixture_path.read_bytes()
                self.assertEqual(len(payload), fixture["bytes"])
                self.assertEqual(hashlib.sha256(payload).hexdigest(), fixture["sha256"])

            caveman = next(item for item in manifest["fixtures"] if item["id"] == "cavemanCatalog")
            hard = next(item for item in manifest["fixtures"] if item["id"] == "hardCatalog")
            self.assertEqual(caveman["expectedValues"], ["USD 19.73"])
            self.assertEqual(len(hard["expectedValues"]), 64)
            self.assertEqual(hard["selectedRecords"], 64)


if __name__ == "__main__":
    unittest.main()
