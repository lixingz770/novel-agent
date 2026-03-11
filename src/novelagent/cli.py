from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .config import load_config
from .library import (
    analyze_source,
    build_index,
    extract_first_n_chapters,
    generate_role_notes,
    ingest_path,
    search_index,
)
from .paths import WorkspacePaths
from .projects import ProjectBrief, create_project, generate_chapter_outlines, generate_outline, revise_outline
from .writing import review_chapter, write_chapter
from .delivery import package_project


app = typer.Typer(add_completion=False, help="小说编辑部 Agent（本地CLI）")
console = Console()


def ensure_workspace_dirs(ws: WorkspacePaths) -> None:
    dirs = [
        ws.root,
        ws.library_root,
        ws.library_raw,
        ws.library_chunks,
        ws.library_notes,
        ws.library_index,
        ws.library_role_notes,
        ws.projects_root,
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


@app.command()
def init(
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="工作区路径（默认读配置）"),
) -> None:
    """初始化工作区目录结构。"""
    cfg = load_config()
    ws_root = workspace or Path(cfg.workspace)
    ws = WorkspacePaths(root=ws_root)
    ensure_workspace_dirs(ws)
    console.print(f"[green]OK[/green] Workspace initialized at: {ws.root.resolve()}")


@app.command()
def doctor() -> None:
    """显示当前配置与环境检查。"""
    cfg = load_config()
    console.print("[bold]Config[/bold]")
    console.print(cfg.model_dump())
    ws = WorkspacePaths(root=Path(cfg.workspace))
    console.print("\n[bold]Workspace[/bold]")
    console.print({"root": str(ws.root), "exists": ws.root.exists()})


@app.command()
def ingest(
    path: Path = typer.Argument(..., help="要导入的文件或目录（txt/md）"),
) -> None:
    """导入学习素材并切分为chunks。"""
    cfg = load_config()
    ws = WorkspacePaths(root=Path(cfg.workspace))
    ensure_workspace_dirs(ws)
    source_ids = ingest_path(
        ws,
        path,
        max_chars=cfg.retrieval.chunk.max_chars,
        overlap_chars=cfg.retrieval.chunk.overlap_chars,
    )
    console.print({"imported": source_ids, "count": len(source_ids)})


@app.command()
def analyze(
    source_id: str = typer.Argument(..., help="素材source_id（在library/raw里）"),
    force: bool = typer.Option(False, "--force", help="强制重算学习笔记"),
    min_chars: int = typer.Option(3000, "--min-chars", help="学习笔记最少字符数（用于扩写）"),
) -> None:
    """对某个素材生成学习笔记（md+json）。"""
    cfg = load_config()
    ws = WorkspacePaths(root=Path(cfg.workspace))
    ensure_workspace_dirs(ws)
    out = analyze_source(ws, cfg, source_id, force=force, min_chars=min_chars)
    console.print(f"[green]OK[/green] Note generated: {out}")


@app.command()
def index() -> None:
    """构建/刷新本地向量索引。"""
    cfg = load_config()
    ws = WorkspacePaths(root=Path(cfg.workspace))
    ensure_workspace_dirs(ws)
    out = build_index(ws)
    console.print(f"[green]OK[/green] Index built: {out}")


@app.command()
def search(
    query: str = typer.Argument(..., help="检索问题/关键词"),
    top_k: int = typer.Option(8, "--top-k", help="返回数量"),
) -> None:
    """在学习库里检索相似笔记/片段（用于验证学习是否可用）。"""
    cfg = load_config()
    ws = WorkspacePaths(root=Path(cfg.workspace))
    ensure_workspace_dirs(ws)
    hits = search_index(ws, query, top_k=top_k)
    console.print(hits)


@app.command("learn-roles")
def learn_roles(
    path: Path = typer.Argument(..., help="小说文本文件（txt/md）"),
    chapters: int = typer.Option(500, "--chapters", help="抽取前N章用于学习"),
    force: bool = typer.Option(False, "--force", help="强制重算学习笔记"),
    min_chars: int = typer.Option(3000, "--min-chars", help="每个角色学习笔记最少字符数（用于扩写）"),
) -> None:
    """
    抽取前N章→导入学习库→生成通用学习笔记→为每个编辑部角色生成各自学习笔记→重建索引。
    """
    cfg = load_config()
    ws = WorkspacePaths(root=Path(cfg.workspace))
    ensure_workspace_dirs(ws)

    extracted = ws.library_raw / f"{path.stem}.first_{chapters}.txt"
    included = extract_first_n_chapters(path, extracted, chapters)
    console.print(f"[cyan]Extracted[/cyan] {included} chapters to: {extracted}")

    source_ids = ingest_path(
        ws,
        extracted,
        max_chars=cfg.retrieval.chunk.max_chars,
        overlap_chars=cfg.retrieval.chunk.overlap_chars,
    )
    if not source_ids:
        raise typer.Exit(code=1)
    source_id = source_ids[0]
    console.print(f"[green]OK[/green] Ingested source_id: {source_id}")

    analyze_source(ws, cfg, source_id, force=force, min_chars=min_chars)
    role_paths = generate_role_notes(ws, cfg, source_id, force=force, min_chars=min_chars)
    console.print({"role_notes": [str(p) for p in role_paths]})

    build_index(ws)
    console.print("[green]OK[/green] Index refreshed (including role notes).")


