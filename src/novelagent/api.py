from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import load_config
from .library.utils import read_json, write_json
from .paths import WorkspacePaths
from .projects import (
    ProjectBrief,
    create_project,
    approve_outline as approve_outline_impl,
    get_approved_outline_version,
)
from .projects.models import OutlineVersion
from .projects.project_flow import (
    generate_chapter_outlines,
    generate_outline,
    generate_outline_refined_by_roles,
    project_root,
)
from .writing.writer import write_chapter


cfg = load_config()
ws = WorkspacePaths(root=Path(cfg.workspace))

app = FastAPI(title="NovelAgent Web API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "workspace": str(ws.root),
    }


@app.get("/projects")
def list_projects() -> list[dict[str, Any]]:
    if not ws.projects_root.exists():
        return []

    items: list[dict[str, Any]] = []
    for p in sorted(ws.projects_root.iterdir()):
        if not p.is_dir():
            continue
        brief_path = p / "brief.json"
        if not brief_path.exists():
            continue
        brief = ProjectBrief.model_validate(read_json(brief_path))
        items.append(
            {
                "id": p.name,
                "name": brief.name,
                "genre": brief.genre,
                "audience": brief.audience,
                "tone": brief.tone,
            }
        )
    return items


@app.post("/projects")
def create_project_api(brief: ProjectBrief) -> dict[str, Any]:
    """
    创建新项目：接收 ProjectBrief，落盘 brief.json 并返回项目ID。
    """
    ws.projects_root.mkdir(parents=True, exist_ok=True)
    project_id = create_project(ws, brief)
    return {"id": project_id, "brief": brief.model_dump()}


@app.post("/projects/{project_id}/brief/update")
def update_project_brief(
    project_id: str,
    body: dict[str, Any] | None = Body(default=None),
) -> dict[str, Any]:
    """
    更新项目 brief.json（用于“任务与设定”页面）。
    - 只更新请求体中出现的字段
    - 支持 extra 合并（浅合并）
    """
    root = project_root(ws, project_id)
    brief_path = root / "brief.json"
    if not brief_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    current = read_json(brief_path)
    incoming = body or {}

    merged = dict(current)
    for k, v in incoming.items():
        if k == "extra" and isinstance(v, dict):
            cur_extra = merged.get("extra")
            if not isinstance(cur_extra, dict):
                cur_extra = {}
            merged["extra"] = {**cur_extra, **v}
        else:
            merged[k] = v

    brief = ProjectBrief.model_validate(merged)
    write_json(brief_path, brief.model_dump())
    return {"id": project_id, "brief": brief.model_dump()}


@app.get("/projects/{project_id}")
def get_project(project_id: str) -> dict[str, Any]:
    root = project_root(ws, project_id)
    brief_path = root / "brief.json"
    if not brief_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    brief = ProjectBrief.model_validate(read_json(brief_path))
    outlines_dir = root / "outlines"
    latest_outline_path: Path | None = None
    if outlines_dir.exists():
        outlines = sorted(outlines_dir.glob("outline_v*.json"))
        if outlines:
            latest_outline_path = outlines[-1]

    latest_outline: dict[str, Any] | None = None
    if latest_outline_path is not None:
        outline = OutlineVersion.model_validate(read_json(latest_outline_path))
        latest_outline = {
            "version": outline.version,
            "created_at": outline.created_at.isoformat(),
            "logline": outline.structure.logline,
        }

    approved = get_approved_outline_version(ws, project_id)
    return {
        "id": project_id,
        "brief": brief.model_dump(),
        "latest_outline": latest_outline,
        "approved_outline_version": approved,
    }


@app.get("/projects/{project_id}/outlines/{version}")
def get_outline_content(project_id: str, version: int) -> dict[str, Any]:
    """返回指定版本大纲的完整内容（markdown 与 structure）。"""
    root = project_root(ws, project_id)
    md_path = root / "outlines" / f"outline_v{version}.md"
    json_path = root / "outlines" / f"outline_v{version}.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Outline version not found")
    outline = OutlineVersion.model_validate(read_json(json_path))
    md_content = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
    return {
        "version": outline.version,
        "created_at": outline.created_at.isoformat(),
        "structure": outline.structure.model_dump(),
        "markdown": md_content,
    }


@app.get("/projects/{project_id}/outlines")
def list_outlines(project_id: str) -> list[dict[str, Any]]:
    root = project_root(ws, project_id)
    outlines_dir = root / "outlines"
    if not outlines_dir.exists():
        return []

    items: list[dict[str, Any]] = []
    for p in sorted(outlines_dir.glob("outline_v*.json")):
        outline = OutlineVersion.model_validate(read_json(p))
        items.append(
            {
                "version": outline.version,
                "created_at": outline.created_at.isoformat(),
                "file": p.name,
            }
        )
    return items


