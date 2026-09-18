"""Shared tokenization and TF-overlap scoring."""
from __future__ import annotations
import re

_TOKEN_RE = re.compile(r"[a-zA-Z0-9À-ɏ']+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def score(query_tokens: list[str], doc_tokens: list[str]) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    qset = set(query_tokens)
    dset = set(doc_tokens)
    if not (qset & dset):
        return 0.0
    tf: dict[str, int] = {}
    for t in doc_tokens:
        tf[t] = tf.get(t, 0) + 1
    total = 0.0
    for t in qset:
        if t in tf:
            total += 1.0 + min(tf[t], 8) * 0.12 + (0.25 if len(t) > 5 else 0)
    return total / (len(qset) ** 0.5)
