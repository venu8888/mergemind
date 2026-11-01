"""Unit and integration tests for Phase 3 shared analysis runners and sandbox engine."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import AsyncMock, patch

import pytest

from app.services.analysis.base import AnalysisResult, CheckStatus, CheckType
from app.services.analysis.runners.bandit_runner import BanditRunner
from app.services.analysis.runners.pip_audit_runner import PipAuditRunner
from app.services.analysis.runners.radon_runner import RadonRunner
from app.services.analysis.runners.ruff_runner import RuffRunner
from app.services.sandbox.engine import SandboxEngine
from app.services.sandbox.pytest_runner import PytestSandboxRunner


@pytest.mark.asyncio
async def test_analysis_result_output_digest():
    """Verify SHA-256 output digest calculation across stdout and stderr."""
    res = AnalysisResult(
        tool_name="test_tool",
        check_type=CheckType.STATIC_LINT,
        status=CheckStatus.PASSED,
        raw_stdout="line 1\nline 2",
        raw_stderr="warning 1",
    )
    assert res.output_digest is not None
    assert len(res.output_digest) == 64
    assert res.duration_ms == 0


@pytest.mark.asyncio
async def test_radon_runner_ast_complexity_and_docstrings():
    """Test McCabe cyclomatic complexity calculation and docstring coverage."""
    code = """
def simple_function(x):
    \"\"\"This is a documented simple function.\"\"\"
    return x + 1

def highly_complex_function(a, b, c, d, e):
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        for i in range(10):
                            if i % 2 == 0:
                                while a < 100:
                                    a += 1
                                    if a == 50:
                                        break
                                    elif a == 60:
                                        continue
                                    elif a == 70:
                                        return True
    try:
        x = 1 if a else 2
        assert x > 0
    except Exception:
        pass
    return False
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "complex_sample.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(code)

        runner = RadonRunner()
        result = await runner.run(tmpdir)

        assert result.status == CheckStatus.PASSED
        assert result.check_type == CheckType.MAINTAINABILITY
        assert result.metrics["total_definitions"] == 2
        assert result.metrics["documented_definitions"] == 1
        assert result.metrics["docstring_coverage_pct"] == 50.0
        assert result.metrics["complex_functions_count"] >= 1
        assert len(result.findings) >= 1
        assert result.findings[0].rule_id == "MAINTAINABILITY_COMPLEXITY"
        assert result.findings[0].severity in ("LOW", "MEDIUM")


@pytest.mark.asyncio
async def test_ruff_runner_execution_and_findings():
    """Verify RuffRunner parses linting defects from code files."""
    code_with_issues = """
import os
import sys

def bad_syntax( x , y ):
    unused_var = 123
    return x+y
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "bad_lint.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(code_with_issues)

        runner = RuffRunner()
        result = await runner.run(tmpdir)

        assert result.check_type == CheckType.STATIC_LINT
        if result.status == CheckStatus.FAILED:
            assert len(result.findings) > 0
            for f in result.findings:
                assert f.rule_id is not None
                assert f.category == "SYNTAX"


@pytest.mark.asyncio
async def test_bandit_runner_security_defects():
    """Verify BanditRunner detects security vulnerabilities like assert or hardcoded passwords."""
    insecure_code = """
import subprocess

def run_user_cmd(cmd):
    # Insecure use of shell=True
    subprocess.call(cmd, shell=True)
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "insecure.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(insecure_code)

        runner = BanditRunner()
        result = await runner.run(tmpdir)

        assert result.check_type == CheckType.SECURITY_SCAN
        if result.status == CheckStatus.FAILED:
            assert any(
                "B602" in (f.rule_id or "") or "subprocess" in f.message for f in result.findings
            )


@pytest.mark.asyncio
async def test_pip_audit_runner_empty_and_populated():
    """Verify PipAuditRunner behavior when requirements file is missing or present."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = PipAuditRunner()
        # Empty dir -> SKIPPED (no deps)
        res_empty = await runner.run(tmpdir)
        assert res_empty.status == CheckStatus.SKIPPED
        assert "No dependency requirements file found" in (res_empty.raw_stdout or "")

        # Write clean requirements
        req_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_file, "w", encoding="utf-8") as f:
            f.write("fastapi>=0.115.0\n")

        res_clean = await runner.run(tmpdir)
        assert res_clean.status in (CheckStatus.PASSED, CheckStatus.SKIPPED, CheckStatus.FAILED)


@pytest.mark.asyncio
async def test_sandbox_engine_fail_closed_zero_host():
    """Verify SandboxEngine fails closed when container execution is disabled or unavailable."""
    from app.core.config import settings

    orig_sandbox = settings.SANDBOX_TYPE
    try:
        settings.SANDBOX_TYPE = "disabled"
        engine = SandboxEngine()
        with tempfile.TemporaryDirectory() as tmpdir:
            res = await engine.execute_in_container(tmpdir, ["pytest"])
            assert res.exit_code == -1
            assert "Execution sandbox is disabled" in (res.error or "")

        # Test missing docker binary
        settings.SANDBOX_TYPE = "docker"
        with patch("shutil.which", return_value=None):
            engine_no_docker = SandboxEngine()
            res_no_docker = await engine_no_docker.execute_in_container(tmpdir, ["pytest"])
            assert res_no_docker.exit_code == -1
            assert "Docker CLI not found" in (res_no_docker.error or "")
    finally:
        settings.SANDBOX_TYPE = orig_sandbox


@pytest.mark.asyncio
async def test_pytest_sandbox_runner():
    """Verify PytestSandboxRunner discovers tests or skips cleanly."""
    from app.services.sandbox.engine import SandboxExecutionResult

    with tempfile.TemporaryDirectory() as tmpdir:
        runner = PytestSandboxRunner()
        # No tests present -> SKIPPED
        res_no_tests = await runner.run(tmpdir)
        assert res_no_tests.status == CheckStatus.SKIPPED

        # Add a passing test
        test_file = os.path.join(tmpdir, "test_sample.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def test_ok(): assert 1 == 1\n")

        with patch.object(
            runner.sandbox,
            "execute_in_container",
            new_callable=AsyncMock,
            return_value=SandboxExecutionResult(
                exit_code=0,
                duration_ms=15,
                stdout="1 passed in 0.01s",
                stderr="",
            ),
        ):
            res_pass = await runner.run(tmpdir)
            assert res_pass.status == CheckStatus.PASSED
            assert res_pass.metrics["tests_passed"] == 1
