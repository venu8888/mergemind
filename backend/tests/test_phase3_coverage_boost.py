"""Coverage boost tests for Phase 3 endpoints, runners, and services."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.services.analysis.base import AnalysisResult, CheckStatus, CheckType, RawFinding
from app.services.analysis.runners.bandit_runner import BanditRunner
from app.services.analysis.runners.pip_audit_runner import PipAuditRunner
from app.services.analysis.runners.ruff_runner import RuffRunner
from app.services.sandbox.engine import SandboxEngine, SandboxExecutionResult
from app.services.sandbox.pytest_runner import PytestSandboxRunner
from app.services.verification.delta_classifier import ClassifiedFinding
from app.services.verification.quality_gate import PRQualityGateEvaluator
from app.services.verification.verifier import PRVerificationService


@pytest.mark.asyncio
async def test_health_assessment_api_endpoints(async_client: AsyncClient):
    """Test full GET and POST API endpoints for repository health assessment."""
    fake_id = str(uuid.uuid4())
    # 1. 404 on nonexistent repo
    resp = await async_client.get(f"/api/v1/repositories/{fake_id}/health")
    assert resp.status_code == 404

    resp_post = await async_client.post(f"/api/v1/repositories/{fake_id}/health/assess")
    assert resp_post.status_code == 404

    # 2. Create repo
    repo_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        repo = Repository(
            id=repo_id,
            github_repo_id=987654,
            full_name="venu8888/health-api-repo",
            default_branch="main",
            is_active=True,
        )
        session.add(repo)
        await session.commit()

    # 3. 404 when no assessments yet
    resp_empty = await async_client.get(f"/api/v1/repositories/{repo_id}/health")
    assert resp_empty.status_code == 404

    # 4. Trigger assessment via POST
    resp_assess = await async_client.post(
        f"/api/v1/repositories/{repo_id}/health/assess",
        json={"branch": "main", "commit_sha": "a" * 40},
    )
    assert resp_assess.status_code == 200
    data = resp_assess.json()
    assert data["repository_id"] == repo_id
    assert "health_score" in data
    assert "is_qualified" in data

    # 5. GET now succeeds with 200
    resp_get = await async_client.get(f"/api/v1/repositories/{repo_id}/health")
    assert resp_get.status_code == 200
    assert resp_get.json()["id"] == data["id"]


@pytest.mark.asyncio
async def test_pr_verification_api_endpoints(async_client: AsyncClient):
    """Test verification API endpoints for 404 conditions and verify trigger."""
    fake_id = str(uuid.uuid4())
    resp = await async_client.get(f"/api/v1/repositories/{fake_id}/pulls/99/verification")
    assert resp.status_code == 404

    resp_post = await async_client.post(f"/api/v1/repositories/{fake_id}/pulls/99/verify")
    assert resp_post.status_code == 404

    # Create repo and PR
    repo_id = str(uuid.uuid4())
    pr_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        repo = Repository(
            id=repo_id,
            github_repo_id=554433,
            full_name="venu8888/verify-api-repo",
            default_branch="main",
            is_active=True,
        )
        session.add(repo)
        pr = PullRequest(
            id=pr_id,
            repository_id=repo_id,
            pr_number=99,
            title="Coverage boost PR",
            state="open",
            author_username="testuser",
            base_branch="main",
            head_branch="patch-1",
            current_head_sha="b" * 40,
        )
        session.add(pr)
        await session.commit()

    # Trigger verify via POST endpoint
    resp_verify = await async_client.post(
        f"/api/v1/repositories/{repo_id}/pulls/99/verify",
        json={"commit_sha": "b" * 40},
    )
    assert resp_verify.status_code == 200
    verify_data = resp_verify.json()
    assert verify_data["pull_request_id"] == pr_id
    assert verify_data["commit_sha"] == "b" * 40


@pytest.mark.asyncio
async def test_verifier_findings_and_evidence_persistence():
    """Verify PRVerificationService correctly persists findings and evidence records."""
    repo_id = str(uuid.uuid4())
    pr_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        repo = Repository(
            id=repo_id,
            github_repo_id=778899,
            full_name="venu8888/evidence-repo",
            default_branch="main",
            is_active=True,
        )
        session.add(repo)
        pr = PullRequest(
            id=pr_id,
            repository_id=repo_id,
            pr_number=7,
            title="Evidence PR",
            state="open",
            author_username="testuser",
            base_branch="main",
            head_branch="patch-evidence",
            current_head_sha="c" * 40,
        )
        session.add(pr)
        await session.commit()

    finding_with_snippet = RawFinding(
        rule_id="B101",
        message="Assert used in production code",
        severity="LOW",
        category="SECURITY",
        file_path="app/core/check.py",
        start_line=10,
        end_line=10,
        code_snippet="assert value is not None",
        raw_output="B101: assert detected",
    )

    service = PRVerificationService()
    async with AsyncSessionLocal() as session:
        run = await service.verify_pull_request(
            repository_id=repo_id,
            pr_number=7,
            db=session,
            changed_files=["app/core/check.py"],
            head_findings=[finding_with_snippet],
            base_findings=[],
            check_results=[
                AnalysisResult(
                    check_type=CheckType.SECURITY_SCAN,
                    status=CheckStatus.PASSED,
                    tool_name="bandit",
                    findings=[finding_with_snippet],
                )
            ],
        )
        assert run.id is not None
        assert len(run.findings) == 1
        assert run.findings[0].fingerprint is not None


@pytest.mark.asyncio
async def test_quality_gate_evaluator_all_branches():
    """Exercise all branch conditions in PRQualityGateEvaluator."""
    evaluator = PRQualityGateEvaluator()

    # 1. Check failure
    res_failed = [
        AnalysisResult(
            check_type=CheckType.STATIC_LINT,
            status=CheckStatus.FAILED,
            tool_name="ruff",
            error_message="Linter crashed",
        )
    ]
    verdict1 = evaluator.evaluate({CheckType.STATIC_LINT}, res_failed, [])
    assert verdict1.gate_verdict == "FAILED"
    assert "Required check(s) failed" in verdict1.reasons[0]

    # 2. Completeness deficit (TIMEOUT or UNAVAILABLE)
    res_timeout = [
        AnalysisResult(
            check_type=CheckType.TEST_EXECUTION,
            status=CheckStatus.TIMEOUT,
            tool_name="pytest",
        )
    ]
    verdict2 = evaluator.evaluate({CheckType.TEST_EXECUTION}, res_timeout, [])
    assert verdict2.gate_verdict == "BLOCKED_COMPLETENESS"
    assert "Verification completeness is" in verdict2.reasons[0]

    # 3. Quality score below threshold (e.g. many medium issues)
    res_passed = [
        AnalysisResult(
            check_type=CheckType.STATIC_LINT, status=CheckStatus.PASSED, tool_name="ruff"
        )
    ]
    med_findings = [
        ClassifiedFinding(
            finding=RawFinding(
                rule_id=f"M{i}",
                message="Medium defect",
                severity="MEDIUM",
                category="SYNTAX",
                file_path="app/x.py",
            ),
            fingerprint=f"fp{i}",
            delta_status="INTRODUCED_NEW",
        )
        for i in range(5)  # 5 * 5 = 25 deduction -> 75 score < 80
    ]
    verdict3 = evaluator.evaluate({CheckType.STATIC_LINT}, res_passed, med_findings)
    assert verdict3.gate_verdict == "FAILED"
    assert verdict3.quality_score == 75.0

    # 4. Warning on non-blocking medium findings
    single_med = [
        ClassifiedFinding(
            finding=RawFinding(
                rule_id="M1",
                message="Single medium defect",
                severity="MEDIUM",
                category="SYNTAX",
                file_path="app/x.py",
            ),
            fingerprint="fp_med",
            delta_status="INTRODUCED_NEW",
        )
    ]
    verdict4 = evaluator.evaluate({CheckType.STATIC_LINT}, res_passed, single_med)
    assert verdict4.gate_verdict == "WARNING"
    assert "PR introduces 1 non-blocking medium" in verdict4.reasons[0]

    # 5. Warning on AMBIGUOUS_MODIFIED_CONTEXT
    ambiguous = [
        ClassifiedFinding(
            finding=RawFinding(
                rule_id="A1",
                message="Ambiguous context",
                severity="LOW",
                category="SYNTAX",
                file_path="app/x.py",
            ),
            fingerprint="fp_amb",
            delta_status="AMBIGUOUS_MODIFIED_CONTEXT",
        )
    ]
    verdict5 = evaluator.evaluate({CheckType.STATIC_LINT}, res_passed, ambiguous)
    assert verdict5.gate_verdict == "WARNING"
    assert any("ambiguous modified context" in r for r in verdict5.reasons)


@pytest.mark.asyncio
async def test_pip_audit_runner_mock_subprocess():
    """Test PipAuditRunner subprocess parsing, timeout and exception handling."""
    with tempfile.TemporaryDirectory() as tmpdir:
        req_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("requests==2.20.0\n")

        runner = PipAuditRunner()

        # Mock successful audit with JSON vulnerability records
        audit_payload = {
            "dependencies": [
                {
                    "name": "requests",
                    "version": "2.20.0",
                    "vulns": [
                        {
                            "id": "PYSEC-2018-123",
                            "description": "Session fixation vulnerability in requests",
                            "aliases": ["CVE-2018-18074"],
                        }
                    ],
                }
            ]
        }
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (json.dumps(audit_payload).encode(), b"")

        with (
            patch("shutil.which", return_value="/fake/pip-audit"),
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
        ):
            res = await runner.run(tmpdir)
            assert res.status == CheckStatus.FAILED
            assert len(res.findings) == 1
            assert res.findings[0].rule_id == "PYSEC-2018-123"
            assert res.findings[0].severity == "HIGH"

        # Mock TimeoutError
        with (
            patch("shutil.which", return_value="/fake/pip-audit"),
            patch("asyncio.create_subprocess_exec", side_effect=TimeoutError()),
        ):
            res_timeout = await runner.run(tmpdir)
            assert res_timeout.status == CheckStatus.TIMEOUT

        # Mock Generic Exception
        with (
            patch("shutil.which", return_value="/fake/pip-audit"),
            patch("asyncio.create_subprocess_exec", side_effect=RuntimeError("Subprocess failed")),
        ):
            res_exc = await runner.run(tmpdir)
            assert res_exc.status == CheckStatus.UNAVAILABLE


@pytest.mark.asyncio
async def test_ruff_and_bandit_error_paths():
    """Test Ruff and Bandit runners on timeouts, exceptions, and non-python targets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruff = RuffRunner()
        # Skipped when targets have no Python files
        res_skip = await ruff.run(tmpdir, target_files=["README.md", "image.png"])
        assert res_skip.status == CheckStatus.SKIPPED

        # Ruff timeout
        with (
            patch("shutil.which", return_value="/fake/ruff"),
            patch("asyncio.create_subprocess_exec", side_effect=TimeoutError()),
        ):
            res_to = await ruff.run(tmpdir)
            assert res_to.status == CheckStatus.TIMEOUT

        # Ruff exception
        with (
            patch("shutil.which", return_value="/fake/ruff"),
            patch("asyncio.create_subprocess_exec", side_effect=RuntimeError("exec error")),
        ):
            res_err = await ruff.run(tmpdir)
            assert res_err.status == CheckStatus.UNAVAILABLE

        bandit = BanditRunner()
        # Bandit timeout
        with (
            patch("shutil.which", return_value="/fake/bandit"),
            patch("asyncio.create_subprocess_exec", side_effect=TimeoutError()),
        ):
            res_b_to = await bandit.run(tmpdir)
            assert res_b_to.status == CheckStatus.TIMEOUT

        # Bandit exception
        with (
            patch("shutil.which", return_value="/fake/bandit"),
            patch("asyncio.create_subprocess_exec", side_effect=RuntimeError("exec error")),
        ):
            res_b_err = await bandit.run(tmpdir)
            assert res_b_err.status == CheckStatus.UNAVAILABLE


