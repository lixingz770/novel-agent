from __future__ import annotations

import math
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


def _tokenize(text: str) -> list[str]:
    # Very lightweight tokenizer for CN/EN mixed text
    text = text.strip().lower()
    tokens: list[str] = []
    buf: list[str] = []
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            if buf:
                tokens.append("".join(buf))
                buf = []
            tokens.append(ch)
        elif ch.isalnum():
            buf.append(ch)
        else:
            if buf:
                tokens.append("".join(buf))
                buf = []
    if buf:
        tokens.append("".join(buf))
    return [t for t in tokens if t]


def hashed_embedding(text: str, *, dim: int = 1536) -> np.ndarray:
    """
    Local, dependency-free embedding via feature hashing.
    Not as strong as real embeddings, but deterministic and fast for MVP retrieval.
    """
    vec = np.zeros((dim,), dtype=np.float32)
    tokens = _tokenize(text)
    if not tokens:
        return vec
    for t in tokens:
        digest = hashlib.sha1(t.encode("utf-8"), usedforsecurity=False).digest()
        h = int.from_bytes(digest[:8], "little", signed=False)
        idx = h % dim
        sign = 1.0 if (h & 1) == 0 else -1.0
        vec[idx] += sign
    # L2 normalize
    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec /= norm
    return vec


@dataclass
class VectorRow:
    id: str
    text: str
    meta: dict[str, Any]
    vec: np.ndarray


@dataclass
class LocalVectorStore:
    path: Path
    dim: int = 1536

    def load(self) -> list[VectorRow]:
        if not self.path.exists():
            return []
        data = np.load(self.path, allow_pickle=True)
        ids = data["ids"].tolist()
        texts = data["texts"].tolist()
        metas = data["metas"].tolist()
        vecs = data["vecs"]
        rows: list[VectorRow] = []
        for i in range(len(ids)):
            rows.append(VectorRow(id=str(ids[i]), text=str(texts[i]), meta=dict(metas[i]), vec=vecs[i]))
        return rows

    def save(self, rows: list[VectorRow]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        ids = np.array([r.id for r in rows], dtype=object)
        texts = np.array([r.text for r in rows], dtype=object)
        metas = np.array([r.meta for r in rows], dtype=object)
        vecs = np.stack([r.vec for r in rows], axis=0) if rows else np.zeros((0, self.dim), dtype=np.float32)
        np.savez(self.path, ids=ids, texts=texts, metas=metas, vecs=vecs)

    def upsert(self, rows: list[VectorRow]) -> None:
        existing = {r.id: r for r in self.load()}
        for r in rows:
            existing[r.id] = r
        self.save(list(existing.values()))

    def search(self, query: str, *, top_k: int = 8) -> list[dict[str, Any]]:
        rows = self.load()
        if not rows:
            return []
        q = hashed_embedding(query, dim=self.dim)
        vecs = np.stack([r.vec for r in rows], axis=0)
        scores = vecs @ q  # cosine because vectors are normalized
        idxs = np.argsort(-scores)[: max(1, top_k)]
        out: list[dict[str, Any]] = []
        for i in idxs:
            s = float(scores[i])
            if math.isnan(s):
                continue
            r = rows[int(i)]
            out.append({"id": r.id, "score": s, "meta": r.meta, "text_preview": r.text[:240]})
        return out

