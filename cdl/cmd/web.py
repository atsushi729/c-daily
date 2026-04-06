"""
cdl/cmd/web.py — `cdl web` subcommand.

Usage:
    cdl web [--port PORT]

Starts the insights web UI on localhost and opens it in the default browser.
"""

from __future__ import annotations

import platform
import subprocess
import sys
import threading
import time
from pathlib import Path


def run(_lib_dir: Path, _log_dir: Path) -> None:
    # Parse optional --port argument
    port = 8765
    args = sys.argv[2:]
    if "--port" in args:
        idx = args.index("--port")
        try:
            port = int(args[idx + 1])
        except (IndexError, ValueError):
            print("❌ --port requires an integer value", file=sys.stderr)
            sys.exit(1)

    from cdl.insights.server import DEFAULT_HOST, serve

    # Open browser after a short delay so the server is ready
    url = f"http://{DEFAULT_HOST}:{port}"

    def _open_browser() -> None:
        time.sleep(0.4)
        if platform.system() == "Darwin":
            subprocess.run(["open", url], check=False)
        elif platform.system() == "Linux":
            subprocess.run(["xdg-open", url], check=False)

    threading.Thread(target=_open_browser, daemon=True).start()
    serve(host=DEFAULT_HOST, port=port)
