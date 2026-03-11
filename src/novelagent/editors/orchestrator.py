from __future__ import annotations

from pathlib import Path

from ..config import AppConfig
from ..library.index import search_index
from ..library.utils import read_json, utcnow, write_json
from ..llm import LLMClient
from ..paths import WorkspacePaths
from ..projects.models import OutlineVersion, ProjectBrief
from .roles import (
    character_manager,
    copy_editor,
    dialog_writer,
    emotion_director,
    hype_engineer,
    logic_proofreader,
    producer,
    scene_renderer,
)


def run_editorial_board(
    ws: WorkspacePaths,
    cfg: AppConfig,
    *,
    project_id: str,
    chapter: int,
    chapter_outline_md: str,
) -> dict[str, str]:
    """
    Simulate an editorial department: producer coordinates multiple specialized roles.
    Returns role->memo.
    Also persists memos to projects/<id>/artifacts/editorial_board/.
    """
    root = ws.projects_root / project_id
    brief = ProjectBrief.model_validate(read_json(root / "brief.json"))
    outlines = sorted(root.joinpath("outlines").glob("outline_v*.json"))
    outline = OutlineVersion.model_validate(read_json(outlines[-1])) if outlines else None

    query = "\n".join(
        [
            brief.genre or "",
            brief.tone or "",
            "爽点",
            "情绪",
            "对话",
            chapter_outline_md[:500],
        ]
    ).strip()
    refs = search_index(ws, query, top_k=min(6, cfg.retrieval.top_k))

    context = "\n\n".join(
        [
            f"【项目】{project_id} 第{chapter}章",
            f"【Brief】{brief.model_dump()}",
            f"【总纲】{outline.structure.model_dump() if outline else ''}",
            f"【本章大纲】\n{chapter_outline_md}",
            "【学习参照命中】\n"
            + "\n".join([f"- {r['id']} score={r['score']:.3f} {r['text_preview']}" for r in refs]),
        ]
    )

    client = LLMClient(cfg.llm)

    results = [
        producer(client, context),
        character_manager(client, context),
        copy_editor(client, context),
        hype_engineer(client, context),
        emotion_director(client, context),
        scene_renderer(client, context),
        dialog_writer(client, context),
        logic_proofreader(client, context),
    ]

    memos = {r.role: r.memo for r in results}

    out_dir = root / "artifacts" / "editorial_board" / f"chapter_{chapter:03d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        out_dir / "memos.json",
        {"project_id": project_id, "chapter": chapter, "created_at": utcnow().isoformat(), "memos": memos},
    )
    md_lines = [f"## 编辑部备忘录（第{chapter}章）", "", f"- 生成时间：{utcnow().isoformat()}", ""]
    for role, memo in memos.items():
        md_lines.append(f"### {role}")
        md_lines.append(memo.strip())
        md_lines.append("")
    (out_dir / "memos.md").write_text("\n".join(md_lines).strip() + "\n", encoding="utf-8")

    return memos

