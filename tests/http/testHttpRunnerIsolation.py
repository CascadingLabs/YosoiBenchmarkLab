from __future__ import annotations

import argparse
import unittest
from pathlib import Path

from tools.runHttpMatrix import command


class HttpRunnerIsolationTests(unittest.TestCase):
    def testCrawleeUsesAdapterWorkingDirectory(self) -> None:
        repository = Path("/benchmark-lab")
        arguments = argparse.Namespace(
            repository=repository,
            base="http://127.0.0.1:1234",
            count=4,
            yosoi=Path("/artifacts/yosoiRequest"),
            colly=Path("/artifacts/colly"),
            python=Path("/python"),
        )

        commandValue, cwd = command(arguments, "crawleeCheerio", 2, 20)

        self.assertEqual(commandValue[0:2], ["node", "adapter.mjs"])
        self.assertEqual(cwd, repository / "adapters/http/node-crawlee")


if __name__ == "__main__":
    unittest.main()
