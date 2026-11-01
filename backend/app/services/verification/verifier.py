"""PR Verification Service orchestrating applicable check execution, delta classification, and quality gate evaluation."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analysis_run import AnalysisRun
from app.models.evidence_record import EvidenceRecord
from app.models.finding import Finding
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.services.analysis.base import AnalysisResult, CheckType, RawFinding
from app.services.analysis.runners.bandit_runner import BanditRunner
from app.services.analysis.runners.pip_audit_runner import PipAuditRunner
from app.services.analysis.runners.radon_runner import RadonRunner
from app.services.analysis.runners.ruff_runner import RuffRunner
from app.services.github.client import GitHubClient
from app.services.github.diff_parser import DiffParser, FileDiff
from app.services.sandbox.pytest_runner import PytestSandboxRunner
from app.services.verification.applicability import determine_applicable_checks
from app.services.verification.delta_classifier import (
    DeltaClassificationResult,
    FindingDeltaClassifier,
)
from app.services.verification.quality_gate import PRQualityGateEvaluator, QualityGateVerdict

logger = logging.getLogger(__name__)


class PRVerificationService:
    """End-to-end pull request verification orchestrator.

    Integrates:
    1. Pre-calculated check applicability (zero denominator padding).
    2. Concurrent execution of applicable analysis runners.
    3. Content-derived SHA-256 fingerprint matching & delta classification.
    4. Anti-masking Quality Gate decision matrix.
    5. Durable database persistence of AnalysisRun, Findings, and EvidenceRecords.
    """

    def __init__(
        self,
        ruff_runner: RuffRunner | None = None,
        bandit_runner: BanditRunner | None = None,
        pip_audit_runner: PipAuditRunner | None = None,
        pytest_runner: PytestSandboxRunner | None = None,
        radon_runner: RadonRunner | None = None,
        classifier: FindingDeltaClassifier | None = None,
        quality_gate: PRQualityGateEvaluator | None = None,
        github_client: GitHubClient | None = None,
    ):
        self.ruff = ruff_runner or RuffRunner()
        self.bandit = bandit_runner or BanditRunner()
        self.pip_audit = pip_audit_runner or PipAuditRunner()
        self.pytest = pytest_runner or PytestSandboxRunner()
        self.radon = radon_runner or RadonRunner()
        self.classifier = classifier or FindingDeltaClassifier()
        self.quality_gate = quality_gate or PRQualityGateEvaluator()
        self.github_client = github_client

    async def verify_pull_request(
        self,
        repository_id: str,
        pr_number: int,
        db: AsyncSession,
        commit_sha: str | None = None,
        head_dir: str | None = None,
        base_dir: str | None = None,
        changed_files: list[str] | None = None,
        diff_content: str | None = None,
        diff_files: list[FileDiff] | None = None,
        base_findings: list[RawFinding] | None = None,
        head_findings: list[RawFinding] | None = None,
        check_results: list[AnalysisResult] | None = None,
        min_quality_score: float | None = None,
        min_completeness: float | None = None,
    ) -> AnalysisRun:
        """Execute full verification pipeline for a pull request."""
        # 1. Fetch Repository and PullRequest
        stmt = (
            select(PullRequest, Repository)
            .join(Repository, PullRequest.repository_id == Repository.id)
            .where(
                Repository.id == repository_id,
                PullRequest.pr_number == pr_number,
            )
        )
        result = await db.execute(stmt)
        row = result.first()
        if not row:
            raise ValueError(f"Pull request #{pr_number} not found for repository {repository_id}")
        pr, repo = row[0], row[1]

        target_commit_sha = commit_sha or pr.current_head_sha

        # 2. Extract changed files and diff structure
        parsed_diff_files: list[FileDiff] = diff_files or []
        effective_changed_files = list(changed_files) if changed_files is not None else []

        # If diff_content is not provided and github_client is available, retrieve live diff
        if not diff_content and not parsed_diff_files and self.github_client and repo.full_name:
            try:
                diff_content = await self.github_client.get_pull_request_diff(
                    owner=repo.full_name,
                    pull_number=pr_number,
                )
            except Exception as exc:
                logger.warning(
                    "Could not retrieve live diff from GitHub for %s#%d: %s",
                    repo.full_name,
                    pr_number,
                    exc,
                )

        if diff_content and not parsed_diff_files:
            parser = DiffParser()
            parse_res = parser.parse(diff_content)
            parsed_diff_files = parse_res.files
            if not effective_changed_files:
                for f in parsed_diff_files:
                    path = f.new_path or f.old_path
                    if path:
                        effective_changed_files.append(path)

        # 3. Determine check applicability
        applicable_checks = determine_applicable_checks(effective_changed_files)
        logger.info(
            "PR #%d: %d changed files, applicable checks: %s",
            pr_number,
            len(effective_changed_files),
            [c.value for c in applicable_checks],
        )

        start_time = datetime.now(UTC)

        # 4. Execute checks or reuse supplied check_results
        executed_results: list[AnalysisResult] = list(check_results) if check_results else []
        collected_head_findings: list[RawFinding] = list(head_findings) if head_findings else []

        if not check_results and head_dir:
            tasks: dict[CheckType, Any] = {}
            if CheckType.STATIC_LINT in applicable_checks:
                tasks[CheckType.STATIC_LINT] = self.ruff.run(head_dir)
            if CheckType.SECURITY_SCAN in applicable_checks:
                tasks[CheckType.SECURITY_SCAN] = self.bandit.run(head_dir)
            if CheckType.DEPENDENCY_AUDIT in applicable_checks:
                tasks[CheckType.DEPENDENCY_AUDIT] = self.pip_audit.run(head_dir)
            if CheckType.TEST_EXECUTION in applicable_checks:
                tasks[CheckType.TEST_EXECUTION] = self.pytest.run(head_dir)

            if tasks:
                gathered = await asyncio.gather(*tasks.values())
                for (_check_type, _), res in zip(tasks.items(), gathered, strict=False):
                    executed_results.append(res)
                    if not head_findings:
                        collected_head_findings.extend(res.findings)

        # 5. Base findings resolution
        effective_base_findings: list[RawFinding] = list(base_findings) if base_findings else []
        if base_findings is None and base_dir and applicable_checks:
            base_tasks = []
            if CheckType.STATIC_LINT in applicable_checks:
                base_tasks.append(self.ruff.run(base_dir))
            if CheckType.SECURITY_SCAN in applicable_checks:
                base_tasks.append(self.bandit.run(base_dir))
            if base_tasks:
                base_gathered = await asyncio.gather(*base_tasks)
                for res in base_gathered:
                    effective_base_findings.extend(res.findings)

        # 6. Delta Classification
        classification_result: DeltaClassificationResult = self.classifier.classify(
            base_findings=effective_base_findings,
            head_findings=collected_head_findings,
            diff_files=parsed_diff_files if parsed_diff_files else None,
        )

        # 7. Quality Gate Evaluation
        verdict: QualityGateVerdict = self.quality_gate.evaluate(
            applicable_checks=applicable_checks,
            check_results=executed_results,
            classified_findings=classification_result.classified_findings,
            min_quality_score=min_quality_score,
            min_completeness=min_completeness,
        )

        completed_at = datetime.now(UTC)
        duration_ms = int((completed_at - start_time).total_seconds() * 1000)

        # 8. Query next run_number
        run_number_stmt = select(func.coalesce(func.max(AnalysisRun.run_number), 0)).where(
            AnalysisRun.pull_request_id == pr.id,
            AnalysisRun.commit_sha == target_commit_sha,
        )
        max_run = (await db.execute(run_number_stmt)).scalar() or 0
        next_run_number = max_run + 1

        # 9. Persist AnalysisRun
        run_id = str(uuid.uuid4())
        delta_summary = {
            **classification_result.summary,
            "reasons": verdict.reasons,
            "metrics": verdict.metrics,
            "checks": [
                {
                    "check_type": r.check_type.value,
                    "status": r.status.value,
                    "duration_ms": r.duration_ms,
                    "message": getattr(r, "error_message", None)
                    or getattr(r, "raw_stdout", "")
                    or "",
                    "output_digest": r.output_digest,
                }
                for r in executed_results
            ],
        }

        analysis_run = AnalysisRun(
            id=run_id,
            pull_request_id=pr.id,
            commit_sha=target_commit_sha,
            run_number=next_run_number,
            status="COMPLETED",
            runner_type="CONTAINER",
            duration_ms=duration_ms,
            verification_completeness=verdict.verification_completeness,
            quality_score=verdict.quality_score,
            gate_verdict=verdict.gate_verdict,
            delta_summary=delta_summary,
            completed_at=completed_at,
        )
        db.add(analysis_run)

        # 10. Persist Findings & Evidence Records
        for cf in classification_result.classified_findings:
            raw_f = cf.finding
            finding_id = str(uuid.uuid4())
            db_finding = Finding(
                id=finding_id,
                analysis_run_id=run_id,
                commit_sha=target_commit_sha,
                tool_source=raw_f.tool_source,
                tool_version=raw_f.tool_version,
                category=raw_f.category,
                severity=raw_f.severity,
                file_path=raw_f.file_path,
                start_line=raw_f.start_line,
                end_line=raw_f.end_line,
                rule_id=raw_f.rule_id,
                title=raw_f.title,
                message=raw_f.message,
                is_blocking=raw_f.is_blocking,
                delta_status=cf.delta_status,
                fingerprint=cf.fingerprint,
                provenance_type=raw_f.provenance_type,
                advisory_confidence=raw_f.advisory_confidence,
            )
            db.add(db_finding)

            # Persist raw evidence record if raw snippet/output exists
            if raw_f.code_snippet or raw_f.raw_output:
                evidence = EvidenceRecord(
                    id=str(uuid.uuid4()),
                    finding_id=finding_id,
                    evidence_type="RAW_FINDING_PAYLOAD",
                    raw_digest=cf.fingerprint,
                    structured_data={
                        "rule_id": raw_f.rule_id,
                        "enclosing_symbol": raw_f.enclosing_symbol,
                        "code_snippet": raw_f.code_snippet,
                        "raw_output": raw_f.raw_output,
                    },
                )
                db.add(evidence)

        await db.commit()

        # Re-fetch with findings loaded
        fetch_stmt = (
            select(AnalysisRun)
            .options(selectinload(AnalysisRun.findings))
            .where(AnalysisRun.id == run_id)
        )
        saved_run = (await db.execute(fetch_stmt)).scalar_one()
        return saved_run
