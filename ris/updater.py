"""Optional online content update for RIS (library packs only).

Pulls a content manifest from GitHub and downloads matching library files.
Does NOT replace application code or model weights unless explicitly listed.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from .config import LIBRARY, ROOT

# Public content feed (repo where the 24/7 collector commits)
FEED_RAW = "https://raw.githubusercontent.com/shadrackb1/research-in-a-stick/main"
MANIFEST_URL = f"{FEED_RAW}/wiki/manifest.json"
UA = "RIS-Updater/1.0"

_log: list[str] = []


def _log_add(msg: str) -> None:
    _log.append(f"{time.strftime('%H:%M:%S')} {msg}")


def status() -> dict:
    return {
        "feed": FEED_RAW,
        "manifest_url": MANIFEST_URL,
        "last_log": _log[-8:],
    }


def check_remote() -> dict:
    """Fetch manifest only (tiny)."""
    req = urllib.request.Request(MANIFEST_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return {"ok": True, "manifest": data}


def download_file(rel: str, dest: Path) -> bool:
    url = f"{FEED_RAW}/{rel.replace(chr(92), '/')}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            tmp.write_bytes(resp.read())
        tmp.replace(dest)
        _log_add(f"updated {rel}")
        return True
    except Exception as e:
        _log_add(f"fail {rel}: {e}")
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        return False


def apply_update(max_files: int = 40) -> dict:
    """Optional user-triggered update of knowledge packs from the feed."""
    _log.clear()
    try:
        remote = check_remote()
    except Exception as e:
        _log_add(f"manifest error: {e}")
        return {"ok": False, "error": str(e), "updated": 0, "log": _log[:]}
    man = remote.get("manifest") or {}
    _log_add(f"manifest ok updated={man.get('updated')}")

    # Local file list from feed via common library paths we maintain in TOPICS
    # Conservative: only overwrite known library .md paths listed in a simple index if present,
    # else try GET for every .md we already have + known topic names.
    candidates: list[str] = []
    index_url = f"{FEED_RAW}/data/library/index.json"
    try:
        req = urllib.request.Request(index_url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            idx = json.loads(resp.read().decode("utf-8"))
        candidates = [str(x).replace("\\", "/") for x in idx.get("files", [])]
    except Exception:
        # fallback: whatever we already have locally
        if LIBRARY.exists():
            for p in LIBRARY.rglob("*.md"):
                candidates.append(str(p.relative_to(ROOT)).replace("\\", "/"))

    updated = 0
    for rel in candidates[:max_files]:
        if not rel.startswith("data/library/") or not rel.endswith(".md"):
            continue
        dest = ROOT / rel
        if download_file(rel, dest):
            updated += 1

    _log_add(f"update done files={updated}")
    return {"ok": True, "updated": updated, "manifest": man, "log": _log[:]}
