"""Provider-independent LLM remediation adapter with zero credential leakage."""

from __future__ import annotations

import hashlib
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
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
        )
        self.model_name = model_name or os.getenv("REMEDIATION_MODEL", "gemini-3.6-flash")
        self.endpoint_url = endpoint_url or os.getenv(
            "REMEDIATION_ENDPOINT",
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            if os.getenv("GEMINI_API_KEY")
            else "https://api.openai.com/v1/chat/completions",
        )
        self.fallback = fallback_provider or MockRemediationProvider()
        self.validator = validator or UnifiedDiffValidator()
        self._proposal_cache: dict[str, RemediationResult] = {}

    def is_configured(self) -> bool:
        """Check if an external AI provider API key is present."""
        return bool(self.api_key)

    def _compute_cache_key(self, ctx: RemediationContext) -> str:
        """Compute deterministic hash key to avoid redundant API calls for unchanged code."""
        key_str = f"{ctx.target_commit_sha}:{ctx.target_file}:{ctx.error_message}:{self.model_name}"
        return hashlib.sha256(key_str.encode("utf-8")).hexdigest()

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

        # Check proposal cache to avoid unnecessary LLM calls
        cache_key = self._compute_cache_key(sanitized_ctx)
        if cache_key in self._proposal_cache:
            logger.info("Reusing cached LLM proposal for key=%s", cache_key[:12])
            return self._proposal_cache[cache_key]

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
                            "starting with 'diff --git' to fix the defect described. Do NOT include markdown blocks or commentary.\n"
                            "Format example:\n"
                            "diff --git a/path/to/file.py b/path/to/file.py\n"
                            "--- a/path/to/file.py\n"
                            "+++ b/path/to/file.py\n"
                            "@@ -1,3 +1,3 @@\n"
                            "-def faulty():\n"
                            "+def fixed():\n"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 1500,
            }

            url = self.endpoint_url
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_content = data["choices"][0]["message"]["content"]
                    logger.debug("Raw LLM completion: %s", raw_content[:300])
                    clean_diff = self._extract_diff(raw_content)

                    # Extract usage metadata
                    usage = data.get("usage", {})
                    token_usage = {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    }

                    is_valid, val_err, affected = self.validator.validate(clean_diff)
                    if is_valid:
                        result = RemediationResult(
                            title=f"AI Remediation for {sanitized_ctx.failure_category}",
                            description=f"Automated corrective patch for {sanitized_ctx.error_message}",
                            patch_diff=clean_diff,
                            affected_files=affected or [sanitized_ctx.target_file or "unknown"],
                            rationale=f"Model {self.model_name} generated unified diff targeting error: {sanitized_ctx.error_message}",
                            provider_name=self.provider_name,
                            model_identifier=self.model_name,
                            confidence_score=0.88,
                            is_valid_diff=True,
                            token_usage=token_usage,
                        )
                        self._proposal_cache[cache_key] = result
                        logger.info(
                            "LLM remediation generated for %s (Tokens: %s)",
                            sanitized_ctx.target_file,
                            token_usage,
                        )
                        return result
                    else:
                        logger.warning(
                            "LLM generated invalid diff (%s); falling back to rule engine", val_err
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
        """Construct prompt with zero sensitive tokens or credentials and bounded size."""
        snippet = ctx.code_snippet or "N/A"
        if snippet != "N/A":
            snippet_lines = snippet.splitlines()
            if len(snippet_lines) > 50:
                snippet = "\n".join(snippet_lines[:50]) + "\n... [truncated for token optimization]"

        log_exc = ctx.log_excerpt or "N/A"
        if log_exc != "N/A":
            log_lines = log_exc.splitlines()
            if len(log_lines) > 50:
                log_exc = "\n".join(log_lines[:50]) + "\n... [truncated for token optimization]"

        return (
            f"Repository: {ctx.repository_name}\n"
            f"Failure Category: {ctx.failure_category}\n"
            f"Target File: {ctx.target_file}:{ctx.target_line}\n"
            f"Error Message: {ctx.error_message}\n"
            f"Code Snippet:\n{snippet}\n"
            f"Log Excerpt:\n{log_exc}\n\n"
            "Generate a standard unified diff that resolves this error without introducing regressions."
        )

    def _extract_diff(self, text: str) -> str:
        """Extract diff text even if wrapped in markdown code blocks or prose."""
        cleaned = text.strip()
        if "```diff" in cleaned:
            parts = cleaned.split("```diff")
            cleaned = parts[1].split("```")[0].strip()
        elif "```" in cleaned:
            parts = cleaned.split("```")
            cleaned = parts[1].split("```")[0].strip()

        if "diff --git " in cleaned:
            cleaned = "diff --git " + cleaned.split("diff --git ", 1)[1]

        return cleaned.strip()
