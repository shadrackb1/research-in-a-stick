"""End-to-end smoke test for local RIS."""
import json
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ris.config import HOST, PORT, ensure_dirs
from ris import server as ris_server


def req(method: str, path: str, data: dict | None = None):
    body = None
    headers = {}
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(f"http://{HOST}:{PORT}{path}", data=body, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=15) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    ensure_dirs()
    httpd = ris_server.ThreadingHTTPServer((HOST, PORT), ris_server.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.3)
    checks: list[bool] = []

    def check(name: str, cond: bool, detail: str = ""):
        checks.append(cond)
        print(("PASS" if cond else "FAIL"), "-", name, detail)

    try:
        st = req("GET", "/api/status")
        check("status", st.get("product") == "Research-in-a-Stick", f"mode={st.get('mode')} skills={len(st.get('skills') or [])}")
        lib = req("GET", "/api/library")
        check("library", lib.get("count", 0) >= 5, str(lib.get("count")))
        chat = req("POST", "/api/chat", {"message": "What are common malaria symptoms?"})
        check("chat", "fever" in chat.get("reply", "").lower() or "malaria" in chat.get("reply", "").lower(), chat.get("mode"))
        cite = req("POST", "/api/cite", {"style": "apa", "source_type": "journal",
                                         "fields": {"authors": ["Mwangi, Alice"], "title": "T", "year": "2026", "journal": "J"}})
        check("cite", "Mwangi" in cite.get("citation", ""), cite.get("citation", "")[:60])
        ana = req("POST", "/api/analyze_csv", {"sample": "student_survey.csv"})
        check("csv", ana.get("rows") == 25, str(ana.get("rows")))
        wiki = req("GET", "/api/wiki")
        check("wiki_api", "count" in wiki, str(wiki.get("count")))
    finally:
        httpd.shutdown()
        httpd.server_close()
    print("-" * 40)
    print(f"{sum(checks)}/{len(checks)} checks passed")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
