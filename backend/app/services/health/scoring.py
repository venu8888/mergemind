"""Repository Health Scoring Engine implementing policy v2.2-calibrated."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.analysis.base import AnalysisResult, CheckStatus


@dataclass
class HealthScoringOutput:
    """Calculated repository health scores, completeness, and availability profile."""

    health_score: float | None
    assessment_completeness: float
    is_qualified: bool
    qualification_reason: str | None
    code_quality_score: float | None
    security_score: float | None
    dependency_score: float | None
    test_health_score: float | None
    maintainability_score: float | None
    dimension_status: dict[str, str] = field(default_factory=dict)
    summary_metrics: dict[str, Any] = field(default_factory=dict)
    scoring_policy_version: str = "v2.2-calibrated"


class RepositoryHealthScorer:
    """Evaluates the five-factor repository health assessment according to policy v2.2-calibrated.

    Enforces:
    - Zero neutral scores for unconfigured checks.
    - Dynamic re-normalization of assessed weights.
    - Explicit blindspot qualification guards (PROVISIONAL vs QUALIFIED).
    - Infrastructure failure vs code defect segregation.
    """

    POLICY_VERSION = "v2.2-calibrated"

    DEFAULT_WEIGHTS = {
        "code_quality": 0.25,
        "security": 0.25,
        "dependencies": 0.20,
        "test_health": 0.20,
        "maintainability": 0.10,
    }

    def evaluate(
        self,
        code_quality_res: AnalysisResult,
        security_res: AnalysisResult,
        dependency_res: AnalysisResult,
        test_health_res: AnalysisResult,
        maintainability_res: AnalysisResult,
        weights_override: dict[str, float] | None = None,
    ) -> HealthScoringOutput:
        weights = weights_override or self.DEFAULT_WEIGHTS

        dimension_status: dict[str, str] = {}
        sub_scores: dict[str, float | None] = {}
        summary_metrics: dict[str, Any] = {}

        # 1. Code Quality Dimension (Ruff)
        total_loc = maintainability_res.metrics.get("total_loc", 1000) or 1000
        loc_normalized = max(100.0, float(total_loc)) / 1000.0

        if code_quality_res.status == CheckStatus.SKIPPED:
            dimension_status["code_quality"] = "UNCONFIGURED"
            sub_scores["code_quality"] = None
        elif code_quality_res.status in (CheckStatus.UNAVAILABLE, CheckStatus.TIMEOUT):
            dimension_status["code_quality"] = "FAILED_DEPENDENCY"
            sub_scores["code_quality"] = 0.0
        else:
            dimension_status["code_quality"] = "ENABLED"
            errs = code_quality_res.metrics.get("errors_count", 0)
            warns = code_quality_res.metrics.get("warnings_count", 0)
            deduction = (2.0 * errs / loc_normalized) + (0.5 * warns / loc_normalized)
            sub_scores["code_quality"] = round(max(0.0, 100.0 - deduction), 2)
            summary_metrics["lint_errors"] = errs
            summary_metrics["lint_warnings"] = warns

        # 2. Security Dimension (Bandit)
        if security_res.status == CheckStatus.SKIPPED:
            dimension_status["security"] = "UNCONFIGURED"
            sub_scores["security"] = None
        elif security_res.status in (CheckStatus.UNAVAILABLE, CheckStatus.TIMEOUT):
            dimension_status["security"] = "FAILED_DEPENDENCY"
            sub_scores["security"] = 0.0
        else:
            dimension_status["security"] = "ENABLED"
            crit = security_res.metrics.get("critical", 0)
            high = security_res.metrics.get("high", 0)
            med = security_res.metrics.get("medium", 0)
            low = security_res.metrics.get("low", 0)
            sec_deduction = (30.0 * crit) + (15.0 * high) + (5.0 * med) + (1.0 * low)
            sub_scores["security"] = round(max(0.0, 100.0 - sec_deduction), 2)
            summary_metrics["security_critical_high"] = crit + high
            summary_metrics["security_medium"] = med

        # 3. Dependency Dimension (pip-audit)
        if dependency_res.status == CheckStatus.SKIPPED:
            dimension_status["dependencies"] = "UNCONFIGURED"
            sub_scores["dependencies"] = None
        elif dependency_res.status in (CheckStatus.UNAVAILABLE, CheckStatus.TIMEOUT):
            dimension_status["dependencies"] = "FAILED_DEPENDENCY"
            sub_scores["dependencies"] = 0.0
        else:
            dimension_status["dependencies"] = "ENABLED"
            cve_crit_high = dependency_res.metrics.get("cve_critical_high", 0)
            cve_med = dependency_res.metrics.get("cve_medium", 0)
            dep_deduction = (25.0 * cve_crit_high) + (10.0 * cve_med)
            sub_scores["dependencies"] = round(max(0.0, 100.0 - dep_deduction), 2)
            summary_metrics["dependency_cves"] = cve_crit_high + cve_med

        # 4. Test Health Dimension (Pytest in Sandbox)
        if test_health_res.status == CheckStatus.SKIPPED:
            dimension_status["test_health"] = "UNCONFIGURED"
            sub_scores["test_health"] = None
        elif test_health_res.status in (CheckStatus.UNAVAILABLE, CheckStatus.TIMEOUT):
            dimension_status["test_health"] = "FAILED_DEPENDENCY"
            sub_scores["test_health"] = 0.0
        else:
            dimension_status["test_health"] = "ENABLED"
            tests_failed = test_health_res.metrics.get("tests_failed", 0)
            pass_rate = test_health_res.metrics.get("pass_rate_pct", 0.0)
            coverage = test_health_res.metrics.get("coverage_pct")
            cov_effective = coverage if coverage is not None else 50.0

            if tests_failed > 0:
                t_score = 0.0
            else:
                t_score = (0.6 * cov_effective) + (0.4 * pass_rate)
            sub_scores["test_health"] = round(min(100.0, max(0.0, t_score)), 2)
            summary_metrics["tests_total"] = test_health_res.metrics.get("tests_total", 0)
            summary_metrics["pass_rate_pct"] = pass_rate
            summary_metrics["coverage_pct"] = coverage

        # 5. Maintainability Dimension (Radon)
        if maintainability_res.status == CheckStatus.SKIPPED:
            dimension_status["maintainability"] = "UNCONFIGURED"
            sub_scores["maintainability"] = None
        elif maintainability_res.status in (CheckStatus.UNAVAILABLE, CheckStatus.TIMEOUT):
            dimension_status["maintainability"] = "FAILED_DEPENDENCY"
            sub_scores["maintainability"] = 0.0
        else:
            dimension_status["maintainability"] = "ENABLED"
            doc_cov = maintainability_res.metrics.get("docstring_coverage_pct", 100.0)
            complex_cnt = maintainability_res.metrics.get("complex_functions_count", 0)
            m_score = (0.5 * doc_cov) + (0.5 * max(0.0, 100.0 - (5.0 * complex_cnt)))
            sub_scores["maintainability"] = round(min(100.0, max(0.0, m_score)), 2)
            summary_metrics["total_loc"] = total_loc
            summary_metrics["docstring_coverage_pct"] = doc_cov
            summary_metrics["complex_functions"] = complex_cnt

        # 6. Dynamic Re-normalization & Completeness
        assessed_weight = 0.0
        weighted_sum = 0.0
        total_possible_weight = sum(weights.values())

        for dim, score in sub_scores.items():
            if score is not None:
                dim_weight = weights.get(dim, 0.20)
                assessed_weight += dim_weight
                weighted_sum += dim_weight * score

        if assessed_weight > 0:
            health_score = round(weighted_sum / assessed_weight, 2)
            completeness = round((assessed_weight / total_possible_weight) * 100.0, 2)
        else:
            health_score = None
            completeness = 0.0

        # 7. Qualification Guard
        # Qualified requires completeness >= 80% AND core dimensions (code_quality & security) active
        core_enabled = (
            dimension_status.get("code_quality") == "ENABLED"
            and dimension_status.get("security") == "ENABLED"
        )

        if completeness >= 80.0 and core_enabled:
            is_qualified = True
            qualification_reason = None
        else:
            is_qualified = False
            reasons = []
            if completeness < 80.0:
                reasons.append(
                    f"Assessment completeness is {completeness:.1f}% (requires >= 80.0%)"
                )
            if not core_enabled:
                reasons.append(
                    "Core dimensions (Code Quality or Security) were unconfigured or failed"
                )
            qualification_reason = "; ".join(reasons)

        return HealthScoringOutput(
            health_score=health_score,
            assessment_completeness=completeness,
            is_qualified=is_qualified,
            qualification_reason=qualification_reason,
            code_quality_score=sub_scores.get("code_quality"),
            security_score=sub_scores.get("security"),
            dependency_score=sub_scores.get("dependencies"),
            test_health_score=sub_scores.get("test_health"),
            maintainability_score=sub_scores.get("maintainability"),
            dimension_status=dimension_status,
            summary_metrics=summary_metrics,
            scoring_policy_version=self.POLICY_VERSION,
        )
