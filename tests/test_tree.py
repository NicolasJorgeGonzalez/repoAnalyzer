"""Unit tests for repo_analyzer.tree Rich visual components and formatting helpers."""

from __future__ import annotations

import io
import unittest
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from repo_analyzer.scanner import FileInfo, RepoStats
from repo_analyzer.tree import (
    build_file_tree,
    build_stats_table,
    build_summary_panel,
    create_rich_tree,
    create_stats_table,
    format_size,
    format_tree_as_text,
    get_file_color,
)


class TestFormatSize(unittest.TestCase):
    """Test human-readable byte formatting."""

    def test_bytes(self) -> None:
        self.assertEqual(format_size(0), "0 B")
        self.assertEqual(format_size(512), "512 B")
        self.assertEqual(format_size(1023), "1023 B")

    def test_kilobytes(self) -> None:
        self.assertEqual(format_size(1024), "1.0 KB")
        self.assertEqual(format_size(1536), "1.5 KB")
        self.assertEqual(format_size(1024 * 1024 - 1), "1024.0 KB")

    def test_megabytes(self) -> None:
        self.assertEqual(format_size(1024 * 1024), "1.0 MB")
        self.assertEqual(format_size(5 * 1024 * 1024 + 512 * 1024), "5.5 MB")

    def test_gigabytes(self) -> None:
        self.assertEqual(format_size(1024 * 1024 * 1024), "1.0 GB")
        self.assertEqual(format_size(2 * 1024 * 1024 * 1024), "2.0 GB")


class TestFileColor(unittest.TestCase):
    """Test file category color mapping."""

    def test_code_extensions(self) -> None:
        for ext in [".py", ".js", ".ts", ".go", ".rs", ".java", ".c", ".html"]:
            self.assertEqual(get_file_color(ext), "green")

    def test_config_extensions(self) -> None:
        for ext in [".json", ".yaml", ".yml", ".toml", ".ini", ".md", ".txt"]:
            self.assertEqual(get_file_color(ext), "yellow")

    def test_binary_extensions_and_flag(self) -> None:
        self.assertEqual(get_file_color(".png"), "magenta")
        self.assertEqual(get_file_color(".exe"), "magenta")
        self.assertEqual(get_file_color(".unknown", is_binary=True), "magenta")

    def test_other_extensions(self) -> None:
        self.assertEqual(get_file_color(".xyz"), "white")
        self.assertEqual(get_file_color(""), "white")


class TestBuildFileTree(unittest.TestCase):
    """Test tree construction and rendering."""

    def test_empty_tree(self) -> None:
        tree = build_file_tree({"dirs": {}, "files": []}, "root")
        self.assertIsInstance(tree, Tree)

        buf = io.StringIO()
        console = Console(file=buf, color_system=None)
        console.print(tree)
        output = buf.getvalue()
        self.assertIn("root", output)

    def test_tree_with_files_and_dirs(self) -> None:
        tree_dict = {
            "dirs": {
                "src": {
                    "dirs": {},
                    "files": [
                        FileInfo(
                            path=Path("src/main.py"),
                            relative_path=Path("src/main.py"),
                            name="main.py",
                            size_bytes=2048,
                            extension=".py",
                            is_binary=False,
                            line_count=50,
                        )
                    ],
                }
            },
            "files": [
                FileInfo(
                    path=Path("README.md"),
                    relative_path=Path("README.md"),
                    name="README.md",
                    size_bytes=500,
                    extension=".md",
                    is_binary=False,
                    line_count=10,
                ),
                FileInfo(
                    path=Path("logo.png"),
                    relative_path=Path("logo.png"),
                    name="logo.png",
                    size_bytes=1048576,
                    extension=".png",
                    is_binary=True,
                ),
            ],
        }

        tree = build_file_tree(tree_dict, "my_repo")
        self.assertIsInstance(tree, Tree)

        buf = io.StringIO()
        console = Console(file=buf, color_system=None)
        console.print(tree)
        output = buf.getvalue()

        self.assertIn("my_repo", output)
        self.assertIn("src", output)
        self.assertIn("main.py", output)
        self.assertIn("2.0 KB", output)
        self.assertIn("README.md", output)
        self.assertIn("500 B", output)
        self.assertIn("logo.png", output)
        self.assertIn("1.0 MB", output)

    def test_tree_with_dict_entries(self) -> None:
        """Ensure tree gracefully supports dictionary representations of files."""
        tree_dict = {
            "dirs": {},
            "files": [
                {
                    "name": "sample.txt",
                    "size_bytes": 100,
                    "extension": ".txt",
                    "is_binary": False,
                }
            ],
        }
        tree = build_file_tree(tree_dict, "dict_repo")
        buf = io.StringIO()
        console = Console(file=buf, color_system=None)
        console.print(tree)
        output = buf.getvalue()
        self.assertIn("sample.txt", output)
        self.assertIn("100 B", output)


