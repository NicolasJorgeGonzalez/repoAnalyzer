"""Repository scanner and file analysis engine."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from repo_analyzer.config import (
    BINARY_EXTENSIONS,
    DEFAULT_IGNORED_DIRS,
    DEFAULT_IGNORED_FILES,
    KEY_FILES_PRIORITY,
    MAX_FILE_SIZE_BYTES,
    MAX_TOTAL_CONTENT_BYTES,
)


@dataclass
class FileInfo:
    """Information about an analyzed file."""

    path: Path
    relative_path: Path
    name: str
    size_bytes: int
    extension: str
    is_binary: bool
    line_count: int | None = None
    is_large: bool = False


@dataclass
class RepoStats:
    """Aggregated statistics for a scanned repository."""

    total_files: int = 0
    total_dirs: int = 0
    total_size_bytes: int = 0
    total_lines: int = 0
    extension_counts: dict[str, int] = field(default_factory=dict)
    extension_sizes: dict[str, int] = field(default_factory=dict)
    extension_lines: dict[str, int] = field(default_factory=dict)
    binary_files_count: int = 0
    text_files_count: int = 0
    skipped_large_files_count: int = 0
    ignored_files_count: int = 0


class GitIgnoreRule:
    """Represents a single .gitignore pattern rule."""

    def __init__(self, raw_pattern: str, base_dir: Path):
        self.raw_pattern = raw_pattern.strip()
        self.base_dir = base_dir.resolve()
        self.is_negative = False
        self.dir_only = False
        self.regex = self._compile(self.raw_pattern)

    def _compile(self, pattern: str) -> re.Pattern:
        if pattern.startswith("!"):
            self.is_negative = True
            pattern = pattern[1:]

        if pattern.endswith("/"):
            self.dir_only = True
            pattern = pattern[:-1]

        anchored = False
        if pattern.startswith("/"):
            anchored = True
            pattern = pattern[1:]
        elif "/" in pattern:
            anchored = True

        parts = pattern.split("**")
        regex_parts: list[str] = []

        for part in parts:
            sub = ""
            j = 0
            n = len(part)
            while j < n:
                c = part[j]
                if c == "*":
                    sub += "[^/]*"
                elif c == "?":
                    sub += "[^/]"
                elif c == "[":
                    k = j + 1
                    if k < n and part[k] == "!":
                        k += 1
                    if k < n and part[k] == "]":
                        k += 1
                    while k < n and part[k] != "]":
                        k += 1
                    if k < n:
                        bracket_content = part[j + 1 : k]
                        if bracket_content.startswith("!"):
                            bracket_content = "^" + bracket_content[1:]
                        sub += "[" + bracket_content + "]"
                        j = k
                    else:
                        sub += "\\["
                elif c in ".+(){}^$|\\":
                    sub += "\\" + c
                else:
                    sub += c
                j += 1
            regex_parts.append(sub)

        res = ""
        for i, p in enumerate(regex_parts):
            if i > 0:
                prev_slash = parts[i - 1].endswith("/")
                next_slash = parts[i].startswith("/")
                if prev_slash and next_slash:
                    res = res[:-1]
                    res += "(?:/|/.+/)"
                    p = p[1:]
                elif prev_slash and not next_slash:
                    res = res[:-1]
                    res += "(?:/.*)?"
                elif not prev_slash and next_slash:
                    res += "(?:^|.*/)"
                    p = p[1:]
                else:
                    res += ".*"
            res += p

        if anchored:
            final_pattern = f"^{res}$"
        else:
            final_pattern = f"(?:^|/){res}$"

        return re.compile(final_pattern)

    def matches(self, path: Path, is_dir: bool = False) -> bool:
        """Check if path matches this gitignore rule."""
        if self.dir_only and not is_dir:
            return False

        try:
            rel = path.resolve().relative_to(self.base_dir).as_posix()
        except ValueError:
            return False

        return bool(self.regex.search(rel))


class GitIgnoreMatcher:
    """Parses and matches .gitignore rules within a directory tree."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir.resolve()
        self.rules: list[GitIgnoreRule] = []

    def add_rule(self, pattern: str, base_dir: Path | None = None) -> None:
        """Add a pattern to the matcher."""
        pattern = pattern.rstrip("\r\n")
        if not pattern.strip() or pattern.strip().startswith("#"):
            return
        if base_dir is None:
            base_dir = self.root_dir
        rule = GitIgnoreRule(pattern.strip(), base_dir)
        self.rules.append(rule)

    def load_file(self, gitignore_path: Path) -> None:
        """Load rules from a .gitignore file."""
        if not gitignore_path.is_file():
            return
        base_dir = gitignore_path.parent.resolve()
        try:
            with open(gitignore_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    self.add_rule(line, base_dir=base_dir)
        except OSError:
            pass

    def is_ignored(self, path: Path, is_dir: bool = False) -> bool:
        """Determine if a file or directory is ignored by the loaded rules."""
        ignored = False
        for rule in self.rules:
            if rule.matches(path, is_dir=is_dir):
                ignored = not rule.is_negative
        return ignored


def parse_gitignore_content(content: str, base_dir: Path) -> GitIgnoreMatcher:
    """Convenience function to parse gitignore string content."""
    matcher = GitIgnoreMatcher(base_dir)
    for line in content.splitlines():
        matcher.add_rule(line, base_dir=base_dir)
    return matcher


def is_binary_file(file_path: Path, sample_size: int = 1024) -> bool:
    """Determine if a file is binary by extension and byte inspection."""
    # 1. Fast path: check known binary extensions
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        return True

    # 2. Inspect first sample_size bytes
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(sample_size)
            if not chunk:
                return False  # Empty file is considered text
            if b"\x00" in chunk:
                return True
            try:
                chunk.decode("utf-8")
            except UnicodeDecodeError as exc:
                # Multi-byte UTF-8 character could be truncated at chunk boundary
                if exc.end == len(chunk):
                    try:
                        chunk[: exc.start].decode("utf-8")
                        return False
                    except UnicodeDecodeError:
                        return True
                return True
    except (OSError, PermissionError):
        return True

    return False


def count_file_lines(file_path: Path, max_file_size: int = MAX_FILE_SIZE_BYTES) -> int | None:
    """Count lines in a text file if its size is within the allowed limit."""
    try:
        size = file_path.stat().st_size
        if size > max_file_size:
            return None
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except (OSError, PermissionError):
        return None


def scan_repository(
    path: Path | str,
    max_depth: int | None = None,
    respect_gitignore: bool = True,
    ignored_dirs: set[str] | None = None,
    ignored_files: set[str] | None = None,
    max_file_size: int = MAX_FILE_SIZE_BYTES,
) -> tuple[list[FileInfo], RepoStats, dict]:
    """Scan a repository directory recursively.

    Args:
        path: Path to the repository directory.
        max_depth: Optional max directory recursion depth (None for unlimited).
        respect_gitignore: Whether to load and evaluate .gitignore files.
        ignored_dirs: Custom set of directory names to ignore.
        ignored_files: Custom set of file names to ignore.
        max_file_size: Size limit in bytes beyond which file line reading is skipped.

    Returns:
        tuple containing:
            - list of FileInfo objects
            - RepoStats summary
            - dict representing hierarchical directory tree
    """
    root_path = Path(path).resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"Path does not exist: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {root_path}")

    dirs_to_ignore = DEFAULT_IGNORED_DIRS if ignored_dirs is None else ignored_dirs
    files_to_ignore = DEFAULT_IGNORED_FILES if ignored_files is None else ignored_files

    gitignore_matcher = GitIgnoreMatcher(root_path) if respect_gitignore else None

    all_files: list[FileInfo] = []
    visited_dirs_count = 0
    ignored_files_count = 0

    def _build_tree(current_dir: Path, current_depth: int) -> dict:
        nonlocal visited_dirs_count, ignored_files_count
        visited_dirs_count += 1

        if gitignore_matcher is not None:
            local_gitignore = current_dir / ".gitignore"
            if local_gitignore.is_file():
                gitignore_matcher.load_file(local_gitignore)

        node: dict = {
            "name": current_dir.name,
            "path": str(current_dir),
            "dirs": {},
            "files": [],
        }

        try:
            entries = sorted(os.scandir(current_dir), key=lambda e: e.name)
        except (OSError, PermissionError):
            return node

        for entry in entries:
            entry_path = Path(entry.path)

            if entry.is_dir(follow_symlinks=False):
                if entry.name in dirs_to_ignore:
                    ignored_files_count += 1
                    continue
                if gitignore_matcher is not None and gitignore_matcher.is_ignored(entry_path, is_dir=True):
                    ignored_files_count += 1
                    continue
                if max_depth is not None and current_depth >= max_depth:
                    continue

                sub_tree = _build_tree(entry_path, current_depth + 1)
                node["dirs"][entry.name] = sub_tree

            elif entry.is_file(follow_symlinks=False):
                if entry.name in files_to_ignore:
                    ignored_files_count += 1
                    continue
                if gitignore_matcher is not None and gitignore_matcher.is_ignored(entry_path, is_dir=False):
                    ignored_files_count += 1
                    continue

                try:
                    stat_res = entry.stat(follow_symlinks=False)
                    size = stat_res.st_size
                except (OSError, PermissionError):
                    size = 0

                is_bin = is_binary_file(entry_path)
                is_large = size > max_file_size

                line_count: int | None = None
                if not is_bin and not is_large:
                    line_count = count_file_lines(entry_path, max_file_size=max_file_size)

                file_info = FileInfo(
                    path=entry_path,
                    relative_path=entry_path.relative_to(root_path),
                    name=entry.name,
                    size_bytes=size,
                    extension=entry_path.suffix.lower(),
                    is_binary=is_bin,
                    line_count=line_count,
                    is_large=is_large,
                )
                node["files"].append(file_info)
                all_files.append(file_info)

        return node

    tree_dict = _build_tree(root_path, current_depth=0)

    stats = RepoStats(
        total_files=len(all_files),
        total_dirs=visited_dirs_count,
        total_size_bytes=sum(f.size_bytes for f in all_files),
        total_lines=sum(f.line_count for f in all_files if f.line_count is not None),
        binary_files_count=sum(1 for f in all_files if f.is_binary),
        text_files_count=sum(1 for f in all_files if not f.is_binary),
        skipped_large_files_count=sum(1 for f in all_files if f.is_large),
        ignored_files_count=ignored_files_count,
    )

    for f in all_files:
        ext = f.extension if f.extension else "(no extension)"
        stats.extension_counts[ext] = stats.extension_counts.get(ext, 0) + 1
        stats.extension_sizes[ext] = stats.extension_sizes.get(ext, 0) + f.size_bytes
        if f.line_count is not None:
            stats.extension_lines[ext] = stats.extension_lines.get(ext, 0) + f.line_count

    return all_files, stats, tree_dict


