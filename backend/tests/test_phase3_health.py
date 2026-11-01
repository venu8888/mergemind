"""Unit and integration tests for Repository Health Assessment Engine and Scoring."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.repository import Repository
from app.services.analysis.base import AnalysisResult, CheckStatus, CheckType
from app.services.health.scoring import RepositoryHealthScorer
from app.services.health.service import RepositoryHealthService


@pytest.fixture
def scorer():
    return RepositoryHealthScorer()


def test_scorer_all_dimensions_perfect(scorer):
    """When all 5 dimensions pass cleanly, health score is 100 and status is QUALIFIED."""
    cq = AnalysisResult(
        check_type=CheckType.STATIC_LINT, status=CheckStatus.PASSED, tool_name="ruff"
    )
    sec = AnalysisResult(
        check_type=CheckType.SECURITY_SCAN, status=CheckStatus.PASSED, tool_name="bandit"
    )
    dep = AnalysisResult(
        check_type=CheckType.DEPENDENCY_AUDIT, status=CheckStatus.PASSED, tool_name="pip-audit"
    )
    test = AnalysisResult(
        check_type=CheckType.TEST_EXECUTION,
        status=CheckStatus.PASSED,
        tool_name="pytest",
        metrics={"pass_rate_pct": 100.0, "coverage_pct": 100.0, "tests_total": 10},
    )
    maint = AnalysisResult(
        check_type=CheckType.MAINTAINABILITY,
        status=CheckStatus.PASSED,
        tool_name="radon",
        metrics={"docstring_coverage_pct": 100.0, "complex_functions_count": 0, "total_loc": 1000},
    )

    out = scorer.evaluate(cq, sec, dep, test, maint)
    assert out.health_score == 100.0
    assert out.assessment_completeness == 100.0
    assert out.is_qualified is True
    assert out.qualification_reason is None


def test_scorer_renormalization_no_neutral_padding(scorer):
    """Verify that unconfigured/skipped dimensions do NOT inject neutral 50.0 scores."""
    # Only code quality and security are configured
    cq = AnalysisResult(
        check_type=CheckType.STATIC_LINT, status=CheckStatus.PASSED, tool_name="ruff"
    )
    sec = AnalysisResult(
        check_type=CheckType.SECURITY_SCAN, status=CheckStatus.PASSED, tool_name="bandit"
    )
    dep = AnalysisResult(
        check_type=CheckType.DEPENDENCY_AUDIT, status=CheckStatus.SKIPPED, tool_name="pip-audit"
    )
    test = AnalysisResult(
        check_type=CheckType.TEST_EXECUTION, status=CheckStatus.SKIPPED, tool_name="pytest"
    )
    maint = AnalysisResult(
        check_type=CheckType.MAINTAINABILITY, status=CheckStatus.SKIPPED, tool_name="radon"
    )

    out = scorer.evaluate(cq, sec, dep, test, maint)
    # CQ (0.25) + SEC (0.25) = 0.50 active weight. Both score 100.0.
    # Re-normalized health score: 100.0
    assert out.health_score == 100.0
    # Assessed weight: 0.50 / 1.00 = 50.0%
    assert out.assessment_completeness == 50.0
    # Completeness < 80.0% -> PROVISIONAL
    assert out.is_qualified is False
    assert "Assessment completeness is 50.0%" in (out.qualification_reason or "")


def test_scorer_distinguishes_infra_failure_from_code_defects(scorer):
    """Verify scanner timeout/infra failure affects completeness and qualification, not raw defect penalties."""
    cq = AnalysisResult(
        check_type=CheckType.STATIC_LINT,
        status=CheckStatus.TIMEOUT,
        tool_name="ruff",
        error_message="Execution timed out after 60s",
    )
    sec = AnalysisResult(
        check_type=CheckType.SECURITY_SCAN, status=CheckStatus.PASSED, tool_name="bandit"
    )
    dep = AnalysisResult(
        check_type=CheckType.DEPENDENCY_AUDIT, status=CheckStatus.PASSED, tool_name="pip-audit"
    )
    test = AnalysisResult(
        check_type=CheckType.TEST_EXECUTION,
        status=CheckStatus.PASSED,
        tool_name="pytest",
        metrics={"pass_rate_pct": 100.0, "coverage_pct": 100.0},
    )
    maint = AnalysisResult(
        check_type=CheckType.MAINTAINABILITY,
        status=CheckStatus.PASSED,
        tool_name="radon",
        metrics={"docstring_coverage_pct": 100.0, "complex_functions_count": 0},
    )

    out = scorer.evaluate(cq, sec, dep, test, maint)
    # CQ is TIMEOUT -> dimension_status is FAILED_DEPENDENCY, sub_score is None (not 0.0 code defect)
    assert out.dimension_status["code_quality"] == "FAILED_DEPENDENCY"
    assert out.code_quality_score is None
    assert out.assessment_completeness == 75.0
    assert out.is_qualified is False


def test_scorer_defect_penalties(scorer):
    """Verify security vulnerabilities and linting defects penalize the dimensional scores."""
    sec = AnalysisResult(
        check_type=CheckType.SECURITY_SCAN,
        status=CheckStatus.FAILED,
        tool_name="bandit",
        metrics={"high": 1, "critical": 0, "medium": 0, "low": 0},
    )
    cq = AnalysisResult(
        check_type=CheckType.STATIC_LINT, status=CheckStatus.PASSED, tool_name="ruff"
    )
    dep = AnalysisResult(
        check_type=CheckType.DEPENDENCY_AUDIT, status=CheckStatus.PASSED, tool_name="pip-audit"
    )
    test = AnalysisResult(
        check_type=CheckType.TEST_EXECUTION,
        status=CheckStatus.PASSED,
        tool_name="pytest",
        metrics={"pass_rate_pct": 100.0, "coverage_pct": 100.0},
    )
    maint = AnalysisResult(
        check_type=CheckType.MAINTAINABILITY,
        status=CheckStatus.PASSED,
        tool_name="radon",
        metrics={"docstring_coverage_pct": 100.0, "complex_functions_count": 0},
    )

    out = scorer.evaluate(cq, sec, dep, test, maint)
    # High defect penalizes security score by 15 -> security_score = 85.0
    assert out.security_score == 85.0
    assert out.health_score < 100.0
    assert out.is_qualified is True


@pytest.mark.asyncio
async def test_repository_health_service_and_api(async_client: AsyncClient):
    """Integration test verifying DB persistence and API retrieval for health assessments."""
    repo_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        repo = Repository(
            id=repo_id,
            github_repo_id=987654,
            full_name="venu8888/test-repo",
            default_branch="main",
            is_active=True,
        )
        session.add(repo)
        await session.commit()

    # Query health before assessment -> 404
    resp = await async_client.get(f"/api/v1/repositories/{repo_id}/health")
    assert resp.status_code == 404

    # Trigger manual health assessment via service
    service = RepositoryHealthService()
    async with AsyncSessionLocal() as session:
        assessment = await service.assess_repository(
            repository_id=repo_id,
            source_dir=".",
            commit_sha="a" * 40,
            branch_name="main",
            db=session,
        )
        assert assessment.id is not None
        assert assessment.health_score >= 0.0

    # Query health after assessment -> 200 OK
    resp_after = await async_client.get(f"/api/v1/repositories/{repo_id}/health")
    assert resp_after.status_code == 200
    data = resp_after.json()
    assert data["repository_id"] == repo_id
    assert data["commit_sha"] == "a" * 40
    assert "health_score" in data
    assert "assessment_completeness" in data
    assert "dimension_status" in data
