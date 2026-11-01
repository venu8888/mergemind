"""CI/CD failure intelligence and root-cause localization models."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.pull_request import PullRequest
    from app.models.remediation import RemediationProposal
    from app.models.repository import Repository

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class CIFailureRecord(Base):
    """Stores ingested GitHub Actions workflow/job failures with root-cause intelligence."""

    __tablename__ = "ci_failures"

    repository_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pull_request_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("pull_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workflow_run_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    workflow_name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    job_name: Mapped[str] = mapped_column(String(255), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    branch: Mapped[str] = mapped_column(String(255), nullable=False)
    failure_category: Mapped[str] = mapped_column(
        String(50), nullable=False, default="BUILD_ERROR", index=True
    )  # TEST_FAILURE, LINT_ERROR, SECURITY_VIOLATION, DEPENDENCY_CONFLICT, BUILD_ERROR, TIMEOUT, INFRASTRUCTURE_FAILURE
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="DETECTED", index=True
    )  # DETECTED, INVESTIGATING, REMEDIATION_PROPOSED, RESOLVED, IGNORED
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    log_excerpt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    localized_files: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON_TYPE, nullable=False, default=list
    )
    root_cause_analysis: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE, nullable=False, default=dict
    )
    ai_advisory_hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    repository: Mapped[Repository] = relationship("Repository", lazy="selectin")
    pull_request: Mapped[PullRequest | None] = relationship("PullRequest", lazy="selectin")
    remediation_proposals: Mapped[list[RemediationProposal]] = relationship(
        "RemediationProposal", back_populates="ci_failure", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_ci_failures_repo_status", "repository_id", "status"),
        Index("ix_ci_failures_commit_category", "commit_sha", "failure_category"),
    )