@app.command("new-project")
def new_project(
    name: str = typer.Option(..., "--name", help="项目名称"),
    genre: str | None = typer.Option(None, "--genre", help="题材/类型"),
    audience: str | None = typer.Option(None, "--audience", help="目标读者"),
    tone: str | None = typer.Option(None, "--tone", help="基调"),
    pov: str | None = typer.Option(None, "--pov", help="视角（第一/第三等）"),
    taboo: list[str] = typer.Option([], "--taboo", help="禁忌/雷点（可多次传）"),
    must_have: list[str] = typer.Option([], "--must-have", help="必须要的元素（可多次传）"),
    refs: list[str] = typer.Option([], "--ref", help="参考作品（可多次传）"),
) -> None:
    """创建客户项目并落盘 brief.json。"""
    cfg = load_config()
    ws = WorkspacePaths(root=Path(cfg.workspace))
    ensure_workspace_dirs(ws)
    brief = ProjectBrief(
        name=name,
        genre=genre,
        audience=audience,
        tone=tone,
        pov=pov,
        taboo=taboo,
        must_have=must_have,
        references=refs,
    )
    project_id = create_project(ws, brief)
    console.print(f"[green]OK[/green] Project created: {project_id}")


@app.command()
def outline(
    project_id: str = typer.Argument(..., help="项目ID"),
    force: bool = typer.Option(False, "--force", help="强制重算v1（若已存在会跳过）"),
) -> None:
    """生成总大纲 v1（md+json）。"""
    cfg = load_config()
    ws = WorkspacePaths(root=Path(cfg.workspace))
    ensure_workspace_dirs(ws)
    out = generate_outline(ws, cfg, project_id, force=force)
    console.print(f"[green]OK[/green] Outline generated: {out}")


@app.command("revise-outline")
def revise_outline_cmd(
    project_id: str = typer.Argument(..., help="项目ID"),
    feedback: Path = typer.Option(..., "--feedback", "-f", help="客户反馈文本文件"),
) -> None:
    """根据客户反馈修订大纲（生成 v2/v3...）。"""
    cfg = load_config()
    ws = WorkspacePaths(root=Path(cfg.workspace))
    ensure_workspace_dirs(ws)
    fb = feedback.read_text(encoding="utf-8")
    out = revise_outline(ws, cfg, project_id, fb)
    console.print(f"[green]OK[/green] Outline revised: {out}")


@app.command("chapter-outlines")
def chapter_outlines(
    project_id: str = typer.Argument(..., help="项目ID"),
) -> None:
    """从最新总大纲生成每章大纲（chapter_outlines/）。"""
    cfg = load_config()
    ws = WorkspacePaths(root=Path(cfg.workspace))
    ensure_workspace_dirs(ws)
    out = generate_chapter_outlines(ws, cfg, project_id)
    console.print(f"[green]OK[/green] Chapter outlines generated: {out}")


@app.command()
def write(
    project_id: str = typer.Argument(..., help="项目ID"),
    chapter: int = typer.Option(..., "--chapter", "-c", help="章节编号（从1开始）"),
) -> None:
    """生成指定章节草稿（会附引用/约束清单）。"""
    cfg = load_config()
    ws = WorkspacePaths(root=Path(cfg.workspace))
    ensure_workspace_dirs(ws)
    out = write_chapter(ws, cfg, project_id, chapter)
    console.print(f"[green]OK[/green] Draft generated: {out}")


@app.command()
def review(
    project_id: str = typer.Argument(..., help="项目ID"),
    draft: Path = typer.Option(..., "--draft", "-d", help="草稿文件路径（projects/<id>/drafts/...）"),
) -> None:
    """审稿指定草稿，输出审稿报告（md+json）。"""
    cfg = load_config()
    ws = WorkspacePaths(root=Path(cfg.workspace))
    ensure_workspace_dirs(ws)
    out = review_chapter(ws, cfg, project_id, draft)
    console.print(f"[green]OK[/green] Review generated: {out}")


@app.command()
def package(
    project_id: str = typer.Argument(..., help="项目ID"),
) -> None:
    """打包交付产物到 delivery/（含zip）。"""
    cfg = load_config()
    ws = WorkspacePaths(root=Path(cfg.workspace))
    ensure_workspace_dirs(ws)
    res = package_project(ws, project_id)
    console.print({"folder": str(res.folder), "zip": str(res.zip_path)})

