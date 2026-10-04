from __future__ import annotations

import gzip
import json
import threading
import unittest
import urllib.request

from tools.httpFixtureServer import create_server


class HttpFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = create_server()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_page_redirect_gzip_encoding_status_and_metrics(self) -> None:
        page = urllib.request.urlopen(f"{self.base}/page?id=7").read()
        self.assertIn(b'value-7', page)

        redirected = urllib.request.urlopen(f"{self.base}/redirect?id=8").read()
        self.assertIn(b'value-8', redirected)

        request = urllib.request.Request(f"{self.base}/gzip?id=9")
        with urllib.request.urlopen(request) as response:
            self.assertEqual(gzip.decompress(response.read()).find(b'value-9') >= 0, True)

        latin = urllib.request.urlopen(f"{self.base}/latin1?id=10").read().decode("latin-1")
        self.assertIn("value-10-café", latin)

        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(f"{self.base}/status?id=11")
        self.assertEqual(context.exception.code, 503)

        metrics = json.loads(urllib.request.urlopen(f"{self.base}/metrics").read())
        self.assertGreaterEqual(metrics["requests"], 6)
        self.assertGreaterEqual(metrics["peakActive"], 1)


if __name__ == "__main__":
    unittest.main()
