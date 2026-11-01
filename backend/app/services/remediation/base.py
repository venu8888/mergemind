"""Base definitions and context for provider-independent AI remediation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.security import sanitize_secret


@dataclass
class RemediationContext:
    """Sanitized context describing the defect or CI failure requiring remediation."""

    repository_id: str
    repository_name: str
    target_commit_sha: str
    target_branch: str
    error_message: str
    failure_category: str
    target_file: str | None = None
    target_line: int | None = None
    enclosing_symbol: str | None = None
    code_snippet: str | None = None
    log_excerpt: str | None = None
    ci_failure_id: str | None = None
    finding_id: str | None = None
    pull_request_id: str | None = None
    extra_evidence: dict[str, Any] = field(default_factory=dict)

    def sanitize(self) -> RemediationContext:
        """Return a copy of the context with any sensitive tokens or credentials stripped."""
        return RemediationContext(
            repository_id=self.repository_id,
            repository_name=self.repository_name,
            target_commit_sha=self.target_commit_sha,
            target_branch=self.target_branch,
            error_message=sanitize_secret(self.error_message),
            failure_category=self.failure_category,
            target_file=self.target_file,
            target_line=self.target_line,
            enclosing_symbol=self.enclosing_symbol,
            code_snippet=sanitize_secret(self.code_snippet) if self.code_snippet else None,
            log_excerpt=sanitize_secret(self.log_excerpt) if self.log_excerpt else None,
            ci_failure_id=self.ci_failure_id,
            finding_id=self.finding_id,
            pull_request_id=self.pull_request_id,
            extra_evidence=self.extra_evidence,
        )


@dataclass
class RemediationResult:
    """Generated remediation proposal containing unified diff patch and structured rationale."""

    title: str
    description: str
    patch_diff: str
    affected_files: list[str]
    rationale: str
    provider_name: str
    model_identifier: str | None = None
    confidence_score: float = 0.85
    is_valid_diff: bool = True
    validation_error: str | None = None


class BaseRemediationProvider(ABC):
    """Abstract interface for AI and deterministic remediation providers."""

    provider_name: str

    @abstractmethod
    async def generate_proposal(self, context: RemediationContext) -> RemediationResult:
        """Synthesize a corrective patch for the given defect context."""
        pass
