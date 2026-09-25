/* RIS chat UI — Ollama-style */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

const state = { busy: false, view: "chat", warmed: false };

async function api(path, options = {}) {
  const res = await fetch(path, options);
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch { data = { error: text || `HTTP ${res.status}` }; }
  if (!res.ok) throw new Error(typeof data.error === "string" ? data.error : `HTTP ${res.status}`);
  return data;
}

function setModeLabel(mode, modelName) {
  const labels = {
    local: modelName || "Local model",
    loading: "Loading model…",
    ollama: "Ollama",
    offline: "Offline skills",
    "offline-fallback": "Offline skills",
  };
  const t = labels[mode] || mode || "…";
  $("#sideMode").textContent = t;
  $("#statModel").textContent = modelName || (mode === "local" || mode === "loading" ? "bundled" : mode || "—");
  if (mode === "local") state.warmed = true;
}

async function refreshStatus() {
  try {
    const st = await api("/api/status");
    setModeLabel(st.mode, st.local_model_name);
    $("#statLib").textContent = st.library_docs ?? "—";
    $("#statWiki").textContent = st.wiki?.count ?? "—";
  } catch {
    $("#sideMode").textContent = "error";
  }
}

/* Views */
function showView(name) {
  state.view = name;
  $$(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${name}`));
  if (name === "library") loadLibrary();
  if (name === "rag") loadDocs();
  if (name === "wiki") loadWiki();
  if (name === "browser") initBrowser();
  if (name === "update") loadUpdateStatus();
}

$$(".nav-item").forEach((btn) => btn.addEventListener("click", () => showView(btn.dataset.view)));
$("#sidebarToggle").addEventListener("click", () => $("#sidebar").classList.toggle("collapsed"));

/* Chat */
function welcomeHTML() {
  return `
  <div class="welcome" id="welcomeBlock">
    <h1>What can I help with?</h1>
    <p>Chat freely. I pull offline library / wiki / citations only when useful.</p>
    <div class="chips">
      <button type="button" class="chip" data-q="What are common malaria symptoms?">Malaria symptoms</button>
      <button type="button" class="chip" data-q="Tips for a stuck assignment">Study tips</button>
      <button type="button" class="chip" data-q="Format an APA citation for a journal article">APA citation</button>
      <button type="button" class="chip" data-q="Summarize maize smallholder advice">Maize notes</button>
    </div>
  </div>`;
}

function ensureWelcome() {
  const log = $("#chatLog");
  if (!log.querySelector(".msg") && !$("#welcomeBlock")) {
    log.innerHTML = welcomeHTML();
    $$("#welcomeBlock .chip").forEach((c) =>
      c.addEventListener("click", () => {
        $("#chatInput").value = c.dataset.q;
        $("#chatInput").focus();
        autoGrow();
      })
    );
  }
}

function clearWelcome() {
  const w = $("#welcomeBlock");
  if (w) w.remove();
}

function addMsg(role, text, tools) {
  clearWelcome();
  const log = $("#chatLog");
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  const who = role === "user" ? "You" : "RIS";
  div.innerHTML = `<div class="who">${who}</div><div class="bubble"></div>`;
  const bubble = div.querySelector(".bubble");
  // light markdown: **bold**, `code`, line breaks already pre-wrap
  bubble.innerHTML = renderMarkdown(text);
  if (tools && tools.length) {
    const t = document.createElement("div");
    t.className = "tools";
    t.textContent = `tools: ${tools.join(", ")}`;
    div.appendChild(t);
  }
  log.appendChild(div);
  scrollChat();
  return div;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function renderMarkdown(text) {
  let s = escapeHtml(text);
  // fenced code
  s = s.replace(/```([a-zA-Z]*)\n([\s\S]*?)```/g, (_, _lang, code) => {
    return `<pre class="code-block"><code>${code.replace(/\n$/, "")}</code></pre>`;
  });
  // inline code / bold
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
  s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  return s;
}

function addTyping(hint) {
  clearWelcome();
  const log = $("#chatLog");
  const div = document.createElement("div");
  div.className = "msg bot";
  div.id = "typingMsg";
  const label = hint || "Thinking…";
  div.innerHTML = `<div class="who">RIS</div><div class="typing"><i></i><i></i><i></i></div><div class="who" style="margin-top:4px;text-transform:none;letter-spacing:0">${escapeHtml(label)}</div>`;
  log.appendChild(div);
  scrollChat();
}

function removeTyping() {
  $("#typingMsg")?.remove();
}

function scrollChat() {
  const el = $("#chatScroll");
  el.scrollTop = el.scrollHeight;
}

function autoGrow() {
  const ta = $("#chatInput");
  ta.style.height = "auto";
  ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
}

$("#chatInput").addEventListener("input", autoGrow);
$("#chatInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    $("#chatForm").requestSubmit();
  }
});

$("#newChat").addEventListener("click", () => {
  $("#chatLog").innerHTML = welcomeHTML();
  ensureWelcome();
  showView("chat");
  $("#chatInput").focus();
});

$("#chatForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (state.busy) return;
  const input = $("#chatInput");
  const msg = input.value.trim();
  if (!msg) return;
  addMsg("user", msg);
  input.value = "";
  autoGrow();
  state.busy = true;
  $("#chatSend").disabled = true;
  addTyping(state.warmed ? "Thinking…" : "Loading local model — first reply can take ~30s…");
  try {
    const data = await api("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg }),
    });
    removeTyping();
    addMsg("bot", data.reply || "…", data.skills || []);
    if (data.mode === "local" || data.mode === "ollama") state.warmed = true;
    refreshStatus();
  } catch (err) {
    removeTyping();
    addMsg("bot", `Error: ${err.message}`);
  } finally {
    state.busy = false;
    $("#chatSend").disabled = false;
    input.focus();
  }
});

/* Library */
async function loadLibrary() {
  try {
    const data = await api("/api/library");
    $("#libDocs").innerHTML = (data.docs || [])
      .map((d) => `<div class="item"><strong>${escapeHtml(d.title)}</strong><div class="meta">${escapeHtml(d.category)} · ${escapeHtml(d.snippet || "")}</div></div>`)
      .join("") || `<div class="item muted">No notes yet.</div>`;
  } catch (e) {
    $("#libDocs").innerHTML = `<div class="item">Error: ${escapeHtml(e.message)}</div>`;
  }
}
$("#libForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = $("#libQuery").value.trim();
  if (!q) return;
  try {
    const data = await api("/api/search_library", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q }),
    });
    $("#libResults").innerHTML = (data.results || [])
      .map((r) => `<div class="item"><strong>${escapeHtml(r.title)}</strong><div class="meta">${escapeHtml(r.category)}</div><div>${escapeHtml(r.excerpt || "")}</div></div>`)
      .join("") || `<div class="item muted">No matches.</div>`;
  } catch (err) {
    $("#libResults").innerHTML = `<div class="item">Error: ${escapeHtml(err.message)}</div>`;
  }
});

/* RAG */
async function loadDocs() {
  try {
    const data = await api("/api/documents");
    $("#docList").innerHTML = (data.docs || [])
      .map((d) => `<div class="item"><strong>${escapeHtml(d.name)}</strong><div class="meta">${d.chunks || 0} chunks</div></div>`)
      .join("") || `<div class="item muted">No uploads.</div>`;
  } catch {}
}
$("#uploadForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = $("#uploadFile").files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  try {
    await api("/api/upload", { method: "POST", body: fd });
    $("#ragOut").textContent = `Uploaded ${file.name}`;
    loadDocs();
  } catch (err) {
    $("#ragOut").textContent = `Error: ${err.message}`;
  }
});
$("#ragForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = $("#ragQuery").value.trim();
  if (!q) return;
  $("#ragOut").textContent = "Searching…";
  try {
    const data = await api("/api/rag", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q }),
    });
    $("#ragOut").textContent = data.answer || "No answer.";
  } catch (err) {
    $("#ragOut").textContent = `Error: ${err.message}`;
  }
});

/* Cite */
$("#citeForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const parts = ($("#citeVol").value || "").split("/").map((s) => s.trim());
  const fields = {
    authors: ($("#citeAuthors").value || "").split(";").map((s) => s.trim()).filter(Boolean),
    title: $("#citeTitle").value,
    year: $("#citeYear").value,
    journal: $("#citeJournal").value,
    volume: parts[0] || "",
    issue: parts[1] || "",
    pages: parts[2] || "",
  };
  try {
    const data = await api("/api/cite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ style: $("#citeStyle").value, source_type: "journal", fields }),
    });
    $("#citeOut").textContent = data.citation || data.error || "Failed";
    $("#citeOut").classList.remove("muted");
  } catch (err) {
    $("#citeOut").textContent = `Error: ${err.message}`;
  }
});

/* Data */
$("#analyzeBtn").addEventListener("click", async () => {
  $("#dataOut").textContent = "Analyzing…";
  try {
    const data = await api("/api/analyze_csv", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sample: "student_survey.csv" }),
    });
    const lines = [
      `Source: ${data.source || ""}`,
      `Rows: ${data.rows} · Cols: ${data.cols}`,
      "",
      ...(data.columns || []).slice(0, 12).map((c) =>
        c.kind === "numeric"
          ? `• ${c.name}: mean=${c.mean} median=${c.median} min=${c.min} max=${c.max}`
          : `• ${c.name}: ${(c.top || []).slice(0, 3).map((t) => `${t.value}(${t.count})`).join(", ")}`
      ),
    ];
    $("#dataOut").textContent = lines.join("\n");
    $("#dataOut").classList.remove("muted");
  } catch (err) {
    $("#dataOut").textContent = `Error: ${err.message}`;
  }
});

/* Wiki */
async function loadWiki() {
  try {
    const st = await api("/api/wiki");
    $("#wikiStatus").textContent = st.running
      ? `Running · ${st.url} · ${st.count} pack(s)`
      : `Packs: ${st.count}${st.ready ? " · start server to browse" : " · add ZIMs in wiki/"}`;
    $("#wikiBooks").innerHTML = (st.books || [])
      .map((b) => `<div class="item"><strong>${escapeHtml(b.label)}</strong><div class="meta">${b.mb} MB</div></div>`)
      .join("");
  } catch (e) {
    $("#wikiStatus").textContent = "Wiki error: " + e.message;
  }
}
$("#wikiOpen").addEventListener("click", async () => {
  try { await api("/api/wiki_start", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }); } catch {}
  const st = await api("/api/wiki").catch(() => null);
  if (st?.url) window.open(st.url, "_blank", "noopener");
  else alert("Wiki not ready.");
  loadWiki();
});
$("#wikiStart").addEventListener("click", async () => {
  $("#wikiStatus").textContent = "Starting…";
  try {
    await api("/api/wiki_start", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
  } catch (e) {
    alert(e.message);
  }
  loadWiki();
});
$("#wikiForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = $("#wikiQuery").value.trim();
  try { await api("/api/wiki_start", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }); } catch {}
  const st = await api("/api/wiki").catch(() => null);
  if (st?.url) window.open(`${st.url}/search?pattern=${encodeURIComponent(q)}`, "_blank", "noopener");
});

/* ——— RIS Browser (offline, Brave-inspired) ——— */
const rb = { history: [], idx: -1, ready: false };

function isLocalUrl(u) {
  if (!u) return false;
  const s = u.trim();
  if (s.startsWith("ris://")) return true;
  if (s.startsWith("http://127.0.0.1") || s.startsWith("http://localhost")) return true;
  if (s.startsWith("http://localhost:")) return true;
  return false;
}

function homeHtml() {
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>RIS Browser</title>
<style>
  body{font-family:system-ui,sans-serif;background:#0f1115;color:#e8e8e8;margin:0;padding:2rem;max-width:40rem}
  h1{font-weight:600;font-size:1.4rem;margin:0 0 .5rem}
  p{color:#9aa0a6;line-height:1.5}
  a{color:#e8c27a}
  ul{padding-left:1.1rem;color:#9aa0a6} li{margin:.35rem 0}
  .badge{display:inline-block;border:1px solid #3d3d3d;border-radius:99px;padding:.2rem .6rem;font-size:.75rem;color:#6dce8a}
</style></head><body>
  <p class="badge">RIS Browser · offline only</p>
  <h1>Research-in-a-Stick</h1>
  <p>Your Brave-style browser for content that never leaves this machine. External websites are blocked.</p>
  <p><strong>Open</strong></p>
  <ul>
    <li><a href="ris://wiki">Offline wiki</a></li>
    <li><a href="ris://library">Knowledge library</a></li>
    <li><a href="http://127.0.0.1:8765">RIS chat app</a></li>
    <li><a href="http://127.0.0.1:8767">Kiwix wiki server</a></li>
  </ul>
  <p>Type a <code>ris://</code> or <code>127.0.0.1</code> address in the bar. Internet URLs are blocked on purpose.</p>
</body></html>`;
}

function libraryHtml() {
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Library</title>
<style>body{font-family:system-ui,sans-serif;background:#0f1115;color:#e8e8e8;padding:1.5rem;max-width:40rem}
h1{font-size:1.2rem} a{color:#e8c27a} p{color:#9aa0a6}</style></head><body>
  <h1>Knowledge library</h1>
  <p>Open the full library in the RIS app:</p>
  <p><a href="http://127.0.0.1:8765">RIS → Library</a></p>
  <p class="muted">Notes ship on the stick under <code>data/library/</code>.</p>
</body></html>`;
}

function resolveUrl(raw) {
  let u = (raw || "").trim();
  if (!u) u = "ris://home";
  if (u === "ris://home") return { kind: "html", html: homeHtml(), label: "ris://home" };
  if (u === "ris://library") return { kind: "html", html: libraryHtml(), label: "ris://library" };
  if (u === "ris://wiki" || u === "ris://site") {
    return { kind: "wiki", label: u === "ris://wiki" ? "ris://wiki" : "ris://site", which: u };
  }
  if (isLocalUrl(u)) {
    if (u.startsWith("ris://")) return { kind: "html", html: homeHtml(), label: u };
    return { kind: "frame", url: u, label: u };
  }
  return { kind: "blocked", label: u };
}

async function rbNavigate(raw, push = true) {
  const frame = $("#rbFrame");
  const status = $("#rbStatus");
  const addr = $("#rbUrl");
  const res = resolveUrl(raw);

  if (res.kind === "blocked") {
    status.textContent = `Blocked: ${raw} — RIS Browser only loads local / offline addresses`;
    status.style.color = "#e07a7a";
    frame.removeAttribute("src");
    frame.srcdoc = `<!DOCTYPE html><html><body style="font-family:system-ui;background:#0f1115;color:#e8e8e8;padding:2rem;max-width:36rem">
      <h1 style="font-size:1.2rem">Blocked by offline shield</h1>
      <p style="color:#9aa0a6">RIS Browser does not open external sites. Stay on <code>ris://</code> or <code>127.0.0.1</code>.</p>
      <p><a style="color:#e8c27a" href="ris://home">← Back to home</a></p></body></html>`;
    if (push && addr.value !== raw) { /* keep typed blocked url in bar */ }
    $("#rbUrl").value = raw;
    return;
  }

  status.style.color = "";
  $("#rbUrl").value = res.label || raw;

  if (push) {
    if (rb.idx < rb.history.length - 1) rb.history = rb.history.slice(0, rb.idx + 1);
    if (rb.history[rb.history.length - 1] !== res.label) {
      rb.history.push(res.label);
      rb.idx = rb.history.length - 1;
    }
  }
  updateNavBtns();

  if (res.kind === "html") {
    frame.removeAttribute("src");
    frame.srcdoc = res.html;
    status.textContent = "Local page · offline";
    return;
  }

  if (res.kind === "wiki") {
    status.textContent = "Starting offline wiki…";
    try { await api("/api/wiki_start", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }); } catch {}
    const st = await api("/api/wiki").catch(() => null);
    if (st?.url) {
      frame.srcdoc = "";
      frame.removeAttribute("srcdoc");
      frame.src = res.which === "ris://wiki" ? `${st.url}/` : `http://127.0.0.1:8765/`;
      status.textContent = `Connected to ${st.url}`;
      return;
    }
    frame.srcdoc = homeHtml();
    status.textContent = "Wiki server not ready — click Start in Offline Wiki";
    return;
  }

  // frame URL
  frame.removeAttribute("srcdoc");
  frame.src = res.url;
  status.textContent = `Loading ${res.url} (local only)…`;
}

function updateNavBtns() {
  const back = $("#rbBack");
  const fwd = $("#rbFwd");
  if (back) back.disabled = rb.idx <= 0;
  if (fwd) fwd.disabled = rb.idx >= rb.history.length - 1;
}

function initBrowser() {
  if (rb.ready) return;
  rb.ready = true;
  $("#rbAddrForm").addEventListener("submit", (e) => {
    e.preventDefault();
    rbNavigate($("#rbUrl").value);
  });
  $("#rbGo").addEventListener("click", () => rbNavigate($("#rbUrl").value));
  $("#rbReload").addEventListener("click", () => {
    const cur = rb.history[rb.idx] || "ris://home";
    rbNavigate(cur, false);
  });
  $("#rbBack").addEventListener("click", () => {
    if (rb.idx > 0) { rb.idx--; rbNavigate(rb.history[rb.idx], false); }
  });
  $("#rbFwd").addEventListener("click", () => {
    if (rb.idx < rb.history.length - 1) { rb.idx++; rbNavigate(rb.history[rb.idx], false); }
  });
  $$(".rb-bm").forEach((b) => b.addEventListener("click", () => rbNavigate(b.dataset.url)));
  const frame = $("#rbFrame");
  frame.addEventListener("load", () => {
    try {
      const doc = frame.contentDocument;
      if (!doc) return;
      doc.addEventListener("click", (ev) => {
        const a = ev.target.closest("a[href]");
        if (!a) return;
        ev.preventDefault();
        rbNavigate(a.getAttribute("href"));
      });
    } catch (e) { /* cross-origin frames */ }
  });
  rbNavigate("ris://home", true);
}

/* ——— Optional updates ——— */
async function loadUpdateStatus() {
  try {
    const st = await api("/api/update_status");
    $("#updateOut").textContent = `Feed: ${st.feed}\nLast: ${(st.last_log || []).join("\n") || "no update run yet"}`;
    $("#updateOut").classList.remove("muted");
  } catch (e) {
    $("#updateOut").textContent = "Update status unavailable: " + e.message;
  }
}
$("#updateCheck").addEventListener("click", async () => {
  $("#updateOut").textContent = "Checking online feed…";
  try {
    const st = await api("/api/update_status");
    $("#updateOut").textContent =
      "Feed ready.\n" +
      (st.manifest_url || "") +
      "\nPress Download & apply to refresh knowledge packs.";
    $("#updateOut").classList.remove("muted");
  } catch (e) {
    $("#updateOut").textContent = "Cannot reach update feed: " + e.message;
  }
});
$("#updateRun").addEventListener("click", async () => {
  const btn = $("#updateRun");
  btn.disabled = true;
  $("#updateOut").textContent = "Downloading updates…";
  try {
    const res = await api("/api/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    $("#updateOut").textContent =
      res.ok
        ? `Done. Updated ${res.updated} file(s).`
        : `Update failed: ${res.error || "unknown"}`;
    $("#updateOut").classList.remove("muted");
    $("#updateLog").innerHTML = (res.log || [])
      .map((l) => `<div class="item">${escapeHtml(l)}</div>`)
      .join("");
    refreshStatus();
  } catch (e) {
    $("#updateOut").textContent = "Error: " + e.message;
  } finally {
    btn.disabled = false;
  }
});

/* Init */
ensureWelcome();
refreshStatus();
setInterval(refreshStatus, 6000);
// warm the local model in the background so the first chat is faster
fetch("/api/status").then(() => {}).catch(() => {});
$("#chatInput").focus();
