"""Conversational AI chat for RIS.

Priority:
1. Free-form chat with the bundled local model (ChatGPT-like)
2. Host Ollama if present
3. Conversational offline brain — uses skills/RAG only when needed
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from typing import Any

from . import local_llm
from .config import DEFAULT_MODEL, OLLAMA_URL
from .library import KnowledgeLibrary
from .rag import DocumentStore
from .skills import SkillRouter, build_tool_block, catalog, catalog_prompt

# Questions that clearly want local research tools (not casual chat)
_RESEARCH_HINTS = (
    "malaria", "cholera", "maize", "agriculture", "curriculum", "biology",
    "policy", "digital superhighway", "kenya", "citation", "cite", "apa",
    "vancouver", "harvard", "csv", "dataset", "survey", "uploaded", "document",
    "rag", "wiki", "wikipedia", "encyclopedia", "definition of", "according to",
    "library", "source", "reference", "bibliography", "doi",
    # advanced offline powers
    "calculate", "compute", "solve", "equation", "math", "integral", "derivative",
    "python", "write code", "write a function", "script", "implement", "debug",
    "algorithm", "program", "organize files", "sort files", "list files",
    "workspace", "folder",
)


def ollama_available(timeout: float = 0.6) -> bool:
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def _ollama_chat(messages: list[dict[str, str]], model: str | None = None) -> str:
    payload = {"model": model or DEFAULT_MODEL, "messages": messages, "stream": False}
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return (data.get("message") or {}).get("content", "").strip()


def _needs_local_knowledge(message: str) -> bool:
    m = (message or "").lower()
    if len(m.split()) <= 2 and m.rstrip("?!") in {
        "hi", "hey", "hello", "thanks", "thank you", "ok", "okay", "cool", "yes", "no",
        "help", "who are you", "what can you do",
    }:
        return False
    return any(h in m for h in _RESEARCH_HINTS)


def _persona_system(inject_skills: bool, inject_context: bool, message: str, skills: SkillRouter) -> str:
    system = (
        "You are Research-in-a-Stick (RIS), a warm, capable offline study companion "
        "for students and researchers in Kenya. Talk like ChatGPT: natural, friendly, "
        "helpful, and clear. You can explain concepts, help write, do math, write and "
        "run Python code, and organize local files — all offline. "
        "Use short paragraphs. Prefer fenced code blocks for code. "
        "Do not claim to browse the live internet."
    )
    if inject_skills:
        system += (
            "\n\nYou have local skills, but use them ONLY when needed "
            "(facts from the offline library, user documents, wiki, citations, or CSV data). "
            "For greetings, brainstorming, explanations, writing help, or casual chat — just talk.\n"
            + catalog_prompt()
        )
    if inject_context:
        ctx = []
        for h in skills.library.search(message, limit=2):
            ctx.append(f"[LIBRARY/{h['category']}] {h['title']}: {h['excerpt'][:280]}")
        for h in skills.docs.search(message, limit=1):
            ctx.append(f"[DOC/{h['doc']}] {h['text'][:280]}")
        if ctx:
            system += (
                "\n\nOptional local notes (use only if they help; never recite them raw):\n"
                "<context>\n" + "\n".join(ctx) + "\n</context>"
            )
    return system


def _strip_skill_calls(text: str) -> str:
    return re.sub(r"SKILL:[a-z_]+\s*\{.*?\}", "", text or "", flags=re.DOTALL).strip()


def _power_tools(message: str, skills: SkillRouter, model_reply: str = "") -> tuple[list[str], list[str]]:
    """Deterministic execution for math / code / files when the small model doesn't emit SKILL:."""
    used: list[str] = []
    notes: list[str] = []
    mlow = (message or "").lower()
    rlow = (model_reply or "").lower()

    # calculate
    m = re.search(r"(\d[\d\s\.\+\-\*/\^\(\)%]+)", message or "")
    if m and any(op in m.group(1) for op in "+-*/^") and any(
        k in mlow for k in ("calculate", "compute", "solve", "what is", "math", "eval")
    ):
        res = skills.run("calculate", {"expression": m.group(1).strip()})
        used.append("calculate")
        notes.append(f"SKILL:calculate → {skills.render(res, 180)}")

    # organize files (preview by default; apply if user says apply/do it/for real)
    if any(k in mlow for k in ("organize files", "sort files", "tidy files", "clean folder", "organize my")):
        apply = any(k in mlow for k in ("apply", "do it", "for real", "actually", "really organize", "yes organize"))
        res = skills.run(
            "organize_files",
            {"source": "workspace", "mode": "by_type", "dry_run": not apply},
        )
        used.append("organize_files")
        notes.append(f"SKILL:organize_files → {skills.render(res, 220)}")

    # list files
    if any(k in mlow for k in ("list files", "what files", "show files", "workspace contents")):
        res = skills.run("list_files", {"path": "workspace"})
        used.append("list_files")
        notes.append(f"SKILL:list_files → {skills.render(res, 200)}")

    # execute Python the model (or user) provided
    wants_run = any(k in mlow for k in ("run python", "execute", "run the code", "run this", "compute", "calculate"))
    code = None
    fm = re.search(r"```(?:python|py)?\n([\s\S]+?)```", model_reply or "")
    if fm:
        code = fm.group(1).strip()
    elif "```" not in (model_reply or "") and "print(" in (model_reply or ""):
        # inline print(...) snippet
        cm = re.search(r"(import [^\n]+\n)?(print\([^\n]+\))", model_reply)
        if cm:
            code = cm.group(0)
    if code and (wants_run or "factorial" in mlow or "sqrt" in mlow):
        res = skills.run("run_python", {"code": code})
        used.append("run_python")
        notes.append(f"SKILL:run_python → {skills.render(res, 240)}")

    return used, notes


