"""APA / Vancouver / Harvard citation formatters."""
from __future__ import annotations
import re
from typing import Any


def _clean(s: str | None) -> str:
    return (s or "").strip()


def _authors_apa(authors: list[str]) -> list[str]:
    names = []
    for a in authors:
        a = _clean(a)
        if not a:
            continue
        if "," in a:
            last, first = a.split(",", 1)
            initials = "".join(p[0].upper() + "." for p in first.split() if p)
            names.append(f"{last.strip()}, {initials}".strip())
        else:
            parts = a.split()
            if len(parts) == 1:
                names.append(parts[0])
            else:
                last = parts[-1]
                initials = "".join(p[0].upper() + "." for p in parts[:-1])
                names.append(f"{last}, {initials}")
    return names


def format_citation(style: str, source_type: str, fields: dict[str, Any]) -> str:
    style = (style or "apa").strip().lower()
    authors = fields.get("authors") or []
    if isinstance(authors, str):
        authors = [a.strip() for a in re.split(r";| and ", authors) if a.strip()]
    title = _clean(fields.get("title"))
    year = _clean(str(fields.get("year") or fields.get("date") or "n.d."))[:4]
    if not year[:1].isdigit():
        year = "n.d."
    journal = _clean(fields.get("journal"))
    volume = _clean(fields.get("volume"))
    issue = _clean(fields.get("issue"))
    pages = _clean(fields.get("pages"))
    url = _clean(fields.get("url"))
    doi = _clean(fields.get("doi"))
    publisher = _clean(fields.get("publisher"))
    a = _authors_apa(authors)
    a_str = ", ".join(a[:-1]) + ", & " + a[-1] if len(a) > 1 else (a[0] if a else "Anonymous")
    t = title.rstrip(".") + "." if title else "Untitled."

    if style in ("apa", "apa7"):
        if (source_type or "journal") in ("journal", "article"):
            iss = f"({issue})" if issue else ""
            pg = f", {pages}" if pages else ""
            core = re.sub(r"\s+", " ", f"{a_str} ({year}). {t} {journal}, {volume}{iss}{pg}.").strip()
            if doi:
                core += f" https://doi.org/{doi}"
            elif url:
                core += f" {url}"
            return core
        return re.sub(r"\s+", " ", f"{a_str} ({year}). {t} {publisher}.").strip()
    if style == "vancouver":
        a2 = []
        for x in authors:
            x = _clean(x)
            if "," in x:
                last, first = x.split(",", 1)
                a2.append(f"{last.strip()} {''.join(p[0].upper() for p in first.split() if p)}")
            else:
                a2.append(x)
        head = ", ".join(a2) + "."
        return re.sub(r"\s+", " ", f"{head} {t} {journal}. {year};{volume}:{pages}.").strip()
    if style == "harvard":
        if len(a) == 2:
            who = f"{a[0]} and {a[1]}"
        elif len(a) > 2:
            who = f"{a[0]} et al."
        else:
            who = a_str
        return re.sub(r"\s+", " ", f"{who} ({year}) '{title}', {journal}{f', {volume}' if volume else ''}{f'({issue})' if issue else ''}{f', pp. {pages}' if pages else ''}.").strip()
    raise ValueError(f"Unsupported style: {style}. Use apa, vancouver, or harvard.")
