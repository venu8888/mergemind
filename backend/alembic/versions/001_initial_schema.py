"""Initial database schema creation.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-11-01 16:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. webhook_deliveries
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("delivery_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=True),
        sa.Column("payload_summary", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="RECEIVED"),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_webhook_deliveries_delivery_id", "webhook_deliveries", ["delivery_id"], unique=True
    )

    # 2. repositories
    op.create_table(
        "repositories",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("github_repo_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("default_branch", sa.String(length=100), nullable=False, server_default="main"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("settings_override", sa.JSON(), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_repositories_github_repo_id", "repositories", ["github_repo_id"], unique=True
    )
    op.create_index("ix_repositories_full_name", "repositories", ["full_name"])

    # 3. pull_requests
    op.create_table(
        "pull_requests",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "repository_id",
            sa.String(length=36),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pr_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("author_username", sa.String(length=100), nullable=False),
        sa.Column("base_branch", sa.String(length=100), nullable=False),
        sa.Column("head_branch", sa.String(length=100), nullable=False),
        sa.Column("current_head_sha", sa.String(length=40), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("repository_id", "pr_number", name="uq_repo_pr_number"),
    )
    op.create_index("ix_pull_requests_repository_id", "pull_requests", ["repository_id"])
    op.create_index("ix_pull_requests_pr_number", "pull_requests", ["pr_number"])
    op.create_index("ix_pull_requests_current_head_sha", "pull_requests", ["current_head_sha"])

    # 4. analysis_runs
    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "pull_request_id",
            sa.String(length=36),
            sa.ForeignKey("pull_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("commit_sha", sa.String(length=40), nullable=False),
        sa.Column("run_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("runner_type", sa.String(length=32), nullable=False, server_default="CONTAINER"),
        sa.Column("runner_id", sa.String(length=100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("failure_reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("pull_request_id", "commit_sha", "run_number", name="uq_pr_commit_run"),
    )
    op.create_index("ix_analysis_runs_pull_request_id", "analysis_runs", ["pull_request_id"])
    op.create_index("ix_analysis_runs_commit_sha", "analysis_runs", ["commit_sha"])
    op.create_index("ix_analysis_runs_status", "analysis_runs", ["status"])

    # 5. findings
    op.create_table(
        "findings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "analysis_run_id",
            sa.String(length=36),
            sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("commit_sha", sa.String(length=40), nullable=False),
        sa.Column("tool_source", sa.String(length=50), nullable=False),
        sa.Column("tool_version", sa.String(length=50), nullable=False, server_default="unknown"),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=True),
        sa.Column("end_line", sa.Integer(), nullable=True),
        sa.Column("rule_id", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "verification_status",
            sa.String(length=50),
            nullable=False,
            server_default="CONFIRMED_DETERMINISTIC",
        ),
        sa.Column("is_blocking", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_findings_analysis_run_id", "findings", ["analysis_run_id"])
    op.create_index("ix_findings_commit_sha", "findings", ["commit_sha"])
    op.create_index("ix_findings_severity", "findings", ["severity"])
    op.create_index(
        "idx_findings_run_severity", "findings", ["analysis_run_id", "severity", "is_blocking"]
    )

    # 6. test_executions
    op.create_table(
        "test_executions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "analysis_run_id",
            sa.String(length=36),
            sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("commit_sha", sa.String(length=40), nullable=False),
        sa.Column("framework", sa.String(length=50), nullable=False, server_default="PYTEST"),
        sa.Column("total_tests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("exit_code", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stdout_sample", sa.Text(), nullable=True),
        sa.Column("stderr_sample", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="SUCCESS"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_test_executions_analysis_run_id", "test_executions", ["analysis_run_id"])
    op.create_index("ix_test_executions_commit_sha", "test_executions", ["commit_sha"])

    # 7. evidence_records
    op.create_table(
        "evidence_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "finding_id",
            sa.String(length=36),
            sa.ForeignKey("findings.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "test_execution_id",
            sa.String(length=36),
            sa.ForeignKey("test_executions.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("evidence_type", sa.String(length=50), nullable=False),
        sa.Column("raw_digest", sa.String(length=64), nullable=False),
        sa.Column("structured_data", sa.JSON(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evidence_records_finding_id", "evidence_records", ["finding_id"])
    op.create_index(
        "ix_evidence_records_test_execution_id", "evidence_records", ["test_execution_id"]
    )

    # 8. quality_assessments
    op.create_table(
        "quality_assessments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "analysis_run_id",
            sa.String(length=36),
            sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("verification_completeness", sa.Float(), nullable=False),
        sa.Column("gate_decision", sa.String(length=20), nullable=False),
        sa.Column(
            "gate_policy_name", sa.String(length=50), nullable=False, server_default="default"
        ),
        sa.Column("rule_evaluations", sa.JSON(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("analysis_run_id", name="uq_assessment_run"),
    )
    op.create_index(
        "ix_quality_assessments_analysis_run_id", "quality_assessments", ["analysis_run_id"]
    )
    op.create_index(
        "ix_quality_assessments_gate_decision", "quality_assessments", ["gate_decision"]
    )


def downgrade() -> None:
    op.drop_table("quality_assessments")
    op.drop_table("evidence_records")
    op.drop_table("test_executions")
    op.drop_table("findings")
    op.drop_table("analysis_runs")
    op.drop_table("pull_requests")
    op.drop_table("repositories")
    op.drop_table("webhook_deliveries")
