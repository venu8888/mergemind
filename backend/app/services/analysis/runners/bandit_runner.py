"""Bandit static security analysis runner."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
from typing import Any

from app.core.security import sanitize_secret
from app.services.analysis.base import (
    AnalysisResult,
    BaseAnalysisRunner,
    CheckStatus,
    CheckType,
    RawFinding,
)

logger = logging.getLogger(__name__)


class BanditRunner(BaseAnalysisRunner):
    """Executes Bandit static security scan and parses structured JSON output."""

    tool_name: str = "bandit"
    check_type: CheckType = CheckType.SECURITY_SCAN

    async def run(
        self,
        source_dir: str,
        target_files: list[str] | None = None,
        config_override: dict[str, Any] | None = None,
    ) -> AnalysisResult:
        start_time = time.perf_counter()

        bandit_bin = shutil.which("bandit")
        if not bandit_bin:
            return AnalysisResult(
                check_type=self.check_type,
                status=CheckStatus.UNAVAILABLE,
                duration_ms=0,
                tool_name=self.tool_name,
                error_message="Bandit binary not found in system path",
            )

        cmd = [bandit_bin, "-r", "-f", "json"]

        if target_files:
            existing_targets = []
            for f in target_files:
                abs_f = os.path.join(source_dir, f) if not os.path.isabs(f) else f
                if os.path.exists(abs_f) and f.endswith(".py"):
                    existing_targets.append(abs_f)

            if not existing_targets:
                return AnalysisResult(
                    check_type=self.check_type,
                    status=CheckStatus.SKIPPED,
                    duration_ms=0,
                    tool_name=self.tool_name,
                    raw_stdout="No matching Python target files found for security scan",
                )
            cmd.extend(existing_targets)
        else:
            cmd.append(source_dir)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=source_dir,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=60.0)
            raw_stdout = stdout_bytes.decode("utf-8", errors="replace")
            raw_stderr = stderr_bytes.decode("utf-8", errors="replace")
        except TimeoutError:
            return AnalysisResult(
                check_type=self.check_type,
                status=CheckStatus.TIMEOUT,
                duration_ms=int((time.perf_counter() - start_time) * 1000),
                tool_name=self.tool_name,
                error_message="Bandit security scan timed out after 60 seconds",
            )
        except Exception as exc:
            return AnalysisResult(
                check_type=self.check_type,
                status=CheckStatus.UNAVAILABLE,
                duration_ms=int((time.perf_counter() - start_time) * 1000),
                tool_name=self.tool_name,
                error_message=f"Failed to execute Bandit: {exc}",
            )

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        sanitized_stdout = sanitize_secret(raw_stdout)
        sanitized_stderr = sanitize_secret(raw_stderr)

        findings: list[RawFinding] = []
        metrics = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        try:
            if raw_stdout.strip():
                data = json.loads(raw_stdout)
                results = data.get("results", [])
                for res in results:
                    test_id = res.get("test_id", "SECURITY_ISSUE")
                    issue_text = res.get("issue_text", "Security flaw")
                    severity_raw = res.get("issue_severity", "MEDIUM").upper()
                    filename = res.get("filename", "")
                    line_no = res.get("line_number")
                    code_snippet = res.get("code", "").strip()

                    rel_path = (
                        os.path.relpath(filename, source_dir).replace("\\", "/")
                        if filename
                        else "unknown"
                    )

                    # Normalize severity
                    if severity_raw in ("HIGH", "CRITICAL"):
                        severity = "HIGH"
                        metrics["high"] += 1
                        is_blocking = True
                    elif severity_raw == "MEDIUM":
                        severity = "MEDIUM"
                        metrics["medium"] += 1
                        is_blocking = False
                    else:
                        severity = "LOW"
                        metrics["low"] += 1
                        is_blocking = False

                    findings.append(
                        RawFinding(
                            rule_id=test_id,
                            message=issue_text,
                            severity=severity,
                            file_path=rel_path,
                            start_line=line_no,
                            end_line=line_no,
                            category="SECURITY",
                            code_snippet=code_snippet,
                            is_blocking=is_blocking,
                        )
                    )
        except json.JSONDecodeError as err:
            logger.warning("Failed to parse Bandit JSON output: %s", err)

        status = CheckStatus.FAILED if any(f.is_blocking for f in findings) else CheckStatus.PASSED

        return AnalysisResult(
            check_type=self.check_type,
            status=status,
            duration_ms=duration_ms,
            findings=findings,
            raw_stdout=sanitized_stdout,
            raw_stderr=sanitized_stderr,
            tool_name=self.tool_name,
            tool_version="1.9.4",
            metrics=metrics,
        )
