from __future__ import annotations

from .models import TextChunk
from .utils import sha1_text


def chunk_text(
    *,
    source_id: str,
    text: str,
    max_chars: int,
    overlap_chars: int,
) -> list[TextChunk]:
    if max_chars <= 0:
        raise ValueError("max_chars must be > 0")
    if overlap_chars < 0:
        raise ValueError("overlap_chars must be >= 0")
    if overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be < max_chars")

    chunks: list[TextChunk] = []
    n = len(text)
    start = 0
    idx = 0
    while start < n:
        end = min(n, start + max_chars)
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunk_id = sha1_text(f"{source_id}:{idx}:{start}:{end}:{chunk_text[:32]}")[:20]
            chunks.append(
                TextChunk(
                    chunk_id=chunk_id,
                    source_id=source_id,
                    idx=idx,
                    text=chunk_text,
                    start_char=start,
                    end_char=end,
                )
            )
            idx += 1
        if end >= n:
            break
        start = max(0, end - overlap_chars)
    return chunks

