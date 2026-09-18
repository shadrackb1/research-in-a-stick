"""Local offline power tools: math, Python code, and file organization.

Runs entirely on-device. Code executes in a short-lived local Python
subprocess (no network required). Intended for the stick owner's own work.
"""

from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .config import ROOT, UPLOADS

# Workspace the user can safely browse/organize
WORKSPACE = ROOT / "workspace"
WORKSPACE.mkdir(parents=True, exist_ok=True)

_PY = sys.executable
_TIMEOUT = 12


def _safe_expr(expr: str) -> bool:
    """Allow only arithmetic / math-ish expressions for the quick calculator."""
    expr = expr.strip().rstrip("=")
    if not expr or len(expr) > 200:
        return False
    # reject obvious dangerous calls
    lowered = expr.lower()
    for bad in ("__", "import", "exec", "eval", "open", "os.", "sys.", "subprocess"):
        if bad in lowered:
            return False
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Attribute, ast.Call)):
            # allow a tiny set of math functions via names only (pow, abs, round)
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name) or node.func.id not in {
                    "abs", "round", "min", "max", "sum", "pow", "int", "float",
                    "len", "sorted",
                }:
                    return False
            elif isinstance(node, ast.Attribute):
                return False
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                return False
        if isinstance(node, (ast.Lambda, ast.Dict, ast.Set, ast.ListComp)):
            return False
    return True


def calculate(expr: str) -> dict:
    """Offline calculator. Example: 2**10 + sqrt is not allowed; use run_python for math module."""
    expr = (expr or "").strip()
    if not expr:
        return {"error": "Empty expression"}
    # convenience: allow ^ as power
    py_expr = expr.replace("^", "**")
    if not _safe_expr(py_expr):
        # fall through to python code if it looks richer
        return run_python(f"print({py_expr})" if _safe_expr(py_expr) else f"result = {py_expr}\nprint(result)")
    try:
        value = eval(compile(py_expr, "<calc>", "eval"), {"__builtins__": {}}, {})  # noqa: S307
        return {"expression": expr, "result": value}
    except Exception as e:
        return {"error": str(e)}


def run_python(code: str, timeout: int = _TIMEOUT) -> dict:
    """Run a short Python snippet locally. Returns stdout/stderr/exit code."""
    code = (code or "").strip()
    if not code:
        return {"error": "Empty code"}
    if len(code) > 20000:
        return {"error": "Code too long (max 20k chars)"}
    # strip accidental markdown fences
    if code.startswith("```"):
        code = re.sub(r"^```[a-zA-Z]*\n?", "", code)
        code = re.sub(r"\n?```$", "", code)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        proc = subprocess.run(
            [_PY, "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(WORKSPACE),
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"Timed out after {timeout}s"}
    except OSError as e:
        return {"error": f"Could not start Python: {e}"}
    out = (proc.stdout or "")[:8000]
    err = (proc.stderr or "")[:4000]
    return {"stdout": out, "stderr": err, "exit_code": proc.returncode}


def list_files(path: str = ".") -> dict:
    """List files under workspace (or uploads). Relative paths only."""
    rel = (path or ".").strip().lstrip("/\\")
    if rel in (".", "", "workspace"):
        base = WORKSPACE
    elif rel in ("uploads", "data/uploads"):
        base = UPLOADS
    else:
        base = (WORKSPACE / rel).resolve()
        if not str(base).startswith(str(WORKSPACE.resolve())) and not str(base).startswith(str(UPLOADS.resolve())):
            return {"error": "Path outside allowed folders"}
    if not base.exists():
        return {"error": f"Not found: {rel}", "workspace": str(WORKSPACE)}
    items = []
    try:
        for p in sorted(base.iterdir())[:200]:
            items.append(
                {
                    "name": p.name,
                    "type": "dir" if p.is_dir() else "file",
                    "size": p.stat().st_size if p.is_file() else None,
                }
            )
    except OSError as e:
        return {"error": str(e)}
    return {"path": str(base), "count": len(items), "items": items}


def organize_files(
    source: str = ".",
    mode: str = "by_extension",
    dry_run: bool = True,
) -> dict:
    """Organize files in workspace/uploads into subfolders.

    mode:
      by_extension  → documents/pdf, images/jpg, ...
      by_type       → documents, images, archives, code, other
    """
    rel = (source or ".").strip().lstrip("/\\")
    if rel in (".", "", "workspace"):
        base = WORKSPACE
    elif rel in ("uploads", "data/uploads"):
        base = UPLOADS
    else:
        return {"error": "source must be workspace or uploads"}
    if not base.exists():
        return {"error": f"Missing {base}"}

    ext_map = {
        ".pdf": "documents",
        ".docx": "documents",
        ".doc": "documents",
        ".txt": "documents",
        ".md": "documents",
        ".csv": "data",
        ".json": "data",
        ".xlsx": "data",
        ".png": "images",
        ".jpg": "images",
        ".jpeg": "images",
        ".gif": "images",
        ".webp": "images",
        ".zip": "archives",
        ".gz": "archives",
        ".7z": "archives",
        ".py": "code",
        ".js": "code",
        ".html": "code",
        ".css": "code",
    }

    moves: list[dict] = []
    for p in list(base.iterdir()):
        if not p.is_file():
            continue
        if p.name.startswith("."):
            continue
        ext = p.suffix.lower()
        if mode == "by_extension":
            folder = (ext.lstrip(".") or "no_ext").lower()
            folder = f"by_ext/{folder}"
        else:
            folder = ext_map.get(ext, "other")
        dest_dir = base / folder
        dest = dest_dir / p.name
        # avoid clobber
        if dest.exists():
            stem, suffix = dest.stem, dest.suffix
            i = 1
            while dest.exists():
                dest = dest_dir / f"{stem}_{i}{suffix}"
                i += 1
        moves.append({"from": str(p), "to": str(dest), "name": p.name})
        if not dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(dest))

    return {
        "source": str(base),
        "mode": mode,
        "dry_run": dry_run,
        "planned": len(moves),
        "moves": moves[:50],
        "note": "dry_run=true means preview only. Call again with dry_run=false to apply.",
    }


def write_text_file(path: str, content: str, overwrite: bool = False) -> dict:
    """Create a text file under workspace/ for notes, code, reports."""
    rel = (path or "").strip().lstrip("/\\")
    if not rel:
        return {"error": "path required"}
    target = (WORKSPACE / rel).resolve()
    if not str(target).startswith(str(WORKSPACE.resolve())):
        return {"error": "Path must stay inside workspace/"}
    if target.exists() and not overwrite:
        return {"error": "File exists (set overwrite=true)", "path": str(target)}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content or "", encoding="utf-8")
    return {"path": str(target), "bytes": target.stat().st_size}
