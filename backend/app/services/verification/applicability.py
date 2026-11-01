"""Check applicability determination based on pull request changed files or categories."""

from __future__ import annotations

import os
from collections.abc import Iterable

from app.services.analysis.base import CheckType
from app.services.github.classifier import FileCategory, FileClassifier

DEPENDENCY_FILENAMES = {
    "requirements.txt",
    "requirements-dev.txt",
    "pipfile",
    "pipfile.lock",
    "pyproject.toml",
    "poetry.lock",
    "setup.py",
    "setup.cfg",
}


def determine_applicable_checks(
    items: Iterable[str | FileCategory],
) -> set[CheckType]:
    """Determine the exact set of applicable verification checks for a pull request.

    Enforces zero denominator padding:
    - Pure documentation PRs do not require test execution, security scans, or static lint.
    - Python PRs require static lint, security scan, and test execution.
    - Dependency file changes require dependency audit.
    """
    categories: set[FileCategory] = set()
    has_dependency_change = False
    has_python_change = False
    has_test_change = False

    for item in items:
        if isinstance(item, FileCategory):
            categories.add(item)
            if item == FileCategory.PYTHON_SOURCE:
                has_python_change = True
            elif item == FileCategory.TEST_SUITE:
                has_test_change = True
        elif isinstance(item, str):
            basename = os.path.basename(item.replace("\\", "/")).lower()
            if basename in DEPENDENCY_FILENAMES or "requirements" in basename:
                has_dependency_change = True

            cat = FileClassifier.classify(item)
            categories.add(cat)
            if cat == FileCategory.PYTHON_SOURCE:
                has_python_change = True
            elif cat == FileCategory.TEST_SUITE:
                has_test_change = True

    applicable: set[CheckType] = set()

    if has_python_change:
        applicable.add(CheckType.STATIC_LINT)
        applicable.add(CheckType.SECURITY_SCAN)
        applicable.add(CheckType.TEST_EXECUTION)

    if has_test_change:
        applicable.add(CheckType.STATIC_LINT)
        applicable.add(CheckType.TEST_EXECUTION)

    if has_dependency_change:
        applicable.add(CheckType.DEPENDENCY_AUDIT)

    # Pure documentation PR: zero required checks in the denominator
    # (If only DOCUMENTATION or empty, applicable remains empty set)

    return applicable
