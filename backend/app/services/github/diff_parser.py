"""Unified Diff Parser and Chunk Line Mapping Service."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import StrEnum

logger = logging.getLogger(__name__)


class ChangeType(StrEnum):
    """Classification of changes applied to a file within a patch."""

    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    RENAMED = "RENAMED"


class LineType(StrEnum):
    """Categorization of individual lines within a diff chunk."""

    CONTEXT = "CONTEXT"
    ADDITION = "ADDITION"
    DELETION = "DELETION"


@dataclass
class DiffLine:
    """Represents a single line within a diff hunk with source and target line coordinates."""

    line_type: LineType
    content: str
    old_line_number: int | None
    new_line_number: int | None


@dataclass
class DiffChunk:
    """Represents a discrete hunk of modifications (@@ -old,len +new,len @@)."""

    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    header: str
    lines: list[DiffLine] = field(default_factory=list)


@dataclass
class FileDiff:
    """Represents changes to a single file within a pull request patch."""

    old_path: str | None
    new_path: str
    change_type: ChangeType
    is_binary: bool = False
    is_truncated: bool = False
    chunks: list[DiffChunk] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0


@dataclass
class ParsedDiff:
    """Aggregates all file diffs parsed from a pull request with size bounds."""

    files: list[FileDiff] = field(default_factory=list)
    total_additions: int = 0
    total_deletions: int = 0
    is_truncated: bool = False
    truncation_reason: str | None = None


_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")


def sanitize_diff_path(raw_path: str) -> str:
    """Strips git prefixes (a/, b/) and verifies against directory traversal."""
    cleaned = raw_path.strip()
    if cleaned.startswith("a/") or cleaned.startswith("b/"):
        cleaned = cleaned[2:]
    cleaned = cleaned.lstrip("/")
    if ".." in cleaned.split("/"):
        raise ValueError(f"Path traversal detected in diff header: {raw_path}")
    return cleaned


class DiffParser:
    """Parses unified diff text streams deterministically into structured diff models."""

    def __init__(
        self,
        max_diff_bytes: int = 5 * 1024 * 1024,
        max_changed_lines: int = 5000,
    ):
        self.max_diff_bytes = max_diff_bytes
        self.max_changed_lines = max_changed_lines

    @classmethod
    def parse(
        cls,
        diff_text: str,
        max_diff_bytes: int = 5 * 1024 * 1024,
        max_changed_lines: int = 5000,
        max_lines: int | None = None,
    ) -> ParsedDiff:
        """Parses raw unified diff patch into structured FileDiff and DiffChunk models."""
        effective_max_lines = max_lines if max_lines is not None else max_changed_lines
        parsed = ParsedDiff()

        if not diff_text or not diff_text.strip():
            return parsed

        raw_bytes_len = len(diff_text.encode("utf-8"))
        if raw_bytes_len > max_diff_bytes:
            parsed.is_truncated = True
            parsed.truncation_reason = (
                f"Diff size ({raw_bytes_len} bytes) exceeded maximum bound ({max_diff_bytes} bytes)"
            )
            return parsed

        lines = diff_text.splitlines()
        current_file: FileDiff | None = None
        current_chunk: DiffChunk | None = None
        old_line_cursor = 0
        new_line_cursor = 0
        total_changed = 0

        i = 0
        while i < len(lines):
            line = lines[i]

            # Enforce line bounds
            if total_changed >= effective_max_lines:
                parsed.is_truncated = True
                parsed.truncation_reason = (
                    f"Changed lines count exceeded maximum bound ({effective_max_lines})"
                )
                if current_file:
                    current_file.is_truncated = True
                break

            # Check new file header: diff --git a/path b/path
            if line.startswith("diff --git "):
                if current_file:
                    parsed.files.append(current_file)
                match = re.match(r"^diff --git a/(.*?) b/(.*?)$", line)
                if match:
                    old_path = sanitize_diff_path(match.group(1))
                    new_path = sanitize_diff_path(match.group(2))
                else:
                    parts = line.split()
                    old_path = sanitize_diff_path(parts[2]) if len(parts) > 2 else "unknown"
                    new_path = sanitize_diff_path(parts[3]) if len(parts) > 3 else "unknown"

                current_file = FileDiff(
                    old_path=old_path,
                    new_path=new_path,
                    change_type=ChangeType.MODIFIED,
                )
                current_chunk = None
                i += 1
                continue

            if not current_file:
                i += 1
                continue

            # Detect file status
            if line.startswith("new file mode "):
                current_file.change_type = ChangeType.ADDED
                current_file.old_path = None
                i += 1
                continue

            if line.startswith("deleted file mode "):
                current_file.change_type = ChangeType.DELETED
                i += 1
                continue

            if line.startswith("similarity index ") or line.startswith("rename from "):
                current_file.change_type = ChangeType.RENAMED
                i += 1
                continue

            if line.startswith("Binary files "):
                current_file.is_binary = True
                i += 1
                continue

            # Check Hunk header: @@ -old,len +new,len @@
            hunk_match = _HUNK_RE.match(line)
            if hunk_match:
                old_start = int(hunk_match.group(1))
                old_len = int(hunk_match.group(2)) if hunk_match.group(2) else 1
                new_start = int(hunk_match.group(3))
                new_len = int(hunk_match.group(4)) if hunk_match.group(4) else 1

                current_chunk = DiffChunk(
                    old_start=old_start,
                    old_lines=old_len,
                    new_start=new_start,
                    new_lines=new_len,
                    header=line,
                )
                current_file.chunks.append(current_chunk)
                old_line_cursor = old_start
                new_line_cursor = new_start
                i += 1
                continue

            # Parse line inside chunk
            if current_chunk is not None:
                if line.startswith("+"):
                    diff_line = DiffLine(
                        line_type=LineType.ADDITION,
                        content=line[1:],
                        old_line_number=None,
                        new_line_number=new_line_cursor,
                    )
                    new_line_cursor += 1
                    current_chunk.lines.append(diff_line)
                    current_file.additions += 1
                    parsed.total_additions += 1
                    total_changed += 1
                elif line.startswith("-"):
                    diff_line = DiffLine(
                        line_type=LineType.DELETION,
                        content=line[1:],
                        old_line_number=old_line_cursor,
                        new_line_number=None,
                    )
                    old_line_cursor += 1
                    current_chunk.lines.append(diff_line)
                    current_file.deletions += 1
                    parsed.total_deletions += 1
                    total_changed += 1
                elif line.startswith(" "):
                    diff_line = DiffLine(
                        line_type=LineType.CONTEXT,
                        content=line[1:],
                        old_line_number=old_line_cursor,
                        new_line_number=new_line_cursor,
                    )
                    old_line_cursor += 1
                    new_line_cursor += 1
                    current_chunk.lines.append(diff_line)

            i += 1

        if current_file:
            parsed.files.append(current_file)

        return parsed
