"""Unit tests for repo_analyzer.scanner and configuration."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repo_analyzer.config import (
    DEFAULT_IGNORED_DIRS,
    DEFAULT_IGNORED_FILES,
    MAX_FILE_SIZE_BYTES,
    MAX_TOTAL_CONTENT_BYTES,
)
from repo_analyzer.scanner import (
    FileInfo,
    GitIgnoreMatcher,
    RepoStats,
    count_file_lines,
    get_key_files_content,
    is_binary_file,
    parse_gitignore_content,
    scan_repository,
)


class TestGitIgnoreParsing(unittest.TestCase):
    """Test .gitignore rules and pattern evaluation."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name).resolve()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_comments_and_empty_lines(self) -> None:
        content = """
        # This is a comment
           # Another comment with indentation
        
        *.tmp
        """
        matcher = parse_gitignore_content(content, self.root)
        self.assertEqual(len(matcher.rules), 1)
        self.assertTrue(matcher.is_ignored(self.root / "test.tmp"))
        self.assertFalse(matcher.is_ignored(self.root / "test.txt"))

    def test_wildcard_star(self) -> None:
        content = "*.log\ncache_*.json"
        matcher = parse_gitignore_content(content, self.root)
        self.assertTrue(matcher.is_ignored(self.root / "app.log"))
        self.assertTrue(matcher.is_ignored(self.root / "sub" / "deep.log"))
        self.assertTrue(matcher.is_ignored(self.root / "cache_123.json"))
        self.assertFalse(matcher.is_ignored(self.root / "app.logger"))

    def test_directory_only_pattern(self) -> None:
        content = "build/"
        matcher = parse_gitignore_content(content, self.root)
        # Directory named build
        self.assertTrue(matcher.is_ignored(self.root / "build", is_dir=True))
        self.assertTrue(matcher.is_ignored(self.root / "sub" / "build", is_dir=True))
        # Regular file named build should not match
        self.assertFalse(matcher.is_ignored(self.root / "build", is_dir=False))

    def test_anchored_pattern(self) -> None:
        content = "/root_only.txt\nsrc/module"
        matcher = parse_gitignore_content(content, self.root)
        # /root_only.txt
        self.assertTrue(matcher.is_ignored(self.root / "root_only.txt"))
        self.assertFalse(matcher.is_ignored(self.root / "nested" / "root_only.txt"))
        # src/module
        self.assertTrue(matcher.is_ignored(self.root / "src" / "module"))
        self.assertFalse(matcher.is_ignored(self.root / "other" / "src" / "module"))

    def test_double_star_glob(self) -> None:
        content = "**/temp/*.bak\nlogs/**"
        matcher = parse_gitignore_content(content, self.root)
        self.assertTrue(matcher.is_ignored(self.root / "temp" / "file.bak"))
        self.assertTrue(matcher.is_ignored(self.root / "a" / "b" / "temp" / "file.bak"))
        self.assertFalse(matcher.is_ignored(self.root / "temp" / "file.txt"))
        self.assertTrue(matcher.is_ignored(self.root / "logs" / "2026" / "app.log"))

    def test_negation_rule(self) -> None:
        content = """
        *.txt
        !important.txt
        !sub/important.txt
        """
        matcher = parse_gitignore_content(content, self.root)
        self.assertTrue(matcher.is_ignored(self.root / "notes.txt"))
        self.assertFalse(matcher.is_ignored(self.root / "important.txt"))
        self.assertFalse(matcher.is_ignored(self.root / "sub" / "important.txt"))

    def test_character_class(self) -> None:
        content = "*.py[cod]"
        matcher = parse_gitignore_content(content, self.root)
        self.assertTrue(matcher.is_ignored(self.root / "foo.pyc"))
        self.assertTrue(matcher.is_ignored(self.root / "foo.pyo"))
        self.assertTrue(matcher.is_ignored(self.root / "foo.pyd"))
        self.assertFalse(matcher.is_ignored(self.root / "foo.py"))


