"""Visual tree and statistics presentation components using Rich, and tree formatting utilities."""

from __future__ import annotations

from typing import Any

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from repo_analyzer.config import BINARY_EXTENSIONS
from repo_analyzer.scanner import FileInfo, RepoStats

CODE_EXTENSIONS = {
    ".py",
    ".pyw",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".jsx",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cc",
    ".cxx",
    ".cs",
    ".java",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".kts",
    ".sh",
    ".bash",
    ".zsh",
    ".sql",
    ".r",
    ".lua",
    ".dart",
    ".scala",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".vue",
    ".svelte",
}

CONFIG_EXTENSIONS = {
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".xml",
    ".ini",
    ".cfg",
    ".conf",
    ".env",
    ".properties",
    ".lock",
    ".md",
    ".markdown",
    ".rst",
    ".txt",
    ".csv",
    ".tsv",
}


def format_size(size_bytes: int) -> str:
    """Format bytes into human-readable string (B, KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def get_file_color(extension: str, is_binary: bool = False) -> str:
    """Determine terminal display color based on file type and extension."""
    ext_lower = extension.lower()
    if is_binary or ext_lower in BINARY_EXTENSIONS:
        return "magenta"
    if ext_lower in CODE_EXTENSIONS:
        return "green"
    if ext_lower in CONFIG_EXTENSIONS:
        return "yellow"
    return "white"


def build_file_tree(tree_dict: dict[str, Any], root_name: str) -> Tree:
    """Build a Rich Tree from a hierarchical directory dictionary.

    Args:
        tree_dict: Dictionary containing 'dirs' and 'files' as produced by scan_repository.
        root_name: Display label for the root directory node.

    Returns:
        A rich.tree.Tree object representing the directory structure.
    """
    root_tree = Tree(f"📁 [bold cyan]{root_name}[/bold cyan]")

    def _populate_tree(parent_tree: Tree, node: dict[str, Any]) -> None:
        dirs_dict: dict[str, dict] = node.get("dirs", {})
        for dir_name in sorted(dirs_dict.keys(), key=str.lower):
            sub_node = dirs_dict[dir_name]
            dir_branch = parent_tree.add(f"📁 [bold cyan]{dir_name}[/bold cyan]")
            _populate_tree(dir_branch, sub_node)

        files_list: list[FileInfo | dict[str, Any]] = node.get("files", [])
        sorted_files = sorted(
            files_list,
            key=lambda f: (f.name if hasattr(f, "name") else f.get("name", "")).lower(),
        )

        for file_item in sorted_files:
            name = file_item.name if hasattr(file_item, "name") else file_item.get("name", "")
            size = (
                file_item.size_bytes
                if hasattr(file_item, "size_bytes")
                else file_item.get("size_bytes", 0)
            )
            ext = (
                file_item.extension
                if hasattr(file_item, "extension")
                else file_item.get("extension", "")
            )
            is_bin = (
                file_item.is_binary
                if hasattr(file_item, "is_binary")
                else file_item.get("is_binary", False)
            )

            color = get_file_color(ext, is_binary=is_bin)
            size_str = format_size(size)
            parent_tree.add(f"📄 [{color}]{name}[/{color}] [dim]({size_str})[/dim]")

    _populate_tree(root_tree, tree_dict)
    return root_tree


def build_stats_table(stats: RepoStats, sort_by: str = "files") -> Table:
    """Build a Rich Table presenting file extension breakdown and statistics.

    Args:
        stats: RepoStats object containing scan metrics.
        sort_by: Metric to sort rows by ('files' or 'size').

    Returns:
        A rich.table.Table instance.
    """
    table = Table(
        title="[bold]Estadísticas por Extensión / Tipo[/bold]",
        box=box.ROUNDED,
        header_style="bold magenta",
        show_footer=False,
    )

    table.add_column("Extensión/Tipo", justify="left", style="bold cyan")
    table.add_column("Archivos", justify="right", style="green")
    table.add_column("% del total", justify="right", style="yellow")
    table.add_column("Tamaño formateado", justify="right", style="magenta")
    table.add_column("Líneas de código", justify="right", style="blue")

    if sort_by == "size":
        sorted_exts = sorted(
            stats.extension_counts.keys(),
            key=lambda ext: (
                stats.extension_sizes.get(ext, 0),
                stats.extension_counts.get(ext, 0),
            ),
            reverse=True,
        )
    else:
        sorted_exts = sorted(
            stats.extension_counts.keys(),
            key=lambda ext: (
                stats.extension_counts.get(ext, 0),
                stats.extension_sizes.get(ext, 0),
            ),
            reverse=True,
        )

    for ext in sorted_exts:
        count = stats.extension_counts.get(ext, 0)
        percentage = (
            f"{(count / stats.total_files * 100):.1f}%" if stats.total_files > 0 else "0.0%"
        )
        size_str = format_size(stats.extension_sizes.get(ext, 0))
        lines = stats.extension_lines.get(ext)
        lines_str = f"{lines:,}" if lines is not None else "-"

        table.add_row(ext, f"{count:,}", percentage, size_str, lines_str)

    if stats.total_files > 0:
        table.add_section()
        table.add_row(
            "[bold]Total[/bold]",
            f"[bold]{stats.total_files:,}[/bold]",
            "100.0%",
            f"[bold]{format_size(stats.total_size_bytes)}[/bold]",
            f"[bold]{stats.total_lines:,}[/bold]",
        )

    return table


def build_summary_panel(stats: RepoStats, ignored_count: int | None = None) -> Panel:
    """Build a Rich Panel displaying overall repository summary metrics.

    Args:
        stats: RepoStats object containing scan metrics.
        ignored_count: Optional override for count of ignored files/directories.

    Returns:
        A rich.panel.Panel instance.
    """
    ignored = (
        ignored_count
        if ignored_count is not None
        else getattr(stats, "ignored_files_count", 0)
    )

    summary_text = (
        f"• [bold cyan]Total de archivos:[/bold cyan] {stats.total_files:,}\n"
        f"• [bold cyan]Total de carpetas:[/bold cyan] {stats.total_dirs:,}\n"
        f"• [bold cyan]Líneas de código:[/bold cyan] {stats.total_lines:,}\n"
        f"• [bold cyan]Tamaño total:[/bold cyan] {format_size(stats.total_size_bytes)}\n"
        f"• [bold cyan]Archivos ignorados:[/bold cyan] {ignored:,}"
    )

    return Panel(
        summary_text,
        title="[bold green]Resumen del Repositorio[/bold green]",
        box=box.ROUNDED,
        border_style="cyan",
        expand=False,
    )


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
    for f in sorted(files, key=lambda x: x.name if hasattr(x, "name") else x.get("name", "")):
        fname = f.name if hasattr(f, "name") else f.get("name", "")
        items.append((fname, f, False))

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

        for f in sorted(files, key=lambda x: x.name if hasattr(x, "name") else x.get("name", "")):
            fname = f.name if hasattr(f, "name") else f.get("name", "")
            is_bin = f.is_binary if hasattr(f, "is_binary") else f.get("is_binary", False)
            size = f.size_bytes if hasattr(f, "size_bytes") else f.get("size_bytes", 0)
            line_cnt = getattr(f, "line_count", None) if hasattr(f, "line_count") else f.get("line_count")
            if is_bin:
                parent_node.add(f"[magenta]:package: {fname}[/magenta] [dim]({size} B)[/dim]")
            else:
                lines_info = f", {line_cnt} líneas" if line_cnt is not None else ""
                parent_node.add(f"[green]:page_facing_up: {fname}[/green] [dim]({size} B{lines_info})[/dim]")

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
