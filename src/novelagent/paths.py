from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspacePaths:
    root: Path

    @property
    def library_root(self) -> Path:
        return self.root / "library"

    @property
    def library_raw(self) -> Path:
        return self.library_root / "raw"

    @property
    def library_chunks(self) -> Path:
        return self.library_root / "chunks"

    @property
    def library_notes(self) -> Path:
        return self.library_root / "notes"

    @property
    def library_index(self) -> Path:
        return self.library_root / "index"

    @property
    def library_role_notes(self) -> Path:
        return self.library_root / "role_notes"

    @property
    def projects_root(self) -> Path:
        return self.root / "projects"

