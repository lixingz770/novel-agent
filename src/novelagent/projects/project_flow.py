from __future__ import annotations

import re
from pathlib import Path

from ..config import AppConfig
from ..llm import LLMClient, LLMError
from ..paths import WorkspacePaths
from ..library.utils import sha1_text, utcnow, write_json, read_json
from .models import OutlineStructure, OutlineVersion, ProjectBrief


def get_role_notes_context(ws: WorkspacePaths, max_chars_per_role: int = 8000) -> str:
    """
    汇总各角色学习笔记内容，供大纲细化时作为参照。按角色名分组，每组取该角色下所有 .md 笔记并截断。
    """
    role_root = ws.library_role_notes
    if not role_root.exists():
        return ""

    parts: list[str] = []
    for role_dir in sorted(role_root.iterdir()):
        if not role_dir.is_dir():
            continue
        role_name = role_dir.name
        chunks: list[str] = []
        for p in sorted(role_dir.glob("*.md")):
            try:
                text = p.read_text(encoding="utf-8").strip()
                if text:
                    chunks.append(text)
            except Exception:  # noqa: BLE001
                continue
        if not chunks:
            continue
        combined = "\n\n---\n\n".join(chunks)
        if len(combined) > max_chars_per_role:
            combined = combined[: max_chars_per_role] + "\n\n…（已截断）"
        parts.append(f"## 角色：{role_name}\n\n{combined}")
    return "\n\n" + "\n\n".join(parts) if parts else ""