class TestDefaultIgnoresAndScanner(unittest.TestCase):
    """Test default ignored directories, files and scan_repository behavior."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name).resolve()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_default_ignored_dirs_and_files(self) -> None:
        # Create default ignored folders
        (self.root / ".git").mkdir()
        (self.root / ".git" / "config").write_text("git config")
        (self.root / ".venv").mkdir()
        (self.root / ".venv" / "pyvenv.cfg").write_text("venv config")
        (self.root / "node_modules").mkdir()
        (self.root / "node_modules" / "package").write_text("module")
        (self.root / "__pycache__").mkdir()
        (self.root / "__pycache__" / "test.cpython-314.pyc").write_bytes(b"\x00\x01\x02")

        # Create default ignored files
        (self.root / ".DS_Store").write_bytes(b"mac_garbage")
        (self.root / "Thumbs.db").write_bytes(b"win_garbage")

        # Create valid repo files
        (self.root / "main.py").write_text("print('hello')\n")
        (self.root / "src").mkdir()
        (self.root / "src" / "utils.py").write_text("def add(a, b):\n    return a + b\n")

        files, stats, tree_dict = scan_repository(self.root, respect_gitignore=False)

        scanned_rel_paths = {f.relative_path.as_posix() for f in files}
        self.assertIn("main.py", scanned_rel_paths)
        self.assertIn("src/utils.py", scanned_rel_paths)
        self.assertNotIn(".git/config", scanned_rel_paths)
        self.assertNotIn(".venv/pyvenv.cfg", scanned_rel_paths)
        self.assertNotIn("node_modules/package", scanned_rel_paths)
        self.assertNotIn("__pycache__/test.cpython-314.pyc", scanned_rel_paths)
        self.assertNotIn(".DS_Store", scanned_rel_paths)
        self.assertNotIn("Thumbs.db", scanned_rel_paths)

    def test_respect_gitignore_in_scan(self) -> None:
        (self.root / ".gitignore").write_text("*.log\nsecret/\n!public.log\n")
        (self.root / "app.log").write_text("some log\n")
        (self.root / "public.log").write_text("public log\n")
        (self.root / "secret").mkdir()
        (self.root / "secret" / "passwords.txt").write_text("password123\n")
        (self.root / "app.py").write_text("print('test')\n")

        files, stats, _ = scan_repository(self.root, respect_gitignore=True)
        rel_paths = {f.relative_path.as_posix() for f in files}

        self.assertIn("app.py", rel_paths)
        self.assertIn("public.log", rel_paths)
        self.assertNotIn("app.log", rel_paths)
        self.assertNotIn("secret/passwords.txt", rel_paths)

    def test_without_respect_gitignore(self) -> None:
        (self.root / ".gitignore").write_text("*.log\n")
        (self.root / "app.log").write_text("log content\n")
        (self.root / "main.py").write_text("code\n")

        files, stats, _ = scan_repository(self.root, respect_gitignore=False)
        rel_paths = {f.relative_path.as_posix() for f in files}

        self.assertIn("app.log", rel_paths)
        self.assertIn("main.py", rel_paths)

    def test_max_depth_parameter(self) -> None:
        (self.root / "level0.txt").write_text("0")
        (self.root / "d1").mkdir()
        (self.root / "d1" / "level1.txt").write_text("1")
        (self.root / "d1" / "d2").mkdir()
        (self.root / "d1" / "d2" / "level2.txt").write_text("2")

        # max_depth = 0 (only root directory files)
        files_0, _, _ = scan_repository(self.root, max_depth=0)
        rel_0 = {f.relative_path.as_posix() for f in files_0}
        self.assertIn("level0.txt", rel_0)
        self.assertNotIn("d1/level1.txt", rel_0)
        self.assertNotIn("d1/d2/level2.txt", rel_0)

        # max_depth = 1 (root and depth 1)
        files_1, _, _ = scan_repository(self.root, max_depth=1)
        rel_1 = {f.relative_path.as_posix() for f in files_1}
        self.assertIn("level0.txt", rel_1)
        self.assertIn("d1/level1.txt", rel_1)
        self.assertNotIn("d1/d2/level2.txt", rel_1)


class TestBinaryDetection(unittest.TestCase):
    """Test detection of binary files vs text files."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name).resolve()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_binary_by_extension(self) -> None:
        img = self.root / "photo.png"
        img.write_bytes(b"some content")
        self.assertTrue(is_binary_file(img))

        doc = self.root / "document.pdf"
        doc.write_bytes(b"%PDF-1.4")
        self.assertTrue(is_binary_file(doc))

    def test_binary_by_null_byte(self) -> None:
        bin_file = self.root / "data.txt"  # text extension, but binary contents
        bin_file.write_bytes(b"header\x00data\x01data")
        self.assertTrue(is_binary_file(bin_file))

    def test_binary_by_invalid_utf8(self) -> None:
        invalid_utf8 = self.root / "invalid.txt"
        invalid_utf8.write_bytes(b"\x80\x81\x82\x83")
        self.assertTrue(is_binary_file(invalid_utf8))

    def test_valid_text_utf8(self) -> None:
        txt_file = self.root / "hello.py"
        txt_file.write_text("# こんにちは世界, Ñandú, Éxito!\nprint('test')\n", encoding="utf-8")
        self.assertFalse(is_binary_file(txt_file))

    def test_empty_file_treated_as_text(self) -> None:
        empty = self.root / "empty.txt"
        empty.write_text("", encoding="utf-8")
        self.assertFalse(is_binary_file(empty))


