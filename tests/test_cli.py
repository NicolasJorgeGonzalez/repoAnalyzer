"""Unit and integration tests for Typer CLI commands (scan & analyze)."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from repo_analyzer.cli import app
from repo_analyzer.llm_client import APIQuotaExceededError


class TestCliCommands(unittest.TestCase):
    """Test suite for CLI commands."""

    def setUp(self):
        self.runner = CliRunner()

    def test_help_command(self):
        """CLI without arguments or with --help should display help."""
        result = self.runner.invoke(app, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("scan", result.output)
        self.assertIn("analyze", result.output)

    def test_analyze_nonexistent_path(self):
        """Analyze on a nonexistent path should exit with code 1 and error message."""
        result = self.runner.invoke(app, ["analyze", "non_existent_directory_xyz123"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Ruta inexistente", result.output)

    def test_analyze_file_instead_of_directory(self):
        """Analyze on a file path instead of directory should exit with code 1."""
        with tempfile.NamedTemporaryFile(suffix=".txt") as f:
            result = self.runner.invoke(app, ["analyze", f.name])
            self.assertEqual(result.exit_code, 1)
            self.assertIn("no es un directorio", result.output)

    def test_analyze_missing_api_key_friendly_error(self):
        """Analyze without API key should show friendly Rich error panel and exit 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {}, clear=True):
                result = self.runner.invoke(app, ["analyze", tmpdir])
                self.assertEqual(result.exit_code, 1)
                self.assertIn("Falta Gemini API Key", result.output)
                self.assertIn("GEMINI_API_KEY", result.output)
                # Ensure no Python traceback dump
                self.assertNotIn("Traceback (most recent call last)", result.output)

    @patch("repo_analyzer.cli.GeminiAnalyzer")
    def test_analyze_successful_output_to_stdout(self, mock_analyzer_cls):
        """Analyze should display Markdown report in terminal on success."""
        mock_instance = MagicMock()
        mock_instance.analyze_codebase.return_value = (
            "# Reporte Arquitectónico\n\n## 1. Resumen\nCódigo modular y limpio."
        )
        mock_analyzer_cls.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a sample file
            (Path(tmpdir) / "app.py").write_text("print('hello')", encoding="utf-8")

            result = self.runner.invoke(
                app,
                ["analyze", tmpdir, "--api-key", "test-key-xyz"],
            )

            self.assertEqual(result.exit_code, 0)
            mock_analyzer_cls.assert_called_once()
            self.assertEqual(mock_analyzer_cls.call_args.kwargs["api_key"], "test-key-xyz")
            self.assertIn("Reporte Arquitectónico", result.output)
            self.assertIn("Resumen", result.output)

    @patch("repo_analyzer.cli.GeminiAnalyzer")
    def test_analyze_saves_report_to_output_file(self, mock_analyzer_cls):
        """Analyze with --output should save markdown report to disk."""
        mock_instance = MagicMock()
        mock_markdown = "# Reporte\nGuardado correctamente."
        mock_instance.analyze_codebase.return_value = mock_markdown
        mock_analyzer_cls.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "main.py").write_text("print('test')", encoding="utf-8")
            output_file = Path(tmpdir) / "sub" / "reporte.md"

            result = self.runner.invoke(
                app,
                ["analyze", tmpdir, "-k", "test-key", "-o", str(output_file)],
            )

            self.assertEqual(result.exit_code, 0)
            self.assertTrue(output_file.is_file())
            self.assertEqual(output_file.read_text(encoding="utf-8"), mock_markdown)
            self.assertIn("guardado exitosamente", result.output)

    @patch("repo_analyzer.cli.GeminiAnalyzer")
    def test_analyze_handles_llm_error_gracefully(self, mock_analyzer_cls):
        """Analyze should handle LLMAnalysisError cleanly without crashing."""
        mock_instance = MagicMock()
        mock_instance.analyze_codebase.side_effect = APIQuotaExceededError(
            "Límite de cuota excedido (429)"
        )
        mock_analyzer_cls.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.runner.invoke(app, ["analyze", tmpdir, "-k", "test-key"])
            self.assertEqual(result.exit_code, 1)
            self.assertIn("Límite de cuota excedido", result.output)
            self.assertNotIn("Traceback (most recent call last)", result.output)

    def test_scan_command_basic(self):
        """Scan command should render tree and stats table."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "test.py").write_text("print('hello')", encoding="utf-8")
            result = self.runner.invoke(app, ["scan", tmpdir])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Estadísticas del Repositorio", result.output)
            self.assertIn("Total de Archivos", result.output)


if __name__ == "__main__":
    unittest.main()
