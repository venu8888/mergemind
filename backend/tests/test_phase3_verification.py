"""Unit and integration tests for PR Verification, Delta Classification, and Quality Gate."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.services.analysis.base import AnalysisResult, CheckStatus, CheckType, RawFinding
from app.services.verification.applicability import determine_applicable_checks
from app.services.verification.delta_classifier import (
    ClassifiedFinding,
)
from app.services.verification.fingerprint import (
    compute_finding_fingerprint,
)
from app.services.verification.quality_gate import PRQualityGateEvaluator
from app.services.verification.verifier import PRVerificationService


def test_fingerprint_normalization_and_stability():
    """Verify finding fingerprint is stable across line numbers and variable naming noise."""
    fp1 = compute_finding_fingerprint(
        rule_id="B602",
        message="Use of shell=True in subprocess call: cmd_exec()",
        enclosing_symbol="execute_task",
        code_snippet="   subprocess.run(cmd, shell=True)  \n",
    )
    fp2 = compute_finding_fingerprint(
        rule_id="B602",
        message="Use of shell=True in subprocess call: cmd_exec()",
        enclosing_symbol="execute_task",
        code_snippet="subprocess.run(cmd, shell=True)",
    )
    # Exact match despite whitespace variations
    assert fp1 == fp2
    assert len(fp1) == 64

    # Different rule produces different fingerprint
    fp3 = compute_finding_fingerprint(
        rule_id="B101",
        message="Use of assert detected",
        enclosing_symbol="execute_task",
        code_snippet="subprocess.run(cmd, shell=True)",
    )
    assert fp1 != fp3


def test_precalculated_check_applicability():
    """Verify check applicability determines the denominator without padding."""
    # 1. Documentation-only PR
    docs_pr = ["README.md", "docs/architecture.md", "LICENSE"]
    assert determine_applicable_checks(docs_pr) == set()

    # 2. Python code PR
    py_pr = ["app/main.py", "app/services/worker.py"]
    py_checks = determine_applicable_checks(py_pr)
    assert CheckType.STATIC_LINT in py_checks
    assert CheckType.SECURITY_SCAN in py_checks
    assert CheckType.TEST_EXECUTION in py_checks
    assert CheckType.DEPENDENCY_AUDIT not in py_checks

    # 3. Dependency-only PR
    dep_pr = ["requirements.txt", "Pipfile.lock"]
    dep_checks = determine_applicable_checks(dep_pr)
    assert CheckType.DEPENDENCY_AUDIT in dep_checks
    assert CheckType.STATIC_LINT not in dep_checks

    # 4. Mixed PR
    mixed_pr = ["README.md", "backend/app/main.py", "pyproject.toml"]
    mixed_checks = determine_applicable_checks(mixed_pr)
    assert len(mixed_checks) == 4


def test_quality_gate_anti_masking_rule():
    """Verify critical introduced defects reject merge even if completeness is 100%."""
    evaluator = PRQualityGateEvaluator()
    applicable = {CheckType.STATIC_LINT, CheckType.SECURITY_SCAN, CheckType.TEST_EXECUTION}

    # All checks passed execution (completeness = 100%)
    results = [
        AnalysisResult(
            check_type=CheckType.STATIC_LINT, status=CheckStatus.PASSED, tool_name="ruff"
        ),
        AnalysisResult(
            check_type=CheckType.SECURITY_SCAN, status=CheckStatus.PASSED, tool_name="bandit"
        ),
        AnalysisResult(
            check_type=CheckType.TEST_EXECUTION, status=CheckStatus.PASSED, tool_name="pytest"
        ),
    ]

    # But Bandit caught a CRITICAL newly introduced defect
    critical_raw = RawFinding(
        rule_id="B602",
        message="Command injection via shell=True",
        severity="CRITICAL",
        category="SECURITY",
        file_path="app/exec.py",
        is_blocking=True,
    )
    classified = [
        ClassifiedFinding(
            finding=critical_raw,
            fingerprint="abc12345",
            delta_status="INTRODUCED_NEW",
        )
    ]

    verdict = evaluator.evaluate(applicable, results, classified)
    assert verdict.verification_completeness == 100.0
    # Anti-masking rule triggered:
    assert verdict.gate_verdict == "FAILED"
    assert any("critical/high severity defect" in r for r in verdict.reasons)
    assert verdict.quality_score == 70.0  # 100 - 30


def test_quality_gate_baseline_defect_tolerance():
    """Verify existing baseline findings do NOT penalize the PR quality score."""
    evaluator = PRQualityGateEvaluator()
    applicable = {CheckType.STATIC_LINT}
    results = [
        AnalysisResult(
            check_type=CheckType.STATIC_LINT, status=CheckStatus.PASSED, tool_name="ruff"
        )
    ]

    baseline_raw = RawFinding(
        rule_id="E501",
        message="Line too long",
        severity="LOW",
        category="STYLE",
        file_path="app/legacy.py",
    )
    classified = [
        ClassifiedFinding(
            finding=baseline_raw,
            fingerprint="def67890",
            delta_status="EXISTING_BASELINE",
        )
    ]

    verdict = evaluator.evaluate(applicable, results, classified)
    # Zero introduced defects -> Score remains 100.0 and PASSED
    assert verdict.quality_score == 100.0
    assert verdict.gate_verdict == "PASSED"
    assert verdict.introduced_defects_count == 0


@pytest.mark.asyncio
async def test_pr_verification_service_and_api(async_client: AsyncClient):
    """Integration test verifying end-to-end PR verification persistence and endpoints."""
    repo_id = str(uuid.uuid4())
    pr_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        repo = Repository(
            id=repo_id,
            github_repo_id=1234567,
            full_name="venu8888/verification-test-repo",
            default_branch="main",
            is_active=True,
        )
        session.add(repo)
        pr = PullRequest(
            id=pr_id,
            repository_id=repo_id,
            pr_number=42,
            title="Feature PR with verification",
            state="open",
            author_username="testuser",
            base_branch="main",
            head_branch="feature-x",
            current_head_sha="f" * 40,
        )
        session.add(pr)
        await session.commit()

    # Query verification before execution -> 404
    resp = await async_client.get(f"/api/v1/repositories/{repo_id}/pulls/42/verification")
    assert resp.status_code == 404

    # Trigger verification
    service = PRVerificationService()
    async with AsyncSessionLocal() as session:
        run = await service.verify_pull_request(
            repository_id=repo_id,
            pr_number=42,
            db=session,
            changed_files=["app/services/core.py"],
            check_results=[
                AnalysisResult(
                    check_type=CheckType.STATIC_LINT, status=CheckStatus.PASSED, tool_name="ruff"
                ),
                AnalysisResult(
                    check_type=CheckType.SECURITY_SCAN,
                    status=CheckStatus.PASSED,
                    tool_name="bandit",
                ),
                AnalysisResult(
                    check_type=CheckType.TEST_EXECUTION,
                    status=CheckStatus.PASSED,
                    tool_name="pytest",
                ),
            ],
            head_findings=[],
            base_findings=[],
        )
        assert run.id is not None
        assert run.gate_verdict == "PASSED"
        assert run.verification_completeness == 100.0

    # Query verification after execution -> 200 OK
    resp_after = await async_client.get(f"/api/v1/repositories/{repo_id}/pulls/42/verification")
    assert resp_after.status_code == 200
    data = resp_after.json()
    assert data["pull_request_id"] == pr_id
    assert data["commit_sha"] == "f" * 40
    assert data["gate_verdict"] == "PASSED"
    assert data["verification_completeness"] == 100.0
