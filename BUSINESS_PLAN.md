# Research-in-a-Stick (RIS) — Business Plan

**Audience:** CRIW 2026 judges, university pilot partners, seed funders  
**Decision this plan supports:** Whether to fund and pilot RIS as a portable offline research workstation for Kenyan students  
**Product maturity:** Working prototype (local LLM + library + RAG + wiki + citations + CSV tools on USB)  
**Date:** 2026-09-13  

---

## Executive summary

**Recommendation:** Fund a **12-month university pilot** (3 campuses, ~1,500 student seats) rather than mass production. The prototype already proves the core claim: a **ChatGPT-style research assistant that runs fully offline** on a USB stick. The binding constraints are **content depth, support model, and verified willingness-to-pay** — not core tech.

| Item | Base case |
|------|-----------|
| Unit BOM (16–32 GB stick + imaging) | **USD 12–22** |
| One-year pilot cost (3 campuses) | **USD 18k–35k** |
| Student willingness-to-pay (assumed) | **USD 5–15 / year** |
| Break-even seats (pilot economics) | **~2k–4k paying seats** |
| Primary risk | Adoption + support load, not model quality |

RIS monetizes **access and packaging**, not cloud tokens. That is the strategic bet.

---

## 1. Problem

| Evidence (project / field) | Implication |
|----------------------------|-------------|
| Mobile data often **KES 25–50 / GB** (project pitch anchor; treat as directional) | Cloud AI and Wikipedia are expensive for daily student use |
| Uneven campus Wi‑Fi; many students rely on phone bundles | Research tools must work **without continuous connectivity** |
| Need for local-language / Kenya-relevant notes (health, agri, curriculum, policy) | Generic global chatbots are a weak fit without local packs |

**Job to be done:** *Let a student do literature lookup, drafting help, citations, and basic data work on a cheap laptop with no reliable internet.*

---

## 2. Solution (what we already built)

RIS is a **plug-and-play USB workstation**:

| Module | Status |
|--------|--------|
| Local LLM (Qwen2.5-0.5B via llama.cpp) | Working — auto-load + watchdog |
| Chat UI (Ollama-style, conversational-first) | Working |
| Knowledge library (health, agri, curriculum, policy) | Working (small seed pack) |
| Document RAG (PDF/TXT/MD/CSV) | Working |
| Offline wiki (Kiwix + ZIM) | Working (small pack; large Wikipedia optional) |
| Citations (APA / Vancouver / Harvard) | Working |
| CSV analysis | Working |
| Skills: math, Python run, file organize | Working |
| Portable Python on stick | Working |
| Zero cloud / zero API keys | Design constraint |

**Differentiation:** Not “another chatbot” — a **self-contained research OS on a stick** with local knowledge packs and academic tooling.

---

## 3. Customer and use cases

### Primary segments

| Segment | Who | Pain | Willingness to pay |
|---------|-----|------|--------------------|
| **A. Undergrad research** | Year 2–4 students, universities | Data cost, assignment pressure | Medium (low price, high volume) |
| **B. Postgrad / lab** | MSc/PhD, supervisors | Offline field notes, citations | Medium–high |
| **C. Secondary / TVET** | Form 3–4, TVET | Curriculum revision packs | Low–medium (institution buy) |
| **D. Community health / agri** | CHWs, extension | Offline reference packs | Institution / NGO |

**Beachhead for pilot:** Segment A + B at 3 universities (e.g. Rift Valley cluster — aligns with Kabarak / CRIW network).

### Jobs

1. “Explain this concept without burning bundles.”  
2. “Find a passage in my PDF and cite it.”  
3. “Open offline Wikipedia / medical wiki.”  
4. “Summarize this CSV for my methods section.”  

---

## 4. Market sizing (transparent model)

> **Method:** Bottom-up. Public population proxies only. **No fabricated primary research.**  
> All figures are **planning estimates** with wide error bars until we run campus surveys.

### Assumptions (A1–A8)

| ID | Assumption | Base | Low | High | Basis |
|----|------------|------|-----|------|-------|
| A1 | Kenyan university students (public + private) | 500k | 400k | 600k | Order-of-magnitude HE population |
| A2 | Own or can use a laptop/desktop regularly | 55% | 40% | 70% | Device access still uneven |
| A3 | Would use offline research tool if free/cheap | 40% | 25% | 55% | Interest without WTP |
| A4 | Willing to pay USD 5–15 / year (or institution pays) | 15% | 8% | 25% | Price-sensitive segment |
| A5 | Institutions buy site licenses | 20 campuses | 10 | 40 | 3-year horizon |
| A6 | Site license | USD 2,000 / campus / yr | 1k | 4k | Pilot-to-scale |
| A7 | Stick + image + support, year 1 | USD 18 | 12 | 22 | BOM + imaging |
| A8 | NGOs / TVET secondary | 50k addressable | 20k | 100k | Adjacent |

### TAM / SAM / SOM (12–36 months)

| Layer | Definition | Base estimate |
|-------|------------|---------------|
| **TAM** | All HE students × (A2×A3) potential users | 500k × 0.55 × 0.40 ≈ **110k** users |
| **SAM** | Users who could pay (direct or via school) | 110k × 0.15 ≈ **16.5k** payers + campus licenses |
| **SOM (3 yr)** | Realistic capture with 1 NGO + 10 campuses + direct sales | **2–5k** seats + **8–12** campuses |

### Revenue scenarios (3-year, illustrative)

