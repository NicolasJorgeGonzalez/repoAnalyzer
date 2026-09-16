"""Tree rendering and formatting utilities for terminal display and prompts."""

from __future__ import annotations

from typing import Any
from rich.tree import Tree
from rich.table import Table
from rich import box

from repo_analyzer.scanner import FileInfo, RepoStats


def format_tree_as_text(tree_dict: dict[str, Any], prefix: str = "") -> str:
    """Format a hierarchical directory tree dictionary into a plain text tree string.

    Args:
        tree_dict: Dict with keys 'name', 'dirs', and 'files' (from scan_repository).
        prefix: Indentation prefix for recursive calls.

    Returns:
        Formatted multi-line string representing the directory tree.
    """
    lines: list[str] = []
    root_name = tree_dict.get("name", ".")
    if not prefix:
        lines.append(f"{root_name}/")

    sub_dirs = tree_dict.get("dirs", {})
    files = tree_dict.get("files", [])

    items: list[tuple[str, Any, bool]] = []
    for dir_name in sorted(sub_dirs.keys()):
        items.append((dir_name, sub_dirs[dir_name], True))
    for f in sorted(files, key=lambda x: x.name):
        items.append((f.name, f, False))

    total = len(items)
    for idx, (name, val, is_dir) in enumerate(items):
        is_last = idx == (total - 1)
        connector = "└── " if is_last else "├── "
        child_prefix = "    " if is_last else "│   "

        if is_dir:
            lines.append(f"{prefix}{connector}{name}/")
            sub_text = format_tree_as_text(val, prefix=prefix + child_prefix)
            if sub_text:
                lines.append(sub_text)
        else:
            lines.append(f"{prefix}{connector}{name}")

    return "\n".join(lines)


def create_rich_tree(tree_dict: dict[str, Any]) -> Tree:
    """Create a Rich Tree object from a directory tree dict for terminal rendering."""
    root_name = tree_dict.get("name", ".")
    rich_tree = Tree(f"[bold cyan]:open_file_folder: {root_name}[/bold cyan]")

    def _add_children(parent_node: Tree, current_dict: dict[str, Any]) -> None:
        sub_dirs = current_dict.get("dirs", {})
        files = current_dict.get("files", [])

        for dir_name in sorted(sub_dirs.keys()):
            branch = parent_node.add(f"[bold yellow]:file_folder: {dir_name}[/bold yellow]")
            _add_children(branch, sub_dirs[dir_name])

        for f in sorted(files, key=lambda x: x.name):
            if f.is_binary:
                parent_node.add(f"[magenta]:package: {f.name}[/magenta] [dim]({f.size_bytes} B)[/dim]")
            else:
                lines_info = f", {f.line_count} líneas" if f.line_count is not None else ""
                parent_node.add(f"[green]:page_facing_up: {f.name}[/green] [dim]({f.size_bytes} B{lines_info})[/dim]")

    _add_children(rich_tree, tree_dict)
    return rich_tree


def create_stats_table(stats: RepoStats) -> Table:
    """Create a formatted Rich Table summarizing repository stats."""
    table = Table(
        title="Estadísticas del Repositorio",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_lines=True,
    )
    table.add_column("Métrica", style="bold")
    table.add_column("Valor", justify="right")

    table.add_row("Total de Archivos", str(stats.total_files))
    table.add_row("Archivos de Texto", str(stats.text_files_count))
    table.add_row("Archivos Binarios", str(stats.binary_files_count))
    table.add_row("Directorios", str(stats.total_dirs))
    table.add_row("Líneas de Código", f"{stats.total_lines:,}")
    table.add_row("Tamaño Total", f"{stats.total_size_bytes:,} bytes")
    table.add_row("Archivos Grandes Omitidos", str(stats.skipped_large_files_count))

    return table
