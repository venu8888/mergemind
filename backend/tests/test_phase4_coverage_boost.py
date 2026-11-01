"""Targeted coverage booster tests for Phase 4 CI failure intelligence, remediation, and endpoints."""

import os
import tempfile
from unittest.mock import AsyncMock, patch

import pytest

from app.core.database import AsyncSessionLocal
from app.models.ci_failure import CIFailureRecord
from app.models.installation import Installation
from app.models.remediation import RemediationProposal
from app.models.repository import Repository
from app.services.ci_intelligence.localizer import CIRootCauseLocalizer
from app.services.ci_intelligence.parser import CILogParser
from app.services.remediation.base import RemediationContext
from app.services.remediation.diff_validator import UnifiedDiffValidator
from app.services.remediation.mock_provider import MockRemediationProvider
from app.services.remediation.patch_verifier import PatchVerifier


@pytest.fixture
async def boost_repo():
    async with AsyncSessionLocal() as session:
        inst = Installation(
            github_installation_id=66778,
            account_login="boost-org",
            account_type="Organization",
        )
        session.add(inst)
        await session.flush()

        repo = Repository(
            github_repo_id=121212,
            installation_id=inst.id,
            name="boost-repo",
            full_name="boost-org/boost-repo",
            default_branch="main",
        )
        session.add(repo)
        await session.flush()

        failure = CIFailureRecord(
            repository_id=repo.id,
            workflow_run_id=777,
            workflow_name="Boost Run",
            job_name="boost-job",
            commit_sha="cboost1",
            branch="main",
            failure_category="LINT_ERROR",
            status="ANALYZED",
            error_message="E501 line too long",
            log_excerpt="app.py:10:1: E501 line too long",
            localized_files=[{"file_path": "app.py", "line_number": 10}],
            root_cause_analysis={"primary_error": "E501"},
        )
        session.add(failure)

        proposal = RemediationProposal(
            repository_id=repo.id,
            ci_failure_id=failure.id,
            title="Fix line length in app.py",
            description="Splits long string",
            target_commit_sha="cboost1",
            target_branch="main",
            status="PROPOSED",
            provider_name="mock",
            confidence_score=0.9,
            patch_diff="--- a/app.py\n+++ b/app.py\n@@ -1,1 +1,2 @@\n-long line\n+short\n+line\n",
            affected_files=["app.py"],
            rationale="Improves formatting",
            evidence_records={},
        )
        session.add(proposal)
        await session.commit()
        await session.refresh(repo)
        await session.refresh(failure)
        await session.refresh(proposal)
        return repo, failure, proposal


@pytest.mark.asyncio
async def test_ci_failure_endpoints_extended(async_client, boost_repo):
    """Test listing and failure detail endpoints with filters and error handling."""
    repo, failure, _ = boost_repo
    headers = {"X-API-Key": "test-api-key-12345"}

    # 1. List with status filter
    res = await async_client.get(
        f"/api/v1/repositories/{repo.id}/ci-failures?status=ANALYZED&limit=10",
        headers=headers,
    )
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # 2. List with non-existent repo (404)
    res404 = await async_client.get(
        "/api/v1/repositories/non-existent-id/ci-failures",
        headers=headers,
    )
    assert res404.status_code == 404

    # 3. Get detail
    res_det = await async_client.get(
        f"/api/v1/repositories/{repo.id}/ci-failures/{failure.id}",
        headers=headers,
    )
    assert res_det.status_code == 200
    assert res_det.json()["id"] == failure.id

    # 4. Get detail missing (404)
    res_det_404 = await async_client.get(
        f"/api/v1/repositories/{repo.id}/ci-failures/missing-failure-id",
        headers=headers,
    )
    assert res_det_404.status_code == 404


