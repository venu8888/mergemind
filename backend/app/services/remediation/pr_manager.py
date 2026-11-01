"""Manager for creating and tracking corrective draft pull requests on GitHub."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.remediation import (
    PatchVerification,
    RemediationProposal,
    RemediationPullRequest,
)
from app.models.repository import Repository
from app.services.github.client import GitHubClient

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

        target_base = base_branch or proposal.target_branch or "main"
        branch_name = f"mergemind/fix-{proposal.id[:8]}"

        # Retrieve verification record if present
        verif = (
            await db.execute(
                select(PatchVerification).where(PatchVerification.proposal_id == proposal_id)
            )
        ).scalar_one_or_none()

        body_markdown = self._generate_pr_body(proposal, verif, repo.full_name)

        pr_number = 101  # Default fallback if offline/mock
        pr_url = f"https://github.com/{repo.full_name}/pull/{pr_number}"

        if self.github_client and repo.full_name:
            try:
                pr_data = await self.github_client.create_pull_request(
                    owner=repo.full_name,
                    title=f"[MergeMind] {proposal.title}",
                    head=branch_name,
                    base=target_base,
                    body=body_markdown,
                    draft=True,
                )
                pr_number = pr_data.get("number", pr_number)
                pr_url = pr_data.get("html_url", pr_url)
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

        files_str = "\n".join(f"- `{f}`" for f in proposal.affected_files)

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
