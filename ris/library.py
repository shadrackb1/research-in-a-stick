"""Offline knowledge library search over local markdown notes."""
from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path
from .config import LIBRARY
from .scoring import score as _score
from .scoring import tokenize as _tokenize


@dataclass
class Doc:
    id: str
    title: str
    category: str
    path: str
    text: str

    def snippet(self, n: int = 280) -> str:
        t = re.sub(r"\s+", " ", self.text).strip()
        return t[:n] + ("…" if len(t) > n else "")


class KnowledgeLibrary:
    def __init__(self, root: Path | None = None):
        self.root = root or LIBRARY
        self.docs: list[Doc] = []
        self.reload()

    def reload(self) -> int:
        self.docs = []
        if not self.root.exists():
            return 0
        for path in sorted(self.root.rglob("*")):
            if path.suffix.lower() not in {".md", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            title = path.stem.replace("_", " ").replace("-", " ").title()
            for line in text.splitlines():
                if line.startswith("#"):
                    title = line.lstrip("# ").strip() or title
                    break
            category = path.parent.name if path.parent != self.root else "general"
            self.docs.append(Doc(id=str(path.relative_to(self.root)), title=title, category=category, path=str(path), text=text))
        return len(self.docs)

    def list_docs(self) -> list[dict]:
        return [{"id": d.id, "title": d.title, "category": d.category, "snippet": d.snippet(160)} for d in self.docs]

    def search(self, query: str, limit: int = 5) -> list[dict]:
        q = _tokenize(query)
        scored = []
        for d in self.docs:
            s = _score(q, _tokenize(d.title + " " + d.category + " " + d.text))
            if s > 0:
                scored.append((s, d))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for s, d in scored[:limit]:
            sentences = re.split(r"(?<=[.!?])\s+", d.text)
            best = d.snippet(280)
            best_s = 0.0
            qset = set(q)
            for sent in sentences:
                sc = len(qset & set(_tokenize(sent)))
                if sc > best_s:
                    best_s = sc
                    best = sent.strip()[:400]
            results.append({"score": round(s, 3), "id": d.id, "title": d.title, "category": d.category, "excerpt": best})
        return results
