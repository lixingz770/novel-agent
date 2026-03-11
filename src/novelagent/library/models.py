from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SourceMeta(BaseModel):
    source_id: str
    original_path: str
    imported_at: datetime
    title: str
    extra: dict[str, Any] = Field(default_factory=dict)


class TextChunk(BaseModel):
    chunk_id: str
    source_id: str
    idx: int
    text: str
    start_char: int
    end_char: int


class LearningNote(BaseModel):
    note_id: str
    source_id: str
    created_at: datetime

    style_tags: list[str] = Field(default_factory=list)
    dos: list[str] = Field(default_factory=list)
    donts: list[str] = Field(default_factory=list)
    plot_devices: list[str] = Field(default_factory=list)
    character_arcs: list[str] = Field(default_factory=list)
    pacing_notes: list[str] = Field(default_factory=list)
    dialog_notes: list[str] = Field(default_factory=list)
    scene_notes: list[str] = Field(default_factory=list)
    taboo_or_risks: list[str] = Field(default_factory=list)

    short_summary: Optional[str] = None
    example_chunk_ids: list[str] = Field(default_factory=list)