class TestStatsAndLineCounting(unittest.TestCase):
    """Test calculation of repository statistics, line counts, and extensions."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name).resolve()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_accurate_statistics_and_line_counting(self) -> None:
        # File 1: Python, 3 lines
        (self.root / "one.py").write_text("line 1\nline 2\nline 3\n")
        # File 2: Python, 2 lines
        (self.root / "two.py").write_text("a\nb\n")
        # File 3: Markdown, 4 lines
        (self.root / "README.md").write_text("# Title\n\nBody\nFooter\n")
        # File 4: No extension, 1 line
        (self.root / "Dockerfile").write_text("FROM python:3.14-slim\n")
        # File 5: Binary file (.png)
        (self.root / "icon.png").write_bytes(b"\x89PNG\r\n\x1a\n")

        files, stats, tree_dict = scan_repository(self.root)

        self.assertEqual(stats.total_files, 5)
        self.assertEqual(stats.binary_files_count, 1)
        self.assertEqual(stats.text_files_count, 4)

        # 3 + 2 + 4 + 1 = 10 lines
        self.assertEqual(stats.total_lines, 10)

        # Extension counts
        self.assertEqual(stats.extension_counts[".py"], 2)
        self.assertEqual(stats.extension_counts[".md"], 1)
        self.assertEqual(stats.extension_counts["(no extension)"], 1)
        self.assertEqual(stats.extension_counts[".png"], 1)

        # Extension lines
        self.assertEqual(stats.extension_lines[".py"], 5)
        self.assertEqual(stats.extension_lines[".md"], 4)
        self.assertEqual(stats.extension_lines["(no extension)"], 1)
        self.assertNotIn(".png", stats.extension_lines)

        # Extension sizes
        self.assertGreater(stats.extension_sizes[".py"], 0)
        self.assertGreater(stats.total_size_bytes, 0)

        # Tree dict verification
        self.assertIn("files", tree_dict)
        self.assertIn("dirs", tree_dict)
        self.assertEqual(len(tree_dict["files"]), 5)


class TestSizeLimits(unittest.TestCase):
    """Test file size limits and controlled key files extraction."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name).resolve()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_file_exceeding_max_file_size(self) -> None:
        small_file = self.root / "small.txt"
        small_file.write_text("small text\n")

        large_file = self.root / "large.txt"
        # Create a file exceeding custom 500 bytes threshold
        large_file.write_text("A" * 600)

        files, stats, _ = scan_repository(self.root, max_file_size=500)

        files_map = {f.name: f for f in files}
        self.assertFalse(files_map["small.txt"].is_large)
        self.assertIsNotNone(files_map["small.txt"].line_count)

        self.assertTrue(files_map["large.txt"].is_large)
        # Line count should be skipped (None) for large files
        self.assertIsNone(files_map["large.txt"].line_count)
        self.assertEqual(stats.skipped_large_files_count, 1)

    def test_get_key_files_content_budget_and_filtering(self) -> None:
        (self.root / "pyproject.toml").write_text("[project]\nname = 'demo'\n")
        (self.root / "README.md").write_text("# Demo Project\n")
        (self.root / "main.py").write_text("print('app running')\n")
        (self.root / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (self.root / "giant.txt").write_text("X" * 2000)

        files, _, _ = scan_repository(self.root)

        # Extract with budget allowing pyproject.toml, README.md, and main.py
        contents = get_key_files_content(
            files,
            root_path=self.root,
            max_total_bytes=1000,
            max_file_bytes=500,  # giant.txt is 2000 bytes, so it should be skipped
        )

        self.assertIn("pyproject.toml", contents)
        self.assertIn("README.md", contents)
        self.assertIn("main.py", contents)
        self.assertNotIn("logo.png", contents)
        self.assertNotIn("giant.txt", contents)

    def test_get_key_files_content_respects_total_budget_limit(self) -> None:
        (self.root / "file1.txt").write_text("A" * 300)
        (self.root / "file2.txt").write_text("B" * 300)
        (self.root / "file3.txt").write_text("C" * 300)

        files, _, _ = scan_repository(self.root)

        # Only allow 400 bytes total budget
        contents = get_key_files_content(files, root_path=self.root, max_total_bytes=400)
        total_extracted_bytes = sum(len(v.encode("utf-8")) for v in contents.values())
        self.assertLessEqual(total_extracted_bytes, 400)


if __name__ == "__main__":
    unittest.main()
