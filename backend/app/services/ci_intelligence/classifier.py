"""Deterministic failure classification for CI/CD workflow and job outputs."""

from __future__ import annotations

import re


class CIFailureClassifier:
    """Classifies CI/CD failure logs into structured failure categories."""

    CATEGORIES = [
        "TEST_FAILURE",
        "LINT_ERROR",
        "SECURITY_VIOLATION",
        "DEPENDENCY_CONFLICT",
        "BUILD_ERROR",
        "TIMEOUT",
        "INFRASTRUCTURE_FAILURE",
    ]

    # Deterministic regex signatures
    SIGNATURES = {
        "TIMEOUT": [
            re.compile(r"timed out", re.IGNORECASE),
            re.compile(r"exceeded maximum timeout", re.IGNORECASE),
            re.compile(r"operation timed out", re.IGNORECASE),
            re.compile(r"SIGKILL after \d+s", re.IGNORECASE),
        ],
        "SECURITY_VIOLATION": [
            re.compile(r"bandit", re.IGNORECASE),
            re.compile(r"B\d{3}:", re.IGNORECASE),
            re.compile(r"CVE-\d{4}-\d+", re.IGNORECASE),
            re.compile(r"security vulnerability detected", re.IGNORECASE),
            re.compile(r"pip-audit found", re.IGNORECASE),
        ],
        "DEPENDENCY_CONFLICT": [
            re.compile(r"ModuleNotFoundError:", re.IGNORECASE),
            re.compile(r"ImportError: cannot import name", re.IGNORECASE),
            re.compile(r"ResolutionImpossible", re.IGNORECASE),
            re.compile(r"Could not find a version that satisfies the requirement", re.IGNORECASE),
            re.compile(r"package not found", re.IGNORECASE),
        ],
        "TEST_FAILURE": [
            re.compile(r"FAILED\s+[^\s:]+::", re.IGNORECASE),
            re.compile(r"=+\s+FAILURES\s+=+", re.IGNORECASE),
            re.compile(r"=+\s+\d+\s+failed", re.IGNORECASE),
            re.compile(r"AssertionError", re.IGNORECASE),
            re.compile(r"pytest-cov: failure", re.IGNORECASE),
        ],
        "LINT_ERROR": [
            re.compile(r"ruff check", re.IGNORECASE),
            re.compile(r"[A-Z]\d{3,4}\s+[*]?\s+`[^`]+`", re.IGNORECASE),
            re.compile(r"SyntaxError:", re.IGNORECASE),
            re.compile(r"IndentationError:", re.IGNORECASE),
            re.compile(r"flake8", re.IGNORECASE),
            re.compile(r"biome check", re.IGNORECASE),
        ],
        "INFRASTRUCTURE_FAILURE": [
            re.compile(r"Docker CLI not found", re.IGNORECASE),
            re.compile(r"Cannot connect to the Docker daemon", re.IGNORECASE),
            re.compile(r"runner disconnected", re.IGNORECASE),
            re.compile(r"lost communication with the server", re.IGNORECASE),
            re.compile(r"disk full", re.IGNORECASE),
            re.compile(r"no space left on device", re.IGNORECASE),
        ],
    }

    def classify(self, error_message: str, log_excerpt: str) -> str:
        """Deterministically determine the failure category using priority-ordered signature matching."""
        combined_text = f"{error_message}\n{log_excerpt}"

        # 1. Check for infrastructure failures first (cannot be fixed by code changes)
        for pattern in self.SIGNATURES["INFRASTRUCTURE_FAILURE"]:
            if pattern.search(combined_text):
                return "INFRASTRUCTURE_FAILURE"

        # 2. Check for timeouts
        for pattern in self.SIGNATURES["TIMEOUT"]:
            if pattern.search(combined_text):
                return "TIMEOUT"

        # 3. Check for security violations
        for pattern in self.SIGNATURES["SECURITY_VIOLATION"]:
            if pattern.search(combined_text):
                return "SECURITY_VIOLATION"

        # 4. Check for dependency conflicts
        for pattern in self.SIGNATURES["DEPENDENCY_CONFLICT"]:
            if pattern.search(combined_text):
                return "DEPENDENCY_CONFLICT"

        # 5. Check for test failures
        for pattern in self.SIGNATURES["TEST_FAILURE"]:
            if pattern.search(combined_text):
                return "TEST_FAILURE"

        # 6. Check for lint errors
        for pattern in self.SIGNATURES["LINT_ERROR"]:
            if pattern.search(combined_text):
                return "LINT_ERROR"

        # Default fallback is BUILD_ERROR
        return "BUILD_ERROR"
