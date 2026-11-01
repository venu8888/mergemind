"""CI/CD log parser with secret sanitization and stack-trace extraction."""

from __future__ import annotations

import re
from typing import Any


class CILogParser:
    """Parses raw CI/CD workflow and job logs to isolate failure locations and error signatures."""

    # Patterns matching file path references in common stack traces (Python, JS/TS, etc.)
    PYTHON_STACK_PATTERN = re.compile(
        r'File "(?P<file>[^"]+)", line (?P<line>\d+)(?:, in (?P<symbol>[^\n]+))?'
    )
    PYTEST_FAIL_PATTERN = re.compile(
        r"FAILED\s+(?P<file>[^\s:]+)::(?P<symbol>[^\s]+)\s+-\s+(?P<message>.+)"
    )
    GENERIC_LOC_PATTERN = re.compile(
        r"(?P<file>[a-zA-Z0-9_\-\./]+\.(?:py|ts|tsx|js|jsx|json|ya?ml|toml|lock)):(?P<line>\d+)(?::(?P<col>\d+))?"
    )

    # Patterns for sensitive tokens to mask in raw logs
    TOKEN_PATTERNS = [
        re.compile(r"(ghp_[A-Za-z0-9_]+)"),
        re.compile(r"(github_pat_[A-Za-z0-9_]+)"),
        re.compile(r"Bearer\s+([A-Za-z0-9_\-\.]{20,})", re.IGNORECASE),
        re.compile(r"(-----BEGIN [A-Z ]+ PRIVATE KEY-----[^-]+-----END [A-Z ]+ PRIVATE KEY-----)"),
        re.compile(r"password\s*=\s*['\"]?([^'\"\s]{4,})['\"]?", re.IGNORECASE),
        re.compile(r"secret\s*=\s*['\"]?([^'\"\s]{4,})['\"]?", re.IGNORECASE),
    ]

    def sanitize_logs(self, raw_logs: str) -> str:
        """Sanitize secrets, tokens, private keys, and credential patterns from raw log strings."""
        if not raw_logs:
            return ""

        sanitized = raw_logs
        for pattern in self.TOKEN_PATTERNS:
            sanitized = pattern.sub("[REDACTED_CREDENTIAL]", sanitized)

        return sanitized

    def parse(self, raw_logs: str, max_excerpt_lines: int = 150) -> dict[str, Any]:
        """Parse raw CI logs to extract primary error message, excerpt, and localized files."""
        clean_logs = self.sanitize_logs(raw_logs)
        lines = clean_logs.splitlines()

        localized_files: list[dict[str, Any]] = []
        seen_locations: set[tuple[str, int]] = set()
        error_lines: list[str] = []
        failure_excerpt_lines: list[str] = []

        is_capturing_failure = False

        for _idx, line in enumerate(lines):
            # Detect Pytest failure lines
            pytest_match = self.PYTEST_FAIL_PATTERN.search(line)
            if pytest_match:
                f_path = pytest_match.group("file").replace("\\", "/")
                symbol = pytest_match.group("symbol")
                msg = pytest_match.group("message")
                loc_key = (f_path, 1)
                if loc_key not in seen_locations:
                    seen_locations.add(loc_key)
                    localized_files.append(
                        {
                            "file_path": f_path,
                            "line_number": 1,
                            "enclosing_symbol": symbol,
                            "context": line.strip(),
                        }
                    )
                error_lines.append(f"{f_path}::{symbol}: {msg}")

            # Detect Python stack traces
            py_match = self.PYTHON_STACK_PATTERN.search(line)
            if py_match:
                f_path = py_match.group("file").replace("\\", "/")
                line_no = int(py_match.group("line"))
                symbol = py_match.group("symbol") or ""
                loc_key = (f_path, line_no)
                if loc_key not in seen_locations and not f_path.startswith("<"):
                    seen_locations.add(loc_key)
                    localized_files.append(
                        {
                            "file_path": f_path,
                            "line_number": line_no,
                            "enclosing_symbol": symbol.strip() if symbol else None,
                            "context": line.strip(),
                        }
                    )

            # Detect Generic file:line matches if no python match
            if not py_match and not pytest_match:
                gen_match = self.GENERIC_LOC_PATTERN.search(line)
                if gen_match:
                    f_path = gen_match.group("file").replace("\\", "/")
                    line_no = int(gen_match.group("line"))
                    loc_key = (f_path, line_no)
                    if loc_key not in seen_locations:
                        seen_locations.add(loc_key)
                        localized_files.append(
                            {
                                "file_path": f_path,
                                "line_number": line_no,
                                "enclosing_symbol": None,
                                "context": line.strip(),
                            }
                        )

            # Collect failure context
            lower_line = line.lower()
            if any(
                k in lower_line
                for k in ("error:", "exception:", "fail:", "failed", "fatal:", "traceback")
            ):
                is_capturing_failure = True
                if len(error_lines) < 5:
                    error_lines.append(line.strip())

            if is_capturing_failure:
                failure_excerpt_lines.append(line)
                if len(failure_excerpt_lines) >= max_excerpt_lines:
                    break

        # If no explicit failure block was marked, take the final lines as excerpt
        if not failure_excerpt_lines:
            failure_excerpt_lines = (
                lines[-max_excerpt_lines:] if len(lines) > max_excerpt_lines else lines
            )

        # Select the most descriptive error line (prefer specific errors over "Traceback")
        descriptive_errors = [e for e in error_lines if not e.lower().startswith("traceback")]
        primary_error = (
            descriptive_errors[-1]
            if descriptive_errors
            else (
                error_lines[0]
                if error_lines
                else (
                    failure_excerpt_lines[0].strip()
                    if failure_excerpt_lines
                    else "CI job failed without explicit error trace"
                )
            )
        )

        return {
            "primary_error": primary_error[:500],
            "log_excerpt": "\n".join(failure_excerpt_lines),
            "localized_files": localized_files,
            "error_lines": error_lines[:10],
            "total_lines_analyzed": len(lines),
        }
