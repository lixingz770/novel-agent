from __future__ import annotations

from pathlib import Path

from ..config import AppConfig
from ..llm import LLMClient, LLMError
from ..paths import WorkspacePaths
from .models import LearningNote
from .utils import read_jsonl, sha1_text, utcnow, write_json


SYSTEM_PROMPT = """你是小说编辑部的“编辑研究员（Analyst）”。\n
目标：从给定的小说文本片段中，提炼可复用的写作规律，并输出结构化学习笔记（JSON）。\n
要求：\n- 更关注“可迁移的方法/规律”，而不是复述剧情。\n- 语言用中文。\n- 本次需要“内容充分”：请让 short_summary 与各条目合计尽量详细（后续会用于写作与审校）。\n- 如果信息不足，允许留空列表。\n"""


def _fallback_note(source_id: str, chunks_text: str) -> LearningNote:
    # 无LLM配置时的降级：给一个可编辑模板 + 统计摘要
    preview = chunks_text[:800].strip()
    note_id = sha1_text(f"note:{source_id}:{utcnow().isoformat()}")[:16]
    return LearningNote(
        note_id=note_id,
        source_id=source_id,
        created_at=utcnow(),
        style_tags=["待补充"],
        dos=["补充：本书的强项是什么（叙述/人物/节奏/爽点）"],
        donts=["补充：本书的常见问题或雷点（拖沓/人设飘/设定漏洞）"],
        plot_devices=["补充：常用桥段/反转/钩子类型"],
        character_arcs=["补充：主角弧线/关键关系变化"],
        pacing_notes=["补充：开篇钩子、转折点、高潮位置大致分布"],
        dialog_notes=["补充：对白占比、口头禅、冲突对话写法"],
        scene_notes=["补充：场景描写密度、感官细节、意象偏好"],
        taboo_or_risks=["补充：敏感点/侵权风险/同质化风险"],
        short_summary=f"（降级模板）文本预览：{preview}",
        example_chunk_ids=[],
    )


def analyze_source(
    ws: WorkspacePaths,
    cfg: AppConfig,
    source_id: str,
    *,
    force: bool = False,
    min_chars: int = 3000,
) -> Path:
    out_json = ws.library_notes / f"{source_id}.note.json"
    out_md = ws.library_notes / f"{source_id}.note.md"
    if out_json.exists() and out_md.exists() and not force:
        return out_json

    chunks_path = ws.library_chunks / f"{source_id}.jsonl"
    rows = read_jsonl(chunks_path)
    # 控制上下文：取较多片段，但仍尽量避免无限膨胀
    joined = "\n\n".join(r.get("text", "") for r in rows[:80])

    client = LLMClient(cfg.llm)
    note: LearningNote
    if client.is_configured():
        schema_hint = "LearningNote JSON: {style_tags:[], dos:[], donts:[], plot_devices:[], character_arcs:[], pacing_notes:[], dialog_notes:[], scene_notes:[], taboo_or_risks:[], short_summary:string, example_chunk_ids:[]}"
        user = (
            "请基于下列小说文本片段，输出结构化学习笔记JSON。"
            "字段包括：style_tags, dos, donts, plot_devices, character_arcs, pacing_notes, dialog_notes, scene_notes, taboo_or_risks, short_summary, example_chunk_ids。\n"
            f"强制要求：short_summary 必须足够长且可复用（至少 {min_chars} 字符左右），并包含分节："
            "①风格指纹 ②叙事结构/节奏 ③人物与冲突 ④桥段与钩子 ⑤可复用写作方法 ⑥易踩坑与雷点。\n\n"
            f"【文本片段】\n{joined}"
        )
        try:
            data = client.chat_json(system=SYSTEM_PROMPT, user=user, json_schema_hint=schema_hint)
            note_id = sha1_text(f"note:{source_id}:{utcnow().isoformat()}")[:16]
            note = LearningNote(
                note_id=note_id,
                source_id=source_id,
                created_at=utcnow(),
                **{k: v for k, v in data.items() if k in LearningNote.model_fields},
            )
        except LLMError:
            note = _fallback_note(source_id, joined)
    else:
        note = _fallback_note(source_id, joined)

    # Always try to expand short_summary when LLM is configured
    if client.is_configured() and len(note.short_summary or "") < min_chars:
        try:
            expanded = client.chat_text(
                system="你是小说编辑部编辑研究员。你的任务是扩写学习笔记摘要，使其更详尽可复用。",
                user=(
                    f"请把下面 short_summary 扩写到至少 {min_chars} 字符，并保持分节结构与可复用写作建议。\n\n"
                    f"【原 short_summary】\n{note.short_summary or ''}\n\n"
                    f"【补充参考文本片段】\n{joined[:7000]}"
                ),
            )
            note.short_summary = expanded.strip()
        except LLMError:
            pass

    write_json(out_json, note.model_dump(mode="json"))

    md = [
        f"## 学习笔记：{source_id}",
        "",
        f"- 生成时间：{note.created_at.isoformat()}",
        "",
        "### 风格标签",
        *[f"- {x}" for x in note.style_tags],
        "",
        "### 可复用做法（Dos）",
        *[f"- {x}" for x in note.dos],
        "",
        "### 需要避免（Don'ts）",
        *[f"- {x}" for x in note.donts],
        "",
        "### 常用桥段/装置",
        *[f"- {x}" for x in note.plot_devices],
        "",
        "### 人物弧线/关系",
        *[f"- {x}" for x in note.character_arcs],
        "",
        "### 节奏",
        *[f"- {x}" for x in note.pacing_notes],
        "",
        "### 对白",
        *[f"- {x}" for x in note.dialog_notes],
        "",
        "### 场景渲染",
        *[f"- {x}" for x in note.scene_notes],
        "",
        "### 雷点/风险",
        *[f"- {x}" for x in note.taboo_or_risks],
        "",
        "### 简短摘要",
        note.short_summary or "",
        "",
    ]
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(md).strip() + "\n", encoding="utf-8")

    return out_json