@pytest.mark.asyncio
async def test_pytest_sandbox_coverage_file_and_failures():
    """Test PytestSandboxRunner parsing test failures and coverage reports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test_core.py")
        with open(test_file, "w") as f:
            f.write("def test_one(): pass\n")

        cov_file = os.path.join(tmpdir, ".mergemind_cov.json")
        with open(cov_file, "w") as f:
            json.dump({"totals": {"percent_covered": 92.5}}, f)

        runner = PytestSandboxRunner()

        with patch.object(
            runner.sandbox,
            "execute_in_container",
            new_callable=AsyncMock,
            return_value=SandboxExecutionResult(
                exit_code=1,
                duration_ms=500,
                stdout="2 passed, 1 failed in 0.5s\nFAILED test_core.py::test_one - AssertionError",
                stderr="",
            ),
        ):
            res = await runner.run(tmpdir)
            assert res.status == CheckStatus.FAILED
            assert res.metrics["tests_passed"] == 2
            assert res.metrics["tests_failed"] == 1
            assert res.metrics["coverage_pct"] == 92.5
            assert len(res.findings) == 1
            assert res.findings[0].category == "TEST_REGRESSION"


@pytest.mark.asyncio
async def test_applicability_with_file_categories_and_tests():
    """Test check applicability determination with FileCategory enum and test files."""
    from app.services.github.classifier import FileCategory
    from app.services.verification.applicability import determine_applicable_checks

    checks1 = determine_applicable_checks([FileCategory.PYTHON_SOURCE, FileCategory.TEST_SUITE])
    assert CheckType.STATIC_LINT in checks1
    assert CheckType.SECURITY_SCAN in checks1
    assert CheckType.TEST_EXECUTION in checks1

    checks2 = determine_applicable_checks(["tests/test_something.py"])
    assert CheckType.TEST_EXECUTION in checks2
    assert CheckType.STATIC_LINT in checks2


@pytest.mark.asyncio
async def test_sandbox_engine_docker_available_and_env():
    """Test Docker availability check and environment variable injection."""
    engine = SandboxEngine()
    with patch("shutil.which", return_value="/usr/bin/docker"):
        assert engine.is_docker_available() is True
    with patch("shutil.which", return_value=None):
        assert engine.is_docker_available() is False


@pytest.mark.asyncio
async def test_verifier_with_diff_content_and_head_base_dirs():
    """Test PRVerificationService executing runner tasks and parsing diff content."""
    repo_id = str(uuid.uuid4())
    pr_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        repo = Repository(
            id=repo_id,
            github_repo_id=1122334,
            full_name="venu8888/diff-verify-repo",
            default_branch="main",
            is_active=True,
        )
        session.add(repo)
        pr = PullRequest(
            id=pr_id,
            repository_id=repo_id,
            pr_number=88,
            title="Diff PR",
            state="open",
            author_username="testuser",
            base_branch="main",
            head_branch="patch-88",
            current_head_sha="d" * 40,
        )
        session.add(pr)
        await session.commit()

    diff_str = """diff --git a/app/main.py b/app/main.py
