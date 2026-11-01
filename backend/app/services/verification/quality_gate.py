"""PR Quality Gate and Verification Completeness Evaluator with Anti-Masking Rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.analysis.base import AnalysisResult, CheckStatus, CheckType
from app.services.verification.delta_classifier import ClassifiedFinding


@dataclass
class QualityGateVerdict:
    """Evaluated quality gate decision and metrics."""

    gate_verdict: str  # PASSED, FAILED, BLOCKED_COMPLETENESS, WARNING
    quality_score: float
    verification_completeness: float
    reasons: list[str] = field(default_factory=list)
    blocking_findings_count: int = 0
    introduced_defects_count: int = 0
    metrics: dict[str, Any] = field(default_factory=dict)


class PRQualityGateEvaluator:
    """Evaluates PR merge readiness according to policy v2.2-calibrated.

    Enforces:
    - Pre-calculated check applicability (zero denominator padding).
    - Anti-masking rule: critical failures cannot be masked by completeness percentage.
    - Strict delta scoring (penalizes only INTRODUCED_NEW findings).
    """

    DEFAULT_MIN_QUALITY_SCORE: float = 80.0
    DEFAULT_MIN_COMPLETENESS: float = 90.0

    def evaluate(
        self,
        applicable_checks: set[CheckType],
        check_results: list[AnalysisResult],
        classified_findings: list[ClassifiedFinding],
        min_quality_score: float | None = None,
        min_completeness: float | None = None,
    ) -> QualityGateVerdict:
        threshold_score = min_quality_score or self.DEFAULT_MIN_QUALITY_SCORE
        threshold_completeness = min_completeness or self.DEFAULT_MIN_COMPLETENESS

        reasons: list[str] = []

        # 1. Verification Completeness Calculation
        # Map results by check_type
        result_by_type = {res.check_type: res for res in check_results}

        successful_checks = 0
        total_applicable = len(applicable_checks)

        has_failed_check = False
        failed_check_types: list[str] = []
        unavailable_or_timeout: list[str] = []

        for check_type in applicable_checks:
            res = result_by_type.get(check_type)
            if res and res.status in (CheckStatus.PASSED, CheckStatus.SKIPPED):
                successful_checks += 1
            elif res and res.status == CheckStatus.FAILED:
                has_failed_check = True
                failed_check_types.append(check_type.value)
            elif res and res.status in (CheckStatus.TIMEOUT, CheckStatus.UNAVAILABLE):
                unavailable_or_timeout.append(f"{check_type.value} ({res.status.value})")
            else:
                unavailable_or_timeout.append(f"{check_type.value} (NOT_RUN)")

        completeness = (
            round((successful_checks / total_applicable) * 100.0, 2)
            if total_applicable > 0
            else 100.0
        )

        # 2. Score Calculation on INTRODUCED_NEW findings only
        introduced = [cf for cf in classified_findings if cf.delta_status == "INTRODUCED_NEW"]
        crit_count = sum(1 for cf in introduced if cf.finding.severity == "CRITICAL")
        high_count = sum(1 for cf in introduced if cf.finding.severity == "HIGH")
        med_count = sum(1 for cf in introduced if cf.finding.severity == "MEDIUM")
        low_count = sum(1 for cf in introduced if cf.finding.severity == "LOW")

        deduction = (
            (30.0 * crit_count) + (15.0 * high_count) + (5.0 * med_count) + (1.0 * low_count)
        )
        quality_score = round(max(0.0, 100.0 - deduction), 2)

        blocking_findings = [cf for cf in introduced if cf.finding.is_blocking]

        # 3. Decision Matrix & Anti-Masking
        # Rule 1: Any check failed execution or test failure -> FAILED
        if has_failed_check:
            gate_verdict = "FAILED"
            reasons.append(f"Required check(s) failed: {', '.join(failed_check_types)}")

        # Rule 2: Critical or High newly introduced defects -> FAILED
        elif crit_count > 0 or high_count > 0:
            gate_verdict = "FAILED"
            reasons.append(
                f"PR introduces {crit_count + high_count} critical/high severity defect(s)"
            )

        # Rule 3: Completeness deficit below threshold -> BLOCKED_COMPLETENESS
        elif completeness < threshold_completeness:
            gate_verdict = "BLOCKED_COMPLETENESS"
            reasons.append(
                f"Verification completeness is {completeness:.1f}% (required >= {threshold_completeness:.1f}%). Incomplete checks: {', '.join(unavailable_or_timeout)}"
            )

        # Rule 4: Quality score below threshold -> FAILED
        elif quality_score < threshold_score:
            gate_verdict = "FAILED"
            reasons.append(
                f"PR Quality score is {quality_score:.1f} (required >= {threshold_score:.1f})"
            )

        # Rule 5: Non-blocking medium/low findings or ambiguous hunks -> WARNING
        elif med_count > 0 or any(
            cf.delta_status == "AMBIGUOUS_MODIFIED_CONTEXT" for cf in classified_findings
        ):
            gate_verdict = "WARNING"
            if med_count > 0:
                reasons.append(f"PR introduces {med_count} non-blocking medium severity issue(s)")
            if any(cf.delta_status == "AMBIGUOUS_MODIFIED_CONTEXT" for cf in classified_findings):
                reasons.append(
                    "PR contains ambiguous modified context requiring reviewer confirmation"
                )

        # Rule 6: Clean Pass
        else:
            gate_verdict = "PASSED"
            reasons.append(
                "All applicable verification checks passed with acceptable quality score"
            )

        return QualityGateVerdict(
            gate_verdict=gate_verdict,
            quality_score=quality_score,
            verification_completeness=completeness,
            reasons=reasons,
            blocking_findings_count=len(blocking_findings),
            introduced_defects_count=len(introduced),
            metrics={
                "total_applicable_checks": total_applicable,
                "successful_checks": successful_checks,
                "critical_introduced": crit_count,
                "high_introduced": high_count,
                "medium_introduced": med_count,
                "low_introduced": low_count,
            },
        )
