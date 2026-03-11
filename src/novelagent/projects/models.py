from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ProjectBrief(BaseModel):
    name: str
    genre: Optional[str] = None
    audience: Optional[str] = None
    length_words: Optional[int] = None
    tone: Optional[str] = None
    pov: Optional[str] = None
    taboo: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    must_have: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    delivery: Optional[str] = "markdown"
    extra: dict[str, Any] = Field(default_factory=dict)


class OutlineStructure(BaseModel):
    logline: Optional[str] = None
    selling_points: list[str] = Field(default_factory=list)
    world: list[str] = Field(default_factory=list)
    main_characters: list[dict[str, Any]] = Field(default_factory=list)
    main_plot: list[str] = Field(default_factory=list)
    pacing_plan: list[str] = Field(default_factory=list)
    chapter_plan: list[dict[str, Any]] = Field(default_factory=list)  # [{chapter:int,title:str,goal:str,conflict:str,hook:str}]
    constraints: list[str] = Field(default_factory=list)


class OutlineVersion(BaseModel):
    project_id: str
    version: int
    created_at: datetime
    based_on_version: Optional[int] = None
    change_log: list[str] = Field(default_factory=list)
    structure: OutlineStructure = Field(default_factory=OutlineStructure)

