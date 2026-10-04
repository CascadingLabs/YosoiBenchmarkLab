from __future__ import annotations

import argparse
import gzip
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


def body_for(identifier: int) -> bytes:
    padding = ("deterministic payload café 東京 🦀 " * 850).encode("utf-8")
    return (
        b'<!doctype html><html><body><article class="result" data-id="'
        + str(identifier).encode()
        + b'"><span class="value">value-'
        + str(identifier).encode()
        + b"</span><p>"
        + padding
        + b"</p></article></body></html>"
    )


class FixtureState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.requests = 0
        self.active = 0
        self.peak_active = 0

    def begin(self) -> None:
        with self.lock:
            self.requests += 1
            self.active += 1
            self.peak_active = max(self.peak_active, self.active)

    def end(self) -> None:
        with self.lock:
            self.active -= 1


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    state: FixtureState

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def respond(self, status: int, body: bytes, content_type: str, *, encoding: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        if encoding is not None:
            self.send_header("Content-Encoding", encoding)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        self.state.begin()
        try:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            identifier = int(query.get("id", ["0"])[0])
            delay_ms = int(query.get("delayMs", ["0"])[0])
            if delay_ms:
                time.sleep(delay_ms / 1000)
            if parsed.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", f"/page?id={identifier}&delayMs={delay_ms}")
                self.send_header("Content-Length", "0")
                self.send_header("Connection", "close")
                self.end_headers()
            elif parsed.path == "/gzip":
                self.respond(200, gzip.compress(body_for(identifier)), "text/html; charset=utf-8", encoding="gzip")
            elif parsed.path == "/latin1":
                body = f'<span class="value">value-{identifier}-café</span>'.encode("latin-1")
                self.respond(200, body, "text/html; charset=iso-8859-1")
            elif parsed.path == "/status":
                self.respond(503, body_for(identifier), "text/html; charset=utf-8")
            elif parsed.path == "/script":
                script = f'document.querySelector("span.value").textContent="value-{identifier}";'.encode()
                self.respond(200, script, "application/javascript; charset=utf-8")
            elif parsed.path == "/dynamic":
                body = (
                    f'<!doctype html><html><body><article data-id="{identifier}">'
                    '<span class="value">pending</span>'
                    f'<script src="/script?id={identifier}&delayMs={delay_ms}"></script>'
                    '</article></body></html>'
                ).encode()
                self.respond(200, body, "text/html; charset=utf-8")
            elif parsed.path == "/metrics":
                payload = json.dumps(
                    {"requests": self.state.requests, "active": self.state.active, "peakActive": self.state.peak_active}
                ).encode()
                self.respond(200, payload, "application/json")
            else:
                self.respond(200, body_for(identifier), "text/html; charset=utf-8")
        finally:
            self.state.end()


class BenchmarkServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 128


def create_server() -> ThreadingHTTPServer:
    state = FixtureState()
    handler = type("BoundHandler", (Handler,), {"state": state})
    return BenchmarkServer(("127.0.0.1", 0), handler)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity", required=True)
    args = parser.parse_args()
    server = create_server()
    print(json.dumps({"identity": args.identity, "port": server.server_port}), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
