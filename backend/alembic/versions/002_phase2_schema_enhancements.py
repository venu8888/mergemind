"""Phase 2 schema enhancements: installations table, repository linkage, PR timestamps, and durable queue attributes.

Revision ID: 002_phase2_schema_enhancements
Revises: 001_initial_schema
Create Date: 2026-11-01 22:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002_phase2_schema_enhancements"
down_revision: str | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create installations table
    op.create_table(
        "installations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("github_installation_id", sa.Integer(), nullable=False),
        sa.Column("account_login", sa.String(length=255), nullable=False),
        sa.Column("account_type", sa.String(length=50), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("sync_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("github_installation_id", name="uq_installations_github_id"),
    )
    op.create_index(
        "ix_installations_github_installation_id",
        "installations",
        ["github_installation_id"],
        unique=True,
    )
    op.create_index("ix_installations_state", "installations", ["state"])

    # 2. Add installation_id & github_updated_at to repositories
    op.add_column(
        "repositories",
        sa.Column(
            "installation_id",
            sa.String(length=36),
            sa.ForeignKey("installations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_repositories_installation_id", "repositories", ["installation_id"])
    op.add_column(
        "repositories",
        sa.Column("github_updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 3. Add github_updated_at to pull_requests
    op.add_column(
        "pull_requests",
        sa.Column("github_updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 4. Add durable queue columns to webhook_deliveries
    op.add_column(
        "webhook_deliveries",
        sa.Column(
            "processing_status", sa.String(length=32), nullable=False, server_default="PENDING"
        ),
    )
    op.create_index(
        "ix_webhook_deliveries_processing_status",
        "webhook_deliveries",
        ["processing_status"],
    )
    op.add_column(
        "webhook_deliveries",
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "webhook_deliveries",
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
    )
    op.add_column(
        "webhook_deliveries",
        sa.Column(
            "scheduled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_webhook_deliveries_scheduled_at",
        "webhook_deliveries",
        ["scheduled_at"],
    )
    op.add_column(
        "webhook_deliveries",
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "webhook_deliveries",
        sa.Column("locked_by", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "webhook_deliveries",
        sa.Column("lease_token", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_webhook_deliveries_lease_token",
        "webhook_deliveries",
        ["lease_token"],
    )
    op.add_column(
        "webhook_deliveries",
        sa.Column("lease_generation", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "webhook_deliveries",
        sa.Column("last_error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    # 4. Remove durable queue columns from webhook_deliveries
    op.drop_index("ix_webhook_deliveries_lease_token", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_scheduled_at", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_processing_status", table_name="webhook_deliveries")
    op.drop_column("webhook_deliveries", "last_error")
    op.drop_column("webhook_deliveries", "lease_generation")
    op.drop_column("webhook_deliveries", "lease_token")
    op.drop_column("webhook_deliveries", "locked_by")
    op.drop_column("webhook_deliveries", "locked_at")
    op.drop_column("webhook_deliveries", "scheduled_at")
    op.drop_column("webhook_deliveries", "max_attempts")
    op.drop_column("webhook_deliveries", "attempts")
    op.drop_column("webhook_deliveries", "processing_status")

    # 3. Remove github_updated_at from pull_requests
    op.drop_column("pull_requests", "github_updated_at")

    # 2. Remove installation_id & github_updated_at from repositories
    op.drop_column("repositories", "github_updated_at")
    op.drop_index("ix_repositories_installation_id", table_name="repositories")
    op.drop_column("repositories", "installation_id")

    # 1. Drop installations table
    op.drop_index("ix_installations_state", table_name="installations")
    op.drop_index("ix_installations_github_installation_id", table_name="installations")
    op.drop_table("installations")
