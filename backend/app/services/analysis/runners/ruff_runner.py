"""Ruff deterministic AST linting and syntax runner."""

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


class RuffRunner(BaseAnalysisRunner):
    """Executes Ruff deterministic static analysis and parses structured JSON output."""

    tool_name: str = "ruff"
    check_type: CheckType = CheckType.STATIC_LINT

    async def run(
        self,
        source_dir: str,
        target_files: list[str] | None = None,
        config_override: dict[str, Any] | None = None,
    ) -> AnalysisResult:
        start_time = time.perf_counter()

        ruff_bin = shutil.which("ruff")
        if not ruff_bin:
            return AnalysisResult(
                check_type=self.check_type,
                status=CheckStatus.UNAVAILABLE,
                duration_ms=0,
                tool_name=self.tool_name,
                error_message="Ruff binary not found in system path",
            )

        cmd = [ruff_bin, "check", "--output-format=json"]
        if target_files:
            # Filter only files that exist within source_dir
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
                    raw_stdout="No matching Python target files found for static analysis",
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
            stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=45.0)
            raw_stdout = stdout_bytes.decode("utf-8", errors="replace")
            raw_stderr = stderr_bytes.decode("utf-8", errors="replace")
        except TimeoutError:
            return AnalysisResult(
                check_type=self.check_type,
                status=CheckStatus.TIMEOUT,
                duration_ms=int((time.perf_counter() - start_time) * 1000),
                tool_name=self.tool_name,
                error_message="Ruff execution timed out after 45 seconds",
            )
        except Exception as exc:
            return AnalysisResult(
                check_type=self.check_type,
                status=CheckStatus.UNAVAILABLE,
                duration_ms=int((time.perf_counter() - start_time) * 1000),
                tool_name=self.tool_name,
                error_message=f"Failed to execute Ruff: {exc}",
            )

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        sanitized_stdout = sanitize_secret(raw_stdout)
        sanitized_stderr = sanitize_secret(raw_stderr)

        findings: list[RawFinding] = []
        errors_count = 0
        warnings_count = 0

        try:
            if raw_stdout.strip():
                records = json.loads(raw_stdout)
                for item in records:
                    code = item.get("code", "SYNTAX")
                    msg = item.get("message", "Lint violation")
                    filename = item.get("filename", "")
                    rel_path = (
                        os.path.relpath(filename, source_dir).replace("\\", "/")
                        if filename
                        else "unknown"
                    )

                    location = item.get("location", {})
                    end_location = item.get("end_location", {})
                    start_line = location.get("row")
                    end_line = end_location.get("row", start_line)

                    # Severity mapping
                    if code.startswith(("F", "E9")):
                        severity = "HIGH"
                        errors_count += 1
                        is_blocking = True
                    elif code.startswith("E"):
                        severity = "MEDIUM"
                        warnings_count += 1
                        is_blocking = False
                    else:
                        severity = "LOW"
                        warnings_count += 1
                        is_blocking = False

                    findings.append(
                        RawFinding(
                            rule_id=code,
                            message=msg,
                            severity=severity,
                            file_path=rel_path,
                            start_line=start_line,
                            end_line=end_line,
                            category="SYNTAX",
                            is_blocking=is_blocking,
                        )
                    )
        except json.JSONDecodeError as err:
            logger.warning("Failed to parse Ruff JSON output: %s", err)

        status = CheckStatus.FAILED if any(f.is_blocking for f in findings) else CheckStatus.PASSED

        return AnalysisResult(
            check_type=self.check_type,
            status=status,
            duration_ms=duration_ms,
            findings=findings,
            raw_stdout=sanitized_stdout,
            raw_stderr=sanitized_stderr,
            tool_name=self.tool_name,
            tool_version="0.17.3",
            metrics={
                "errors_count": errors_count,
                "warnings_count": warnings_count,
                "total_violations": len(findings),
            },
        )
