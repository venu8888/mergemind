"""Deterministic, offline-ready mock remediation provider for testing and fallback."""

from __future__ import annotations

from app.services.remediation.base import (
    BaseRemediationProvider,
    RemediationContext,
    RemediationResult,
)
from app.services.remediation.diff_validator import UnifiedDiffValidator


class MockRemediationProvider(BaseRemediationProvider):
    """Generates deterministic, verified-safe patch proposals for common defect signatures."""

    provider_name: str = "mock"

    def __init__(self, validator: UnifiedDiffValidator | None = None):
        self.validator = validator or UnifiedDiffValidator()

    async def generate_proposal(self, context: RemediationContext) -> RemediationResult:
        """Synthesize a targeted corrective patch based on context and failure category."""
        sanitized_ctx = context.sanitize()
        target_file = sanitized_ctx.target_file or "src/app.py"
        target_line = sanitized_ctx.target_line or 10

        category = sanitized_ctx.failure_category
        error_msg = sanitized_ctx.error_message

        # Generate targeted unified diff based on failure category
        if category == "TEST_FAILURE":
            title = f"Fix assertion in {target_file}"
            description = f"Correct test assertion or return value mismatch: {error_msg}."
            rationale = (
                f"Identified failing assertion in {target_file} at line {target_line}. "
                "Adjusted expected value to align with verified business logic."
            )
            diff = (
                f"diff --git a/{target_file} b/{target_file}\n"
                f"--- a/{target_file}\n"
                f"+++ b/{target_file}\n"
                f"@@ -{target_line},3 +{target_line},3 @@\n"
                f"-    assert result == False\n"
                f"+    assert result == True\n"
                f"     return result\n"
            )
        elif category == "SECURITY_VIOLATION":
            title = f"Parameterize database query in {target_file}"
            description = f"Remediate security vulnerability (B608 SQL Injection): {error_msg}."
            rationale = (
                f"String formatting was detected in SQL execution in {target_file}. "
                "Replaced raw string concatenation with parameterized query parameters."
            )
            diff = (
                f"diff --git a/{target_file} b/{target_file}\n"
                f"--- a/{target_file}\n"
                f"+++ b/{target_file}\n"
                f"@@ -{target_line},3 +{target_line},3 @@\n"
                f"-    query = f\"SELECT * FROM items WHERE id = '{{item_id}}'\"\n"
                f"-    cursor.execute(query)\n"
                f'+    query = "SELECT * FROM items WHERE id = :item_id"\n'
                f'+    cursor.execute(query, {{"item_id": item_id}})\n'
            )
        elif category == "LINT_ERROR":
            title = f"Fix formatting and style in {target_file}"
            description = f"Address linter warning: {error_msg}."
            rationale = (
                f"Cleaned up line length and unnecessary trailing whitespace in {target_file}."
            )
            diff = (
                f"diff --git a/{target_file} b/{target_file}\n"
                f"--- a/{target_file}\n"
                f"+++ b/{target_file}\n"
                f"@@ -{target_line},2 +{target_line},2 @@\n"
                f"-def compute(x, y):\n"
                f"-    return x + y \n"
                f"+def compute(x: int, y: int) -> int:\n"
                f"+    return x + y\n"
            )
        else:
            title = f"Resolve build error in {target_file}"
            description = f"Correct issue causing {category}: {error_msg}."
            rationale = f"Updated code block in {target_file} to handle edge case cleanly."
            diff = (
                f"diff --git a/{target_file} b/{target_file}\n"
                f"--- a/{target_file}\n"
                f"+++ b/{target_file}\n"
                f"@@ -{target_line},2 +{target_line},3 @@\n"
                f"     val = get_value()\n"
                f"+    if val is None:\n"
                f"+        return 0\n"
                f"     return val\n"
            )

        is_valid, val_err, affected_files = self.validator.validate(diff)
        if not affected_files:
            affected_files = [target_file]

        return RemediationResult(
            title=title,
            description=description,
            patch_diff=diff,
            affected_files=affected_files,
            rationale=rationale,
            provider_name=self.provider_name,
            model_identifier="mock-deterministic-v1",
            confidence_score=0.92,
            is_valid_diff=is_valid,
            validation_error=val_err,
        )
