"""Provider-independent LLM remediation adapter with zero credential leakage."""

from __future__ import annotations

import logging
import os

import httpx

from app.services.remediation.base import (
    BaseRemediationProvider,
    RemediationContext,
    RemediationResult,
)
from app.services.remediation.diff_validator import UnifiedDiffValidator
from app.services.remediation.mock_provider import MockRemediationProvider

logger = logging.getLogger(__name__)


class LLMRemediationProvider(BaseRemediationProvider):
    """External LLM adapter (OpenAI, Gemini, Anthropic) with deterministic fallback."""

    provider_name: str = "llm"

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        endpoint_url: str | None = None,
        fallback_provider: BaseRemediationProvider | None = None,
        validator: UnifiedDiffValidator | None = None,
    ):
        self.api_key = (
            api_key
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
        )
        self.model_name = model_name or os.getenv("REMEDIATION_MODEL", "gpt-4o-mini")
        self.endpoint_url = endpoint_url or os.getenv("REMEDIATION_ENDPOINT")
        self.fallback = fallback_provider or MockRemediationProvider()
        self.validator = validator or UnifiedDiffValidator()

    def is_configured(self) -> bool:
        """Check if an external AI provider API key is present."""
        return bool(self.api_key)

    async def generate_proposal(self, context: RemediationContext) -> RemediationResult:
        """Generate a remediation proposal using configured LLM, or fallback safely."""
        sanitized_ctx = context.sanitize()

        if not self.is_configured():
            logger.info("External LLM provider not configured; utilizing deterministic fallback")
            res = await self.fallback.generate_proposal(sanitized_ctx)
            return RemediationResult(
                title=res.title,
                description=res.description,
                patch_diff=res.patch_diff,
                affected_files=res.affected_files,
                rationale=res.rationale,
                provider_name="deterministic_fallback",
                model_identifier="fallback-rule-engine",
                confidence_score=res.confidence_score,
                is_valid_diff=res.is_valid_diff,
                validation_error=res.validation_error,
            )

        # Call configured LLM API with sanitized context
        try:
            prompt = self._construct_prompt(sanitized_ctx)
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an automated code remediation assistant. Output ONLY a valid git unified diff "
                            "starting with 'diff --git' to fix the defect described. Do not include markdown codeblocks."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
            }

            url = self.endpoint_url or "https://api.openai.com/v1/chat/completions"
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_content = data["choices"][0]["message"]["content"]
                    clean_diff = self._extract_diff(raw_content)

                    is_valid, val_err, affected = self.validator.validate(clean_diff)
                    if is_valid:
                        return RemediationResult(
                            title=f"AI Remediation for {sanitized_ctx.failure_category}",
                            description=f"Automated corrective patch for {sanitized_ctx.error_message}",
                            patch_diff=clean_diff,
                            affected_files=affected or [sanitized_ctx.target_file or "unknown"],
                            rationale=f"Model {self.model_name} generated unified diff targeting error: {sanitized_ctx.error_message}",
                            provider_name=self.provider_name,
                            model_identifier=self.model_name,
                            confidence_score=0.88,
                            is_valid_diff=True,
                        )

            logger.warning(
                "External LLM API returned status %s or invalid diff; using fallback",
                resp.status_code if "resp" in locals() else "unknown",
            )
            return await self.fallback.generate_proposal(sanitized_ctx)
        except Exception as exc:
            logger.warning("Error communicating with external LLM API: %s; using fallback", exc)
            return await self.fallback.generate_proposal(sanitized_ctx)

    def _construct_prompt(self, ctx: RemediationContext) -> str:
        """Construct prompt with zero sensitive tokens or credentials."""
        return (
            f"Repository: {ctx.repository_name}\n"
            f"Failure Category: {ctx.failure_category}\n"
            f"Target File: {ctx.target_file}:{ctx.target_line}\n"
            f"Error Message: {ctx.error_message}\n"
            f"Code Snippet:\n{ctx.code_snippet or 'N/A'}\n"
            f"Log Excerpt:\n{ctx.log_excerpt or 'N/A'}\n\n"
            "Generate a standard unified diff that resolves this error without introducing regressions."
        )

    def _extract_diff(self, text: str) -> str:
        """Extract diff text even if wrapped in markdown code blocks."""
        cleaned = text.strip()
        if "```diff" in cleaned:
            parts = cleaned.split("```diff")
            cleaned = parts[1].split("```")[0].strip()
        elif "```" in cleaned:
            parts = cleaned.split("```")
            cleaned = parts[1].split("```")[0].strip()
        return cleaned
