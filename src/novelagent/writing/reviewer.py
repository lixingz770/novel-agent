from __future__ import annotations

from pathlib import Path

from ..config import AppConfig
from ..library.utils import read_json, sha1_text, utcnow, write_json
from ..llm import LLMClient, LLMError
from ..paths import WorkspacePaths
from ..projects.models import OutlineVersion, ProjectBrief


SYSTEM_REVIEWER = """你是小说编辑部的“逻辑审校（Reviewer）”。\n
你要对章节草稿做编辑部式审校：\n- 人设一致性\n- 时间线/因果链\n- 世界观规则\n- 节奏与爽点密度\n- 对话是否推动冲突\n- 章末钩子是否有效\n\n
输出必须是JSON，字段：severity_issues, issues, suggestions, hook_check, consistency_check, revised_excerpt。\n
其中 severity_issues/issues/suggestions 为数组（每项一句话）。revised_excerpt 可为空或给出一段修订示例。"""


def _project_root(ws: WorkspacePaths, project_id: str) -> Path:
    return ws.projects_root / project_id


def _latest_outline_path(root: Path) -> Path:
    outlines = sorted(root.joinpath("outlines").glob("outline_v*.json"))
    if not outlines:
        raise ValueError("No outline found. Run novelagent outline first.")
    return outlines[-1]


def review_chapter(ws: WorkspacePaths, cfg: AppConfig, project_id: str, draft_path: Path) -> Path:
    root = _project_root(ws, project_id)
    brief = ProjectBrief.model_validate(read_json(root / "brief.json"))
    outline = OutlineVersion.model_validate(read_json(_latest_outline_path(root)))
    draft = draft_path.read_text(encoding="utf-8")

    client = LLMClient(cfg.llm)
    report: dict
    if client.is_configured():
        user = (
            f"【客户Brief】\n{brief.model_dump()}\n\n"
            f"【总纲（最新 v{outline.version}）】\n{outline.structure.model_dump()}\n\n"
            f"【章节草稿】\n{draft}\n\n"
            "请输出审校报告JSON。"
        )
        try:
            report = client.chat_json(system=SYSTEM_REVIEWER, user=user, json_schema_hint="review json")
        except LLMError:
            report = _fallback_review(draft)
    else:
        report = _fallback_review(draft)

    review_id = sha1_text(f"review:{project_id}:{draft_path.name}:{utcnow().isoformat()}")[:10]
    out_json = root / "reviews" / f"{draft_path.stem}.{review_id}.json"
    out_md = root / "reviews" / f"{draft_path.stem}.{review_id}.md"

    write_json(out_json, {"project_id": project_id, "draft": str(draft_path), "created_at": utcnow().isoformat(), "report": report})
    out_md.write_text(_format_review_md(project_id, draft_path, report), encoding="utf-8")

    return out_md


def _fallback_review(draft: str) -> dict:
    issues: list[str] = []
    if "（降级草稿模板" in draft:
        issues.append("当前为降级模板草稿，尚未生成真实正文。")
    if "章末钩子" not in draft and "钩子" not in draft:
        issues.append("章末钩子不明显：建议用危机/反转/悬念收束。")
    if "场景1" in draft and "场景2" in draft:
        issues.append("场景Beat仍是占位符：需要具体化冲突与动作链。")
    return {
        "severity_issues": [],
        "issues": issues,
        "suggestions": ["补齐冲突推进链：目标→阻碍→代价→小胜/小败→更大问题", "对白尽量承担信息与冲突，不要旁白说教"],
        "hook_check": "需要确保结尾是“必须点下一章”的问题/危机/反转。",
        "consistency_check": "（降级检查）未做世界观/人设深度一致性校验。",
        "revised_excerpt": "",
    }


def _format_review_md(project_id: str, draft_path: Path, report: dict) -> str:
    lines: list[str] = []
    lines.append(f"## 审稿报告（项目 {project_id}）")
    lines.append("")
    lines.append(f"- 草稿：{draft_path.name}")
    lines.append(f"- 生成时间：{utcnow().isoformat()}")
    lines.append("")
    lines.append("### 严重问题（Severity）")
    for x in report.get("severity_issues", []) or ["（无）"]:
        lines.append(f"- {x}")
    lines.append("")
    lines.append("### 问题列表（Issues）")
    for x in report.get("issues", []) or ["（无）"]:
        lines.append(f"- {x}")
    lines.append("")
    lines.append("### 建议（Suggestions）")
    for x in report.get("suggestions", []) or ["（无）"]:
        lines.append(f"- {x}")
    lines.append("")
    lines.append("### 钩子检查（HookCheck）")
    lines.append(str(report.get("hook_check", "")))
    lines.append("")
    lines.append("### 一致性检查（ConsistencyCheck）")
    lines.append(str(report.get("consistency_check", "")))
    lines.append("")
    if report.get("revised_excerpt"):
        lines.append("### 修订示例（RevisedExcerpt）")
        lines.append(str(report.get("revised_excerpt")))
        lines.append("")
    return "\n".join(lines).strip() + "\n"

