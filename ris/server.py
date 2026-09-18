"""Local HTTP server for the RIS dashboard."""
from __future__ import annotations
import json, mimetypes, re, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from . import analysis, citations, wiki
from .ai import ResearchAssistant
from .config import HOST, PORT, STATIC, ensure_dirs
from .library import KnowledgeLibrary
from .rag import DocumentStore

ensure_dirs()
LIBRARY = KnowledgeLibrary()
DOCS = DocumentStore()
ASSISTANT = ResearchAssistant(LIBRARY, DOCS)
MAX_BODY = 50 * 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    server_version = "RIS/0.2"

    def log_message(self, fmt, *args):
        try:
            import sys
            sys.stderr.write(f"[RIS] {fmt % args}\n")
        except Exception:
            pass

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _text(self, text, status=200):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        raw = self.headers.get("Content-Length")
        n = int(raw) if raw else 0
        if n <= 0 or n > MAX_BODY:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def _serve_static(self, rel: str):
        rel = rel.lstrip("/") or "index.html"
        target = (STATIC / rel).resolve()
        if not str(target).startswith(str(STATIC.resolve())) or not target.is_file():
            target = STATIC / "index.html"
        if not target.is_file():
            self._text("Not found", 404)
            return
        ctype = mimetypes.guess_type(str(target))[0] or "text/html"
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text/") else ""))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path in ("/", "/index.html"):
                self._serve_static("index.html")
            elif path.startswith("/static/"):
                self._serve_static(path[len("/static/"):])
            elif path == "/api/status":
                st = ASSISTANT.status()
                st.update({"version": "0.2.0", "product": "Research-in-a-Stick", "wiki": wiki.status()})
                self._json(st)
            elif path == "/api/wiki":
                st = wiki.status()
                if st.get("ready") and not st.get("running"):
                    wiki.ensure_ready(timeout=20.0)
                    st = wiki.status()
                self._json(st)
            elif path == "/api/library":
                self._json({"docs": LIBRARY.list_docs(), "count": len(LIBRARY.docs)})
            elif path == "/api/documents":
                self._json({"docs": DOCS.list_docs(), "count": len(DOCS.docs)})
            elif path == "/api/samples":
                self._json({"csvs": analysis.list_sample_csvs()})
            else:
                self._text("Not found", 404)
        except Exception:
            traceback.print_exc()
            self._json({"error": "Internal server error"}, 500)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            data = self._read_json()
            if path == "/api/chat":
                self._json(ASSISTANT.chat(data.get("message", ""), model=data.get("model"), use_ollama=data.get("use_ollama")))
            elif path == "/api/search_library":
                q = data.get("query", "")
                self._json({"query": q, "results": LIBRARY.search(q, limit=8)})
            elif path == "/api/rag":
                q = data.get("query", "")
                self._json({"query": q, "results": DOCS.search(q, limit=6), **DOCS.answer(q)})
            elif path == "/api/cite":
                try:
                    cite = citations.format_citation(data.get("style", "apa"), data.get("source_type", "journal"), data.get("fields", {}))
                    self._json({"citation": cite, "style": data.get("style", "apa")})
                except Exception as e:
                    self._json({"error": str(e)}, 400)
            elif path == "/api/analyze_csv":
                name = data.get("sample") or data.get("name")
                if not name:
                    self._json({"error": "Provide sample filename"}, 400)
                    return
                sp = Path(__import__("ris.config", fromlist=["SAMPLES"]).SAMPLES) / Path(name).name
                if not sp.is_file():
                    self._json({"error": f"Sample not found: {name}"}, 404)
                    return
                self._json(analysis.analyze_csv_path(sp))
            elif path == "/api/upload":
                n = int(self.headers.get("Content-Length") or 0)
                if n <= 0 or n > 50 * 1024 * 1024:
                    self._json({"error": "Empty or too large"}, 400)
                    return
                raw = self.rfile.read(n)
                ctype = self.headers.get("Content-Type") or ""
                filename = "upload.txt"
                if "multipart/form-data" in ctype:
                    m = re.search(r"boundary=(.+)", ctype)
                    if m:
                        boundary = m.group(1).strip().encode("ascii", "ignore")
                        for part in raw.split(b"--" + boundary):
                            if b"Content-Disposition" not in part:
                                continue
                            header_blob, _, content = part.partition(b"\r\n\r\n")
                            if content.endswith(b"\r\n"):
                                content = content[:-2]
                            fm = re.search(r'filename="([^"]+)"', header_blob.decode("utf-8", "ignore"))
                            if fm and content:
                                filename, raw = fm.group(1), content
                                break
                meta = DOCS.add_file(filename, raw)
                self._json({"uploaded": True, "doc": meta, "count": len(DOCS.docs)})
            elif path == "/api/wiki_start":
                ok = wiki.ensure_ready(timeout=30.0)
                self._json({"started": ok, **wiki.status()})
            elif path == "/api/reload":
                self._json({"library_docs": LIBRARY.reload(), "uploaded_docs": DOCS.reload()})
            else:
                self._text("Not found", 404)
        except Exception:
            traceback.print_exc()
            self._json({"error": "Internal server error"}, 500)


def serve(host=HOST, port=PORT):
    httpd = ThreadingHTTPServer((host, port), Handler)
    # Load local model + wiki immediately so first chat works
    try:
        from . import local_llm
        local_llm.warmup_async()
        local_llm.start_watchdog()
    except Exception as e:
        print(f"[RIS] model warmup: {e}")
    try:
        if hasattr(wiki, "warmup_async"):
            wiki.warmup_async()
        else:
            import threading
            threading.Thread(target=lambda: wiki.ensure_ready(60.0), daemon=True).start()
    except Exception:
        pass
    st = ASSISTANT.status()
    print("=" * 52)
    print("  RESEARCH-IN-A-STICK · offline research workstation")
    print(f"  Dashboard:  http://{host}:{port}")
    print(f"  Library:    {len(LIBRARY.docs)} notes · skills: {', '.join(st.get('skills') or [])}")
    print(f"  AI mode:    {st.get('mode')} · model: {st.get('local_model_name') or 'none'}")
    print(f"  Wiki packs: {wiki.status().get('count', 0)}")
    print("  Model loads in background (~15-40s). Watchdog keeps it alive.")
    print("  Stop with Ctrl+C")
    print("=" * 52)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[RIS] Shutting down.")
    finally:
        httpd.server_close()
