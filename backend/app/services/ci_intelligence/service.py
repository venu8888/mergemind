"""Service orchestrating CI failure ingestion, classification, and root-cause localization."""

from __future__ import annotations

import logging

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ci_failure import CIFailureRecord
from app.models.repository import Repository
from app.services.ci_intelligence.classifier import CIFailureClassifier
from app.services.ci_intelligence.localizer import CIRootCauseLocalizer
from app.services.ci_intelligence.parser import CILogParser

logger = logging.getLogger(__name__)


class CIFailureService:
    """Ingests CI/CD workflow runs and jobs, parses logs, and generates root-cause intelligence."""

    def __init__(
        self,
        parser: CILogParser | None = None,
        classifier: CIFailureClassifier | None = None,
        localizer: CIRootCauseLocalizer | None = None,
    ):
        self.parser = parser or CILogParser()
        self.classifier = classifier or CIFailureClassifier()
        self.localizer = localizer or CIRootCauseLocalizer()

    async def ingest_failure(
        self,
        db: AsyncSession,
        repository_id: str,
        workflow_run_id: int,
        workflow_name: str,
        job_name: str,
        commit_sha: str,
        branch: str,
        raw_logs: str,
        job_id: int | None = None,
        pull_request_id: str | None = None,
        changed_files: list[str] | None = None,
    ) -> CIFailureRecord:
        """Parse raw logs, classify failure, localize root cause, and store failure record."""
        # Verify repository exists
        repo = (
            await db.execute(select(Repository).where(Repository.id == repository_id))
        ).scalar_one_or_none()
        if not repo:
            raise ValueError(f"Repository {repository_id} not found")

        # 1. Parse logs and extract error lines / stack frames
        parsed_data = self.parser.parse(raw_logs)
        primary_error = parsed_data["primary_error"]
        log_excerpt = parsed_data["log_excerpt"]
        localized_files = parsed_data["localized_files"]

        # 2. Classify failure category deterministically
        failure_category = self.classifier.classify(primary_error, log_excerpt)

        # 3. Localize probable root cause and generate advisory hypothesis
        loc_res = self.localizer.localize(
            failure_category=failure_category,
            primary_error=primary_error,
            localized_files=localized_files,
            changed_files=changed_files,
        )

        # 4. Create and persist record
        record = CIFailureRecord(
            repository_id=repository_id,
            pull_request_id=pull_request_id,
            workflow_run_id=workflow_run_id,
            workflow_name=workflow_name,
            job_id=job_id,
            job_name=job_name,
            commit_sha=commit_sha,
            branch=branch,
            failure_category=failure_category,
            status="ANALYZED",
            error_message=primary_error,
            log_excerpt=log_excerpt,
            localized_files=localized_files,
            root_cause_analysis=loc_res["root_cause_analysis"],
            ai_advisory_hypothesis=loc_res["ai_advisory_hypothesis"],
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        logger.info(
            "Ingested CI failure %s for repo %s (Run %d, Category: %s)",
            record.id,
            repository_id,
            workflow_run_id,
            failure_category,
        )
        return record

    async def get_failures_for_repository(
        self,
        db: AsyncSession,
        repository_id: str,
        status: str | None = None,
        limit: int = 50,
    ) -> list[CIFailureRecord]:
        """Retrieve recent CI failures for a repository ordered by creation date."""
        stmt = (
            select(CIFailureRecord)
            .where(CIFailureRecord.repository_id == repository_id)
            .order_by(desc(CIFailureRecord.created_at))
            .limit(limit)
        )
        if status:
            stmt = stmt.where(CIFailureRecord.status == status)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_failure_by_id(
        self,
        db: AsyncSession,
        failure_id: str,
    ) -> CIFailureRecord | None:
        """Retrieve a specific CI failure record by ID."""
        stmt = select(CIFailureRecord).where(CIFailureRecord.id == failure_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # Alias for test convenience
    list_failures = get_failures_for_repository
