"""Unit and integration tests for the repo-analyzer CLI."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

from repo_analyzer.cli import app

runner = CliRunner()


class TestCliScan(unittest.TestCase):
    """Test CLI `scan` command invocations."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name).resolve()

        # Create basic structure
        (self.root / "src").mkdir()
        (self.root / "src" / "main.py").write_text("print('hello world')\n")
        (self.root / "README.md").write_text("# Test Repository\n")
        (self.root / ".gitignore").write_text("*.log\n")
        (self.root / "debug.log").write_text("log data\n")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_scan_valid_directory(self) -> None:
        result = runner.invoke(app, ["scan", str(self.root)])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("src", result.output)
        self.assertIn("main.py", result.output)
        self.assertIn("README.md", result.output)
        self.assertIn("Resumen del Repositorio", result.output)
        self.assertIn("Estadísticas por Extensión", result.output)
        # debug.log should be ignored by gitignore by default
        self.assertNotIn("debug.log", result.output)

    def test_scan_default_directory(self) -> None:
        result = runner.invoke(app, ["scan"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Resumen del Repositorio", result.output)

    def test_scan_only_stats_flag(self) -> None:
        result = runner.invoke(app, ["scan", str(self.root), "--only-stats"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Resumen del Repositorio", result.output)
        self.assertIn("Estadísticas por Extensión", result.output)
        # Tree directory icon should not be rendered
        self.assertNotIn("📁", result.output)

    def test_scan_only_stats_short_flag(self) -> None:
        result = runner.invoke(app, ["scan", str(self.root), "-s"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Resumen del Repositorio", result.output)
        self.assertNotIn("📁", result.output)

    def test_scan_max_depth_option(self) -> None:
        result = runner.invoke(app, ["scan", str(self.root), "-d", "0"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("README.md", result.output)
        # When max_depth is 0, subdirectories should not be traversed
        self.assertNotIn("main.py", result.output)

    def test_scan_no_gitignore_flag(self) -> None:
        result = runner.invoke(app, ["scan", str(self.root), "--no-gitignore"])
        self.assertEqual(result.exit_code, 0)
        # debug.log should now appear since gitignore is ignored
        self.assertIn("debug.log", result.output)

    def test_scan_non_existent_path(self) -> None:
        invalid_path = self.root / "does_not_exist_9876"
        result = runner.invoke(app, ["scan", str(invalid_path)])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Error:", result.output)
        self.assertIn("does not exist", result.output)

    def test_scan_file_path_fails(self) -> None:
        file_path = self.root / "README.md"
        result = runner.invoke(app, ["scan", str(file_path)])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Error:", result.output)
        self.assertIn("not a directory", result.output)


if __name__ == "__main__":
    unittest.main()
