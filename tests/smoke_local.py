import sys, json, threading, time, urllib.request
sys.path.insert(0, r"C:\ris-stick")
from ris import server as ris_server
from ris.config import HOST, PORT, ensure_dirs
ensure_dirs()
httpd = ris_server.ThreadingHTTPServer((HOST, PORT), ris_server.Handler)
t = threading.Thread(target=httpd.serve_forever, daemon=True); t.start(); time.sleep(0.3)
def req(method, path, data=None):
    body = None; headers = {}
    if data is not None:
        body = json.dumps(data).encode(); headers["Content-Type"]="application/json"
    r = urllib.request.Request(f"http://{HOST}:{PORT}{path}", data=body, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=10) as resp:
        return json.loads(resp.read().decode())
checks=[]
def check(n,c,d=""):
    checks.append(c); print(("PASS" if c else "FAIL"), n, d)
st=req("GET","/api/status"); check("status", st.get("product")=="Research-in-a-Stick", f"mode={st.get('mode')} skills={st.get('skills')}")
lib=req("GET","/api/library"); check("library", lib.get("count",0)>=5, str(lib.get("count")))
chat=req("POST","/api/chat",{"message":"What are common malaria symptoms?"}); check("chat", "malaria" in chat.get("reply","").lower() or "fever" in chat.get("reply","").lower(), chat.get("mode"))
cite=req("POST","/api/cite",{"style":"apa","source_type":"journal","fields":{"authors":["Mwangi, Alice"],"title":"T","year":"2026","journal":"J"}}); check("cite","Mwangi" in cite.get("citation",""), cite.get("citation","")[:50])
ana=req("POST","/api/analyze_csv",{"sample":"student_survey.csv"}); check("csv", ana.get("rows")==25, str(ana.get("rows")))
print(f"{sum(checks)}/{len(checks)} passed")
httpd.shutdown(); httpd.server_close()
sys.exit(0 if all(checks) else 1)
