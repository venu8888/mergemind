"""Validator for generated unified diff patches."""

from __future__ import annotations

import re


class UnifiedDiffValidator:
    """Validates the structure, size, and safety of proposed unified diff patches."""

    DIFF_HEADER_PATTERN = re.compile(r"^diff --git a/([^\s]+) b/([^\s]+)", re.MULTILINE)
    HUNK_HEADER_PATTERN = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", re.MULTILINE)

    def __init__(self, max_lines: int = 500):
        self.max_lines = max_lines

    def validate(self, diff_text: str) -> tuple[bool, str | None, list[str]]:
        """Validate unified diff string, check safety constraints, and extract affected file paths.

        Returns (is_valid, error_message, affected_files).
        """
        if not diff_text or not diff_text.strip():
            return False, "Patch diff is empty", []

        clean_diff = diff_text.strip()
        lines = clean_diff.splitlines()

        if len(lines) > self.max_lines:
            return (
                False,
                f"Diff exceeds maximum allowed line limit ({len(lines)} > {self.max_lines})",
                [],
            )

        # Check for unified diff markers
        has_git_header = bool(self.DIFF_HEADER_PATTERN.search(clean_diff))
        has_file_header = "--- a/" in clean_diff or "+++ b/" in clean_diff or "--- " in clean_diff
        has_hunk_header = bool(self.HUNK_HEADER_PATTERN.search(clean_diff))

        if not (has_git_header or has_file_header) or not has_hunk_header:
            return (
                False,
                "Patch does not follow standard unified diff format (missing headers or @@ hunk markers)",
                [],
            )

        # Extract affected files
        affected_files: list[str] = []
        for match in self.DIFF_HEADER_PATTERN.finditer(clean_diff):
            b_path = match.group(2)
            if b_path not in affected_files:
                affected_files.append(b_path)

        if not affected_files:
            # Fallback to +++ lines
            for line in lines:
                if line.startswith("+++ b/"):
                    f = line[6:].strip()
                    if f and f not in affected_files:
                        affected_files.append(f)
                elif line.startswith("+++ ") and not line.startswith("+++ /dev/null"):
                    f = line[4:].strip()
                    if f and f not in affected_files:
                        affected_files.append(f)

        # Security check: disallow path traversal or root absolute paths
        for path in affected_files:
            if ".." in path or path.startswith("/") or path.startswith("\\"):
                return False, f"Path traversal or unsafe file path detected: {path}", []

        return True, None, affected_files
