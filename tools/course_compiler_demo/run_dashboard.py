#!/usr/bin/env python3
"""Run the local-only Curriculum Compiler operator dashboard."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.security import DashboardSecurityError, validate_loopback
from dashboard.server import build_server


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()
    try:
        host, port = validate_loopback(args.host, args.port)
        server = build_server(host, port)
    except DashboardSecurityError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Local dashboard: http://{host}:{port}/")
    print("Shutdown: press Ctrl-C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
