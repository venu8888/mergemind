"""Audit verification tests for Repository Health Scoring Engine edge cases."""

from __future__ import annotations

import pytest

from app.services.analysis.base import AnalysisResult, CheckStatus, CheckType
from app.services.health.scoring import RepositoryHealthScorer


@pytest.fixture
def scorer():
    return RepositoryHealthScorer()


def _passed(check_type: CheckType, tool: str, metrics: dict | None = None) -> AnalysisResult:
    return AnalysisResult(
        check_type=check_type,
        status=CheckStatus.PASSED,
        tool_name=tool,
        metrics=metrics or {},
    )


def _skipped(check_type: CheckType, tool: str) -> AnalysisResult:
    return AnalysisResult(check_type=check_type, status=CheckStatus.SKIPPED, tool_name=tool)


def _unavailable(check_type: CheckType, tool: str) -> AnalysisResult:
    return AnalysisResult(
        check_type=check_type,
        status=CheckStatus.UNAVAILABLE,
        tool_name=tool,
        error_message="Scanner binary not found",
    )


def _timeout(check_type: CheckType, tool: str) -> AnalysisResult:
    return AnalysisResult(
        check_type=check_type,
        status=CheckStatus.TIMEOUT,
        tool_name=tool,
        error_message="Execution timed out",
    )


def test_edge_case_no_test_suite(scorer: RepositoryHealthScorer):
    """Edge Case 1: Repository without automated test suite (Pytest SKIPPED)."""
    cq = _passed(CheckType.STATIC_LINT, "ruff")
    sec = _passed(CheckType.SECURITY_SCAN, "bandit")
    dep = _passed(CheckType.DEPENDENCY_AUDIT, "pip-audit")
    test = _skipped(CheckType.TEST_EXECUTION, "pytest")
    maint = _passed(
        CheckType.MAINTAINABILITY,
        "radon",
        {"docstring_coverage_pct": 100.0, "complex_functions_count": 0},
    )

    out = scorer.evaluate(cq, sec, dep, test, maint)
    assert out.dimension_status["test_health"] == "UNCONFIGURED"
    assert out.test_health_score is None
    # 4 of 5 dimensions assessed (0.25+0.25+0.20+0.10 = 0.80 -> 80.0% completeness)
    assert out.assessment_completeness == 80.0
    assert out.is_qualified is True  # Completeness >= 80% and core dimensions active
    assert out.health_score == 100.0


def test_edge_case_missing_security_configuration(scorer: RepositoryHealthScorer):
    """Edge Case 2: Repository with missing security scanner (Bandit SKIPPED)."""
    cq = _passed(CheckType.STATIC_LINT, "ruff")
    sec = _skipped(CheckType.SECURITY_SCAN, "bandit")
    dep = _passed(CheckType.DEPENDENCY_AUDIT, "pip-audit")
    test = _passed(
        CheckType.TEST_EXECUTION, "pytest", {"pass_rate_pct": 100.0, "coverage_pct": 80.0}
    )
    maint = _passed(
        CheckType.MAINTAINABILITY,
        "radon",
        {"docstring_coverage_pct": 100.0, "complex_functions_count": 0},
    )

    out = scorer.evaluate(cq, sec, dep, test, maint)
    assert out.dimension_status["security"] == "UNCONFIGURED"
    assert out.security_score is None
    # Assessed weight: 0.75 -> 75% completeness
    assert out.assessment_completeness == 75.0
    # Core security dimension is unconfigured -> PROVISIONAL
    assert out.is_qualified is False
    assert "Core dimensions (Code Quality or Security) were unconfigured or failed" in (
        out.qualification_reason or ""
    )


def test_edge_case_scanner_unavailable_not_falsely_reported_as_code_defects(
    scorer: RepositoryHealthScorer,
):
    """Edge Case 3: Scanner binary unavailable (Infrastructure issue, NOT code defect)."""
    cq = _unavailable(CheckType.STATIC_LINT, "ruff")
    sec = _passed(CheckType.SECURITY_SCAN, "bandit")
    dep = _passed(CheckType.DEPENDENCY_AUDIT, "pip-audit")
    test = _passed(
        CheckType.TEST_EXECUTION, "pytest", {"pass_rate_pct": 100.0, "coverage_pct": 80.0}
    )
    maint = _passed(
        CheckType.MAINTAINABILITY,
        "radon",
        {"docstring_coverage_pct": 100.0, "complex_functions_count": 0},
    )

    out = scorer.evaluate(cq, sec, dep, test, maint)
    # Infrastructure failure marked as FAILED_DEPENDENCY
    assert out.dimension_status["code_quality"] == "FAILED_DEPENDENCY"
    # CRITICAL: Score must be None, NOT 0.0 (zero code defects fabricated)
    assert out.code_quality_score is None
    # Available dimensions (sec 100, dep 100, test 88, maint 100) are dynamically re-normalized
    assert out.health_score is not None
    assert out.health_score > 90.0  # Not dragged down to 0 by missing tool
    assert out.assessment_completeness == 75.0
    assert out.is_qualified is False