def get_key_files_content(
    files: Sequence[FileInfo],
    root_path: Path | None = None,
    max_total_bytes: int = MAX_TOTAL_CONTENT_BYTES,
    max_file_bytes: int = MAX_FILE_SIZE_BYTES,
    priority_files: list[str] | None = None,
) -> dict[str, str]:
    """Safely extract key file contents within a total size budget.

    Args:
        files: Sequence of FileInfo objects from repository scan.
        root_path: Optional repository root to resolve relative paths if needed.
        max_total_bytes: Maximum cumulative bytes of content to read.
        max_file_bytes: Maximum size of any single file to include.
        priority_files: List of file names or relative paths prioritized in extraction.

    Returns:
        dict mapping relative file path (as POSIX string) to its text content.
    """
    if max_total_bytes <= 0:
        return {}

    priorities = KEY_FILES_PRIORITY if priority_files is None else priority_files
    priority_map = {name.lower(): idx for idx, name in enumerate(priorities)}

    # Filter candidates: text only and <= max_file_bytes
    candidates: list[FileInfo] = [
        f for f in files if not f.is_binary and not f.is_large and f.size_bytes <= max_file_bytes
    ]

    def _score(f: FileInfo) -> tuple[int, int, str]:
        rel_str = f.relative_path.as_posix().lower()
        name_lower = f.name.lower()

        if rel_str in priority_map:
            return (0, priority_map[rel_str], rel_str)
        if name_lower in priority_map:
            return (0, priority_map[name_lower], rel_str)

        if f.name in {
            "pyproject.toml",
            "setup.py",
            "package.json",
            "Cargo.toml",
            "go.mod",
            "pom.xml",
            "requirements.txt",
            "Dockerfile",
            "Makefile",
        }:
            return (1, 0, rel_str)

        if "readme" in name_lower or "architecture" in name_lower or "spec" in name_lower:
            return (1, 1, rel_str)

        if f.name in {"main.py", "app.py", "cli.py", "index.js", "index.ts", "main.go", "main.rs"}:
            return (1, 2, rel_str)

        depth = len(f.relative_path.parts)
        if f.extension in {".py", ".ts", ".js", ".go", ".rs", ".java", ".c", ".cpp", ".html", ".css"}:
            return (2, depth, rel_str)

        return (3, depth, rel_str)

    sorted_candidates = sorted(candidates, key=_score)

    result: dict[str, str] = {}
    total_bytes_used = 0

    for f_info in sorted_candidates:
        if total_bytes_used >= max_total_bytes:
            break

        target_path = f_info.path
        if not target_path.is_absolute() and root_path is not None:
            target_path = root_path / target_path

        try:
            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except (OSError, PermissionError):
            continue

        encoded = content.encode("utf-8")
        file_len = len(encoded)

        if total_bytes_used + file_len <= max_total_bytes:
            result[f_info.relative_path.as_posix()] = content
            total_bytes_used += file_len
        else:
            remaining = max_total_bytes - total_bytes_used
            if remaining >= 200:
                truncated_encoded = encoded[: remaining - 60]
                truncated_content = truncated_encoded.decode("utf-8", errors="ignore")
                truncated_content += "\n... [TRUNCATED DUE TO SIZE LIMIT] ..."
                result[f_info.relative_path.as_posix()] = truncated_content
                total_bytes_used += len(truncated_content.encode("utf-8"))
            break

    return result
