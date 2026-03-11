from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from ..llm import LLMClient, LLMError


@dataclass(frozen=True)
class RoleResult:
    role: str
    memo: str
    data: Optional[dict[str, Any]] = None


def _role_json(client: LLMClient, *, role: str, system: str, user: str) -> RoleResult:
    if not client.is_configured():
        return RoleResult(role=role, memo=_fallback(role))
    try:
        data = client.chat_json(system=system, user=user, json_schema_hint="json")
        memo = data.get("memo") or ""
        if not memo:
            memo = _stringify_json(data)
        return RoleResult(role=role, memo=memo, data=data)
    except LLMError:
        return RoleResult(role=role, memo=_fallback(role))


def _stringify_json(data: dict[str, Any]) -> str:
    lines: list[str] = []
    for k, v in data.items():
        lines.append(f"- {k}: {v}")
    return "\n".join(lines).strip()


def _fallback(role: str) -> str:
    templates = {
        "主编": "- 本章目标是否明确？\n- 章末钩子是否足够强？\n- 与总纲/人设是否冲突？",
        "角色设定管": "- 主角欲望/恐惧/底线是什么？\n- 本章角色关系是否有变化？\n- 口头禅/行为习惯是否稳定？",
        "文字编辑": "- 删冗余旁白\n- 句子更短更有力\n- 名称/称谓一致",
        "爽点工程师": "- 每章至少一个爽点：打脸/反杀/反转\n- 让代价可见、收益可感\n- 章末留下更大爽点预告",
        "情绪戏导演": "- 情绪曲线：紧张→缓冲→爆发\n- 关键对话承载情绪转折\n- 结尾情绪落点明确",
        "场景渲染": "- 用3-5个感官细节立场景\n- 动作线清晰：进场→交锋→结果\n- 避免空泛形容词堆叠",
        "对话编剧": "- 对话要带目的与冲突\n- 少解释，多暗示\n- 用潜台词制造张力",
        "逻辑审校": "- 因果链闭合\n- 信息增量清楚\n- 伏笔不乱埋、能回收",
    }
    return templates.get(role, "- （模板）请补充该角色的检查要点")


def producer(client: LLMClient, context: str) -> RoleResult:
    system = "你是小说编辑部的主编（Producer）。输出一个可执行的本章编辑部任务清单 memo（要点式）。JSON: {memo:string}。"
    user = f"基于上下文，给出本章任务清单。\n\n{context}"
    return _role_json(client, role="主编", system=system, user=user)


def character_manager(client: LLMClient, context: str) -> RoleResult:
    system = "你是角色设定管。输出角色一致性与本章角色推进建议。JSON: {memo:string, checks:[string], risks:[string]}。"
    user = f"基于上下文，输出角色推进建议。\n\n{context}"
    return _role_json(client, role="角色设定管", system=system, user=user)


def copy_editor(client: LLMClient, context: str) -> RoleResult:
    system = "你是文字编辑。输出可执行的语言改进策略（不需要逐句改）。JSON: {memo:string}。"
    user = f"基于上下文，输出文字层面的改进策略。\n\n{context}"
    return _role_json(client, role="文字编辑", system=system, user=user)


def hype_engineer(client: LLMClient, context: str) -> RoleResult:
    system = "你是爽点工程师。输出本章爽点设计与节奏建议。JSON: {memo:string}。"
    user = f"基于上下文，输出爽点与节奏建议。\n\n{context}"
    return _role_json(client, role="爽点工程师", system=system, user=user)


def emotion_director(client: LLMClient, context: str) -> RoleResult:
    system = "你是情绪戏导演。输出情绪曲线与关键情绪转折点建议。JSON: {memo:string}。"
    user = f"基于上下文，输出情绪戏建议。\n\n{context}"
    return _role_json(client, role="情绪戏导演", system=system, user=user)


def scene_renderer(client: LLMClient, context: str) -> RoleResult:
    system = "你是场景渲染。输出场景调度与感官细节建议。JSON: {memo:string}。"
    user = f"基于上下文，输出场景渲染建议。\n\n{context}"
    return _role_json(client, role="场景渲染", system=system, user=user)


def dialog_writer(client: LLMClient, context: str) -> RoleResult:
    system = "你是对话编剧。输出对话推动冲突的策略与示例句式方向。JSON: {memo:string}。"
    user = f"基于上下文，输出对话建议。\n\n{context}"
    return _role_json(client, role="对话编剧", system=system, user=user)


def logic_proofreader(client: LLMClient, context: str) -> RoleResult:
    system = "你是逻辑审校。输出潜在逻辑漏洞与一致性检查清单。JSON: {memo:string}。"
    user = f"基于上下文，输出逻辑审校清单。\n\n{context}"
    return _role_json(client, role="逻辑审校", system=system, user=user)

