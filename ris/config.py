from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LIBRARY = DATA / "library"
SAMPLES = DATA / "samples"
UPLOADS = DATA / "uploads"
STATIC = Path(__file__).resolve().parent / "static"
MODELS = ROOT / "models"
BIN = ROOT / "bin"
WIKI_DIR = ROOT / "wiki"
PORTABLE_PY = ROOT / "portable-python"

HOST = "127.0.0.1"
PORT = 8765
OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5:3b"

LOCAL_LLM_HOST = "127.0.0.1"
LOCAL_LLM_PORT = 8766
LOCAL_LLM_URL = f"http://{LOCAL_LLM_HOST}:{LOCAL_LLM_PORT}"
LOCAL_MODEL_NAME = "RIS"

WIKI_HOST = "127.0.0.1"
WIKI_PORT = 8767
WIKI_URL = f"http://{WIKI_HOST}:{WIKI_PORT}"


def ensure_dirs() -> None:
    for p in (DATA, LIBRARY, SAMPLES, UPLOADS, MODELS, BIN, WIKI_DIR):
        p.mkdir(parents=True, exist_ok=True)
