"""Portable offline LLM via bundled llama.cpp + GGUF.

Guarantees the model can load on any Windows PC from this folder layout:
  models/*.gguf
  bin/win-x64/llama-server.exe  (+ DLLs)

Starts automatically, retries on failure, and keeps a watchdog thread alive.
"""

from __future__ import annotations

import atexit
import json
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from .config import BIN, LOCAL_MODEL_NAME, LOCAL_LLM_PORT, LOCAL_LLM_URL, MODELS, ROOT

_system = platform.system().lower()
_machine = platform.machine().lower()
if _system.startswith("win"):
    _ARCH_DIR = "win-arm64" if "arm" in _machine else "win-x64"
elif _system == "darwin":
    _ARCH_DIR = "macos-arm64" if "arm" in _machine or "aarch" in _machine else "macos-x64"
else:
    _ARCH_DIR = "ubuntu-x64"

_BIN_ROOT = BIN / _ARCH_DIR
_LOG = ROOT / "data" / "llama-server.log"
_proc: subprocess.Popen | None = None
_lock = threading.Lock()
_watchdog_started = False
_last_error: str | None = None


def _env() -> dict:
    env = os.environ.copy()
    # DLLs next to llama-server must be on PATH (Windows)
    paths = []
    if _BIN_ROOT.is_dir():
        paths.append(str(_BIN_ROOT))
    server = find_server()
    if server:
        paths.append(str(server.parent))
    if paths:
        env["PATH"] = os.pathsep.join(paths) + os.pathsep + env.get("PATH", "")
    return env


def find_exe(names: tuple[str, ...]) -> Path | None:
    # 1) stick-relative bin
    if _BIN_ROOT.is_dir():
        for name in names:
            p = _BIN_ROOT / name
            if p.is_file() and p.stat().st_size > 1000:
                return p
    # 2) any bin/* layout
    if BIN.is_dir():
        for p in BIN.rglob(names[0]):
            if p.is_file() and p.stat().st_size > 1000:
                return p
    # 3) PATH
    for name in names:
        w = shutil.which(name)
        if w:
            return Path(w)
    return None


def find_server() -> Path | None:
    return find_exe(("llama-server.exe", "llama-server"))


def find_model() -> Path | None:
    candidates: list[Path] = []
    if MODELS.is_dir():
        candidates.extend(MODELS.glob("*.gguf"))
    # also allow models next to the app root
    root_models = ROOT / "models"
    if root_models.is_dir() and root_models != MODELS:
        candidates.extend(root_models.glob("*.gguf"))
    best: Path | None = None
    best_size = 0
    for p in candidates:
        try:
            sz = p.stat().st_size
        except OSError:
            continue
        # ignore incomplete downloads under 40MB
        if sz < 40_000_000:
            continue
        # prefer known names
        score = sz
        if "qwen" in p.name.lower() and "0.5b" in p.name.lower():
            score += 10_000_000_000
        if score > best_size:
            best, best_size = p, score
    return best


def server_running() -> bool:
    try:
        with urllib.request.urlopen(f"{LOCAL_LLM_URL}/health", timeout=1.0) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def _log(msg: str) -> None:
    try:
        _LOG.parent.mkdir(parents=True, exist_ok=True)
        with _LOG.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except Exception:
        pass


def _kill_port_listeners(port: int) -> None:
    """Best-effort kill of leftover llama-server on our port (Windows)."""
    if not _system.startswith("win"):
        return
    try:
        out = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            capture_output=True,
            text=True,
            timeout=8,
        ).stdout
    except Exception:
        return
    pids = set()
    needle = f":{port}"
    for line in out.splitlines():
        if needle in line and "LISTENING" in line.upper():
            parts = line.split()
            if parts:
                try:
                    pids.add(int(parts[-1]))
                except ValueError:
                    pass
    for pid in pids:
        if pid == os.getpid():
            continue
        try:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=5)
            _log(f"killed pid {pid} on port {port}")
        except Exception:
            pass


def _cleanup() -> None:
    global _proc
    with _lock:
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