@app.get("/projects/{project_id}/chapter-outlines")
def get_chapter_outlines(project_id: str) -> dict[str, Any] | None:
    """获取已生成的分章大纲索引（若存在）。"""
    root = project_root(ws, project_id)
    index_path = root / "chapter_outlines" / "index.json"
    if not index_path.exists():
        return None
    return read_json(index_path)


@app.post("/projects/{project_id}/chapter-outlines")
def ensure_chapter_outlines(project_id: str) -> dict[str, Any]:
    root = project_root(ws, project_id)
    if not root.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    index_path = generate_chapter_outlines(ws, cfg, project_id)
    data = read_json(index_path)
    return data


@app.post("/projects/{project_id}/chapters/{chapter}/draft")
def generate_chapter_draft(project_id: str, chapter: int) -> dict[str, Any]:
    root = project_root(ws, project_id)
    if not root.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    draft_path = write_chapter(ws, cfg, project_id, chapter)
    text = draft_path.read_text(encoding="utf-8")
    return {
        "path": str(draft_path),
        "content": text,
    }


@app.post("/projects/{project_id}/outline")
def generate_project_outline(project_id: str) -> dict[str, Any]:
    """根据客户需求生成初步总大纲（v1）。"""
    root = project_root(ws, project_id)
    if not root.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    out_path = generate_outline(ws, cfg, project_id, force=False)
    outline = OutlineVersion.model_validate(read_json(out_path))
    return {
        "file": out_path.name,
        "version": outline.version,
        "created_at": outline.created_at.isoformat(),
        "structure": outline.structure.model_dump(),
    }


@app.post("/projects/{project_id}/outline/refine-with-roles")
def refine_outline_with_roles(project_id: str) -> dict[str, Any]:
    """在现有总大纲基础上，结合各角色学习笔记由 AI 细化并汇总，生成新版本大纲。"""
    root = project_root(ws, project_id)
    if not root.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    out_path = generate_outline_refined_by_roles(ws, cfg, project_id)
    outline = OutlineVersion.model_validate(read_json(out_path))
    md_path = root / "outlines" / f"outline_v{outline.version}.md"
    md_content = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
    return {
        "file": out_path.name,
        "version": outline.version,
        "created_at": outline.created_at.isoformat(),
        "structure": outline.structure.model_dump(),
        "markdown": md_content,
    }


@app.post("/projects/{project_id}/approve-outline")
def approve_outline_api(
    project_id: str,
    body: dict[str, Any] | None = Body(default=None),
) -> dict[str, Any]:
    """用户确认大纲版本。请求体可传 {"version": number}，不传则使用当前最新版本。"""
    root = project_root(ws, project_id)
    if not root.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    version = (body or {}).get("version")
    if version is None:
        outlines_dir = root / "outlines"
        if not outlines_dir.exists():
            raise HTTPException(status_code=400, detail="No outline to approve")
        versions = sorted(
            int(p.stem.replace("outline_v", ""))
            for p in outlines_dir.glob("outline_v*.json")
        )
        if not versions:
            raise HTTPException(status_code=400, detail="No outline to approve")
        version = versions[-1]
    else:
        version = int(version)
    approve_outline_impl(ws, project_id, version)
    return {"approved_version": version}


@app.get("/library/role-notes")
def list_roles() -> list[dict[str, Any]]:
    root = ws.library_role_notes
    if not root.exists():
        return []

    roles: list[dict[str, Any]] = []
    for role_dir in sorted(root.iterdir()):
        if not role_dir.is_dir():
            continue
        md_count = len(list(role_dir.glob("*.md")))
        json_count = len(list(role_dir.glob("*.json")))
        roles.append(
            {
                "role": role_dir.name,
                "md_count": md_count,
                "json_count": json_count,
            }
        )
    return roles


@app.get("/library/role-notes/{role}")
def list_role_notes(role: str) -> list[dict[str, Any]]:
    role_dir = ws.library_role_notes / role
    if not role_dir.exists():
        raise HTTPException(status_code=404, detail="Role not found")

    items: list[dict[str, Any]] = []
    for p in sorted(role_dir.glob("*.md")):
        items.append(
            {
                "id": p.stem,
                "file": p.name,
            }
        )
    return items


@app.get("/library/role-notes/{role}/{note_id}")
def get_role_note(role: str, note_id: str) -> dict[str, Any]:
    path = ws.library_role_notes / role / f"{note_id}.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Note not found")
    content = path.read_text(encoding="utf-8")
    return {
        "role": role,
        "id": note_id,
        "content": content,
    }

