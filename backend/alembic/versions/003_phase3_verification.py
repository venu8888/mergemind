"""Phase 3 schema enhancements: repository health assessments, verification completeness, and finding fingerprints.

Revision ID: 003_phase3_health_and_verification
Revises: 002_phase2_schema_enhancements
Create Date: 2026-11-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003_phase3_verification"
down_revision: str | None = "002_phase2_schema_enhancements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. repository_health_assessments table
    op.create_table(
        "repository_health_assessments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "repository_id",
            sa.String(length=36),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("commit_sha", sa.String(length=40), nullable=False),
        sa.Column("branch_name", sa.String(length=255), nullable=False, server_default="main"),
        sa.Column("health_score", sa.Float(), nullable=True),
        sa.Column("assessment_completeness", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("is_qualified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("qualification_reason", sa.String(length=255), nullable=True),
        sa.Column("code_quality_score", sa.Float(), nullable=True),
        sa.Column("security_score", sa.Float(), nullable=True),
        sa.Column("dependency_score", sa.Float(), nullable=True),
        sa.Column("test_health_score", sa.Float(), nullable=True),
        sa.Column("maintainability_score", sa.Float(), nullable=True),
        sa.Column(
            "scoring_policy_version",
            sa.String(length=50),
            nullable=False,
            server_default="v2.2-calibrated",
        ),
        sa.Column("dimension_status", sa.JSON(), nullable=False),
        sa.Column("summary_metrics", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_repo_health_repo_id", "repository_health_assessments", ["repository_id"])
    op.create_index("ix_repo_health_commit_sha", "repository_health_assessments", ["commit_sha"])

    # 2. Add verification completeness, quality score, gate verdict, delta summary to analysis_runs
    op.add_column(
        "analysis_runs",
        sa.Column("verification_completeness", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("quality_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("gate_verdict", sa.String(length=32), nullable=False, server_default="PENDING"),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("delta_summary", sa.JSON(), nullable=True),
    )

    # 3. Add delta classification, fingerprint, and provenance to findings
    op.add_column(
        "findings",
        sa.Column("delta_status", sa.String(length=32), nullable=False, server_default="UNKNOWN"),
    )
    op.add_column(
        "findings",
        sa.Column("fingerprint", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "findings",
        sa.Column(
            "provenance_type",
            sa.String(length=32),
            nullable=False,
            server_default="DETERMINISTIC_TOOL",
        ),
    )
    op.add_column(
        "findings",
        sa.Column("advisory_confidence", sa.Float(), nullable=True),
    )
    op.create_index("ix_findings_fingerprint", "findings", ["fingerprint"])


def downgrade() -> None:
    op.drop_index("ix_findings_fingerprint", table_name="findings")
    op.drop_column("findings", "advisory_confidence")
    op.drop_column("findings", "provenance_type")
    op.drop_column("findings", "fingerprint")
    op.drop_column("findings", "delta_status")

    op.drop_column("analysis_runs", "delta_summary")
    op.drop_column("analysis_runs", "gate_verdict")
    op.drop_column("analysis_runs", "quality_score")
    op.drop_column("analysis_runs", "verification_completeness")

    op.drop_index("ix_repo_health_commit_sha", table_name="repository_health_assessments")
    op.drop_index("ix_repo_health_repo_id", table_name="repository_health_assessments")
    op.drop_table("repository_health_assessments")