index 1111111..2222222 100644
--- a/app/main.py
+++ b/app/main.py
@@ -1,2 +1,3 @@
 def old_fn():
+    new_code = True
     pass
"""
    service = PRVerificationService()
    # Mock runner run calls
    mock_ruff = AsyncMock(
        return_value=AnalysisResult(
            check_type=CheckType.STATIC_LINT,
            status=CheckStatus.PASSED,
            tool_name="ruff",
        )
    )
    mock_bandit = AsyncMock(
        return_value=AnalysisResult(
            check_type=CheckType.SECURITY_SCAN,
            status=CheckStatus.PASSED,
            tool_name="bandit",
        )
    )
    mock_pip_audit = AsyncMock(
        return_value=AnalysisResult(
            check_type=CheckType.DEPENDENCY_AUDIT,
            status=CheckStatus.SKIPPED,
            tool_name="pip-audit",
        )
    )
    mock_pytest = AsyncMock(
        return_value=AnalysisResult(
            check_type=CheckType.TEST_EXECUTION,
            status=CheckStatus.PASSED,
            tool_name="pytest",
        )
    )

    with (
        patch.object(service.ruff, "run", mock_ruff),
        patch.object(service.bandit, "run", mock_bandit),
        patch.object(service.pip_audit, "run", mock_pip_audit),
        patch.object(service.pytest, "run", mock_pytest),
        tempfile.TemporaryDirectory() as head_dir,
        tempfile.TemporaryDirectory() as base_dir,
    ):
        async with AsyncSessionLocal() as session:
            run = await service.verify_pull_request(
                repository_id=repo_id,
                pr_number=88,
                diff_content=diff_str,
                head_dir=head_dir,
                base_dir=base_dir,
                db=session,
            )
            assert run.id is not None
            assert run.gate_verdict == "PASSED"

    # Also test ValueError when PR not found
    async with AsyncSessionLocal() as session:
        with pytest.raises(ValueError, match="not found"):
            await service.verify_pull_request(
                repository_id=repo_id,
                pr_number=9999,
                db=session,
            )
