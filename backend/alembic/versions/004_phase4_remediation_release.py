"""Phase 4 schema enhancements: CI failure intelligence, remediation proposals, patch verification, and corrective pull requests.

Revision ID: 004_phase4_remediation
Revises: 003_phase3_verification
Create Date: 2026-11-02 02:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "004_phase4_remediation"
down_revision: str | None = "003_phase3_verification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    # 1. ci_failures table
    op.create_table(
        "ci_failures",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "repository_id",
            sa.String(length=36),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pull_request_id",
            sa.String(length=36),
            sa.ForeignKey("pull_requests.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("workflow_run_id", sa.BigInteger(), nullable=False),
        sa.Column("workflow_name", sa.String(length=255), nullable=False),
        sa.Column("job_id", sa.BigInteger(), nullable=True),
        sa.Column("job_name", sa.String(length=255), nullable=False),
        sa.Column("commit_sha", sa.String(length=40), nullable=False),
        sa.Column("branch", sa.String(length=255), nullable=False),
        sa.Column(
            "failure_category",
            sa.String(length=50),
            nullable=False,
            server_default="BUILD_ERROR",
        ),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="DETECTED"),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("log_excerpt", sa.Text(), nullable=False, server_default=""),
        sa.Column("localized_files", json_type, nullable=False),
        sa.Column("root_cause_analysis", json_type, nullable=False),
        sa.Column("ai_advisory_hypothesis", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_ci_failures_repository_id", "ci_failures", ["repository_id"])
    op.create_index("ix_ci_failures_workflow_run_id", "ci_failures", ["workflow_run_id"])
    op.create_index("ix_ci_failures_commit_sha", "ci_failures", ["commit_sha"])
    op.create_index("ix_ci_failures_status", "ci_failures", ["status"])
    op.create_index("ix_ci_failures_failure_category", "ci_failures", ["failure_category"])
    op.create_index("ix_ci_failures_repo_status", "ci_failures", ["repository_id", "status"])

    # 2. remediation_proposals table
    op.create_table(
        "remediation_proposals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "repository_id",
            sa.String(length=36),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "ci_failure_id",
            sa.String(length=36),
            sa.ForeignKey("ci_failures.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "finding_id",
            sa.String(length=36),
            sa.ForeignKey("findings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "pull_request_id",
            sa.String(length=36),
            sa.ForeignKey("pull_requests.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("target_commit_sha", sa.String(length=40), nullable=False),
        sa.Column("target_branch", sa.String(length=255), nullable=False, server_default="main"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PROPOSED"),
        sa.Column("provider_name", sa.String(length=50), nullable=False, server_default="mock"),
        sa.Column("model_identifier", sa.String(length=100), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.85"),
        sa.Column("patch_diff", sa.Text(), nullable=False),
        sa.Column("affected_files", json_type, nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence_records", json_type, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_remediation_proposals_repository_id", "remediation_proposals", ["repository_id"]
    )
    op.create_index("ix_remediation_proposals_status", "remediation_proposals", ["status"])
    op.create_index(
        "ix_remediation_proposals_commit", "remediation_proposals", ["target_commit_sha"]
    )
    op.create_index(
        "ix_remediation_proposals_repo_status", "remediation_proposals", ["repository_id", "status"]
    )

    # 3. patch_verifications table
    op.create_table(
        "patch_verifications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "proposal_id",
            sa.String(length=36),
            sa.ForeignKey("remediation_proposals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sandbox_status", sa.String(length=50), nullable=False, server_default="RUNNING"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("regressions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resolved_issues_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pre_patch_findings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("post_patch_findings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pre_patch_findings", json_type, nullable=False),
        sa.Column("post_patch_findings", json_type, nullable=False),
        sa.Column("test_results", json_type, nullable=False),
        sa.Column("sandbox_logs", sa.Text(), nullable=False, server_default=""),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_patch_verifications_proposal_id", "patch_verifications", ["proposal_id"])
    op.create_index(
        "ix_patch_verifications_proposal_status",
        "patch_verifications",
        ["proposal_id", "sandbox_status"],
    )

    # 4. remediation_pull_requests table
    op.create_table(
        "remediation_pull_requests",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "proposal_id",
            sa.String(length=36),
            sa.ForeignKey("remediation_proposals.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "repository_id",
            sa.String(length=36),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pr_number", sa.Integer(), nullable=False),
        sa.Column("branch_name", sa.String(length=255), nullable=False),
        sa.Column("base_branch", sa.String(length=255), nullable=False, server_default="main"),
        sa.Column("pr_url", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="DRAFT"),
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_remediation_pull_requests_repo", "remediation_pull_requests", ["repository_id"]
    )
    op.create_index(
        "ix_remediation_pull_requests_pr_number", "remediation_pull_requests", ["pr_number"]
    )
    op.create_index("ix_remediation_pull_requests_status", "remediation_pull_requests", ["status"])


def downgrade() -> None:
    op.drop_table("remediation_pull_requests")
    op.drop_table("patch_verifications")
    op.drop_table("remediation_proposals")
    op.drop_table("ci_failures")