def test_edge_case_infrastructure_timeout(scorer: RepositoryHealthScorer):
    """Edge Case 4: Scanner execution timed out (Infrastructure issue)."""
    cq = _passed(CheckType.STATIC_LINT, "ruff")
    sec = _timeout(CheckType.SECURITY_SCAN, "bandit")
    dep = _passed(CheckType.DEPENDENCY_AUDIT, "pip-audit")
    test = _passed(
        CheckType.TEST_EXECUTION, "pytest", {"pass_rate_pct": 100.0, "coverage_pct": 80.0}
    )
    maint = _passed(
        CheckType.MAINTAINABILITY,
        "radon",
        {"docstring_coverage_pct": 100.0, "complex_functions_count": 0},
    )

    out = scorer.evaluate(cq, sec, dep, test, maint)
    assert out.dimension_status["security"] == "FAILED_DEPENDENCY"
    assert out.security_score is None
    assert out.is_qualified is False


def test_edge_case_zero_applicable_dimensions(scorer: RepositoryHealthScorer):
    """Edge Case 5: All 5 dimensions are SKIPPED (e.g. empty repository or documentation only)."""
    cq = _skipped(CheckType.STATIC_LINT, "ruff")
    sec = _skipped(CheckType.SECURITY_SCAN, "bandit")
    dep = _skipped(CheckType.DEPENDENCY_AUDIT, "pip-audit")
    test = _skipped(CheckType.TEST_EXECUTION, "pytest")
    maint = _skipped(CheckType.MAINTAINABILITY, "radon")

    out = scorer.evaluate(cq, sec, dep, test, maint)
    assert out.health_score is None
    assert out.assessment_completeness == 0.0
    assert out.is_qualified is False
    assert "Assessment completeness is 0.0%" in (out.qualification_reason or "")


def test_edge_case_only_one_dimension_assessed(scorer: RepositoryHealthScorer):
    """Edge Case 6: Only Maintainability dimension is assessed."""
    cq = _skipped(CheckType.STATIC_LINT, "ruff")
    sec = _skipped(CheckType.SECURITY_SCAN, "bandit")
    dep = _skipped(CheckType.DEPENDENCY_AUDIT, "pip-audit")
    test = _skipped(CheckType.TEST_EXECUTION, "pytest")
    maint = _passed(
        CheckType.MAINTAINABILITY,
        "radon",
        {"docstring_coverage_pct": 90.0, "complex_functions_count": 0},
    )

    out = scorer.evaluate(cq, sec, dep, test, maint)
    # Assessed weight: 0.10 / 1.00 = 10.0% completeness
    assert out.assessment_completeness == 10.0
    # Single assessed dimension (m_score = 0.5*90 + 0.5*100 = 95.0) is dynamically re-normalized to 100% of assessed weight
    assert out.health_score == 95.0
    # Completeness is far below 80% and core dimensions missing -> PROVISIONAL
    assert out.is_qualified is False


def test_score_reproducibility_and_version(scorer: RepositoryHealthScorer):
    """Verify that scoring policy is versioned and output is strictly deterministic."""
    cq = _passed(CheckType.STATIC_LINT, "ruff")
    sec = _passed(CheckType.SECURITY_SCAN, "bandit")
    dep = _passed(CheckType.DEPENDENCY_AUDIT, "pip-audit")
    test = _passed(
        CheckType.TEST_EXECUTION, "pytest", {"pass_rate_pct": 100.0, "coverage_pct": 90.0}
    )
    maint = _passed(
        CheckType.MAINTAINABILITY,
        "radon",
        {"docstring_coverage_pct": 80.0, "complex_functions_count": 1},
    )

    out1 = scorer.evaluate(cq, sec, dep, test, maint)
    out2 = scorer.evaluate(cq, sec, dep, test, maint)

    assert out1.scoring_policy_version == "v2.2-calibrated"
    assert out1.health_score == out2.health_score
    assert out1.assessment_completeness == out2.assessment_completeness
    assert out1.is_qualified == out2.is_qualified
    assert out1.dimension_status == out2.dimension_status