def _run_model_skills(text: str, skills: SkillRouter) -> tuple[str, list[str]]:
    traces: list[str] = []
    cleaned = text or ""
    for name, args in skills.extract_calls(cleaned)[:3]:
        traces.append(f"SKILL:{name} → {skills.execute(name, args)}")
    return _strip_skill_calls(cleaned), traces


def _last_user_turns(history: list[dict[str, str]], n: int = 4) -> str:
    turns = [h["content"] for h in history if h.get("role") == "user"][-n:]
    return " ".join(turns)


def _offline_converse(
    message: str,
    history: list[dict[str, str]],
    skills: SkillRouter,
) -> str:
    """Chat-like offline brain. Uses tools only when the question needs them."""
    q = message.strip()
    qlow = q.lower()
    prior = _last_user_turns(history[:-1] if history and history[-1].get("role") == "user" else history)

    # identity / capability
    if any(k in qlow for k in ("who are you", "what are you", "your name")):
        return (
            "I'm RIS — your offline study companion on this stick.\n\n"
            "We can just chat, or I can dig into the knowledge library, your uploaded docs, "
            "citations, CSV data, and the offline wiki when you need that. What are you working on?"
        )

    # casual
    if qlow in {"hi", "hello", "hey", "yo", "sup"} or qlow.startswith(("hello", "hi ", "hey ")):
        return "Hey. What are you studying today — or do you just want to talk something through?"

    if qlow in {"thanks", "thank you", "thx"} or qlow.startswith("thank"):
        return "Anytime. Want another angle on it, or shall we move on?"

    if qlow.startswith("help") or qlow in {"what can you do", "how do you work"}:
        return (
            "Mostly I chat with you. When a question needs local sources, I can also:\n"
            "• search the offline knowledge library\n"
            "• look in documents you upload\n"
            "• format APA / Vancouver / Harvard citations\n"
            "• summarize a sample CSV\n"
            "• open the offline wiki\n\n"
            "Just ask naturally — I'll pull tools only if they help."
        )

    # follow-ups that ask to rephrase the last answer
    if any(k in qlow for k in ("simpler", "simple words", "explain that", "what does that mean",
                               "in other words", "eli5", "easier")):
        last_bot = ""
        for h in reversed(history):
            if h.get("role") == "assistant":
                last_bot = h.get("content") or ""
                break
        if last_bot:
            # strip markdown-ish decorations for a plain rewrite
            plain = re.sub(r"[*_#`]", "", last_bot)
            plain = re.sub(r"\n{3,}", "\n\n", plain).strip()
            # drop trailing “want me to…” coaching lines when rewriting
            plain = re.split(r"\nWant me to |\nWant an even ", plain, maxsplit=1)[0].strip()
            if len(plain) > 420:
                plain = plain[:420].rsplit(" ", 1)[0] + "…"
            return (
                "Sure — simpler version:\n\n"
                f"{plain}\n\n"
                "Want an even shorter version, or an example from everyday life?"
            )

    # research / tools path — avoid false positives like "science" matching "cite"
    if _needs_local_knowledge(q) or re.search(r"\b(cite|citation|apa|csv|wiki|wikipedia)\b", qlow):
        traces = skills.auto_tools(q)
        lib_hits = skills.library.search(q, limit=2)
        doc_hits = skills.docs.search(q, limit=1)

        # citation intent — only explicit citation requests (not "science", etc.)
        if re.search(r"\b(cite|citation|references?|bibliography)\b", qlow) or re.search(r"\b(apa|vancouver|harvard)\b", qlow):
            return (
                "I can format that citation for you. Open **Citations** in the sidebar "
                "(or give me authors, title, year, and journal) and I'll use the citation skill.\n\n"
                "Example: *Format APA: Mwangi Alice; Otieno Brian; Offline AI access; 2026; KJRI*"
            )

        if "csv" in qlow or "dataset" in qlow or "survey" in qlow:
            samples = skills.run("list_samples", {})
            return (
                "For data, use **Data Analysis**, or say which file. "
                f"Sample on this stick: {samples.get('result') or 'student_survey.csv'}."
            )

        if not lib_hits and not doc_hits:
            return (
                f"I don't have a solid offline note for “{q}”.\n\n"
                "Want me to open the offline wiki, or can you add a bit more detail "
                "(symptoms, location, year, what you've tried so far)?"
            )

        # conversational synthesis from the best 1–2 hits — not a RAG dump
        best = lib_hits[0] if lib_hits else doc_hits[0]
        title = best.get("title") or best.get("doc") or "local notes"
        excerpt = (best.get("excerpt") or best.get("text") or "").strip()
        if len(excerpt) > 320:
            excerpt = excerpt[:320].rsplit(" ", 1)[0] + "…"
        lead = f"From what I have offline on **{title}**:"
        extra = ""
        # only attach a related note if it shares real keywords with the question
        q_tokens = set(re.findall(r"[a-zA-Z]{4,}", q.lower()))
        for h in lib_hits[1:]:
            excerpt2 = h.get("excerpt") or ""
            overlap = q_tokens & set(re.findall(r"[a-zA-Z]{4,}", excerpt2.lower()))
            if len(overlap) >= 2:
                e = excerpt2.strip()[:180].rsplit(" ", 1)[0] + "…"
                extra = f"\n\nRelated: {e}"
                break
        follow = "\n\nWant me to go deeper, or turn this into short study notes?"
        body = f"{lead}\n\n{excerpt}{extra}{follow}"
        if traces and any("wiki_status" in t for t in traces):
            body += "\n\n_(Offline wiki is available if you want encyclopedia depth.)_"
        return body

    # small-talk / study coaching (no RAG)
    if "how do i" in qlow or "tips" in qlow or "study" in qlow or "advice" in qlow:
        return (
            "Here's a simple approach: pick one goal for this session, "
            "break it into 25-minute blocks, and end each block with a short recall test.\n\n"
            "If it's course content (health, agri, bio, policy), ask the topic and I'll pull "
            "from the local library. If it's a paper you have, drop it into Document RAG."
        )

    # generic conversational reply using recent topic
    topic = ""
    for w in _RESEARCH_HINTS:
        if w in prior:
            topic = w
            break
    if topic:
        return (
            f"Got it — continuing around **{topic}**. "
            "I can keep chatting here, or search the offline library if you want sourced points. "
            "What should we unpack next?"
        )
    return (
        "I hear you. Tell me a bit more about what you want — explain a concept, "
        "plan an assignment, check facts from the local library, or format a citation?"
    )