def _slugify(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", name)
    name = re.sub(r"-{2,}", "-", name).strip("-")
    return name or "project"


def project_root(ws: WorkspacePaths, project_id: str) -> Path:
    return ws.projects_root / project_id


def _ensure_project_dirs(root: Path) -> None:
    for p in [
        root,
        root / "outlines",
        root / "chapter_outlines",
        root / "drafts",
        root / "reviews",
        root / "delivery",
    ]:
        p.mkdir(parents=True, exist_ok=True)


def create_project(ws: WorkspacePaths, brief: ProjectBrief) -> str:
    project_id = f"{_slugify(brief.name)}-{sha1_text(brief.name + utcnow().isoformat())[:8]}"
    root = project_root(ws, project_id)
    _ensure_project_dirs(root)
    write_json(root / "brief.json", brief.model_dump(mode="json"))
    return project_id


def _latest_outline_version(root: Path) -> int:
    outlines_dir = root / "outlines"
    versions: list[int] = []
    for p in outlines_dir.glob("outline_v*.json"):
        m = re.match(r"outline_v(\d+)\.json$", p.name)
        if m:
            versions.append(int(m.group(1)))
    return max(versions) if versions else 0


SYSTEM_PLANNER = """你是小说编辑部的“大纲策划（Planner）”。\n
你将把客户需求转换成可执行的多层大纲。\n
输出必须是JSON，字段：logline, selling_points, world, main_characters, main_plot, pacing_plan, chapter_plan, constraints。\n
chapter_plan 为数组，每项包含：chapter（从1开始）, title, goal, conflict, hook。\n
语言用中文，条目短、具体。"""


def generate_outline(ws: WorkspacePaths, cfg: AppConfig, project_id: str, *, force: bool = False) -> Path:
    root = project_root(ws, project_id)
    _ensure_project_dirs(root)
    brief = ProjectBrief.model_validate(read_json(root / "brief.json"))

    current_v = _latest_outline_version(root)
    if current_v >= 1 and not force:
        return root / "outlines" / f"outline_v{current_v}.json"

    client = LLMClient(cfg.llm)
    structure: OutlineStructure
    if client.is_configured():
        user = (
            f"【客户需求】\n{brief.model_dump()}\n\n"
            "请生成总大纲v1，并规划章节（可先给10-30章的粗略规划；若长度更长可按卷/篇章分组也行）。"
        )
        try:
            data = client.chat_json(system=SYSTEM_PLANNER, user=user, json_schema_hint="outline json")
            structure = OutlineStructure.model_validate(data)
        except LLMError:
            structure = _fallback_outline(brief)
    else:
        structure = _fallback_outline(brief)

    v = 1
    outline = OutlineVersion(
        project_id=project_id,
        version=v,
        created_at=utcnow(),
        based_on_version=None,
        change_log=["v1 初稿生成"],
        structure=structure,
    )
    out_json = root / "outlines" / f"outline_v{v}.json"
    out_md = root / "outlines" / f"outline_v{v}.md"
    write_json(out_json, outline.model_dump(mode="json"))
    out_md.write_text(_outline_to_markdown(outline), encoding="utf-8")
    return out_json


def revise_outline(ws: WorkspacePaths, cfg: AppConfig, project_id: str, feedback: str) -> Path:
    root = project_root(ws, project_id)
    _ensure_project_dirs(root)

    current_v = _latest_outline_version(root)
    if current_v <= 0:
        raise ValueError("No outline yet. Run outline first.")

    prev = OutlineVersion.model_validate(read_json(root / "outlines" / f"outline_v{current_v}.json"))
    brief = ProjectBrief.model_validate(read_json(root / "brief.json"))

    client = LLMClient(cfg.llm)
    structure: OutlineStructure
    if client.is_configured():
        user = (
            f"【客户需求】\n{brief.model_dump()}\n\n"
            f"【上一版大纲 v{prev.version}】\n{prev.structure.model_dump()}\n\n"
            f"【客户反馈】\n{feedback}\n\n"
            "请基于反馈修订大纲，输出修订后的JSON（同字段）。并确保章节规划与约束一致。"
        )
        try:
            data = client.chat_json(system=SYSTEM_PLANNER, user=user, json_schema_hint="outline json")
            structure = OutlineStructure.model_validate(data)
        except LLMError:
            structure = prev.structure
    else:
        structure = prev.structure

    new_v = current_v + 1
    outline = OutlineVersion(
        project_id=project_id,
        version=new_v,
        created_at=utcnow(),
        based_on_version=prev.version,
        change_log=[f"基于客户反馈修订：{feedback[:120]}"],
        structure=structure,
    )
    out_json = root / "outlines" / f"outline_v{new_v}.json"
    out_md = root / "outlines" / f"outline_v{new_v}.md"
    write_json(out_json, outline.model_dump(mode="json"))
    out_md.write_text(_outline_to_markdown(outline), encoding="utf-8")
    return out_json


SYSTEM_REFINER = """你是小说编辑部的“大纲汇总（Refiner）”。
你手上有：1）当前项目总大纲（JSON）；2）编辑部各角色的学习笔记（来自对参考作品的提炼）。
请根据这些角色笔记中的风格规律、可复用模板与约束，细化并修订总大纲，使章节规划、人物、节奏、卖点等更符合学习笔记中的方法。
输出必须是 JSON，与输入大纲同结构：logline, selling_points, world, main_characters, main_plot, pacing_plan, chapter_plan, constraints。
chapter_plan 为数组，每项包含：chapter（从1开始）, title, goal, conflict, hook。
语言用中文，条目短、具体。不要删减客户需求要点，只做细化与风格统一。"""


def generate_outline_refined_by_roles(ws: WorkspacePaths, cfg: AppConfig, project_id: str) -> Path:
    """
    在已有总大纲（若无则先生成 v1）基础上，根据各角色学习笔记让 AI 细化/汇总，生成新版本大纲。
    """
    root = project_root(ws, project_id)
    _ensure_project_dirs(root)
    current_v = _latest_outline_version(root)
    if current_v <= 0:
        generate_outline(ws, cfg, project_id, force=False)
        current_v = _latest_outline_version(root)
    prev_path = root / "outlines" / f"outline_v{current_v}.json"
    prev = OutlineVersion.model_validate(read_json(prev_path))
    brief = ProjectBrief.model_validate(read_json(root / "brief.json"))

    role_context = get_role_notes_context(ws)
    if not role_context.strip():
        return prev_path

    client = LLMClient(cfg.llm)
    structure: OutlineStructure
    if client.is_configured():
        user = (
            f"【客户需求】\n{brief.model_dump()}\n\n"
            f"【当前总大纲 v{prev.version}】\n{prev.structure.model_dump()}\n\n"
            "【编辑部各角色学习笔记（参照文本）】\n"
            f"{role_context}\n\n"
            "请根据上述角色笔记，细化并修订总大纲，输出修订后的 JSON（同字段）。"
        )
        try:
            data = client.chat_json(system=SYSTEM_REFINER, user=user, json_schema_hint="outline json")
            structure = OutlineStructure.model_validate(data)
        except LLMError:
            structure = prev.structure
    else:
        structure = prev.structure

    new_v = current_v + 1
    outline = OutlineVersion(
        project_id=project_id,
        version=new_v,
        created_at=utcnow(),
        based_on_version=prev.version,
        change_log=[f"基于角色学习笔记细化汇总（v{prev.version} → v{new_v}）"],
        structure=structure,
    )
    out_json = root / "outlines" / f"outline_v{new_v}.json"
    out_md = root / "outlines" / f"outline_v{new_v}.md"
    write_json(out_json, outline.model_dump(mode="json"))
    out_md.write_text(_outline_to_markdown(outline), encoding="utf-8")
    return out_json


def approve_outline(ws: WorkspacePaths, project_id: str, version: int) -> None:
    """记录用户已确认的大纲版本，便于后续仅在有确认时生成正文。"""
    root = project_root(ws, project_id)
    if not root.exists():
        raise ValueError("Project not found")
    path = root / "outline_approved.json"
    write_json(path, {"version": version, "approved_at": utcnow().isoformat()})


def get_approved_outline_version(ws: WorkspacePaths, project_id: str) -> int | None:
    """返回该项目已确认的大纲版本号，未确认返回 None。"""
    root = project_root(ws, project_id)
    path = root / "outline_approved.json"
    if not path.exists():
        return None
    data = read_json(path)
    return int(data.get("version", 0)) or None


def generate_chapter_outlines(ws: WorkspacePaths, cfg: AppConfig, project_id: str) -> Path:
    root = project_root(ws, project_id)
    _ensure_project_dirs(root)
    current_v = _latest_outline_version(root)
    if current_v <= 0:
        raise ValueError("No outline yet. Run outline first.")

    outline = OutlineVersion.model_validate(read_json(root / "outlines" / f"outline_v{current_v}.json"))
    chapters = outline.structure.chapter_plan
    out_dir = root / "chapter_outlines"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_index: list[dict] = []
    for c in chapters:
        chapter_no = int(c.get("chapter", 0) or 0)
        if chapter_no <= 0:
            continue
        md_path = out_dir / f"chapter_{chapter_no:03d}.md"
        md_path.write_text(_chapter_outline_md(outline, c), encoding="utf-8")
        out_index.append({"chapter": chapter_no, "file": str(md_path.name), "title": c.get("title", "")})

    index_path = out_dir / "index.json"
    write_json(index_path, {"project_id": project_id, "outline_version": current_v, "chapters": out_index})
    return index_path


def _fallback_outline(brief: ProjectBrief) -> OutlineStructure:
    return OutlineStructure(
        logline=f"（模板）围绕“{brief.genre or '题材待定'}”的主角成长与冲突升级故事。",
        selling_points=["强钩子开篇", "明确爽点与情绪曲线", "人设稳定", "章末留钩子"],
        world=["世界观：补充时代/地点/规则", "核心矛盾：补充对抗结构"],
        main_characters=[
            {"name": "主角", "want": "目标", "need": "成长", "flaw": "弱点"},
            {"name": "对手/反派", "want": "目标", "method": "手段"},
        ],
        main_plot=["开篇钩子", "进入主线任务", "连续升级", "高潮对决", "收束与余味"],
        pacing_plan=["前3章快节奏建立卖点", "中段拉扯与反转", "末段连续高潮并回收伏笔"],
        chapter_plan=[
            {"chapter": 1, "title": "钩子", "goal": "建立卖点", "conflict": "引爆矛盾", "hook": "抛出更大问题"},
            {"chapter": 2, "title": "任务", "goal": "进入主线", "conflict": "代价显现", "hook": "新障碍"},
            {"chapter": 3, "title": "升级", "goal": "首次胜利/失败", "conflict": "对手出手", "hook": "反转"},
        ],
        constraints=[*(brief.taboo or []), *(brief.must_have or [])],
    )


def _outline_to_markdown(outline: OutlineVersion) -> str:
    s = outline.structure
    lines: list[str] = []
    lines.append(f"## 总大纲 v{outline.version}（{outline.project_id}）")
    lines.append("")
    lines.append(f"- 生成时间：{outline.created_at.isoformat()}")
    if outline.based_on_version:
        lines.append(f"- 基于版本：v{outline.based_on_version}")
    if outline.change_log:
        lines.append("- 变更记录：")
        for x in outline.change_log:
            lines.append(f"  - {x}")
    lines.append("")
    lines.append("### Logline")
    lines.append(s.logline or "")
    lines.append("")
    lines.append("### 卖点")
    lines.extend([f"- {x}" for x in s.selling_points] or ["- （待补充）"])
    lines.append("")
    lines.append("### 世界观")
    lines.extend([f"- {x}" for x in s.world] or ["- （待补充）"])
    lines.append("")
    lines.append("### 主要角色")
    if s.main_characters:
        for c in s.main_characters:
            lines.append(f"- {c.get('name','角色')}: {c}")
    else:
        lines.append("- （待补充）")
    lines.append("")
    lines.append("### 主线剧情（阶段）")
    lines.extend([f"- {x}" for x in s.main_plot] or ["- （待补充）"])
    lines.append("")
    lines.append("### 节奏计划")
    lines.extend([f"- {x}" for x in s.pacing_plan] or ["- （待补充）"])
    lines.append("")
    lines.append("### 章节规划（粗略）")
    for c in s.chapter_plan:
        lines.append(
            f"- 第{c.get('chapter')}章《{c.get('title','')}》：目标={c.get('goal','')}；冲突={c.get('conflict','')}；钩子={c.get('hook','')}"
        )
    lines.append("")
    lines.append("### 约束/禁忌")
    lines.extend([f"- {x}" for x in s.constraints] or ["- （无）"])
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def _chapter_outline_md(outline: OutlineVersion, c: dict) -> str:
    lines: list[str] = []
    lines.append(f"## 第{c.get('chapter')}章《{c.get('title','')}》")
    lines.append("")
    lines.append(f"- 来源总纲：v{outline.version}")
    lines.append(f"- 本章目标：{c.get('goal','')}")
    lines.append(f"- 核心冲突：{c.get('conflict','')}")
    lines.append(f"- 章末钩子：{c.get('hook','')}")
    lines.append("")
    lines.append("### 场景Beat（待Writer细化）")
    lines.append("- 场景1：")
    lines.append("- 场景2：")
    lines.append("- 场景3：")
    lines.append("")
    return "\n".join(lines).strip() + "\n"