class TestBuildStatsTable(unittest.TestCase):
    """Test statistics table generation."""

    def test_empty_stats_table(self) -> None:
        stats = RepoStats()
        table = build_stats_table(stats)
        self.assertIsInstance(table, Table)

        buf = io.StringIO()
        console = Console(file=buf, color_system=None)
        console.print(table)
        output = buf.getvalue()
        self.assertIn("Extensión/Tipo", output)
        self.assertIn("Archivos", output)

    def test_stats_table_content_and_sorting(self) -> None:
        stats = RepoStats(
            total_files=3,
            total_dirs=1,
            total_size_bytes=3000,
            total_lines=150,
            extension_counts={".py": 2, ".md": 1},
            extension_sizes={".py": 2000, ".md": 1000},
            extension_lines={".py": 120, ".md": 30},
        )

        table_by_files = build_stats_table(stats, sort_by="files")
        buf = io.StringIO()
        console = Console(file=buf, color_system=None)
        console.print(table_by_files)
        output_files = buf.getvalue()

        self.assertIn(".py", output_files)
        self.assertIn(".md", output_files)
        self.assertIn("66.7%", output_files)
        self.assertIn("33.3%", output_files)
        self.assertIn("Total", output_files)
        self.assertIn("100.0%", output_files)

        # Test sort_by size
        table_by_size = build_stats_table(stats, sort_by="size")
        self.assertIsInstance(table_by_size, Table)


class TestBuildSummaryPanel(unittest.TestCase):
    """Test repository summary panel generation."""

    def test_summary_panel(self) -> None:
        stats = RepoStats(
            total_files=10,
            total_dirs=2,
            total_size_bytes=50000,
            total_lines=1200,
            ignored_files_count=4,
        )

        panel = build_summary_panel(stats)
        self.assertIsInstance(panel, Panel)

        buf = io.StringIO()
        console = Console(file=buf, color_system=None)
        console.print(panel)
        output = buf.getvalue()

        self.assertIn("Resumen del Repositorio", output)
        self.assertIn("Total de archivos: 10", output)
        self.assertIn("Total de carpetas: 2", output)
        self.assertIn("Líneas de código: 1,200", output)
        self.assertIn("Archivos ignorados: 4", output)

    def test_summary_panel_with_explicit_ignored_count(self) -> None:
        stats = RepoStats(total_files=5, ignored_files_count=1)
        panel = build_summary_panel(stats, ignored_count=99)

        buf = io.StringIO()
        console = Console(file=buf, color_system=None)
        console.print(panel)
        output = buf.getvalue()

        self.assertIn("Archivos ignorados: 99", output)


class TestTreeFormattingAndHelpers(unittest.TestCase):
    """Test suite for tree formatting and helper functions."""

    def test_format_tree_as_text(self) -> None:
        """Should format hierarchical directory tree dictionary into plain text string."""
        file_a = FileInfo(
            path=Path("/repo/main.py"),
            relative_path=Path("main.py"),
            name="main.py",
            size_bytes=100,
            extension=".py",
            is_binary=False,
            line_count=10,
        )
        file_b = FileInfo(
            path=Path("/repo/pkg/mod.py"),
            relative_path=Path("pkg/mod.py"),
            name="mod.py",
            size_bytes=200,
            extension=".py",
            is_binary=False,
            line_count=20,
        )
        tree_dict = {
            "name": "my_repo",
            "path": "/repo",
            "dirs": {
                "pkg": {
                    "name": "pkg",
                    "path": "/repo/pkg",
                    "dirs": {},
                    "files": [file_b],
                }
            },
            "files": [file_a],
        }

        result = format_tree_as_text(tree_dict)
        self.assertIn("my_repo/", result)
        self.assertIn("pkg/", result)
        self.assertIn("mod.py", result)
        self.assertIn("main.py", result)

    def test_create_rich_tree(self) -> None:
        """Should construct a Rich Tree without errors."""
        tree_dict = {
            "name": "test_root",
            "dirs": {},
            "files": [
                FileInfo(
                    path=Path("/test/app.py"),
                    relative_path=Path("app.py"),
                    name="app.py",
                    size_bytes=50,
                    extension=".py",
                    is_binary=False,
                    line_count=5,
                ),
                FileInfo(
                    path=Path("/test/logo.png"),
                    relative_path=Path("logo.png"),
                    name="logo.png",
                    size_bytes=500,
                    extension=".png",
                    is_binary=True,
                ),
            ],
        }
        rich_tree = create_rich_tree(tree_dict)
        self.assertIsNotNone(rich_tree)

    def test_create_stats_table(self) -> None:
        """Should construct a Rich Table with repository metrics."""
        stats = RepoStats(
            total_files=10,
            total_dirs=3,
            total_size_bytes=4096,
            total_lines=250,
            binary_files_count=1,
            text_files_count=9,
        )
        table = create_stats_table(stats)
        self.assertIsNotNone(table)
        self.assertEqual(table.title, "Estadísticas del Repositorio")


if __name__ == "__main__":
    unittest.main()
