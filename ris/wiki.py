"""Offline wiki via bundled Kiwix (kiwix-serve + ZIM files)."""

from __future__ import annotations

import atexit
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote

from .config import BIN, WIKI_DIR, WIKI_HOST, WIKI_PORT, WIKI_URL

_proc: subprocess.Popen | None = None
_arch_dir: str | None = None


def _platform_bin_dir() -> Path | None:
    import platform

    system = platform.system().lower()
    machine = platform.machine().lower()
    if system.startswith("win"):
        name = "win-arm64" if "arm" in machine else "win-x64"
    elif system == "darwin":
        name = "macos-arm64" if "arm" in machine or "aarch" in machine else "macos-x64"
    else:
        name = "ubuntu-x64"
    p = BIN / "kiwix" / name
    if p.is_dir():
        return p
    # Windows tools extracted flat into bin/kiwix
    flat = BIN / "kiwix"
    if (flat / "kiwix-serve.exe").is_file() or (flat / "kiwix-serve").is_file():
        return flat
    return None


def find_server() -> Path | None:
    bindir = _platform_bin_dir()
    if not bindir:
        w = shutil.which("kiwix-serve") or shutil.which("kiwix-serve.exe")
        return Path(w) if w else None
    for name in ("kiwix-serve.exe", "kiwix-serve"):
        p = bindir / name
        if p.is_file():
            return p
    return None


def _is_valid_zim(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            magic = f.read(4)
        # ZIM magic: 44 D8 CD 4D (older) or starts with "ZIM"
        return magic in (b"ZIM\x04", b"ZIM\x05", b"ZIM\x06") or magic[:3] == b"ZIM"
    except OSError:
        return False


def list_zims() -> list[dict]:
    if not WIKI_DIR.is_dir():
        return []
    out = []
    for p in sorted(WIKI_DIR.glob("*.zim")):
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if size < 1_000_000:
            continue
        # Prefer download-complete marker so half-written ZIMs never load
        marker = p.with_suffix(p.suffix + ".complete")
        if not marker.is_file():
            # still allow known-good small packs that predate markers
            if not _looks_finished(p, size):
                continue
        if not _is_valid_zim(p):
            continue
        out.append(
            {
                "name": p.name,
                "path": str(p),
                "mb": round(size / (1024 * 1024), 1),
                "label": _friendly_label(p.name),
            }
        )
    return out


def _looks_finished(path: Path, size: int) -> bool:
    """Heuristic for packs without a .complete sidecar yet."""
    n = path.name.lower()
    # never treat multi-GB WIP downloads as ready unless marked
    if size < 80_000_000 and ("nhs" in n or "100" in n):
        return size >= 15_000_000
    if "zimgit-medicine" in n and size >= 70_000_000:
        return True
    return False


def _friendly_label(name: str) -> str:
    n = name.lower()
    if "medicine" in n or "mdwiki" in n or "wikem" in n:
        return "WikiMed — Medical encyclopedia"
    if "simple" in n:
        return "Wikipedia (Simple English)"
    if "wp1" in n or "0.8" in n:
        return "Wikipedia 0.8 — Best articles"
    if "wikivet" in n or "vet" in n:
        return "WikiVet — Veterinary"
    if "geography" in n:
        return "Wikipedia — Geography"
    if "history" in n:
        return "Wikipedia — History"
    if "wikipedia" in n:
        return "Wikipedia"
    return p_stem(name)


def p_stem(name: str) -> str:
    return Path(name).stem.replace("_", " ")


def server_running() -> bool:
    try:
        with urllib.request.urlopen(f"{WIKI_URL}/", timeout=0.8) as resp:
            return 200 <= resp.status < 400
    except Exception:
        return False


def _cleanup() -> None:
    global _proc
    if _proc and _proc.poll() is None:
        try:
            _proc.terminate()
            _proc.wait(timeout=3)
        except Exception:
            try:
                _proc.kill()
            except Exception:
                pass
    _proc = None


atexit.register(_cleanup)


def status() -> dict:
    zims = list_zims()
    server = find_server()
    running = server_running()
    return {
        "ready": bool(server and zims),
        "running": running,
        "url": WIKI_URL if running else None,
        "books": zims,
        "count": len(zims),
        "server": str(server) if server else None,
    }


def start_server(timeout: float = 45.0) -> bool:
    """Start kiwix-serve on all ZIM files in wiki/."""
    global _proc

    if server_running():
        return True

    server = find_server()
    zims = list_zims()
    if not server or not zims:
        return False

    cmd = [
        str(server),
        "--port",
        str(WIKI_PORT),
        "--address",
        WIKI_HOST,
        "--library",
        str(_write_library_xml(zims)),
        "--nodatealiases",
        "--blockExternal",
    ]
    # older kiwix may not support --blockExternal / --library; fall back to explicit zim paths
    try:
        _proc = subprocess.Popen(
            cmd,
            cwd=str(server.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
    except OSError:
        cmd = [str(server), "--port", str(WIKI_PORT), "--address", WIKI_HOST] + [
            z["path"] for z in zims
        ]
        try:
            _proc = subprocess.Popen(
                cmd,
                cwd=str(server.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        except OSError as e:
            sys.stderr.write(f"[RIS] failed to start kiwix-serve: {e}\n")
            return False

    deadline = time.time() + timeout
    while time.time() < deadline:
        if server_running():
            return True
        if _proc and _proc.poll() is not None:
            # retry with simple zim-path form
            cmd = [str(server), "--port", str(WIKI_PORT)] + [z["path"] for z in zims]
            try:
                _proc = subprocess.Popen(
                    cmd,
                    cwd=str(server.parent),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                )
            except OSError:
                return False
            time.sleep(1.0)
            if server_running():
                return True
        time.sleep(0.4)
    return False


def ensure_ready(timeout: float = 45.0) -> bool:
    if server_running():
        return True
    if not (find_server() and list_zims()):
        return False
    return start_server(timeout=timeout)


def warmup_async() -> None:
    import threading

    def _run() -> None:
        try:
            ensure_ready(timeout=60.0)
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True, name="ris-wiki-warmup").start()


def search_url(query: str) -> str:
    q = (query or "").strip()
    if not q:
        return WIKI_URL
    # kiwix-serve search
    return f"{WIKI_URL}/search?pattern={quote(q)}"


def books_html() -> str:
    """Simple HTML index of available ZIM libraries."""
    zims = list_zims()
    if not zims:
        return "<p>No offline wiki packs found in <code>wiki/</code>.</p>"
    items = []
    for z in zims:
        items.append(
            f'<li><a href="{WIKI_URL}/" target="_blank" rel="noopener">'
            f"<strong>{z['label']}</strong> "
            f"<span class='muted'>({z['mb']} MB)</span></a></li>"
        )
    return "<ul class='book-list'>" + "".join(items) + "</ul>"


def _write_library_xml(zims: list[dict]) -> Path:
    """Minimal library.xml for kiwix-serve --library."""
    path = WIKI_DIR / "library.xml"
    books = []
    for i, z in enumerate(zims):
        books.append(
            f'  <book id="ris-{i}" path="{z["path"]}" title="{z["label"]}" '
            f'language="eng" xmlns="http://kiwix.org/library" />'
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<library xmlns="http://kiwix.org/library">\n'
        + "\n".join(books)
        + "\n</library>\n"
    )
    path.write_text(xml, encoding="utf-8")
    return path


if __name__ == "__main__":
    print(status())
    print("start", ensure_ready())
    print(status())
