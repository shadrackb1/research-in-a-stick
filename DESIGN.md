# DESIGN.md — Research-in-a-Stick site

**Identity:** Editorial Web Designer + Product UI hybrid  
**Artifact:** Conversion landing page for CRIW / university pilots  
**Status:** Taste layer for all future site edits

---

## 1. Objective

Make a stranger believe (1) the product is real and offline, (2) the team is specific, not generic, (3) the pilot ask is worth funding. Convert judges and campus partners in under two minutes of scroll.

## 2. Product context

USB research harness for Kenyan students: local LLM, library, wiki, citations, CSV. Constraint is **connectivity and data cost**, not “we love AI demos.” Voice is campus-lab honest, not SaaS hype.

## 3. Visual foundations

**Direction:** pure black & white darkroom — no gold, no brass, no chroma. Clay + glass + monochrome oil film.

| Token | Value | Role |
|--------|--------|------|
| `--bg` | `#0a0a0a` | Page |
| `--ink` | `#f2f2f0` | Primary text + filled CTA |
| `--muted` | `#9a9a96` | Secondary |
| `--dim` | `#5c5c58` | Captions |
| `--accent` | `#f2f2f0` | Same as ink — B&W only |
| `--clay` | `#141414` / `#1e1e1e` | Graphite clay |
| Display | Georgia | Headlines |
| UI | Segoe UI / system-ui | Body |
| Mono | Cascadia / Consolas | Labels, ports |

**Rules**
- **Zero chromatic color.** Links, CTUs, chips: white/gray/black only.
- Oil WebGL = grayscale film only (black → mid gray), pointer-warped.
- Signature: clay panels + glass + monochrome oil + 3D USB tilt.

**Signature:** graphite clay panels, brass accent only, 3D world tilt + USB (pointer/drag), product docs on a dark field. No purple AI glows.

## 4. Accessibility

- Contrast: body ≥ 4.5:1 on `--bg`; gold on dark ≥ 3:1 for large text  
- Focus rings always visible  
- `prefers-reduced-motion` disables springs, orbit, oil animation  
- Touch: no hover-only information  
- Sticky CTA must not cover last content (safe-area padding)

## 5. Voice & Tone

- Sentence case. One idea per line where possible.  
- Prefer true, product-specific sentences over slogans.  
- No “seamlessly / elevate / unlock / journey.”  
- Max one em-dash per paragraph.  
- Numbers only if we can defend them or label them as planning estimates.

## 6. Implementation practices

- Single self-contained HTML (no CDN)  
- CSS variables for tokens  
- One JS physics engine, not three animation libraries  
- Semantic sections + anchors for conversion path  
- Ship `site/index.html` on stick under `site/`

## 7. Anti-patterns (refuse)

| Pattern | Rule |
|---------|------|
| U1 gradient hero | Oil field is **domain-warped noise**, not purple-blue-cyan SaaS gradient; if simplified, use solid ink |
| U2 card grid | Stations are a **numbered typographic list**, not six icon cards |
| U3 emoji | Never |
| U5 stat trios | Drop floating “0 / 1 / 12 / 200” cards; fold numbers into prose or one strip |
| U6 button soup | **One** filled CTA per viewport; others ghost/text |
| U7 empty copy | Every line must name a real thing (port, model, stick, MOU) |
| W5 icon features | No stroke-icon + title + two-line grid |
| Fake testimonials | None until we have named pilot quotes |

## 8. Decision-making

1. Taste layer (this file) wins over “make it crazier” unless the user overrides.  
2. If a new request conflicts with §7, flag it and offer a non-slop alternative.  
3. Persist Decision Traces for any structural change.

## 9. Workflow

Design → implement in `site/index.html` → visual check at 375px and desktop → sync to USB. Next artifacts (deck, one-pager) reuse this palette and voice.
