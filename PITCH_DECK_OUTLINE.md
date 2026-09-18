# RIS — 1-Page Pitch Deck Outline
### CRIW 2026 · Team of 4 · ~8–10 slides · 5–7 minutes

---

## Slide map

| # | Slide | One line | Owner (primary) |
|---|--------|----------|-----------------|
| 1 | **Title** | Research-in-a-Stick — offline AI for students who can’t afford the cloud | All (logo + names) |
| 2 | **Problem** | KES 25–50/GB + weak campus Wi‑Fi lock students out of AI & Wikipedia | **P1 — Problem & impact** |
| 3 | **Demo hook** | 30s live chat on the stick: malaria Q → real local answer, *no internet* | **P2 — Product demo** |
| 4 | **Solution** | USB = local LLM + library + wiki + RAG + citations + CSV | **P2** |
| 5 | **How it works** | Diagram: stick → llama.cpp → chat UI; data never leaves device | **P3 — Tech** |
| 6 | **Differentiation** | Not a chatbot clone — full research workstation; privacy by design | **P3** |
| 7 | **Market & model** | 3-campus pilot; free demo → Student Pro → campus license | **P4 — Business** |
| 8 | **Traction & plan** | Working prototype + 90-day pilot (MOU, 200 sticks, survey) | **P4** |
| 9 | **Team** | 4 roles, CRIW / Kabarak | All (30s) |
| 10 | **Ask** | Seed for 200 sticks + 1 host university MOU | **P1 closes** |

---

## Speaking script (tight)

| Time | Who | Say |
|------|-----|-----|
| 0:00–0:30 | **P1** | Hook: “A student with 1GB of data can’t run cloud AI. We put the lab on a stick.” |
| 0:30–1:30 | **P2** | Live demo (already warm model): chat + one citation or CSV |
| 1:30–2:30 | **P3** | Stack + privacy: local model, no API keys, works after you unplug the internet |
| 2:30–3:30 | **P4** | Pilot economics: ~USD 12–22/seat build; 1,500-seat pilot; campus license path |
| 3:30–4:00 | **P1** | Ask + 90-day plan |
| Q&A | Rotate | P2 product · P3 tech · P4 money · P1 impact |

---

## Team of 4 — roles

| Role | Focus in pitch | Prep |
|------|----------------|------|
| **P1 — Impact lead** | Problem, Kenya context, ask, open/close | 1-slide problem stats; own the ask |
| **P2 — Product demo** | Live stick demo, UI, features | Rehearse cold-start vs warm; backup video/GIF |
| **P3 — Tech lead** | Architecture, offline model, privacy | 1 diagram; answer “how small is the model?” |
| **P4 — Business lead** | Pilot, pricing, KPIs, 90-day plan | Know USD 25–52k pilot range cold |

**Backup rule:** If demo fails, P2 plays 20s screen recording; P3 explains offline fallback still works.

---

## Visuals to have ready

1. **Before/after:** phone with “no data” vs stick → chat  
2. **Architecture box** (stick / model / UI / never cloud)  
3. **Pilot funnel:** 3 campuses → 1,500 seats → 1 paid license  
4. **Team photo strip** (optional)  
5. **QR** to `BUSINESS_PLAN.html` or USB handout  

---

## One-liners (print on cue cards)

- **P1:** “Zero bundles. Full research stack on one stick.”  
- **P2:** “Watch — this is Qwen on the USB, not ChatGPT’s servers.”  
- **P3:** “llama.cpp + GGUF on-device; watchdog keeps it alive on any Windows PC.”  
- **P4:** “We’re not asking for a factory — we’re asking for a pilot that proves WAU and one paid campus.”  

---

## Judge Q&A cheat sheet

| Likely question | Owner | Short answer |
|-----------------|-------|--------------|
| Why not just Ollama/ChatGPT? | P3 | No install, no net, academic tools built-in |
| Model quality vs GPT-4? | P3 | Small model + local library/wiki; scope is research assist, not everything |
| Who pays? | P4 | Campus first, then Student Pro |
| Data privacy? | P2/P3 | Files stay on stick; no telemetry |
| What’s the ask? | P1 | Pilot seed + host university intro |

---

*Align numbers with `BUSINESS_PLAN.md` (pilot USD 25–52k, stick USD 12–22, WTP USD 5–15).*
