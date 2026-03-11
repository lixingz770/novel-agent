from __future__ import annotations

from pathlib import Path

from ..paths import WorkspacePaths
from .utils import read_json, read_jsonl
from .vectorstore import LocalVectorStore, VectorRow, hashed_embedding


def build_index(ws: WorkspacePaths) -> Path:
    """
    Build/refresh local vector index from:
    - chunks (library/chunks/*.jsonl)
    - learning notes (library/notes/*.note.json)
    """
    store_path = ws.library_index / "local_vectors.npz"
    store = LocalVectorStore(store_path)

    rows: list[VectorRow] = []

    for chunk_file in sorted(ws.library_chunks.glob("*.jsonl")):
        source_id = chunk_file.stem
        for r in read_jsonl(chunk_file):
            chunk_id = str(r["chunk_id"])
            text = str(r["text"])
            rows.append(
                VectorRow(
                    id=f"chunk:{chunk_id}",
                    text=text,
                    meta={"type": "chunk", "source_id": source_id, "chunk_id": chunk_id},
                    vec=hashed_embedding(text, dim=store.dim),
                )
            )

    for note_file in sorted(ws.library_notes.glob("*.note.json")):
        source_id = note_file.name.split(".")[0]
        note = read_json(note_file)
        text = _note_to_text(note)
        rows.append(
            VectorRow(
                id=f"note:{source_id}",
                text=text,
                meta={"type": "note", "source_id": source_id, "note_file": str(note_file)},
                vec=hashed_embedding(text, dim=store.dim),
            )
        )

    # role notes (library/role_notes/<role>/<source_id>.json)
    if ws.library_role_notes.exists():
        for role_dir in sorted([p for p in ws.library_role_notes.iterdir() if p.is_dir()]):
            role = role_dir.name
            for role_note in sorted(role_dir.glob("*.json")):
                source_id = role_note.stem
                note = read_json(role_note)
                text = _role_note_to_text(note)
                rows.append(
                    VectorRow(
                        id=f"role_note:{role}:{source_id}",
                        text=text,
                        meta={"type": "role_note", "role": role, "source_id": source_id, "file": str(role_note)},
                        vec=hashed_embedding(text, dim=store.dim),
                    )
                )

    store.save(rows)
    return store_path


def _note_to_text(note: object) -> str:
    if not isinstance(note, dict):
        return str(note)
    parts: list[str] = []
    for k in [
        "short_summary",
        "style_tags",
        "dos",
        "donts",
        "plot_devices",
        "character_arcs",
        "pacing_notes",
        "dialog_notes",
        "scene_notes",
        "taboo_or_risks",
    ]:
        v = note.get(k)
        if isinstance(v, list):
            parts.append(f"{k}: " + " | ".join(str(x) for x in v))
        elif v:
            parts.append(f"{k}: {v}")
    return "\n".join(parts).strip()


def _role_note_to_text(note: object) -> str:
    if not isinstance(note, dict):
        return str(note)
    parts: list[str] = []
    for k in ["memo", "rules", "checklist", "examples"]:
        v = note.get(k)
        if isinstance(v, list):
            parts.append(f"{k}: " + " | ".join(str(x) for x in v))
        elif v:
            parts.append(f"{k}: {v}")
    return "\n".join(parts).strip()


def search_index(ws: WorkspacePaths, query: str, *, top_k: int = 8) -> list[dict]:
    store = LocalVectorStore(ws.library_index / "local_vectors.npz")
    return store.search(query, top_k=top_k)

