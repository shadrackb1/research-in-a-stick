#!/usr/bin/env python3
"""Research-in-a-Stick launcher."""
from __future__ import annotations
import argparse, sys, webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ris.config import HOST, PORT, ensure_dirs
from ris.server import serve


def main() -> None:
    parser = argparse.ArgumentParser(description="Research-in-a-Stick")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    ensure_dirs()
    if not args.no_browser:
        try:
            webbrowser.open(f"http://{args.host}:{args.port}")
        except Exception:
            pass
    serve(args.host, args.port)


if __name__ == "__main__":
    main()
