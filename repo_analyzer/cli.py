"""CLI entrypoint for Repo Analyzer."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from repo_analyzer.scanner import scan_repository
from repo_analyzer.tree import build_file_tree, build_stats_table, build_summary_panel

console = Console()

app = typer.Typer(
    name="repo-analyzer",
    help="CLI tool to explore repositories and analyze architecture with Gemini.",
)


@app.callback()
def main() -> None:
    """CLI tool to explore repositories and analyze architecture with Gemini."""


@app.command(name="scan", help="Escanear un repositorio local y mostrar estructura y métricas.")
def scan(
    path: Path = typer.Argument(
        default=Path("."),
        help="Ruta al directorio o repositorio a escanear.",
        show_default=True,
    ),
    max_depth: Optional[int] = typer.Option(
        None,
        "--max-depth",
        "-d",
        help="Límite de profundidad para recorrer y mostrar el árbol de directorios.",
    ),
    only_stats: bool = typer.Option(
        False,
        "--only-stats",
        "-s",
        help="Solo mostrar tabla de estadísticas y panel resumen, sin el árbol de archivos.",
    ),
    no_gitignore: bool = typer.Option(
        False,
        "--no-gitignore",
        help="No respetar las reglas definidas en archivos .gitignore.",
    ),
) -> None:
    """Scan a repository and display file tree and statistics."""
    try:
        files, stats, tree_dict = scan_repository(
            path=path,
            max_depth=max_depth,
            respect_gitignore=not no_gitignore,
        )
    except FileNotFoundError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1)
    except NotADirectoryError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1)
    except Exception as exc:
        console.print(f"[bold red]Error inesperado al escanear el repositorio:[/bold red] {exc}")
        raise typer.Exit(code=1)

    resolved_path = path.resolve()
    root_name = resolved_path.name or str(resolved_path)

    if not only_stats:
        tree = build_file_tree(tree_dict, root_name=root_name)
        console.print(tree)
        console.print()

    summary_panel = build_summary_panel(stats)
    console.print(summary_panel)
    console.print()

    stats_table = build_stats_table(stats)
    console.print(stats_table)
