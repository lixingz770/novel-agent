from __future__ import annotations

from pathlib import Path

from ..config import AppConfig
from ..editors import run_editorial_board
from ..library.index import search_index
from ..library.utils import read_json, sha1_text, utcnow
from ..llm import LLMClient, LLMError
from ..paths import WorkspacePaths
from ..projects.models import OutlineVersion, ProjectBrief


SYSTEM_WRITER = """你是小说编辑部的“写手（Writer）”。\n
你必须严格遵守：客户需求、总纲/本章大纲、以及“学习参照约束包”。\n
写作要求：\n- 中文\n- 每章以明确冲突推进\n- 多用动作/对话推动，少说教\n- 章末必须有钩子\n- 避免雷点与禁忌\n"""


def _project_root(ws: WorkspacePaths, project_id: str) -> Path:
    return ws.projects_root / project_id


def _latest_outline_path(root: Path) -> Path:
    outlines = sorted(root.joinpath("outlines").glob("outline_v*.json"))
    if not outlines:
        raise ValueError("No outline found. Run novelagent outline first.")
    return outlines[-1]


def _chapter_outline_path(root: Path, chapter: int) -> Path:
    p = root / "chapter_outlines" / f"chapter_{chapter:03d}.md"
    if not p.exists():
        raise ValueError("No chapter outline found. Run novelagent chapter-outlines first.")
    return p


def _build_retrieval_query(brief: ProjectBrief, chapter_md: str) -> str:
    parts = [
        brief.genre or "",
        brief.tone or "",
        brief.audience or "",
        "写作方法",
        "节奏",
        "对话",
        "场景渲染",
        chapter_md[:400],
    ]
    return "\n".join([p for p in parts if p]).strip()


def write_chapter(ws: WorkspacePaths, cfg: AppConfig, project_id: str, chapter: int) -> Path:
    root = _project_root(ws, project_id)
    brief = ProjectBrief.model_validate(read_json(root / "brief.json"))
    outline = OutlineVersion.model_validate(read_json(_latest_outline_path(root)))
    chapter_md_path = _chapter_outline_path(root, chapter)
    chapter_md = chapter_md_path.read_text(encoding="utf-8")

    query = _build_retrieval_query(brief, chapter_md)
    refs = search_index(ws, query, top_k=cfg.retrieval.top_k)

    ref_text = "\n\n".join(
        [
            f"- REF {i+1}: {r['id']} score={r['score']:.3f}\n  meta={r['meta']}\n  preview={r['text_preview']}"
            for i, r in enumerate(refs)
        ]
    )

    memos = run_editorial_board(ws, cfg, project_id=project_id, chapter=chapter, chapter_outline_md=chapter_md)
    constraint_pack = _constraint_pack_from_refs(
        refs,
        taboo=brief.taboo,
        must_have=brief.must_have,
        editorial_memos=memos,
    )

    client = LLMClient(cfg.llm)
    if client.is_configured():
        user = (
            f"【客户Brief】\n{brief.model_dump()}\n\n"
            f"【总纲（最新 v{outline.version}）】\n{outline.structure.model_dump()}\n\n"
            f"【本章大纲】\n{chapter_md}\n\n"
            f"【学习参照约束包】\n{constraint_pack}\n\n"
            "请生成本章正文（建议1500-2500字，按需要调整），并确保章末留钩子。"
        )
        try:
            text = client.chat_text(system=SYSTEM_WRITER, user=user)
        except LLMError:
            text = _fallback_draft(chapter_md, constraint_pack)
    else:
        text = _fallback_draft(chapter_md, constraint_pack)

    draft_id = sha1_text(f"{project_id}:{chapter}:{utcnow().isoformat()}")[:10]
    out = root / "drafts" / f"chapter_{chapter:03d}_{draft_id}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        _format_draft_md(project_id, outline.version, chapter, refs, constraint_pack, text),
        encoding="utf-8",
    )
    return out


def _constraint_pack_from_refs(
    refs: list[dict],
    *,
    taboo: list[str],
    must_have: list[str],
    editorial_memos: dict[str, str],
) -> str:
    lines: list[str] = []
    if taboo:
        lines.append("【禁忌/雷点】")
        lines.extend([f"- {x}" for x in taboo])
        lines.append("")
    if must_have:
        lines.append("【必须包含】")
        lines.extend([f"- {x}" for x in must_have])
        lines.append("")
    if editorial_memos:
        lines.append("【编辑部备忘录（多角色协作）】")
        for role, memo in editorial_memos.items():
            lines.append(f"- {role}: {memo}")
        lines.append("")
    lines.append("【学习参照（检索命中摘要）】")
    for r in refs:
        lines.append(f"- {r['id']}: {r['text_preview']}")
    return "\n".join(lines).strip()


def _fallback_draft(chapter_md: str, constraint_pack: str) -> str:
    return (
        "（降级草稿模板：未配置大模型）\n\n"
        f"【本章大纲】\n{chapter_md}\n\n"
        f"【约束包】\n{constraint_pack}\n\n"
        "正文：\n- 场景1：\n- 场景2：\n- 场景3：\n\n"
        "章末钩子：\n- （写一个让读者必须点下一章的问题/危机/反转）\n"
    )


def _format_draft_md(
    project_id: str,
    outline_version: int,
    chapter: int,
    refs: list[dict],
    constraint_pack: str,
    text: str,
) -> str:
    lines: list[str] = []
    lines.append(f"## 章节正文（项目 {project_id}）")
    lines.append("")
    lines.append(f"- 章节：第{chapter}章")
    lines.append(f"- 总纲版本：v{outline_version}")
    lines.append(f"- 生成时间：{utcnow().isoformat()}")
    lines.append("")
    lines.append("### 引用清单（UsedNotes/UsedChunks）")
    for r in refs:
        lines.append(f"- {r['id']} score={r['score']:.3f} meta={r['meta']}")
    if not refs:
        lines.append("- （无）")
    lines.append("")
    lines.append("### 约束清单（ConstraintPack）")
    lines.append("```")
    lines.append(constraint_pack)
    lines.append("```")
    lines.append("")
    lines.append("### 正文")
    lines.append(text.strip())
    lines.append("")
    return "\n".join(lines)