| Stream | Year 1 | Year 2 | Year 3 |
|--------|--------|--------|--------|
| Campus licenses (8–12 by Y3) @ ~USD 2k | 4k | 12k | 20k |
| Direct student seats (2–5k) @ ~USD 10 | 5k | 20k | 50k |
| Content / imaging services (NGO, custom packs) | 2k | 10k | 25k |
| **Total** | **~11k** | **~42k** | **~95k** |

**Sensitivity:** Break-even on pilot ops is dominated by **support hours** and **content refresh**, not GPU cost (inference is on device).

---

## 5. Business model

| Layer | Offer | Price logic |
|-------|-------|-------------|
| **Free / demo** | RIS Community image (basic library + tools) | Lead gen, CRIW showcase |
| **Student Pro** | Larger wiki packs + more library content + updates | USD 5–15 / year |
| **Campus** | Site image, lab imaging, training, local content pack | USD 1–4k / campus / year |
| **Custom packs** | Health, agriculture, curriculum for NGO / ministry pilots | Project fee |

**Unit economics (base):**

- COGS per stick: ~USD 15  
- Student Pro net after channel: ~USD 8  
- Campus license: near-100% gross margin (software/content)  
- Support: **primary opex** — must stay under ~USD 1–2 / seat / year at scale via self-serve docs + campus champions  

---

## 6. Go-to-market

### Phase 0 — CRIW 2026 (now)
- Demo booth: offline chat + malaria/maize + citation + CSV  
- Capture emails / pilot LOIs from judges and visiting faculty  

### Phase 1 — Pilot (Months 1–6)
- 3 campuses, ~1,500 seats  
- Measure: weekly active, questions/session, citation use, stick loss rate  
- Train 10–15 student “RIS champions”  

### Phase 2 — Convert (Months 7–12)
- Convert 1–2 campuses to paid site license  
- Publish 1 evidence brief (usage + grades/helpfulness survey)  
- Add 1 NGO / TVET pack  

### Channels
1. University research offices / CRIW network  
2. Student associations / clubs  
3. NGO education & health programs  
4. Direct USB + download image for self-flash  

---

## 7. Operations and delivery

| Function | Approach |
|----------|----------|
| **Imaging** | Scripted USB build (model + bins + packs) — already partially automated |
| **Updates** | Yearly content drop; model updates optional (larger sticks) |
| **Support** | In-app help + FAQ + campus champion; no cloud ticketing required |
| **Privacy** | Data never leaves device — strong selling point for clinical/thesis work |
| **IP** | Open components (llama.cpp, Qwen, Kiwix) + our packaging/UI/content |

**Hardware note:** Prefer **NTFS/exFAT** healthy media; the pilot should QC sticks before imaging.

---

## 8. Financial plan (pilot year)

| Cost line | Low | High |
|-----------|-----|------|
| 1,500 sticks (BOM) | 18k | 33k |
| Content curation (library + ZIM QA) | 3k | 8k |
| Champion stipends / travel | 2k | 6k |
| Support & contingency | 2k | 5k |
| **Total pilot** | **~25k** | **~52k** |

| Funding mix | Notes |
|-------------|-------|
| CRIW / university seed | In-kind venue, faculty sponsor |
| Grant / innovation fund | Primary cash for sticks |
| Early campus LOIs | Non-cash validation |

---

## 9. KPIs (what “working” means)

| KPI | Pilot target |
|-----|----------------|
| Stick boot → first local answer | &lt; 60 s (p95) |
| Weekly active users / seats | ≥ 35% |
| Offline-only sessions | ≥ 90% |
| Citation + RAG + chat used in same week | ≥ 20% of WAU |
| Support tickets / 100 seats / month | ≤ 5 |
| Campus renewal intent (survey) | ≥ 60% “likely/very likely” |
| Stick failure / loss rate | ≤ 8% / term |

---

## 10. Risks and mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Weak adoption (“we have phones”) | High | Champion program; curriculum-aligned packs; assignment hooks |
| Stick loss / corruption | Medium | NTFS format, imaging QC, spare pool 10% |
| Small model quality gaps | Medium | Clear scope; RAG + wiki for facts; optional larger model on bigger sticks |
| Legal / license of packs | Medium | Use CC/open ZIM; document licenses |
| Support overload | High | Self-serve `START_HERE`, check_model.bat, campus champions |
| Data-cost fall (bundles cheaper) | Low–Med | Keep value on **privacy + offline field use**, not cost alone |

---

## 11. Immediate next actions (90 days)

1. **Lock pilot MOU** with 1 host university (CRIW network).  
2. **Image 200 sticks** with current stack + NHS/wiki pack.  
3. **Survey 200 students** (WTP, device access, top 5 research tasks) to replace A1–A4 assumptions.  
4. **Expand library packs** (past papers, methods guides) — content is the moat.  
5. **Write 2-page judge brief** from this plan + live demo script.  

---

## 12. Sources and methodology

| Source | Use |
|--------|-----|
| RIS project README / pitch anchors | Problem framing (data cost KES 25–50/GB — **directional**, not audited) |
| Working prototype on `C:\ris-stick` / USB `D:\research-in-a-stick` | Product capability claims |
| Bottom-up model A1–A8 | TAM/SAM/SOM — **assumptions, not measured demand** |
| Open stack | llama.cpp, Qwen2.5 GGUF, Kiwix ZIM, Python embed |

**Not used:** proprietary university enrollment databases, paid market reports.  
**Confidence:** Product feasibility **high**; market size **medium–low** until pilot survey.

---

## Recommendation

**Approve a funded 12-month pilot** focused on 3 campuses and measurable offline usage. Do **not** scale manufacturing until (1) weekly active ≥ 35% and (2) ≥ 1 campus converts to a paid site license. The technology risk is largely retired; the next dollars buy **evidence and content**, not more model size.
