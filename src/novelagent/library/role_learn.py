from __future__ import annotations

from pathlib import Path

from ..config import AppConfig
from ..llm import LLMClient, LLMError
from ..paths import WorkspacePaths
from .utils import read_jsonl, sha1_text, utcnow, write_json


ROLES = [
    "主编",
    "大纲策划",
    "角色设定管",
    "文字编辑",
    "爽点工程师",
    "情绪戏导演",
    "场景渲染",
    "对话编剧",
    "逻辑审校",
]


ROLE_SYSTEM = {
    "主编": "你是小说编辑部主编。请输出可复用的编辑总规则与检查清单。",
    "大纲策划": "你是大纲策划。请输出结构设计规律、章节钩子与节奏模板。",
    "角色设定管": "你是角色设定管。请输出角色弧线、人设稳定、关系推进的方法。",
    "文字编辑": "你是文字编辑。请输出语言节奏、句式、删改原则与常见问题清单。",
    "爽点工程师": "你是爽点工程师。请输出爽点模型、打脸反转设计、爽点密度控制方法。",
    "情绪戏导演": "你是情绪戏导演。请输出情绪曲线设计、情绪转折点与共情技巧。",
    "场景渲染": "你是场景渲染。请输出场景调度、动作链与感官细节的写法规律。",
    "对话编剧": "你是对话编剧。请输出对话推动冲突、潜台词与信息投放技巧。",
    "逻辑审校": "你是逻辑审校。请输出因果链、时间线、设定一致性与伏笔回收检查清单。",
}


def generate_role_notes(
    ws: WorkspacePaths,
    cfg: AppConfig,
    source_id: str,
    *,
    force: bool = False,
    min_chars: int = 3000,
) -> list[Path]:
    """
    For each editorial role, generate a role-specific learning note (md+json) from the source chunks.
    """
    chunks_path = ws.library_chunks / f"{source_id}.jsonl"
    rows = read_jsonl(chunks_path)
    # 取样更多文本，尽量覆盖不同章节的风格特征（头/中/后）
    if not rows:
        joined = ""
    else:
        sample: list[str] = []
        n = len(rows)
        head = rows[:50]
        mid = rows[max(0, n // 2 - 15) : max(0, n // 2 + 15)]
        tail = rows[max(0, n - 30) :]
        for r in (head + mid + tail):
            t = (r.get("text", "") or "").strip()
            if t:
                sample.append(t)
        joined = "\n\n".join(sample[:120])

    client = LLMClient(cfg.llm)
    out_paths: list[Path] = []

    for role in ROLES:
        role_dir = ws.library_role_notes / role
        out_json = role_dir / f"{source_id}.json"
        out_md = role_dir / f"{source_id}.md"
        if out_json.exists() and out_md.exists() and not force:
            out_paths.append(out_md)
            continue

        note_id = sha1_text(f"role-note:{role}:{source_id}:{utcnow().isoformat()}")[:16]
        if client.is_configured():
            system = (
                f"你是小说编辑部的“{role}”。"
                + ROLE_SYSTEM.get(role, "")
                + "输出JSON: {memo:string, rules:[string], checklist:[string], examples:[string]}。"
                + f"强制要求：memo 必须是长文学习笔记，至少 {min_chars} 字符，并包含分节（用明确小标题/编号）："
                + "①你关注的维度定义 ②从文本归纳出的规律 ③可复用模板/公式 ④常见错误与修复策略 ⑤自检清单 ⑥引用示例（用原文片段概括，不要长篇复制）。"
                + "rules/checklist/examples 也要足够具体、可执行。语言中文。"
            )
            user = (
                f"基于以下小说文本片段（可能是前若干章），为你的角色提炼可复用学习笔记。\n\n"
                f"【文本片段】\n{joined}"
            )
            try:
                data = client.chat_json(system=system, user=user, json_schema_hint="role note json")
                memo = str(data.get("memo") or "").strip()
                rules = data.get("rules") or []
                checklist = data.get("checklist") or []
                examples = data.get("examples") or []
            except Exception:  # noqa: BLE001
                memo, rules, checklist, examples = _fallback_role_note(role)
        else:
            memo, rules, checklist, examples = _fallback_role_note(role)

        # Always try to expand memo when LLM is configured
        if client.is_configured() and len(memo) < min_chars:
            try:
                expanded = client.chat_text(
                    system=f"你是小说编辑部的{role}，擅长把经验写成可复用的长文笔记。",
                    user=(
                        f"请把下面 memo 扩写到至少 {min_chars} 字符，保持结构分节与可复用模板，避免空话。\n\n"
                        f"【原 memo】\n{memo}\n\n"
                        f"【补充参考文本片段】\n{joined[:7000]}"
                    ),
                )
                memo = expanded.strip()
            except LLMError:
                pass

        payload = {
            "note_id": note_id,
            "role": role,
            "source_id": source_id,
            "created_at": utcnow().isoformat(),
            "memo": memo,
            "rules": rules,
            "checklist": checklist,
            "examples": examples,
        }
        write_json(out_json, payload)

        md_lines: list[str] = []
        md_lines.append(f"## 角色学习笔记：{role}")
        md_lines.append("")
        md_lines.append(f"- source_id: {source_id}")
        md_lines.append(f"- created_at: {payload['created_at']}")
        md_lines.append("")
        md_lines.append("### Memo")
        md_lines.append(memo or "")
        md_lines.append("")
        md_lines.append("### Rules")
        for x in rules or ["（无）"]:
            md_lines.append(f"- {x}")
        md_lines.append("")
        md_lines.append("### Checklist")
        for x in checklist or ["（无）"]:
            md_lines.append(f"- {x}")
        md_lines.append("")
        md_lines.append("### Examples")
        for x in examples or ["（无）"]:
            md_lines.append(f"- {x}")
        md_lines.append("")
        role_dir.mkdir(parents=True, exist_ok=True)
        out_md.write_text("\n".join(md_lines).strip() + "\n", encoding="utf-8")
        out_paths.append(out_md)

    return out_paths


def _fallback_role_note(role: str) -> tuple[str, list[str], list[str], list[str]]:
    memo = f"（降级模板：未配置大模型）这是 {role} 的学习笔记占位。"
    rules = ["从文本中抽象出可复用规律，而非复述剧情", "条目短、可执行、可检索"]
    checklist = ["本书的强项是什么？", "本书常见问题是什么？", "有哪些可复用的段落节奏/句式？"]
    examples = ["（自行补充：贴一段你认为最能代表该角色关注点的原文）"]
    return memo, rules, checklist, examples

