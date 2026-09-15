"""Configuration constants and defaults for Repo Analyzer."""

# Default directories to ignore during repository scanning
DEFAULT_IGNORED_DIRS: set[str] = {
    ".git",
    ".github",
    ".gitlab",
    ".svn",
    ".hg",
    ".venv",
    "venv",
    "env",
    ".env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    "dist",
    "build",
    "develop-eggs",
    "eggs",
    ".eggs",
    "parts",
    "sdist",
    "wheels",
    ".idea",
    ".vscode",
    ".fleet",
    "htmlcov",
    ".coverage",
}

# Default files to ignore
DEFAULT_IGNORED_FILES: set[str] = {
    ".DS_Store",
    "Thumbs.db",
    ".gitignore",
    ".gitattributes",
}

# Common binary file extensions
BINARY_EXTENSIONS: set[str] = {
    # Images
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".ico",
    ".webp",
    ".tiff",
    ".svgz",
    # Audio & Video
    ".mp3",
    ".mp4",
    ".wav",
    ".avi",
    ".mov",
    ".flv",
    ".mkv",
    ".ogg",
    ".webm",
    # Archives & Compressed files
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".7z",
    ".rar",
    ".xz",
    ".tgz",
    # Compiled code & Executables
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dll",
    ".dylib",
    ".exe",
    ".bin",
    ".o",
    ".a",
    ".lib",
    ".class",
    ".wasm",
    # Documents
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    # Fonts
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
    ".eot",
    # Databases & Binary Data
    ".sqlite",
    ".sqlite3",
    ".db",
    ".parquet",
    ".pickle",
    ".pkl",
}

# Size limits
MAX_FILE_SIZE_BYTES: int = 100 * 1024  # 100 KB
MAX_TOTAL_CONTENT_BYTES: int = 500 * 1024  # 500 KB

# Default LLM model
DEFAULT_MODEL: str = "gemini-3.8-flash"

# Key files priority order for architectural extraction
KEY_FILES_PRIORITY: list[str] = [
    # Project manifests & configs
    "pyproject.toml",
    "setup.py",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "requirements.txt",
    "Gemfile",
    "composer.json",
    "Dockerfile",
    "docker-compose.yml",
    "Makefile",
    # Documentation & Specs
    "README.md",
    "ARCHITECTURE.md",
    "spec.md",
    # Application entrypoints
    "main.py",
    "app.py",
    "cli.py",
    "index.js",
    "index.ts",
    "main.go",
    "main.rs",
    "lib.rs",
]
