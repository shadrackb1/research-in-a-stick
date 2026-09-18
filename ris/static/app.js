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

/* Init */
ensureWelcome();
refreshStatus();
setInterval(refreshStatus, 6000);
// warm the local model in the background so the first chat is faster
fetch("/api/status").then(() => {}).catch(() => {});
$("#chatInput").focus();
