"""Isolated pytest test execution and coverage extraction runner."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from app.services.analysis.base import (
    AnalysisResult,
    BaseAnalysisRunner,
    CheckStatus,
    CheckType,
    RawFinding,
)
from app.services.sandbox.engine import SandboxEngine

logger = logging.getLogger(__name__)


class PytestSandboxRunner(BaseAnalysisRunner):
    """Executes pytest inside an ephemeral network-isolated container and extracts test metrics."""

    tool_name: str = "pytest"
    check_type: CheckType = CheckType.TEST_EXECUTION

    def __init__(self, sandbox_engine: SandboxEngine | None = None):
        self.sandbox = sandbox_engine or SandboxEngine()

    def has_test_suite(self, source_dir: str) -> bool:
        """Check if tests exist in the source directory."""
        tests_dir = os.path.join(source_dir, "tests")
        if os.path.isdir(tests_dir):
            return True

        for _root, _, files in os.walk(source_dir):
            for f in files:
                if f.startswith("test_") and f.endswith(".py"):
                    return True
                if f.endswith("_test.py"):
                    return True
        return False

    async def run(
        self,
        source_dir: str,
        target_files: list[str] | None = None,
        config_override: dict[str, Any] | None = None,
    ) -> AnalysisResult:
        if not self.has_test_suite(source_dir):
            return AnalysisResult(
                check_type=self.check_type,
                status=CheckStatus.SKIPPED,
                duration_ms=0,
                tool_name=self.tool_name,
                raw_stdout="No automated test suite discovered in repository",
                metrics={
                    "tests_discovered": False,
                    "tests_total": 0,
                    "tests_passed": 0,
                    "tests_failed": 0,
                    "coverage_pct": None,
                },
            )

        cmd = [
            "python",
            "-m",
            "pytest",
            "-v",
            "--cov=.",
            "--cov-report=json:/workspace/.mergemind_cov.json",
        ]

        result = await self.sandbox.execute_in_container(
            workspace_dir=source_dir,
            command=cmd,
        )

        if result.timed_out:
            return AnalysisResult(
                check_type=self.check_type,
                status=CheckStatus.TIMEOUT,
                duration_ms=result.duration_ms,
                tool_name=self.tool_name,
                raw_stdout=result.stdout,
                raw_stderr=result.stderr,
                error_message=f"Test suite execution timed out after {self.sandbox.timeout_seconds}s",
            )

        if result.error and result.exit_code == -1:
            return AnalysisResult(
                check_type=self.check_type,
                status=CheckStatus.UNAVAILABLE,
                duration_ms=result.duration_ms,
                tool_name=self.tool_name,
                raw_stdout=result.stdout,
                raw_stderr=result.stderr,
                error_message=result.error,
            )

        # Parse test results from stdout
        passed = 0
        failed = 0
        skipped = 0
        coverage_pct: float | None = None

        pass_match = re.search(r"(\d+)\s+passed", result.stdout)
        fail_match = re.search(r"(\d+)\s+failed", result.stdout)
        skip_match = re.search(r"(\d+)\s+skipped", result.stdout)

        if pass_match:
            passed = int(pass_match.group(1))
        if fail_match:
            failed = int(fail_match.group(1))
        if skip_match:
            skipped = int(skip_match.group(1))

        total_tests = passed + failed + skipped

        # Attempt reading coverage JSON if written to workspace
        cov_file = os.path.join(source_dir, ".mergemind_cov.json")
        if os.path.exists(cov_file):
            try:
                with open(cov_file, encoding="utf-8") as fp:
                    cov_data = json.load(fp)
                    totals = cov_data.get("totals", {})
                    coverage_pct = round(totals.get("percent_covered", 0.0), 2)
            except Exception as err:
                logger.debug("Failed to read coverage JSON: %s", err)
            finally:
                try:
                    os.remove(cov_file)
                except OSError:
                    pass

        findings: list[RawFinding] = []
        if failed > 0 or result.exit_code not in (0, 5):
            # Parse failures into findings
            findings.append(
                RawFinding(
                    rule_id="TEST_SUITE_FAILURE",
                    message=f"Test suite execution failed with {failed} failing test(s). Exit code: {result.exit_code}.",
                    severity="HIGH",
                    file_path="tests",
                    category="TEST_REGRESSION",
                    is_blocking=True,
                )
            )
            status = CheckStatus.FAILED
        elif total_tests == 0 and result.exit_code == 5:
            status = CheckStatus.SKIPPED
        else:
            status = CheckStatus.PASSED

        pass_rate = (passed / total_tests * 100.0) if total_tests > 0 else 0.0

        metrics = {
            "tests_discovered": True,
            "tests_total": total_tests,
            "tests_passed": passed,
            "tests_failed": failed,
            "tests_skipped": skipped,
            "pass_rate_pct": round(pass_rate, 2),
            "coverage_pct": coverage_pct,
        }

        return AnalysisResult(
            check_type=self.check_type,
            status=status,
            duration_ms=result.duration_ms,
            findings=findings,
            raw_stdout=result.stdout,
            raw_stderr=result.stderr,
            tool_name=self.tool_name,
            tool_version="8.4.2",
            metrics=metrics,
        )
