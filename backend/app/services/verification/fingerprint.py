"""Stable finding fingerprint computation for robust delta tracking across commits."""

from __future__ import annotations

import hashlib
import re


def normalize_finding_message(message: str) -> str:
    """Normalize finding messages by stripping transient line numbers, column numbers, and paths."""
    # Strip line and column references like ':12:5:' or 'line 42'
    norm = re.sub(r":\d+(:\d+)?:", ":*:", message)
    norm = re.sub(r"\bline\s+\d+\b", "line *", norm, flags=re.IGNORECASE)
    norm = re.sub(r"\bcol(umn)?\s+\d+\b", "col *", norm, flags=re.IGNORECASE)
    # Strip memory addresses or hashes like 0x7f8a...
    norm = re.sub(r"0x[0-9a-fA-F]+", "0x*", norm)
    # Collapse multiple whitespaces
    norm = re.sub(r"\s+", " ", norm).strip().lower()
    return norm


def compute_finding_fingerprint(
    rule_id: str,
    message: str,
    enclosing_symbol: str | None = None,
    code_snippet: str | None = None,
) -> str:
    """Compute a content-derived SHA-256 fingerprint for finding matching.

    Formula:
    sha256(rule_id + "\0" + normalized_message + "\0" + enclosing_symbol + "\0" + normalized_code)
    """
    norm_rule = (rule_id or "UNKNOWN_RULE").strip().upper()
    norm_msg = normalize_finding_message(message)
    norm_sym = (enclosing_symbol or "").strip()

    # Normalize code snippet: strip comments and whitespace
    norm_code = ""
    if code_snippet:
        lines = [
            line.strip()
            for line in code_snippet.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        norm_code = "\n".join(lines)

    payload = f"{norm_rule}\0{norm_msg}\0{norm_sym}\0{norm_code}".encode()
    return hashlib.sha256(payload).hexdigest()
