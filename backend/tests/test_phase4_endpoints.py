"""Tests for Phase 4 API Endpoints & Invariant Verification (WP 4.F, WP 4.H)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.database import AsyncSessionLocal
from app.models.ci_failure import CIFailureRecord
from app.models.installation import Installation
from app.models.repository import Repository
from app.models.repository_health import RepositoryHealthAssessment


@pytest.fixture
async def sample_repo():
    """Sets up a test repository with initial health assessment and CI failure."""
    async with AsyncSessionLocal() as session:
        inst = Installation(
            github_installation_id=11223,
            account_login="endpoint-test-org",
            account_type="Organization",
        )
        session.add(inst)
        await session.flush()

        repo = Repository(
            github_repo_id=778899,
            installation_id=inst.id,
            name="endpoint-test-repo",
            full_name="endpoint-test-org/endpoint-test-repo",
            default_branch="main",
        )
        session.add(repo)
        await session.flush()

        # Seed initial health assessment with score = 65.0
        health = RepositoryHealthAssessment(
            repository_id=repo.id,
            commit_sha="init12345678",
            branch_name="main",
            health_score=65.0,
            assessment_completeness=0.8,
            is_qualified=True,
            qualification_reason="QUALIFIED_SCORE",
            code_quality_score=70.0,
            security_score=80.0,
            dependency_score=60.0,
            test_health_score=50.0,
            scoring_policy_version="4.2.0",
            dimension_status={},
            summary_metrics={},
            status="COMPLETED",
        )
        session.add(health)

        # Seed initial CI failure
        failure = CIFailureRecord(
            repository_id=repo.id,
            workflow_run_id=505,
            workflow_name="Unit Tests",
            job_name="pytest",
            commit_sha="fail12345678",
            branch="main",
            failure_category="TEST_FAILURE",
            status="ANALYZED",
            error_message="AssertionError: assert 1 == 2",
            log_excerpt="FAILED test.py - AssertionError",
            localized_files=[{"file_path": "test.py", "line_number": 5}],
            root_cause_analysis={"primary_error": "AssertionError"},
        )
        session.add(failure)
        await session.commit()
        await session.refresh(repo)
        await session.refresh(failure)
        return repo, failure


@pytest.mark.asyncio
async def test_dashboard_endpoint(async_client, sample_repo):
    """Verify GET /api/v1/repositories/{repo_id}/dashboard returns full Phase 4 payload."""
    repo, _ = sample_repo
    headers = {"X-API-Key": "test-api-key-12345"}
    response = await async_client.get(f"/api/v1/repositories/{repo.id}/dashboard", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["repository"]["full_name"] == "endpoint-test-org/endpoint-test-repo"
    assert data["latest_health"]["health_score"] == 65.0
    assert len(data["open_ci_failures"]) >= 1
    assert "summary_counts" in data


@pytest.mark.asyncio
async def test_ci_failure_ingestion_endpoint(async_client, sample_repo):
    """Verify POST /api/v1/ci-failures/ingest parses, sanitizes, and stores failure."""
    repo, _ = sample_repo
    headers = {"X-API-Key": "test-api-key-12345"}

    payload = {
        "repository_id": str(repo.id),
        "workflow_run_id": 999,
        "workflow_name": "Integration Tests",
        "job_name": "pytest",
        "commit_sha": "abc11223344",
        "branch": "main",
        "raw_logs": "FAILED tests/test_api.py::test_login - AssertionError\nSECRET=ghp_exampleToken1234567890abcdef1234567890\n",
    }

    response = await async_client.post("/api/v1/ci-failures/ingest", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["failure_category"] == "TEST_FAILURE"
    assert "ghp_exampleToken" not in data["log_excerpt"]
    assert data["status"] == "ANALYZED"


@pytest.mark.asyncio
async def test_remediation_lifecycle_endpoints(async_client, sample_repo):
    """Verify Propose -> Verify -> Create PR endpoints."""
    repo, failure = sample_repo
    headers = {"X-API-Key": "test-api-key-12345"}

    # 1. Propose
    prop_res = await async_client.post(
        "/api/v1/remediations/propose",
        json={"ci_failure_id": str(failure.id)},
        headers=headers,
    )
    assert prop_res.status_code == 201
    proposal = prop_res.json()
    proposal_id = proposal["id"]
    assert proposal["status"] == "PROPOSED"

    # 2. Verify
    from app.services.analysis.base import RawFinding

    sample_finding = RawFinding(
        rule_id="B101",
        message="Assert used",
        severity="MEDIUM",
        file_path="test.py",
        start_line=5,
        end_line=5,
        enclosing_symbol="test",
        code_snippet="assert 1 == 2",
        tool_source="bandit",
    )

    with patch(
        "app.services.remediation.patch_verifier.PatchVerifier._run_analysis",
        new_callable=AsyncMock,
    ) as mock_analysis:
        mock_analysis.side_effect = [
            [sample_finding],
            [],
        ]

        ver_res = await async_client.post(
            f"/api/v1/remediations/{proposal_id}/verify",
            headers=headers,
        )
        assert ver_res.status_code == 200
        verification = ver_res.json()
        assert verification["is_verified"] is True
        assert verification["sandbox_status"] in ["PASSED", "VERIFIED"]

    # 3. Create Draft PR
    pr_res = await async_client.post(
        f"/api/v1/remediations/{proposal_id}/create-pr",
        json={"base_branch": "main"},
        headers=headers,
    )
    assert pr_res.status_code == 201
    pr_data = pr_res.json()
    assert pr_data["pr_number"] is not None
    assert "mergemind/fix-" in pr_data["branch_name"]


@pytest.mark.asyncio
async def test_remediation_release_gate_invariant(async_client, sample_repo):
    """
    CRITICAL INVARIANT TEST:
    Assert that proposing a remediation, verifying a patch, and creating a Draft PR
    does NOT alter the repository health score. Only post-merge reassessment updates it.
    """
    repo, failure = sample_repo
    headers = {"X-API-Key": "test-api-key-12345"}

    # Step 0: Check initial health score
    init_dash = await async_client.get(f"/api/v1/repositories/{repo.id}/dashboard", headers=headers)
    assert init_dash.status_code == 200
    baseline_score = init_dash.json()["latest_health"]["health_score"]
    assert baseline_score == 65.0

    # Step 1: Propose remediation
    prop_res = await async_client.post(
        "/api/v1/remediations/propose",
        json={"ci_failure_id": str(failure.id)},
        headers=headers,
    )
    assert prop_res.status_code == 201
    prop_id = prop_res.json()["id"]

    # Invariant Check 1: Health score must NOT change after proposal
    dash_after_prop = await async_client.get(
        f"/api/v1/repositories/{repo.id}/dashboard", headers=headers
    )
    assert dash_after_prop.json()["latest_health"]["health_score"] == baseline_score

    # Step 2: Verify candidate patch
    from app.services.analysis.base import RawFinding

    sample_finding = RawFinding(
        rule_id="B101",
        message="Assert used",
        severity="MEDIUM",
        file_path="test.py",
        start_line=5,
        end_line=5,
        enclosing_symbol="test",
        code_snippet="assert 1 == 2",
        tool_source="bandit",
    )

    with patch(
        "app.services.remediation.patch_verifier.PatchVerifier._run_analysis",
        new_callable=AsyncMock,
    ) as mock_analysis:
        mock_analysis.side_effect = [
            [sample_finding],
            [],
        ]
        ver_res = await async_client.post(f"/api/v1/remediations/{prop_id}/verify", headers=headers)
        assert ver_res.status_code == 200

    # Invariant Check 2: Health score must NOT change after verified patch
    dash_after_ver = await async_client.get(
        f"/api/v1/repositories/{repo.id}/dashboard", headers=headers
    )
    assert dash_after_ver.json()["latest_health"]["health_score"] == baseline_score

    # Step 3: Create Draft PR
    pr_res = await async_client.post(f"/api/v1/remediations/{prop_id}/create-pr", headers=headers)
    assert pr_res.status_code == 201

    # Invariant Check 3: Health score must NOT change after Draft PR creation
    dash_after_pr = await async_client.get(
        f"/api/v1/repositories/{repo.id}/dashboard", headers=headers
    )
    assert dash_after_pr.json()["latest_health"]["health_score"] == baseline_score

    # Step 4: Developer merges PR on GitHub and triggers POST post-merge-reassess
    with patch(
        "app.services.health.service.RepositoryHealthService.assess_repository",
        new_callable=AsyncMock,
    ) as mock_assess:
        from datetime import UTC, datetime

        from app.models.repository_health import RepositoryHealthAssessment

        mock_assess.return_value = RepositoryHealthAssessment(
            id="assess-merged-999",
            repository_id=repo.id,
            commit_sha="merged_head_sha_99",
            branch_name="main",
            health_score=92.0,
            assessment_completeness=1.0,
            is_qualified=True,
            qualification_reason="QUALIFIED_SCORE",
            code_quality_score=95.0,
            security_score=90.0,
            dependency_score=90.0,
            test_health_score=95.0,
            scoring_policy_version="4.2.0",
            dimension_status={},
            summary_metrics={},
            status="COMPLETED",
            created_at=datetime.now(UTC),
        )

        reassess_res = await async_client.post(
            f"/api/v1/repositories/{repo.id}/remediation/post-merge-reassess?commit_sha=merged_head_sha_99&branch=main",
            headers=headers,
        )
        assert reassess_res.status_code == 201
        new_health = reassess_res.json()
        assert new_health["health_score"] == 92.0
        assert new_health["commit_sha"] == "merged_head_sha_99"

        # Commit to test DB session to simulate post-merge state update
        async with AsyncSessionLocal() as db_sess:
            db_sess.add(mock_assess.return_value)
            await db_sess.commit()

    # Invariant Check 4: Dashboard now exhibits updated health score post-merge!
    dash_after_merge = await async_client.get(
        f"/api/v1/repositories/{repo.id}/dashboard", headers=headers
    )
    assert dash_after_merge.json()["latest_health"]["health_score"] == 92.0
