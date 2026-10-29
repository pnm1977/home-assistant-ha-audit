#!/usr/bin/env python3
"""HA Audit Ingress UI: read-only issue overview plus persistent context initialization.

This version intentionally does not interpret or change issue priorities and does not
accept investigation feedback yet. The next iteration will add explicit user actions.
"""

from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

PORT = int(os.environ.get("HA_AUDIT_WEB_PORT", "8099"))
REPORT = Path("/config/ha_audit_latest.txt")
ISSUES = Path("/config/log_priority_final.json")
CONTEXT = Path("/config/investigation_context.json")
MAX_REPORT_BYTES = 256 * 1024
MAX_JSON_BYTES = 1024 * 1024
INGRESS_PROXY = "172.30.32.2"
ALLOW_LOCALHOST = os.environ.get("HA_AUDIT_WEB_TEST_LOCAL", "") == "1"


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def initialize_context() -> str | None:
    """Create default private data exactly once, without overwriting existing context."""
    initial = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scheduled_events": [],
        "investigations": {},
    }
    try:
        CONTEXT.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(CONTEXT, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(initial, file, indent=2, ensure_ascii=False)
            file.write("\n")
        return None
    except FileExistsError:
        return None
    except OSError as exc:
        return f"Could not initialize investigation storage: {exc.strerror or type(exc).__name__}"


def read_json(path: Path) -> dict | None:
    try:
        if path.stat().st_size > MAX_JSON_BYTES:
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError):
        return None


def read_summary() -> str:
    try:
        if REPORT.stat().st_size > MAX_REPORT_BYTES:
            return "The latest report is too large to display."
        return REPORT.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "No audit summary yet. Start HA Audit to generate its first report."
    except (OSError, UnicodeError):
        return "The latest audit summary could not be read."


def build_issues() -> str:
    result = read_json(ISSUES)
    if not result or not isinstance(result.get("families"), list):
        return '<p class="muted">Issue details are not yet available; the full audit remains below.</p>'

    ranked = []
    for family in result["families"]:
        if not isinstance(family, dict):
            continue
        priority = family.get("final_priority", "")
        if priority not in ("VERY HIGH", "HIGH", "MEDIUM"):
            continue
        ranked.append(family)

    rank = {"VERY HIGH": 0, "HIGH": 1, "MEDIUM": 2}
    ranked.sort(key=lambda item: (rank[item.get("final_priority")], str(item.get("title", ""))))

    rows = []
    for family in ranked[:20]:
        recurrence = family.get("recurrence", {})
        rec_class = recurrence.get("class", "Unknown") if isinstance(recurrence, dict) else "Unknown"
        rows.append(
            '<tr><td><span class="badge">' + escape(family.get("final_priority", ""))
            + '</span></td><td>' + escape(family.get("title", "Unnamed issue"))
            + '</td><td>' + escape(rec_class) + '</td></tr>'
        )

    if not rows:
        return '<p class="muted">No current HIGH or MEDIUM findings.</p>'
    return (
        '<div class="table-scroll"><table><thead><tr><th>Priority</th><th>Finding</th>'
        '<th>Recurrence</th></tr></thead><tbody>' + "".join(rows)
        + '</tbody></table></div><p class="muted">Original audit priorities are unchanged. '
        'Investigation feedback will be added next.</p>'
    )


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

        page = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>HA Audit</title><style>
:root{font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color-scheme:light dark}
body{margin:0;background:Canvas;color:CanvasText}header{padding:1.25rem 1.5rem;border-bottom:1px solid GrayText}
main{margin:0 auto;max-width:1100px;padding:1.25rem 1.5rem 3rem}h1{margin:0;font-size:1.6rem}h2{font-size:1.2rem;margin-top:1.8rem}
.muted{opacity:.7;font-size:.92rem}.table-scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;text-align:left}
th,td{border-bottom:1px solid GrayText;padding:.7rem .6rem;font-size:.92rem}th{font-weight:700}
.badge{font-weight:700}pre{border:1px solid GrayText;border-radius:8px;padding:1rem;white-space:pre-wrap;
overflow-wrap:anywhere;line-height:1.5;font-size:.9rem}
</style></head><body><header><h1>HA Audit</h1><p class="muted">Read-only findings · investigation foundation</p></header>
<main><h2>Issues needing review</h2>""" + build_issues() + """
<h2>Complete latest audit summary</h2><pre>""" + escape(read_summary()) + """</pre>
<p class="muted">Private investigation storage is initialized automatically and will never be reset by a new audit.</p>
</main></body></html>"""
        self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")

    def do_POST(self) -> None:
        self._send(405, b"Read-only UI", "text/plain; charset=utf-8")


if __name__ == "__main__":
    warning = initialize_context()
    if warning:
        print("HA Audit: " + warning, flush=True)
    else:
        print("HA Audit: persistent investigation storage ready", flush=True)
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
