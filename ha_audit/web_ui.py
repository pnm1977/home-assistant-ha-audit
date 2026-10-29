#!/usr/bin/env python3
"""HA Audit minimal read-only Ingress UI (foundation).

This module is intentionally independent of HA Audit's one-shot audit runner.
Future integration will start it as the long-running app process.
"""

from __future__ import annotations

import html
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


PORT = int(os.environ.get("HA_AUDIT_WEB_PORT", "8099"))
REPORT = Path("/config/ha_audit_latest.txt")
MAX_REPORT_BYTES = 256 * 1024
INGRESS_PROXY = "172.30.32.2"
ALLOW_LOCALHOST = os.environ.get("HA_AUDIT_WEB_TEST_LOCAL", "") == "1"


class Handler(BaseHTTPRequestHandler):
    server_version = "HA-Audit-UI"
    sys_version = ""

    def _allowed(self) -> bool:
        peer = self.client_address[0]
        return peer == INGRESS_PROXY or (ALLOW_LOCALHOST and peer in ("127.0.0.1", "::1"))

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'self'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if not self._allowed():
            self._send(403, b"Forbidden", "text/plain; charset=utf-8")
            return

        path = urlsplit(self.path).path
        if path == "/health":
            self._send(200, b"ok\n", "text/plain; charset=utf-8")
            return
        if path not in ("/", "/index.html"):
            self._send(404, b"Not found", "text/plain; charset=utf-8")
            return

        try:
            if REPORT.stat().st_size > MAX_REPORT_BYTES:
                summary = "The latest report is too large to display in this initial UI."
            else:
                summary = REPORT.read_text(encoding="utf-8")
        except FileNotFoundError:
            summary = "No audit summary yet. Run HA Audit to generate the first report."
        except OSError:
            summary = "The latest audit summary could not be read."

        page = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>HA Audit</title>
<style>
:root{font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color-scheme:light dark}
body{margin:0;background:Canvas;color:CanvasText}
header{padding:1.25rem 1.5rem;border-bottom:1px solid GrayText}
main{margin:0 auto;max-width:1000px;padding:1.25rem 1.5rem 3rem}
h1{margin:0;font-size:1.6rem}h2{font-size:1.1rem}
.sub{opacity:.75;margin:.35rem 0 0}
pre{background:Canvas;border:1px solid GrayText;border-radius:8px;padding:1rem;
white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.5;font-size:.9rem}
</style></head><body>
<header><h1>HA Audit</h1><p class="sub">Read-only dashboard · foundation</p></header>
<main><h2>Latest audit summary</h2><pre>""" + html.escape(summary) + """</pre>
<p class="sub">Investigation feedback and automatic context management will be added in later steps.</p>
</main></body></html>"""
        self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")

    def do_POST(self) -> None:
        self._send(405, b"Read-only UI", "text/plain; charset=utf-8")


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
