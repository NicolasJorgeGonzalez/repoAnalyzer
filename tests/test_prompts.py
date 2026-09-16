"""Unit tests for prompt construction and system prompts."""

import unittest
from repo_analyzer.prompts import (
    SYSTEM_PROMPT,
    _format_size,
    _get_syntax_tag,
    build_analysis_prompt,
)
from repo_analyzer.scanner import RepoStats


class TestPrompts(unittest.TestCase):
    """Tests for prompts and prompt formatting utilities."""

    def test_system_prompt_contains_required_sections(self):
        """Ensure SYSTEM_PROMPT contains the four required sections."""
        self.assertIn("1. Resumen Ejecutivo y Arquitectura", SYSTEM_PROMPT)
        self.assertIn("2. Evaluación de Salud del Código y Buenas Prácticas", SYSTEM_PROMPT)
        self.assertIn("3. Puntos de Dolor y Deuda Técnica", SYSTEM_PROMPT)
        self.assertIn("4. Propuestas Concretas de Refactorización y Mejora", SYSTEM_PROMPT)
        self.assertIn("arquitecto de software", SYSTEM_PROMPT.lower())

    def test_format_size(self):
        """Test formatting sizes into human-readable strings."""
        self.assertEqual(_format_size(500), "500 B")
        self.assertEqual(_format_size(1024), "1.0 KB")
        self.assertEqual(_format_size(2048 * 1024), "2.00 MB")
        self.assertEqual(_format_size(3 * 1024 * 1024 * 1024), "3.00 GB")

    def test_get_syntax_tag(self):
        """Test detection of markdown language tags from filename extensions."""
        self.assertEqual(_get_syntax_tag("main.py"), "python")
        self.assertEqual(_get_syntax_tag("app.ts"), "typescript")
        self.assertEqual(_get_syntax_tag("index.js"), "javascript")
        self.assertEqual(_get_syntax_tag("config.toml"), "toml")
        self.assertEqual(_get_syntax_tag("package.json"), "json")
        self.assertEqual(_get_syntax_tag("deploy.yaml"), "yaml")
        self.assertEqual(_get_syntax_tag("README.md"), "markdown")
        self.assertEqual(_get_syntax_tag("server.go"), "go")
        self.assertEqual(_get_syntax_tag("lib.rs"), "rust")
        self.assertEqual(_get_syntax_tag("Dockerfile"), "dockerfile")
        self.assertEqual(_get_syntax_tag("Makefile"), "makefile")
        self.assertEqual(_get_syntax_tag("unknown.xyz"), "")

    def test_build_analysis_prompt_complete(self):
        """Test building full analysis prompt with stats, tree, and key files."""
        stats = RepoStats(
            total_files=5,
            total_dirs=2,
            total_size_bytes=10480,
            total_lines=420,
            extension_counts={".py": 3, ".toml": 1, ".md": 1},
            extension_sizes={".py": 8000, ".toml": 480, ".md": 2000},
            extension_lines={".py": 350, ".toml": 20, ".md": 50},
            binary_files_count=0,
            text_files_count=5,
            skipped_large_files_count=0,
        )
        tree_str = "my_app/\n├── pyproject.toml\n└── my_app/\n    └── main.py"
        key_files = {
            "pyproject.toml": '[project]\nname = "my_app"',
            "my_app/main.py": 'def run():\n    print("hello")',
        }

        prompt = build_analysis_prompt(
            repo_name="my_app",
            tree_str=tree_str,
            stats=stats,
            key_files=key_files,
        )

        # Check repository name
        self.assertIn("my_app", prompt)
        # Check stats inclusion
        self.assertIn("Total de Archivos:** 5", prompt)
        self.assertIn("Total de Directorios:** 2", prompt)
        self.assertIn("420", prompt)
        self.assertIn(".py", prompt)
        self.assertIn(".toml", prompt)
        # Check tree inclusion
        self.assertIn(tree_str, prompt)
        # Check key files formatting
        self.assertIn("### Archivo: `pyproject.toml`", prompt)
        self.assertIn("```toml", prompt)
        self.assertIn('[project]\nname = "my_app"', prompt)
        self.assertIn("### Archivo: `my_app/main.py`", prompt)
        self.assertIn("```python", prompt)
        self.assertIn('def run():\n    print("hello")', prompt)

    def test_build_analysis_prompt_empty_files(self):
        """Test building prompt when no key files are available."""
        stats = RepoStats()
        prompt = build_analysis_prompt(
            repo_name="empty_repo",
            tree_str="empty_repo/",
            stats=stats,
            key_files={},
        )
        self.assertIn("empty_repo", prompt)
        self.assertIn("No se extrajeron archivos clave", prompt)
        self.assertIn("No se detectaron archivos", prompt)


if __name__ == "__main__":
    unittest.main()
