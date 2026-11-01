"""Service coordinating AI-assisted remediation proposals and database persistence."""

from __future__ import annotations

import logging

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ci_failure import CIFailureRecord
from app.models.finding import Finding
from app.models.remediation import RemediationProposal
from app.models.repository import Repository
from app.services.remediation.base import (
    BaseRemediationProvider,
    RemediationContext,
    RemediationResult,
)
from app.services.remediation.mock_provider import MockRemediationProvider

logger = logging.getLogger(__name__)


class RemediationService:
    """Orchestrates generation, validation, and storage of reviewable code remediations."""

    def __init__(self, provider: BaseRemediationProvider | None = None):
        self.provider = provider or MockRemediationProvider()

    async def propose_for_ci_failure(
        self,
        db: AsyncSession,
        failure_id: str,
    ) -> RemediationProposal:
        """Generate a remediation proposal addressing an ingested CI/CD failure."""
        failure = (
            await db.execute(select(CIFailureRecord).where(CIFailureRecord.id == failure_id))
        ).scalar_one_or_none()
        if not failure:
            raise ValueError(f"CI failure record {failure_id} not found")

        repo = (
            await db.execute(select(Repository).where(Repository.id == failure.repository_id))
        ).scalar_one_or_none()
        repo_name = repo.full_name if repo else "unknown"

        # Extract target file from localized files if available
        target_file = None
        target_line = None
        if failure.localized_files:
            first_loc = failure.localized_files[0]
            target_file = first_loc.get("file_path")
            target_line = first_loc.get("line_number")

        context = RemediationContext(
            repository_id=failure.repository_id,
            repository_name=repo_name,
            target_commit_sha=failure.commit_sha,
            target_branch=failure.branch,
            error_message=failure.error_message,
            failure_category=failure.failure_category,
            target_file=target_file,
            target_line=target_line,
            log_excerpt=failure.log_excerpt,
            ci_failure_id=failure.id,
            pull_request_id=failure.pull_request_id,
            extra_evidence=failure.root_cause_analysis,
        )

        res: RemediationResult = await self.provider.generate_proposal(context)

        proposal = RemediationProposal(
            repository_id=failure.repository_id,
            ci_failure_id=failure.id,
            pull_request_id=failure.pull_request_id,
            title=res.title,
            description=res.description,
            target_commit_sha=failure.commit_sha,
            target_branch=failure.branch,
            status="PROPOSED",
            provider_name=res.provider_name,
            model_identifier=res.model_identifier,
            confidence_score=res.confidence_score,
            patch_diff=res.patch_diff,
            affected_files=res.affected_files,
            rationale=res.rationale,
            evidence_records={"ci_failure_id": failure.id, "error": failure.error_message},
        )
        db.add(proposal)

        # Update failure status to REMEDIATION_PROPOSED
        failure.status = "REMEDIATION_PROPOSED"
        await db.commit()
        await db.refresh(proposal)

        logger.info(
            "Created remediation proposal %s for CI failure %s (Provider: %s)",
            proposal.id,
            failure.id,
            res.provider_name,
        )
        return proposal

    async def propose_for_finding(
        self,
        db: AsyncSession,
        finding_id: str,
    ) -> RemediationProposal:
        """Generate a remediation proposal addressing a code analysis finding."""
        finding = (
            await db.execute(select(Finding).where(Finding.id == finding_id))
        ).scalar_one_or_none()
        if not finding:
            raise ValueError(f"Finding {finding_id} not found")

        repo = (
            await db.execute(select(Repository).where(Repository.id == finding.repository_id))
        ).scalar_one_or_none()
        repo_name = repo.full_name if repo else "unknown"

        context = RemediationContext(
            repository_id=finding.repository_id,
            repository_name=repo_name,
            target_commit_sha=finding.commit_sha,
            target_branch="main",
            error_message=finding.message,
            failure_category=finding.category or "LINT_ERROR",
            target_file=finding.file_path,
            target_line=finding.start_line,
            enclosing_symbol=finding.enclosing_symbol,
            code_snippet=finding.code_snippet,
            finding_id=finding.id,
            pull_request_id=finding.pull_request_id,
        )

        res: RemediationResult = await self.provider.generate_proposal(context)

        proposal = RemediationProposal(
            repository_id=finding.repository_id,
            finding_id=finding.id,
            pull_request_id=finding.pull_request_id,
            title=res.title,
            description=res.description,
            target_commit_sha=finding.commit_sha,
            target_branch="main",
            status="PROPOSED",
            provider_name=res.provider_name,
            model_identifier=res.model_identifier,
            confidence_score=res.confidence_score,
            patch_diff=res.patch_diff,
            affected_files=res.affected_files,
            rationale=res.rationale,
            evidence_records={"finding_id": finding.id, "rule_id": finding.rule_id},
        )
        db.add(proposal)
        await db.commit()
        await db.refresh(proposal)

        logger.info(
            "Created remediation proposal %s for finding %s",
            proposal.id,
            finding.id,
        )
        return proposal

    async def get_proposals_for_repository(
        self,
        db: AsyncSession,
        repository_id: str,
        status: str | None = None,
        limit: int = 50,
    ) -> list[RemediationProposal]:
        """List remediation proposals for a repository ordered by creation date."""
        stmt = (
            select(RemediationProposal)
            .where(RemediationProposal.repository_id == repository_id)
            .order_by(desc(RemediationProposal.created_at))
            .limit(limit)
        )
        if status:
            stmt = stmt.where(RemediationProposal.status == status)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_proposal_by_id(
        self,
        db: AsyncSession,
        proposal_id: str,
    ) -> RemediationProposal | None:
        """Retrieve a specific remediation proposal by ID."""
        stmt = select(RemediationProposal).where(RemediationProposal.id == proposal_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
