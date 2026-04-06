"""
insights/server.py - Lightweight HTTP server for the cdl web UI.

Routes:
    GET /                   → index page (activity heatmap + project list)
    GET /project/{name}     → project detail page
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote, urlparse

from cdl.insights._templates import (
    index_html,
    not_found_html,
    project_html,
    session_html,
)
from cdl.insights.extractor import (
    activity_heatmap,
    project_detail,
    project_list,
    session_data,
)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"

        if path == "/":
            heatmap = activity_heatmap()
            projects = project_list()
            html = index_html(heatmap, projects)
            self._send_html(html)

        elif path.startswith("/project/"):
            tail = unquote(path[len("/project/"):])
            # Route: /project/{name}/session/{session_id}
            if "/session/" in tail:
                name, _, session_id = tail.partition("/session/")
                result = session_data(name, session_id)
                if result is None:
                    self._send_html(not_found_html(path), status=404)
                else:
                    meta, diffs = result
                    self._send_html(session_html(name, meta, diffs))
            # Route: /project/{name}
            else:
                detail = project_detail(tail)
                if detail is None:
                    self._send_html(not_found_html(path), status=404)
                else:
                    self._send_html(project_html(detail))

        else:
            self._send_html(not_found_html(path), status=404)

    def _send_html(self, html: str, status: int = 200) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        # Suppress per-request logs; the caller prints the server URL instead.
        pass


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Start the server and block until KeyboardInterrupt."""
    server = HTTPServer((host, port), _Handler)
    url = f"http://{host}:{port}"
    print(f"  cdl insights  →  {url}")
    print("  Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
    finally:
        server.server_close()
