"""Repository health assessment service."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence_record import EvidenceRecord
from app.models.repository_health import RepositoryHealthAssessment
from app.services.analysis.base import AnalysisResult
from app.services.analysis.runners.bandit_runner import BanditRunner
from app.services.analysis.runners.pip_audit_runner import PipAuditRunner
from app.services.analysis.runners.radon_runner import RadonRunner
from app.services.analysis.runners.ruff_runner import RuffRunner
from app.services.health.scoring import RepositoryHealthScorer
from app.services.sandbox.pytest_runner import PytestSandboxRunner

logger = logging.getLogger(__name__)


class RepositoryHealthService:
    """Orchestrates five-factor continuous repository health assessments."""

    def __init__(
        self,
        ruff_runner: RuffRunner | None = None,
        bandit_runner: BanditRunner | None = None,
        pip_audit_runner: PipAuditRunner | None = None,
        pytest_runner: PytestSandboxRunner | None = None,
        radon_runner: RadonRunner | None = None,
        scorer: RepositoryHealthScorer | None = None,
    ):
        self.ruff = ruff_runner or RuffRunner()
        self.bandit = bandit_runner or BanditRunner()
        self.pip_audit = pip_audit_runner or PipAuditRunner()
        self.pytest = pytest_runner or PytestSandboxRunner()
        self.radon = radon_runner or RadonRunner()
        self.scorer = scorer or RepositoryHealthScorer()

    async def assess_repository(
        self,
        repository_id: str,
        source_dir: str,
        commit_sha: str,
        branch_name: str,
        db: AsyncSession,
    ) -> RepositoryHealthAssessment:
        """Run all five health dimensions against the repository target branch and persist."""
        assessment_id = str(uuid.uuid4())
        created_at = datetime.now(UTC)

        # Execute runners concurrently where practical
        logger.info(
            "Executing five-factor health assessment for repo=%s commit=%s",
            repository_id,
            commit_sha[:8],
        )

        ruff_task = self.ruff.run(source_dir)
        bandit_task = self.bandit.run(source_dir)
        pip_audit_task = self.pip_audit.run(source_dir)
        radon_task = self.radon.run(source_dir)
        pytest_task = self.pytest.run(source_dir)

        ruff_res, bandit_res, pip_audit_res, radon_res, pytest_res = await asyncio.gather(
            ruff_task, bandit_task, pip_audit_task, radon_task, pytest_task
        )

        # Evaluate scoring model
        scoring_out = self.scorer.evaluate(
            code_quality_res=ruff_res,
            security_res=bandit_res,
            dependency_res=pip_audit_res,
            test_health_res=pytest_res,
            maintainability_res=radon_res,
        )

        completed_at = datetime.now(UTC)

        # Persist assessment
        assessment = RepositoryHealthAssessment(
            id=assessment_id,
            repository_id=repository_id,
            commit_sha=commit_sha,
            branch_name=branch_name,
            health_score=scoring_out.health_score,
            assessment_completeness=scoring_out.assessment_completeness,
            is_qualified=scoring_out.is_qualified,
            qualification_reason=scoring_out.qualification_reason,
            code_quality_score=scoring_out.code_quality_score,
            security_score=scoring_out.security_score,
            dependency_score=scoring_out.dependency_score,
            test_health_score=scoring_out.test_health_score,
            maintainability_score=scoring_out.maintainability_score,
            scoring_policy_version=scoring_out.scoring_policy_version,
            dimension_status=scoring_out.dimension_status,
            summary_metrics=scoring_out.summary_metrics,
            status="COMPLETED",
            created_at=created_at,
            completed_at=completed_at,
        )
        db.add(assessment)

        # Persist evidence records for each dimension
        dim_results: list[tuple[str, AnalysisResult]] = [
            ("code_quality", ruff_res),
            ("security", bandit_res),
            ("dependencies", pip_audit_res),
            ("test_health", pytest_res),
            ("maintainability", radon_res),
        ]

        for dim_name, res in dim_results:
            evidence = EvidenceRecord(
                id=str(uuid.uuid4()),
                evidence_type=f"HEALTH_{dim_name.upper()}",
                raw_digest=res.output_digest or "0" * 64,
                structured_data={
                    "dimension": dim_name,
                    "status": res.status,
                    "metrics": res.metrics,
                    "tool_name": res.tool_name,
                    "tool_version": res.tool_version,
                    "error_message": res.error_message,
                    "assessment_id": assessment_id,
                },
                recorded_at=completed_at,
            )
            db.add(evidence)

        await db.commit()
        await db.refresh(assessment)
        return assessment

    async def get_latest_assessment(
        self,
        repository_id: str,
        db: AsyncSession,
    ) -> RepositoryHealthAssessment | None:
        """Fetch the latest health assessment for a repository."""
        stmt = (
            select(RepositoryHealthAssessment)
            .where(RepositoryHealthAssessment.repository_id == repository_id)
            .order_by(RepositoryHealthAssessment.created_at.desc())
            .limit(1)
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()
