from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from ..library.utils import utcnow, write_json
from ..paths import WorkspacePaths


@dataclass(frozen=True)
class PackageResult:
    folder: Path
    zip_path: Path


def package_project(ws: WorkspacePaths, project_id: str) -> PackageResult:
    root = ws.projects_root / project_id
    if not root.exists():
        raise ValueError(f"Project not found: {project_id}")

    ts = utcnow().strftime("%Y%m%d_%H%M%S")
    delivery_root = root / "delivery"
    delivery_root.mkdir(parents=True, exist_ok=True)
    out_folder = delivery_root / f"package_{ts}"
    out_folder.mkdir(parents=True, exist_ok=True)

    manifest: dict = {"project_id": project_id, "created_at": utcnow().isoformat(), "files": []}

    def copy_tree(src: Path, dst: Path) -> None:
        if not src.exists():
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)

    # brief
    copy_tree(root / "brief.json", out_folder / "brief.json")

    # outlines (all versions)
    copy_tree(root / "outlines", out_folder / "outlines")

    # chapter outlines
    copy_tree(root / "chapter_outlines", out_folder / "chapter_outlines")

    # drafts + reviews
    copy_tree(root / "drafts", out_folder / "drafts")
    copy_tree(root / "reviews", out_folder / "reviews")

    # write manifest
    for p in sorted(out_folder.rglob("*")):
        if p.is_file():
            manifest["files"].append(str(p.relative_to(out_folder)))
    write_json(out_folder / "manifest.json", manifest)

    # zip
    zip_path = delivery_root / f"package_{ts}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(out_folder.rglob("*")):
            if p.is_file():
                zf.write(p, arcname=str(p.relative_to(out_folder)))

    return PackageResult(folder=out_folder, zip_path=zip_path)

