"""Verification service package providing PR delta classification and quality gate evaluation."""

from app.services.verification.applicability import determine_applicable_checks
from app.services.verification.delta_classifier import (
    ClassifiedFinding,
    DeltaClassificationResult,
    FindingDeltaClassifier,
)
from app.services.verification.fingerprint import (
    compute_finding_fingerprint,
    normalize_finding_message,
)
from app.services.verification.quality_gate import (
    PRQualityGateEvaluator,
    QualityGateVerdict,
)
from app.services.verification.verifier import PRVerificationService

__all__ = [
    "ClassifiedFinding",
    "DeltaClassificationResult",
    "FindingDeltaClassifier",
    "PRQualityGateEvaluator",
    "PRVerificationService",
    "QualityGateVerdict",
    "compute_finding_fingerprint",
    "determine_applicable_checks",
    "normalize_finding_message",
]
