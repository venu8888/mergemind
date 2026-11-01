"""GitHub App Installation Lifecycle and Optimistic Repository Synchronization."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.installation import Installation
from app.models.repository import Repository
from app.services.github.client import GitHubClient

logger = logging.getLogger(__name__)


def _is_sqlite(db: AsyncSession) -> bool:
    bind = db.bind
    return bind is not None and hasattr(bind, "dialect") and bind.dialect.name == "sqlite"


async def handle_installation_event(
    arg1: Any,
    arg2: Any = None,
    payload: dict[str, Any] | None = None,
    client: GitHubClient | None = None,
) -> Installation | None:
    """Handles installation webhook lifecycle events (created, deleted, suspend, unsuspend).

    Supports flexible signatures:
    - handle_installation_event(payload: dict, db: AsyncSession)
    - handle_installation_event(db: AsyncSession, action: str, payload: dict, client: GitHubClient | None = None)
    """
    if isinstance(arg1, dict):
        payload_data = arg1
        db: AsyncSession = arg2
        action = payload_data.get("action", "")
    else:
        db: AsyncSession = arg1
        action = str(arg2)
        payload_data = payload or {}

    installation_data = payload_data.get("installation", {})
    github_inst_id = installation_data.get("id")
    if not github_inst_id:
        logger.warning("Installation event missing installation.id")
        return None

    account_data = installation_data.get("account", {})
    account_login = account_data.get("login", "unknown")
    account_type = account_data.get("type", "User")
    permissions = installation_data.get("permissions", {})

    now = datetime.now(UTC)

    # Find existing installation
    stmt = select(Installation).where(Installation.github_installation_id == github_inst_id)
    res = await db.execute(stmt)
    installation = res.scalar_one_or_none()

    if action == "created":
        if installation is None:
            installation = Installation(
                github_installation_id=github_inst_id,
                account_login=account_login,
                account_type=account_type,
                state="ACTIVE",
                sync_version=1,
                permissions=permissions,
                installed_at=now,
            )
            db.add(installation)
        else:
            installation.state = "ACTIVE"
            installation.account_login = account_login
            installation.account_type = account_type
            installation.permissions = permissions
            installation.suspended_at = None

        await db.commit()
        await db.refresh(installation)

        # Trigger repository reconciliation if client is provided
        if client:
            await reconcile_installation_repositories(db, github_inst_id, client)
        return installation

    if installation is None:
        logger.warning(
            f"Received installation.{action} for untracked installation {github_inst_id}"
        )
        return None

    if action == "deleted":
        installation.state = "DELETED"
        installation.suspended_at = now
        # Deactivate all linked repositories
        deactivate_stmt = (
            update(Repository)
            .where(Repository.installation_id == installation.id)
            .values(is_active=False)
        )
        await db.execute(deactivate_stmt)
        await db.commit()
        await db.refresh(installation)
        logger.info(f"Installation {github_inst_id} marked DELETED; child repositories deactivated")
        return installation

    if action == "suspend":
        installation.state = "SUSPENDED"
        installation.suspended_at = now
        # Deactivate linked repositories
        deactivate_stmt = (
            update(Repository)
            .where(Repository.installation_id == installation.id)
            .values(is_active=False)
        )
        await db.execute(deactivate_stmt)
        await db.commit()
        await db.refresh(installation)
        logger.info(
            f"Installation {github_inst_id} marked SUSPENDED; child repositories deactivated"
        )
        return installation

    if action == "unsuspend":
        installation.state = "ACTIVE"
        installation.suspended_at = None
        await db.commit()
        await db.refresh(installation)
        logger.info(f"Installation {github_inst_id} restored to ACTIVE")
        if client:
            await reconcile_installation_repositories(db, github_inst_id, client)
        return installation

    return installation


async def reconcile_installation_repositories(
    arg1: Any = None,
    arg2: Any = None,
    arg3: Any = None,
    github_installation_id: int | None = None,
    client: GitHubClient | None = None,
    db: AsyncSession | None = None,
) -> int:
    """Optimistically reconciles repositories accessible to an installation using live GitHub API.

    Supports signatures:
    - reconcile_installation_repositories(db, github_installation_id, client)
    - reconcile_installation_repositories(github_installation_id, client, db)
    - reconcile_installation_repositories(github_installation_id=..., client=..., db=...)
    """
    if isinstance(arg1, AsyncSession):
        db = arg1
        github_installation_id = int(arg2)
        client = arg3
    elif arg1 is not None:
        github_installation_id = int(arg1)
        client = arg2
        db = arg3

    if github_installation_id is None or client is None or db is None:
        logger.error("reconcile_installation_repositories missing required arguments")
        return 0

    # Step 1: Pre-check outside transaction
    stmt = select(Installation.id, Installation.state, Installation.sync_version).where(
        Installation.github_installation_id == github_installation_id
    )
    res = await db.execute(stmt)
    row = res.first()
    if not row:
        logger.warning(
            f"Cannot reconcile repositories: Installation {github_installation_id} not found"
        )
        return 0

    inst_id, state, expected_version = row[0], row[1], row[2]
    if state != "ACTIVE":
        logger.info(
            f"Skipping reconciliation for non-active installation {github_installation_id} ({state})"
        )
        return 0

    # Step 2: Fetch authoritative repository list from GitHub API (OUTSIDE DB TX)
    github_repos = await client.get_installation_repositories()
    active_github_repo_ids = {repo["id"] for repo in github_repos}

    # Step 3: Fast Atomic Reconciliation Transaction (< 5 milliseconds)
    db.expire_all()
    lock_stmt = select(Installation).where(Installation.id == inst_id)
    if not _is_sqlite(db):
        lock_stmt = lock_stmt.with_for_update()

    lock_res = await db.execute(lock_stmt)
    locked_inst = lock_res.scalar_one_or_none()

    if not locked_inst:
        return 0

    # Invariant checks: ensure state is still ACTIVE and sync_version hasn't moved
    if locked_inst.state != "ACTIVE" or locked_inst.sync_version != expected_version:
        logger.warning(
            f"Optimistic sync abort for installation {github_installation_id}: "
            f"State changed to {locked_inst.state} or sync_version changed from {expected_version} to {locked_inst.sync_version}"
        )
        await db.rollback()
        return 0

    now = datetime.now(UTC)

    # 1. Deactivate repos that are no longer accessible to this installation
    deact_stmt = (
        update(Repository)
        .where(
            Repository.installation_id == locked_inst.id,
            Repository.github_repo_id.not_in(active_github_repo_ids),
            Repository.is_active.is_(True),
        )
        .values(is_active=False, updated_at=now)
    )
    await db.execute(deact_stmt)

    # 2. Upsert / reactivate current active repos
    for repo_data in github_repos:
        repo_github_id = repo_data["id"]
        full_name = repo_data["full_name"]
        default_branch = repo_data.get("default_branch", "main")

        existing_stmt = select(Repository).where(Repository.github_repo_id == repo_github_id)
        existing_res = await db.execute(existing_stmt)
        repo_obj = existing_res.scalar_one_or_none()

        if repo_obj is None:
            repo_obj = Repository(
                github_repo_id=repo_github_id,
                full_name=full_name,
                default_branch=default_branch,
                is_active=True,
                installation_id=locked_inst.id,
            )
            db.add(repo_obj)
        else:
            repo_obj.full_name = full_name
            repo_obj.default_branch = default_branch
            repo_obj.is_active = True
            repo_obj.installation_id = locked_inst.id
            repo_obj.updated_at = now

    # Advance sync_version to guard against stale updates
    locked_inst.sync_version += 1
    locked_inst.last_synced_at = now
    await db.commit()

    logger.info(
        f"Reconciled installation {github_installation_id}: {len(github_repos)} active repositories, sync_version advanced to {locked_inst.sync_version}"
    )
    return len(github_repos)
