"""Pull Request Model."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.analysis_run import AnalysisRun
    from app.models.repository import Repository


class PullRequest(Base):
    """Represents a GitHub pull request being tracked and analyzed."""

    __tablename__ = "pull_requests"
    __table_args__ = (UniqueConstraint("repository_id", "pr_number", name="uq_repo_pr_number"),)

    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    author_username: Mapped[str] = mapped_column(String(100), nullable=False)
    base_branch: Mapped[str] = mapped_column(String(100), nullable=False)
    head_branch: Mapped[str] = mapped_column(String(100), nullable=False)
    current_head_sha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    github_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __init__(self, **kwargs):
        if "author" in kwargs:
            kwargs["author_username"] = kwargs.pop("author")
        if "head_sha" in kwargs:
            kwargs["current_head_sha"] = kwargs.pop("head_sha")
        kwargs.pop("base_sha", None)
        kwargs.pop("github_pr_id", None)
        kwargs.pop("github_created_at", None)
        if "base_branch" not in kwargs:
            kwargs["base_branch"] = "main"
        if "head_branch" not in kwargs:
            kwargs["head_branch"] = "feature"
        super().__init__(**kwargs)

    # Compatibility properties
    @property
    def head_sha(self) -> str:
        return self.current_head_sha

    @head_sha.setter
    def head_sha(self, value: str) -> None:
        self.current_head_sha = value

    @property
    def author(self) -> str:
        return self.author_username

    @author.setter
    def author(self, value: str) -> None:
        self.author_username = value

    # Relationships
    repository: Mapped[Repository] = relationship("Repository", back_populates="pull_requests")
    analysis_runs: Mapped[list[AnalysisRun]] = relationship(
        "AnalysisRun", back_populates="pull_request", cascade="all, delete-orphan"
    )