@pytest.mark.asyncio
async def test_remediation_endpoints_extended(async_client, boost_repo):
    """Test proposal lookup, repository listings, and error handling."""
    repo, failure, proposal = boost_repo
    headers = {"X-API-Key": "test-api-key-12345"}

    # 1. Get proposal by ID
    res = await async_client.get(f"/api/v1/remediations/{proposal.id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["title"] == "Fix line length in app.py"

    # 2. Get missing proposal by ID (404)
    res404 = await async_client.get("/api/v1/remediations/non-existent-prop-id", headers=headers)
    assert res404.status_code == 404

    # 3. List repo remediations with status filter
    res_list = await async_client.get(
        f"/api/v1/repositories/{repo.id}/remediations?status=PROPOSED",
        headers=headers,
    )
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # 4. Verify missing proposal (404)
    res_ver_404 = await async_client.post(
        "/api/v1/remediations/missing-prop-id/verify",
        headers=headers,
    )
    assert res_ver_404.status_code == 404

    # 5. Create PR missing proposal (404)
    res_pr_404 = await async_client.post(
        "/api/v1/remediations/missing-prop-id/create-pr",
        headers=headers,
    )
    assert res_pr_404.status_code == 404


@pytest.mark.asyncio
async def test_dashboard_history_endpoint(async_client, boost_repo):
    """Test health history endpoint."""
    repo, _, _ = boost_repo
    headers = {"X-API-Key": "test-api-key-12345"}

    res = await async_client.get(f"/api/v1/repositories/{repo.id}/health/history", headers=headers)
    assert res.status_code == 200

    res404 = await async_client.get(
        "/api/v1/repositories/missing-repo/health/history", headers=headers
    )
    assert res404.status_code == 404


def test_localizer_hypotheses_all_categories():
    """Test advisory hypotheses generation across all failure categories."""
    localizer = CIRootCauseLocalizer()
    loc = {"file_path": "security.py", "line_number": 20, "enclosing_symbol": "login"}

    categories = [
        "SECURITY_VIOLATION",
        "LINT_ERROR",
        "DEPENDENCY_CONFLICT",
        "TIMEOUT",
        "INFRASTRUCTURE_FAILURE",
        "BUILD_ERROR",
        "TEST_FAILURE",
    ]

    for cat in categories:
        hyp = localizer._generate_advisory_hypothesis(cat, "Sample Error", loc)
        assert len(hyp) > 10
        assert "[ADVISORY HYPOTHESIS]" in hyp

    # Test with loc is None
    hyp_no_loc = localizer._generate_advisory_hypothesis("TIMEOUT", "Job timed out", None)
    assert "runtime" in hyp_no_loc.lower() or "threshold" in hyp_no_loc.lower()


def test_parser_edge_cases():
    """Test parser with empty string and generic regex locations."""
    parser = CILogParser()
    assert parser.sanitize_logs("") == ""

    parsed = parser.parse("")
    assert parsed["primary_error"] == "CI job failed without explicit error trace"

    # Generic file:line pattern
    log = "Building frontend\nsrc/components/App.tsx:42:10 - TS2304 Cannot find name\n"
    res = parser.parse(log)
    assert any("App.tsx" in loc["file_path"] for loc in res["localized_files"])


@pytest.mark.asyncio
async def test_mock_provider_all_strategies():
    """Test MockRemediationProvider across categories."""
    provider = MockRemediationProvider()

    for cat in ["LINT_ERROR", "SECURITY_VIOLATION", "DEPENDENCY_CONFLICT", "BUILD_ERROR"]:
        ctx = RemediationContext(
            repository_id="r1",
            repository_name="repo1",
            target_commit_sha="c1",
            target_branch="main",
            error_message="Test error",
            failure_category=cat,
            target_file="module.py",
            target_line=5,
        )
        res = await provider.generate_proposal(ctx)
        assert res.patch_diff
        assert "module.py" in res.affected_files


def test_diff_validator_fallback_lines():
    """Test diff validator edge cases."""
    validator = UnifiedDiffValidator(max_lines=50)

    # Empty
    is_valid, err, _ = validator.validate("")
    assert not is_valid

    # Missing hunk markers
    is_valid, err, _ = validator.validate("diff --git a/file.py b/file.py\n+hello")
    assert not is_valid

    # Fallback without diff --git header
    valid_no_git = "--- a/file.py\n+++ b/file.py\n@@ -1,1 +1,1 @@\n-old\n+new\n"
    is_valid, err, files = validator.validate(valid_no_git)
    assert is_valid
    assert "file.py" in files


@pytest.mark.asyncio
async def test_patch_verifier_regressions_and_failures():
    """Test regression detection and failed patch application in PatchVerifier."""
    verifier = PatchVerifier()
    from app.services.analysis.base import RawFinding

    finding_baseline = RawFinding(
        rule_id="B101",
        message="Assert used",
        severity="LOW",
        file_path="a.py",
        start_line=1,
        end_line=1,
    )
    finding_new_regression = RawFinding(
        rule_id="B102",
        message="Exec used",
        severity="HIGH",
        file_path="a.py",
        start_line=2,
        end_line=2,
    )

    with tempfile.TemporaryDirectory() as base_dir:
        test_file = os.path.join(base_dir, "a.py")
        with open(test_file, "w") as f:
            f.write("print('hello')\n")

        async with AsyncSessionLocal() as session:
            inst = Installation(
                github_installation_id=44556, account_login="org-reg", account_type="Organization"
            )
            session.add(inst)
            await session.flush()
            repo = Repository(
                github_repo_id=556677,
                installation_id=inst.id,
                name="reg-repo",
                full_name="org-reg/reg-repo",
                default_branch="main",
            )
            session.add(repo)
            await session.flush()

            prop = RemediationProposal(
                repository_id=repo.id,
                title="Regressive proposal",
                description="desc",
                target_commit_sha="c1",
                target_branch="main",
                status="PROPOSED",
                provider_name="mock",
                confidence_score=0.8,
                patch_diff="--- a/a.py\n+++ b/a.py\n@@ -1,1 +1,2 @@\n print('hello')\n+exec('bad')\n",
                affected_files=["a.py"],
                rationale="test",
                evidence_records={},
            )
            session.add(prop)
            await session.commit()
            await session.refresh(prop)

            # 1. Test regression introduced
            with patch.object(verifier, "_run_analysis", new_callable=AsyncMock) as mock_a:
                mock_a.side_effect = [
                    [finding_baseline],
                    [finding_baseline, finding_new_regression],
                ]
                v_record = await verifier.verify_proposal(
                    session, prop.id, base_source_dir=base_dir
                )
                assert v_record.sandbox_status == "REGRESSION_DETECTED"
                assert v_record.is_verified is False

            # 2. Test failed patch application
            with patch(
                "app.services.remediation.patch_verifier.apply_unified_diff",
                return_value=(False, "Failed hunk"),
            ):
                v_failed = await verifier.verify_proposal(
                    session, prop.id, base_source_dir=base_dir
                )
                assert v_failed.sandbox_status == "FAILED"
                assert v_failed.is_verified is False
