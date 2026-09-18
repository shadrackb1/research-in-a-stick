"""Lightweight offline document RAG."""
from __future__ import annotations
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from .config import UPLOADS
from .scoring import score as _score
from .scoring import tokenize as _tokenize


@dataclass
class Chunk:
    doc_id: str
    doc_name: str
    chunk_id: int
    text: str


def extract_text(path: Path) -> str | None:
    suffix = path.suffix.lower()
    try:
        if suffix in {".txt", ".md", ".csv", ".json"}:
            return path.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".pdf":
            try:
                from pypdf import PdfReader
            except ImportError:
                return None
            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None


def chunk_text(doc_id: str, doc_name: str, text: str, size: int = 700, overlap: int = 120) -> list[Chunk]:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return []
    chunks: list[Chunk] = []
    start, idx, n = 0, 0, len(text)
    while start < n:
        end = min(n, start + size)
        if end < n:
            window = text[start:end]
            cut = max(window.rfind("\n\n"), window.rfind(". "), window.rfind("\n"))
            if cut > size * 0.45:
                end = start + cut + 1
        piece = text[start:end].strip()
        if piece:
            chunks.append(Chunk(doc_id=doc_id, doc_name=doc_name, chunk_id=idx, text=piece))
            idx += 1
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


class DocumentStore:
    def __init__(self, root: Path | None = None):
        self.root = root or UPLOADS
        self.root.mkdir(parents=True, exist_ok=True)
        self.chunks: list[Chunk] = []
        self.docs: dict[str, dict] = {}
        self.reload()

    def reload(self) -> int:
        self.chunks = []
        self.docs = {}
        for path in sorted(self.root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".txt", ".md", ".pdf", ".csv"}:
                continue
            self._index_file(path)
        return len(self.docs)

    def _index_file(self, path: Path) -> dict | None:
        text = extract_text(path)
        if text is None:
            return None
        doc_id = str(path.relative_to(self.root))
        chunks = chunk_text(doc_id, path.name, text)
        meta = {"name": path.name, "chars": len(text), "chunks": len(chunks), "path": str(path)}
        self.docs[doc_id] = meta
        self.chunks.extend(chunks)
        return meta

    def add_file(self, filename: str, data: bytes) -> dict:
        safe = re.sub(r"[^\w.\- ]+", "_", filename).strip() or "upload.txt"
        dest = self.root / safe
        if dest.exists():
            stem, suffix = dest.stem, dest.suffix
            i = 1
            while dest.exists():
                dest = self.root / f"{stem}_{i}{suffix}"
                i += 1
        dest.write_bytes(data)
        self._index_file(dest)
        return self.docs[dest.name]

    def list_docs(self) -> list[dict]:
        return list(self.docs.values())

    def search(self, query: str, limit: int = 5) -> list[dict]:
        q = _tokenize(query)
        ranked = []
        for c in self.chunks:
            s = _score(q, _tokenize(c.text))
            if s > 0:
                ranked.append((s, c))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [{"score": round(s, 3), "doc": c.doc_name, "chunk_id": c.chunk_id, "text": c.text[:800]} for s, c in ranked[:limit]]

    def answer(self, question: str, limit: int = 4) -> dict:
        hits = self.search(question, limit=limit)
        if not hits:
            return {"answer": "No relevant passages found in your uploaded documents.", "sources": []}
        parts = []
        for h in hits[:3]:
            snippet = h["text"]
            if len(snippet) > 420:
                snippet = snippet[:420].rsplit(" ", 1)[0] + "…"
            parts.append(f"From {h['doc']}: {snippet}")
        return {"answer": "Based on your documents (offline retrieval):\n\n" + "\n\n".join(parts), "sources": hits}