def _spawn() -> subprocess.Popen | None:
    global _proc
    server = find_server()
    model = find_model()
    if not server or not model:
        _log(f"missing server={server} model={model}")
        return None
    cwd = str(server.parent)
    cmd = [
        str(server),
        "-m",
        str(model),
        "--host",
        "127.0.0.1",
        "--port",
        str(LOCAL_LLM_PORT),
        "-c",
        "2048",
        "-t",
        str(max(1, min(4, os.cpu_count() or 2))),
        "--alias",
        LOCAL_MODEL_NAME,
        "--log-disable",
    ]
    try:
        _LOG.parent.mkdir(parents=True, exist_ok=True)
        logf = _LOG.open("ab")
        _proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=_env(),
            stdout=logf,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
        )
        _log(f"spawned pid={_proc.pid} cmd={' '.join(cmd[:6])}…")
        return _proc
    except OSError as e:
        global _last_error
        _last_error = str(e)
        _log(f"spawn failed: {e}")
        return None


def start_server(timeout: float = 120.0) -> bool:
    global _proc, _last_error
    with _lock:
        if server_running():
            return True
        server, model = find_server(), find_model()
        if not server or not model:
            _last_error = "llama-server or GGUF model not found on this stick"
            return False

        # leftover process on the port → free it
        _kill_port_listeners(LOCAL_LLM_PORT)
        time.sleep(0.3)
        if _proc and _proc.poll() is None:
            try:
                _proc.kill()
            except Exception:
                pass
        _proc = None

        # up to 3 spawn attempts
        for attempt in range(3):
            if server_running():
                return True
            if _spawn() is None:
                time.sleep(0.5)
                continue
            deadline = time.time() + timeout
            while time.time() < deadline:
                if server_running():
                    _log("health OK")
                    return True
                if _proc and _proc.poll() is not None:
                    code = _proc.returncode
                    _log(f"exited early code={code} attempt={attempt}")
                    _proc = None
                    break
                time.sleep(0.35)
        _last_error = "model did not become healthy in time (see data/llama-server.log)"
        return False


def ensure_ready(timeout: float = 120.0) -> bool:
    start_watchdog()
    if server_running():
        return True
    if not (find_server() and find_model()):
        return False
    return start_server(timeout=timeout)


def start_watchdog() -> None:
    """Keep llama-server alive for the whole session."""
    global _watchdog_started
    if _watchdog_started:
        return
    _watchdog_started = True

    def loop() -> None:
        while True:
            time.sleep(8)
            try:
                if not (find_server() and find_model()):
                    continue
                if not server_running():
                    _log("watchdog: restarting")
                    start_server(timeout=90.0)
            except Exception as e:
                _log(f"watchdog error: {e}")

    threading.Thread(target=loop, daemon=True, name="ris-llm-watchdog").start()


def warmup_async() -> None:
    """Fire-and-forget load so the dashboard can open immediately."""

    def _run() -> None:
        try:
            ensure_ready(timeout=180.0)
        except Exception as e:
            _log(f"warmup error: {e}")

    threading.Thread(target=_run, daemon=True, name="ris-llm-warmup").start()


def status() -> dict:
    server, model = find_server(), find_model()
    running = server_running()
    return {
        "ready": bool(server and model),
        "running": running,
        "model_name": LOCAL_MODEL_NAME if model else None,
        "model_file": model.name if model else None,
        "model_mb": round(model.stat().st_size / 1024 / 1024, 1) if model else None,
        "bin_path": str(server) if server else None,
        "platform": f"{platform.system()} {platform.machine()}",
        "url": LOCAL_LLM_URL if running else None,
        "alias": LOCAL_MODEL_NAME,
        "log": str(_LOG) if _LOG.exists() else None,
        "last_error": _last_error,
    }


def chat(
    messages: list[dict[str, str]],
    max_tokens: int = 320,
    temperature: float = 0.4,
    timeout: float = 90.0,
) -> str:
    if not ensure_ready(timeout=timeout):
        raise RuntimeError(_last_error or "Bundled local model is not available")
    payload = {
        "model": LOCAL_MODEL_NAME,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    req = urllib.request.Request(
        f"{LOCAL_LLM_URL}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        # one retry after a forced restart
        _log(f"chat failed: {e}; restarting once")
        _cleanup()
        if not ensure_ready(timeout=timeout):
            raise
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Local model returned no choices")
    return ((choices[0].get("message") or {}).get("content") or "").strip()