class ResearchAssistant:
    def __init__(self, library: KnowledgeLibrary, docs: DocumentStore):
        self.library = library
        self.docs = docs
        self.history: list[dict[str, str]] = []
        self.skills = SkillRouter(library, docs)

    def status(self) -> dict[str, Any]:
        local = local_llm.status()
        if local.get("ready") and not local.get("running"):
            try:
                local_llm.warmup_async()
            except Exception:
                pass
            local = local_llm.status()
        if local.get("running"):
            mode = "local"
        elif local.get("ready"):
            mode = "loading"  # model present, warming up
        elif ollama_available():
            mode = "ollama"
        else:
            mode = "offline"
        try:
            from . import wiki as wiki_mod

            wst = wiki_mod.status()
        except Exception:
            wst = {"ready": False, "running": False, "count": 0}
        return {
            "ollama": ollama_available(),
            "local_model": local.get("running", False),
            "local_model_ready": local.get("ready", False),
            "local_model_name": local.get("model_name"),
            "mode": mode,
            "skills": [s["name"] for s in catalog()],
            "wiki": wst,
            "library_docs": len(self.library.docs),
            "uploaded_docs": len(self.docs.docs),
            "style": "conversational-first",
        }

    def chat(self, message: str, model: str | None = None, use_ollama: bool | None = None) -> dict:
        message = (message or "").strip()
        if not message:
            return {"reply": "Hey — what's on your mind?", "mode": "offline"}

        self.history.append({"role": "user", "content": message})
        # keep a tighter history for small models
        self.history = self.history[-16:]

        want_tools = _needs_local_knowledge(message)
        system = _persona_system(
            inject_skills=want_tools,
            inject_context=want_tools,
            message=message,
            skills=self.skills,
        )
        used: list[str] = []

        # 1) Local model — free conversation, skills only on demand
        if use_ollama is not False:
            try:
                if local_llm.ensure_ready(timeout=90.0):
                    messages = [{"role": "system", "content": system}] + self.history
                    raw = local_llm.chat(messages, max_tokens=420, temperature=0.45)
                    cleaned, traces = _run_model_skills(raw, self.skills)
                    p_used, p_notes = _power_tools(message, self.skills, cleaned or raw)
                    if traces or p_notes:
                        all_traces = traces + p_notes
                        used = [t.split("→")[0].replace("SKILL:", "").strip() for t in all_traces]
                        used = list(dict.fromkeys(used + p_used))
                        follow_sys = system + "\n\n" + build_tool_block(all_traces) + (
                            "\nNow answer the user conversationally using these results. "
                            "Do not dump raw JSON."
                        )
                        follow = [{"role": "system", "content": follow_sys}] + self.history
                        raw2 = local_llm.chat(follow, max_tokens=380, temperature=0.35)
                        reply = _strip_skill_calls(raw2) or cleaned or raw
                        # attach compact execution summary when useful
                        exec_bits = [n for n in p_notes if any(k in n for k in ("calculate", "run_python", "organize", "list_files"))]
                        if exec_bits:
                            reply += "\n\n---\n" + "\n".join(exec_bits)
                    else:
                        reply = cleaned or raw
                    if reply:
                        self.history.append({"role": "assistant", "content": reply})
                        return {"reply": reply, "mode": "local", "skills": used, "style": "conversational"}
            except Exception as e:
                sys.stderr.write(f"[RIS] local model error: {e}\n")

        # 2) Ollama
        if ollama_available() if use_ollama is None else bool(use_ollama) and ollama_available():
            try:
                messages = [{"role": "system", "content": system}] + self.history
                raw = _ollama_chat(messages, model=model)
                cleaned, traces = _run_model_skills(raw, self.skills)
                reply = cleaned or raw
                if traces:
                    used = [t.split("→")[0].replace("SKILL:", "").strip() for t in traces]
                    reply = reply + "\n\n" + "\n".join(traces)
                self.history.append({"role": "assistant", "content": reply})
                return {"reply": reply, "mode": "ollama", "skills": used, "style": "conversational"}
            except Exception as e:
                sys.stderr.write(f"[RIS] Ollama error: {e}\n")

        # 3) Offline conversational brain (tools only when needed)
        reply = _offline_converse(message, self.history, self.skills)
        self.history.append({"role": "assistant", "content": reply})
        return {"reply": reply, "mode": "offline", "skills": used, "style": "conversational"}
