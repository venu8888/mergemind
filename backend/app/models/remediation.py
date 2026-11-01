"""Remediation proposal, dual-execution patch verification, and corrective PR models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.ci_failure import CIFailureRecord
    from app.models.finding import Finding
    from app.models.pull_request import PullRequest
    from app.models.repository import Repository

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class RemediationProposal(Base):
    """An AI-assisted or deterministic corrective code patch proposed for an issue or CI failure."""

    __tablename__ = "remediation_proposals"

    repository_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ci_failure_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ci_failures.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    finding_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("findings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pull_request_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("pull_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    target_commit_sha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    target_branch: Mapped[str] = mapped_column(String(255), nullable=False, default="main")
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PROPOSED", index=True
    )  # PROPOSED, VERIFYING, VERIFIED, REGRESSION_DETECTED, FAILED, PR_CREATED, REJECTED
    provider_name: Mapped[str] = mapped_column(
        String(50), nullable=False, default="mock"
    )  # mock, openai, gemini, anthropic, deterministic
    model_identifier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.85)
    patch_diff: Mapped[str] = mapped_column(Text, nullable=False)  # Unified diff format
    affected_files: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False, default=list)
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence_records: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE, nullable=False, default=dict
    )

    # Relationships
    repository: Mapped[Repository] = relationship("Repository", lazy="selectin")
    ci_failure: Mapped[CIFailureRecord | None] = relationship(
        "CIFailureRecord", back_populates="remediation_proposals", lazy="selectin"
    )
    finding: Mapped[Finding | None] = relationship("Finding", lazy="selectin")
    pull_request: Mapped[PullRequest | None] = relationship("PullRequest", lazy="selectin")
    verifications: Mapped[list[PatchVerification]] = relationship(
        "PatchVerification",
        back_populates="proposal",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    remediation_pr: Mapped[RemediationPullRequest | None] = relationship(
        "RemediationPullRequest",
        back_populates="proposal",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (Index("ix_remediation_proposals_repo_status", "repository_id", "status"),)


class PatchVerification(Base):
    """Execution output from dual-run verification of a remediation proposal in the isolated sandbox."""

    __tablename__ = "patch_verifications"

    proposal_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("remediation_proposals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sandbox_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="RUNNING", index=True
    )  # RUNNING, PASSED, FAILED, REGRESSION_DETECTED, TIMEOUT, ERROR
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    regressions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    resolved_issues_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pre_patch_findings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    post_patch_findings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pre_patch_findings: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON_TYPE, nullable=False, default=list
    )
    post_patch_findings: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON_TYPE, nullable=False, default=list
    )
    test_results: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    sandbox_logs: Mapped[str] = mapped_column(Text, nullable=False, default="")
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    proposal: Mapped[RemediationProposal] = relationship(
        "RemediationProposal", back_populates="verifications"
    )

    __table_args__ = (
        Index("ix_patch_verifications_proposal_status", "proposal_id", "sandbox_status"),
    )


class RemediationPullRequest(Base):
    """Corrective pull request created on GitHub for developer review and approval."""

    __tablename__ = "remediation_pull_requests"

    proposal_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("remediation_proposals.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    repository_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    branch_name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_branch: Mapped[str] = mapped_column(String(255), nullable=False, default="main")
    pr_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="DRAFT", index=True
    )  # DRAFT, OPEN, MERGED, CLOSED
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    proposal: Mapped[RemediationProposal] = relationship(
        "RemediationProposal", back_populates="remediation_pr"
    )
    repository: Mapped[Repository] = relationship("Repository", lazy="selectin")
