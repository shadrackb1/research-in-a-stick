#!/usr/bin/env python3
"""RIS content collector — runs continuously, refreshes offline packs from the web.

Collects public, current knowledge (Wikipedia REST/Action API) into
data/library/*.md and optionally lists new wiki ZIM URLs, then can commit
to a git repo (online source of truth for the RIS Update button).

Usage:
  python tools/content_collector.py --once
  python tools/content_collector.py --loop
  python tools/content_collector.py --loop --interval 3600 --commit

Safety:
  - Public read-only APIs only
  - Does not touch models/ or application code
  - Writes only under data/library/ and wiki/manifest.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "data" / "library"
MANIFEST = ROOT / "wiki" / "manifest.json"
STAMP = ROOT / "data" / "collector_status.json"

UA = "RIS-ContentCollector/1.0 (offline education packs; contact via repo)"
TOPICS = [
    # (category, page title on Wikipedia)
    ("health", "Malaria"),
    ("health", "Cholera"),
    ("health", "Oral rehydration therapy"),
    ("agriculture", "Maize"),
    ("agriculture", "Smallholding"),
    ("agriculture", "Fall armyworm"),
    ("curriculum", "Scientific method"),
    ("curriculum", "Photosynthesis"),
    ("policy", "Digital divide"),
    ("policy", "Kenya"),
]

WIKI_API = "https://en.wikipedia.org/w/api.php"


def http_get_json(url: str, timeout: float = 20.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_wikipedia_extract(title: str) -> str | None:
    """Plain-text intro + sections via Action API."""
    params = urllib.parse.urlencode(
        {
            "action": "query",
            "prop": "extracts",
            "explaintext": 1,
            "exsectionformat": "plain",
            "redirects": 1,
            "format": "json",
            "titles": title,
        }
    )
    data = http_get_json(f"{WIKI_API}?{params}")
    pages = (data.get("query") or {}).get("pages") or {}
    for page in pages.values():
        extract = page.get("extract")
        if extract:
            return extract
    return None


def slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")


def write_note(category: str, title: str, body: str) -> Path:
    folder = LIBRARY / category
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{slug(title)}.md"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    text = (
        f"# {title}\n\n"
        f"_Updated {stamp} · source: Wikipedia (CC BY-SA) · distilled for offline use_\n\n"
        f"{body.strip()}\n"
    )
    # keep size reasonable for students
    if len(text) > 12000:
        text = text[:12000] + "\n\n_(truncated for offline pack)_\n"
    path.write_text(text, encoding="utf-8")
    return path


def refresh_library() -> list[Path]:
    written = []
    for category, title in TOPICS:
        try:
            extract = fetch_wikipedia_extract(title)
        except Exception as e:
            print(f"[collector] skip {title}: {e}")
            continue
        if not extract or len(extract) < 200:
            print(f"[collector] skip {title}: short/empty extract")
            continue
        p = write_note(category, title, extract)
        written.append(p)
        print(f"[collector] wrote {p.relative_to(ROOT)} ({p.stat().st_size} bytes)")
        time.sleep(0.8)  # be polite to the API
    return written


def write_manifest() -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    zims = []
    if (ROOT / "wiki").exists():
        for p in sorted((ROOT / "wiki").glob("*.zim")):
            zims.append({"name": p.name, "bytes": p.stat().st_size})
    files = []
    if LIBRARY.exists():
        for p in sorted(LIBRARY.rglob("*.md")):
            files.append(str(p.relative_to(ROOT)).replace("\\", "/"))
    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "library_files": len(files),
        "files": files,
        "zim_packs": zims,
        "note": "Optional Update in RIS pulls data/library packs. Models are large/optional.",
    }
    MANIFEST.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    # feed index for the Update button
    idx = {"files": files, "updated": payload["updated"]}
    (LIBRARY / "index.json").write_text(json.dumps(idx, indent=2), encoding="utf-8")


def git_commit_push() -> bool:
    """Commit data/library + wiki/manifest if this folder is a git remote repo."""
    import subprocess

    def run(args):
        return subprocess.run(
            args,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )

    try:
        run(["git", "add", "data/library", "wiki/manifest.json"])
        status = run(["git", "status", "--porcelain", "data/library", "wiki/manifest.json"])
        if not status.stdout.strip():
            print("[collector] no library changes to commit")
            return True
        run(
            [
                "git",
                "-c",
                "user.name=ris-content-collector",
                "-c",
                "user.email=ris-content-collector@users.noreply.github.com",
                "commit",
                "-m",
                f"content: refresh offline packs {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%MZ')}",
            ]
        )
        push = run(["git", "push"])
        if push.returncode != 0:
            print("[collector] push failed:", push.stderr[-300:])
            return False
        print("[collector] pushed to git remote")
        return True
    except Exception as e:
        print(f"[collector] git error: {e}")
        return False


def write_status(ok: bool, files: int) -> None:
    STAMP.parent.mkdir(parents=True, exist_ok=True)
    STAMP.write_text(
        json.dumps(
            {
                "ok": ok,
                "files_written": files,
                "time": datetime.now(timezone.utc).isoformat(),
                "topics": [f"{c}/{t}" for c, t in TOPICS],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def run_once(commit: bool = False) -> int:
    print(f"[collector] start {datetime.now(timezone.utc).isoformat()}")
    try:
        written = refresh_library()
        write_manifest()
        ok = True
        files = len(written)
        if commit:
            ok = git_commit_push()
        write_status(ok, files)
        print(f"[collector] done files={files} commit={commit}")
        return 0 if ok else 2
    except Exception as e:
        write_status(False, 0)
        print(f"[collector] failed: {e}", file=sys.stderr)
        return 1


def loop(interval: int, commit: bool) -> None:
    print(f"[collector] loop every {interval}s commit={commit}")
    while True:
        try:
            run_once(commit=commit)
        except Exception as e:
            print(f"[collector] loop error: {e}", file=sys.stderr)
        time.sleep(max(60, interval))


def main() -> int:
    ap = argparse.ArgumentParser(description="RIS online content collector")
    ap.add_argument("--loop", action="store_true", help="run forever")
    ap.add_argument("--once", action="store_true", help="single run then exit")
    ap.add_argument("--interval", type=int, default=6 * 3600, help="seconds between refreshes")
    ap.add_argument("--commit", action="store_true", help="git commit+push data/library")
    args = ap.parse_args()
    if args.loop:
        loop(args.interval, args.commit)
        return 0
    return run_once(commit=args.commit)


if __name__ == "__main__":
    raise SystemExit(main())
