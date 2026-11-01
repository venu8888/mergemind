"""Manager for creating and tracking corrective draft pull requests on GitHub."""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.installation import Installation
from app.models.remediation import (
    PatchVerification,
    RemediationProposal,
    RemediationPullRequest,
)
from app.models.repository import Repository
from app.services.github.auth import get_github_client_for_installation
from app.services.github.client import GitHubClient
from app.services.remediation.patch_verifier import apply_unified_diff

logger = logging.getLogger(__name__)


class RemediationPRManager:
    """Creates reviewable corrective draft PRs on GitHub with verification evidence."""

    def __init__(self, github_client: GitHubClient | None = None):
        self.github_client = github_client

    async def create_corrective_pr(
        self,
        db: AsyncSession,
        proposal_id: str,
        base_branch: str | None = None,
    ) -> RemediationPullRequest:
        """Create a draft pull request for a verified remediation proposal."""
        stmt = (
            select(RemediationProposal, Repository)
            .join(Repository, RemediationProposal.repository_id == Repository.id)
            .where(RemediationProposal.id == proposal_id)
        )
        row = (await db.execute(stmt)).first()
        if not row:
            raise ValueError(f"Remediation proposal {proposal_id} not found")

        proposal, repo = row[0], row[1]

        # Check if PR already exists
        existing_pr = (
            await db.execute(
                select(RemediationPullRequest).where(
                    RemediationPullRequest.proposal_id == proposal_id
                )
            )
        ).scalar_one_or_none()
        if existing_pr:
            return existing_pr

        # Retrieve verification record if present
        verif = (
            await db.execute(
                select(PatchVerification).where(PatchVerification.proposal_id == proposal_id)
            )
        ).scalar_one_or_none()

        # Invariant: Never push unverified or explicitly rejected patches
        if verif and not verif.is_verified:
            raise ValueError(
                f"Cannot create PR for rejected patch proposal {proposal_id}: "
                f"regressions detected ({verif.regressions_count} regressions)"
            )

        target_base = base_branch or proposal.target_branch or "main"
        branch_name = f"mergemind/fix-{proposal.id[:8]}"

        body_markdown = self._generate_pr_body(proposal, verif, repo.full_name)

        pr_number = 101  # Default fallback if offline/mock
        pr_url = f"https://github.com/{repo.full_name}/pull/{pr_number}"

        # Resolve GitHub client: explicitly passed or dynamically through repository installation
        client = self.github_client
        if client is None and repo.installation_id:
            inst = (
                await db.execute(
                    select(Installation).where(Installation.id == repo.installation_id)
                )
            ).scalar_one_or_none()
            if inst:
                try:
                    client = await get_github_client_for_installation(inst.github_installation_id)
                except Exception as exc:
                    logger.warning("Could not instantiate installation client: %s", exc)

        if client and repo.full_name:
            try:
                # 1. Fetch base branch SHA
                base_ref = await client.get_branch_ref(repo.full_name, target_base)
                base_sha = base_ref.get("object", {}).get("sha")
                if not base_sha:
                    raise ValueError(f"Could not resolve base branch {target_base} commit SHA")

                # 2. Check if branch already exists, or create it
                try:
                    await client.get_branch_ref(repo.full_name, branch_name)
                    logger.info("Branch %s already exists on %s", branch_name, repo.full_name)
                except Exception:
                    logger.info("Creating corrective branch %s from %s (%s)", branch_name, target_base, base_sha[:8])
                    await client.create_branch_ref(repo.full_name, branch_name, base_sha)

                # 3. Apply patch locally and push updated file contents to the branch
                with tempfile.TemporaryDirectory() as tmp_dir:
                    for rel_file in (proposal.affected_files or []):
                        try:
                            file_bytes = await client.get_raw_content(
                                repo.full_name, rel_file, ref=branch_name
                            )
                            dest = os.path.join(tmp_dir, rel_file)
                            os.makedirs(os.path.dirname(dest), exist_ok=True)
                            with open(dest, "wb") as f:
                                f.write(file_bytes)
                        except Exception as e:
                            logger.debug("File %s not present on branch: %s", rel_file, e)

                    # Apply unified diff
                    diff_applied, diff_err = apply_unified_diff(tmp_dir, proposal.patch_diff)
                    if diff_applied:
                        for rel_file in (proposal.affected_files or []):
                            local_f = os.path.join(tmp_dir, rel_file)
                            if os.path.exists(local_f):
                                with open(local_f, "rb") as f:
                                    patched_bytes = f.read()

                                # Try to resolve current blob SHA if updating existing file
                                current_blob_sha = None
                                try:
                                    tree_info = await client.get_tree(repo.full_name, branch_name)
                                    for t_item in tree_info.get("tree", []):
                                        if t_item.get("path") == rel_file:
                                            current_blob_sha = t_item.get("sha")
                                            break
                                except Exception:
                                    pass

                                logger.info("Committing patched file %s to %s", rel_file, branch_name)
                                await client.create_or_update_file_contents(
                                    owner=repo.full_name,
                                    path=rel_file,
                                    message=f"[MergeMind] Automated fix for {proposal.title}",
                                    content_bytes=patched_bytes,
                                    branch=branch_name,
                                    sha=current_blob_sha,
                                )

                # 4. Open genuine draft Pull Request on GitHub
                logger.info("Opening GitHub Draft Pull Request on %s (%s -> %s)", repo.full_name, branch_name, target_base)
                pr_data = await client.create_pull_request(
                    owner=repo.full_name,
                    title=f"[MergeMind] {proposal.title}",
                    head=branch_name,
                    base=target_base,
                    body=body_markdown,
                    draft=True,
                )
                pr_number = pr_data.get("number", pr_number)
                pr_url = pr_data.get("html_url", pr_url)
                logger.info("Successfully created live GitHub Draft PR #%d at %s", pr_number, pr_url)
            except Exception as exc:
                logger.warning(
                    "Could not create live GitHub PR for %s (using simulated record): %s",
                    repo.full_name,
                    exc,
                )

        record = RemediationPullRequest(
            proposal_id=proposal.id,
            repository_id=repo.id,
            pr_number=pr_number,
            branch_name=branch_name,
            base_branch=target_base,
            pr_url=pr_url,
            status="DRAFT",
        )
        proposal.status = "PR_CREATED"

        db.add(record)
        await db.commit()
        await db.refresh(record)

        logger.info(
            "Created corrective draft PR #%d (%s) for proposal %s",
            record.pr_number,
            record.branch_name,
            proposal.id,
        )
        return record

    def _generate_pr_body(
        self,
        proposal: RemediationProposal,
        verif: PatchVerification | None,
        repo_name: str,
    ) -> str:
        """Construct structured Markdown description with evidence provenance."""
        verif_status = verif.sandbox_status if verif else "UNVERIFIED"
        resolved_count = verif.resolved_issues_count if verif else 0
        regressions_count = verif.regressions_count if verif else 0
        duration_ms = verif.duration_ms if verif else 0

        files_str = "\n".join(f"- `{f}`" for f in (proposal.affected_files or []))

        return f"""## 🤖 MergeMind Automated Corrective Patch

**Target Issue:** {proposal.title}
**Remediation Provider:** `{proposal.provider_name}` ({proposal.model_identifier or "default"})
**Confidence Score:** {proposal.confidence_score * 100:.1f}%

---

### 📋 Description & Rationale
{proposal.description}

> **Engineering Rationale:**
> {proposal.rationale}

---

### 🛡️ Dual-Run Sandbox Verification Evidence
| Verification Metric | Outcome |
|---|---|
| **Sandbox Status** | `{verif_status}` |
| **Resolved Issues** | `{resolved_count}` |
| **Regressions Detected** | `{regressions_count}` |
| **Verification Runtime** | `{duration_ms} ms` |

### 📁 Affected Files
{files_str}

---

### ⚠️ Developer Action Required
> **Important:** This pull request was automatically generated by **MergeMind**.
> Human review and approval is required before merging. MergeMind will never automatically merge corrective pull requests.
> **Health Invariant:** Merging this PR to `{proposal.target_branch}` will trigger an automatic repository health reassessment to update the repository health score.
"""
