"""File classification service for categorizing repository files."""

import os
import re
from enum import StrEnum
from typing import Final


class FileCategory(StrEnum):
    """File categorization taxonomy for MergeMind analysis pipeline."""

    PYTHON_SOURCE = "PYTHON_SOURCE"
    TEST_SUITE = "TEST_SUITE"
    CONFIGURATION = "CONFIGURATION"
    DOCUMENTATION = "DOCUMENTATION"
    SENSITIVE_SECURITY = "SENSITIVE_SECURITY"
    BINARY_UNSUPPORTED = "BINARY_UNSUPPORTED"
    OTHER = "OTHER"


class FileClassifier:
    """Classifies files by security, language, purpose, and supportability."""

    # Sensitive patterns (credentials, secrets, keys, private configs)
    SENSITIVE_FILENAME_PATTERNS: Final[list[re.Pattern]] = [
        re.compile(r"^\.env(\..+)?$", re.IGNORECASE),
        re.compile(r".*\.(pem|key|p12|pfx|pkcs12|asc)$", re.IGNORECASE),
        re.compile(r"^id_(rsa|dsa|ecdsa|ed25519)(\.pub)?$", re.IGNORECASE),
        re.compile(r".*(credential|secret|token|password|auth_token).*", re.IGNORECASE),
        re.compile(r"^\.aws/credentials$", re.IGNORECASE),
        re.compile(r"^\.netrc$", re.IGNORECASE),
    ]

    # Binary file extensions
    BINARY_EXTENSIONS: Final[set[str]] = {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".ico",
        ".webp",
        ".svgz",
        ".pdf",
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".xz",
        ".7z",
        ".rar",
        ".whl",
        ".pyc",
        ".pyo",
        ".pyd",
        ".so",
        ".dll",
        ".dylib",
        ".exe",
        ".bin",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".otf",
        ".mp3",
        ".mp4",
        ".mov",
        ".avi",
        ".flv",
        ".webm",
        ".parquet",
        ".arrow",
        ".sqlite",
        ".db",
    }

    # Configuration extensions & exact filenames
    CONFIG_EXTENSIONS: Final[set[str]] = {
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".xml",
        ".editorconfig",
    }
    CONFIG_FILENAMES: Final[set[str]] = {
        "dockerfile",
        "containerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "requirements.txt",
        "requirements-dev.txt",
        "setup.py",
        "setup.cfg",
        "pyproject.toml",
        "pipfile",
        "pipfile.lock",
        "poetry.lock",
        ".flake8",
        ".pylintrc",
        ".ruff.toml",
        "ruff.toml",
        "alembic.ini",
        ".gitignore",
        ".gitattributes",
        ".dockerignore",
    }

    # Documentation extensions & filenames
    DOC_EXTENSIONS: Final[set[str]] = {
        ".md",
        ".rst",
        ".txt",
        ".adoc",
        ".markdown",
    }
    DOC_FILENAMES: Final[set[str]] = {
        "license",
        "copying",
        "readme",
        "changelog",
        "contributing",
        "notice",
    }

    # Test path patterns
    TEST_PATTERNS: Final[list[re.Pattern]] = [
        re.compile(r"(^|/)tests?/", re.IGNORECASE),
        re.compile(r"(^|/)testing/", re.IGNORECASE),
        re.compile(r"(^|/)spec/", re.IGNORECASE),
        re.compile(r"^test_.*\.py$", re.IGNORECASE),
        re.compile(r".*_test\.py$", re.IGNORECASE),
    ]

    @classmethod
    def classify(cls, path: str) -> FileCategory:
        """Classify a given normalized repository file path into a FileCategory."""
        normalized = path.replace("\\", "/").strip("/")
        basename = os.path.basename(normalized)
        stem, ext = os.path.splitext(basename)
        ext_lower = ext.lower()
        base_lower = basename.lower()
        stem_lower = stem.lower()

        # 1. Sensitive security files (highest priority alert)
        for pattern in cls.SENSITIVE_FILENAME_PATTERNS:
            if pattern.search(basename) or pattern.search(normalized):
                return FileCategory.SENSITIVE_SECURITY

        # 2. Binary unsupported files
        if ext_lower in cls.BINARY_EXTENSIONS:
            return FileCategory.BINARY_UNSUPPORTED

        # 3. Test suites
        for pattern in cls.TEST_PATTERNS:
            if pattern.search(normalized) or pattern.search(basename):
                return FileCategory.TEST_SUITE

        # 4. Python source files
        if ext_lower in {".py", ".pyi"}:
            return FileCategory.PYTHON_SOURCE

        # 5. Configuration files
        if ext_lower in cls.CONFIG_EXTENSIONS or base_lower in cls.CONFIG_FILENAMES:
            return FileCategory.CONFIGURATION

        # 6. Documentation
        if (
            ext_lower in cls.DOC_EXTENSIONS
            or stem_lower in cls.DOC_FILENAMES
            or "docs/" in normalized.lower()
        ):
            return FileCategory.DOCUMENTATION

        return FileCategory.OTHER
