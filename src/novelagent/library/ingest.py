from __future__ import annotations

from pathlib import Path

from ..paths import WorkspacePaths
from .chunking import chunk_text
from .models import SourceMeta
from .utils import stable_source_id, utcnow, write_json, write_jsonl


SUPPORTED_SUFFIXES = {".txt", ".md"}


def _read_text_file(path: Path) -> str:
    # Try utf-8 first, fallback to gbk for some CN sources
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="gbk", errors="replace")


def ingest_file(ws: WorkspacePaths, path: Path, *, max_chars: int, overlap_chars: int) -> str:
    source_id = stable_source_id(path)
    raw_text = _read_text_file(path)

    raw_out = ws.library_raw / f"{source_id}.txt"
    raw_out.parent.mkdir(parents=True, exist_ok=True)
    raw_out.write_text(raw_text, encoding="utf-8")

    chunks = chunk_text(
        source_id=source_id,
        text=raw_text,
        max_chars=max_chars,
        overlap_chars=overlap_chars,
    )
    chunks_out = ws.library_chunks / f"{source_id}.jsonl"
    write_jsonl(chunks_out, [c.model_dump() for c in chunks])

    meta = SourceMeta(
        source_id=source_id,
        original_path=str(path.resolve()),
        imported_at=utcnow(),
        title=path.stem,
    )
    meta_out = ws.library_raw / f"{source_id}.meta.json"
    write_json(meta_out, meta.model_dump(mode="json"))

    return source_id


def ingest_path(ws: WorkspacePaths, path: Path, *, max_chars: int, overlap_chars: int) -> list[str]:
    if path.is_file():
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise ValueError(f"Unsupported file type: {path.suffix}")
        return [ingest_file(ws, path, max_chars=max_chars, overlap_chars=overlap_chars)]

    source_ids: list[str] = []
    for p in sorted(path.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        source_ids.append(ingest_file(ws, p, max_chars=max_chars, overlap_chars=overlap_chars))
    return source_ids

