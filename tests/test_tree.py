"""Unit tests for tree formatting and rich rendering helpers."""

import unittest
from pathlib import Path
from repo_analyzer.scanner import FileInfo, RepoStats
from repo_analyzer.tree import create_rich_tree, create_stats_table, format_tree_as_text


class TestTree(unittest.TestCase):
    """Test suite for tree formatting functions."""

    def test_format_tree_as_text(self):
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

    def test_create_rich_tree(self):
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

    def test_create_stats_table(self):
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
