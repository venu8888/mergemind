"""Base types and abstractions for shared analysis runners."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class CheckType(StrEnum):
    """Taxonomy of discrete verification checks."""

    STATIC_LINT = "STATIC_LINT"
    SECURITY_SCAN = "SECURITY_SCAN"
    DEPENDENCY_AUDIT = "DEPENDENCY_AUDIT"
    TEST_EXECUTION = "TEST_EXECUTION"
    MAINTAINABILITY = "MAINTAINABILITY"
    CONFIG_VALIDATION = "CONFIG_VALIDATION"
    DOC_LINT = "DOC_LINT"


class CheckStatus(StrEnum):
    """Exhaustive execution status of an individual check."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    UNAVAILABLE = "UNAVAILABLE"
    SKIPPED = "SKIPPED"


@dataclass
class RawFinding:
    """Represents an unpersisted finding emitted by an analysis runner."""

    rule_id: str
    message: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    file_path: str
    start_line: int | None = None
    end_line: int | None = None
    category: str = "SYNTAX"  # SYNTAX, SECURITY, TEST_REGRESSION, MAINTAINABILITY, AI_ADVISORY
    enclosing_symbol: str | None = None
    code_snippet: str | None = None
    is_blocking: bool = False
    tool_source: str = "ANALYSIS_RUNNER"
    tool_version: str = "unknown"
    title: str = ""
    raw_output: str | None = None
    provenance_type: str = "DETERMINISTIC_TOOL"
    advisory_confidence: float | None = None

    def __post_init__(self):
        if not self.title:
            self.title = self.rule_id or (self.message[:50] if self.message else "Finding")


@dataclass
class AnalysisResult:
    """Standardized output produced by all deterministic and empirical runners."""

    check_type: CheckType
    status: CheckStatus
    duration_ms: int = 0
    findings: list[RawFinding] = field(default_factory=list)
    output_digest: str = ""
    raw_stdout: str = ""
    raw_stderr: str = ""
    tool_name: str = ""
    tool_version: str = "unknown"
    advisory_db_timestamp: str | None = None
    config_hash: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None

    def __post_init__(self):
        if not self.output_digest:
            stream_data = f"{self.raw_stdout}\0{self.raw_stderr}".encode()
            self.output_digest = hashlib.sha256(stream_data).hexdigest()


class BaseAnalysisRunner(ABC):
    """Abstract base class for all deterministic tool runners."""

    tool_name: str = "base_runner"
    check_type: CheckType = CheckType.STATIC_LINT

    @abstractmethod
    async def run(
        self,
        source_dir: str,
        target_files: list[str] | None = None,
        config_override: dict[str, Any] | None = None,
    ) -> AnalysisResult:
        """Execute the tool against the source directory or target files."""
        raise NotImplementedError
