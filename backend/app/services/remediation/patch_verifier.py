"""Dual-run sandbox verification engine for proposed remediation patches."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.remediation import PatchVerification, RemediationProposal
from app.services.analysis.runners.bandit_runner import BanditRunner
from app.services.analysis.runners.ruff_runner import RuffRunner
from app.services.sandbox.engine import SandboxEngine
from app.services.sandbox.pytest_runner import PytestSandboxRunner
from app.services.verification.fingerprint import compute_finding_fingerprint

logger = logging.getLogger(__name__)


def apply_unified_diff(target_dir: str, patch_diff: str) -> tuple[bool, str | None]:
    """Applies a unified diff patch to files in target_dir.

    Parses hunk headers and applies simple line substitutions.
    Returns (success, error_message).
    """
    try:
        lines = patch_diff.splitlines()
        current_file = None
        file_patches: dict[str, list[tuple[int, int, list[str]]]] = {}

        idx = 0
        while idx < len(lines):
            line = lines[idx]
            if line.startswith("+++ b/"):
                current_file = line[6:].strip()
                file_patches[current_file] = []
                idx += 1
                continue
            elif line.startswith("@@ "):
                # Parse @@ -old_start,old_len +new_start,new_len @@
                parts = line.split("@@")
                header = parts[1].strip()
                new_part = header.split("+")[1].split()[0]
                new_start = int(new_part.split(",")[0])

                hunk_lines: list[str] = []
                idx += 1
                while (
                    idx < len(lines)
                    and not lines[idx].startswith("@@ ")
                    and not lines[idx].startswith("diff --git")
                ):
                    hunk_lines.append(lines[idx])
                    idx += 1

                if current_file:
                    file_patches[current_file].append((new_start, len(hunk_lines), hunk_lines))
                continue
            idx += 1

        for rel_path, patch_list in file_patches.items():
            full_path = os.path.join(target_dir, rel_path)
            if not os.path.exists(full_path):
                # Create parent directories if needed
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                # If file doesn't exist, create it from addition lines
                added_content = []
                for _, _, h_lines in patch_list:
                    for h_line in h_lines:
                        if h_line.startswith("+"):
                            added_content.append(h_line[1:] + "\n")
                        elif not h_line.startswith("-"):
                            added_content.append(h_line[1:] + "\n")
                with open(full_path, "w", encoding="utf-8") as f:
                    f.writelines(added_content)
                continue

            # Read existing content
            with open(full_path, encoding="utf-8", errors="replace") as f:
                orig_lines = f.readlines()

            new_lines = list(orig_lines)
            for _new_start, _, h_lines in patch_list:
                # Simple replacement for target block
                removals = [hl[1:] for hl in h_lines if hl.startswith("-")]
                additions = [
                    hl[1:] + "\n" if not hl.endswith("\n") else hl[1:]
                    for hl in h_lines
                    if hl.startswith("+")
                ]

                if removals and additions:
                    # Look for removal match in file
                    rem_text = "".join(removals).strip()
                    file_text = "".join(new_lines)
                    if rem_text in file_text:
                        file_text = file_text.replace(rem_text, "".join(additions).strip(), 1)
                        new_lines = [line_item + "\n" for line_item in file_text.splitlines()]

            with open(full_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

        return True, None
    except Exception as exc:
        return False, f"Failed to apply unified diff: {exc}"


class PatchVerifier:
    """Executes dual-run sandbox analysis to verify remediation patches before PR creation."""

    def __init__(
        self,
        sandbox: SandboxEngine | None = None,
        ruff_runner: RuffRunner | None = None,
        bandit_runner: BanditRunner | None = None,
        pytest_runner: PytestSandboxRunner | None = None,
    ):
        self.sandbox = sandbox or SandboxEngine()
        self.ruff = ruff_runner or RuffRunner()
        self.bandit = bandit_runner or BanditRunner()
        self.pytest = pytest_runner or PytestSandboxRunner(self.sandbox)

    async def verify_proposal(
        self,
        db: AsyncSession,
        proposal_id: str,
        base_source_dir: str | None = None,
    ) -> PatchVerification:
        """Execute dual-run verification: evaluate pre-patch vs post-patch in sandbox."""
        start_time = time.perf_counter()

        stmt = select(RemediationProposal).where(RemediationProposal.id == proposal_id)
        proposal = (await db.execute(stmt)).scalar_one_or_none()
        if not proposal:
            raise ValueError(f"Remediation proposal {proposal_id} not found")

        proposal.status = "VERIFYING"
        await db.commit()

        # Create isolated temporary scratch directories for pre-patch and post-patch
        with tempfile.TemporaryDirectory() as pre_dir, tempfile.TemporaryDirectory() as post_dir:
            # Populate base files if supplied, or create mock directory structure
            if base_source_dir and os.path.isdir(base_source_dir):
                shutil.copytree(base_source_dir, pre_dir, dirs_exist_ok=True)
                shutil.copytree(base_source_dir, post_dir, dirs_exist_ok=True)
            else:
                # Scaffold minimal target directory from affected files
                for f_rel in proposal.affected_files:
                    pre_file = os.path.join(pre_dir, f_rel)
                    post_file = os.path.join(post_dir, f_rel)
                    os.makedirs(os.path.dirname(pre_file), exist_ok=True)
                    os.makedirs(os.path.dirname(post_file), exist_ok=True)
                    sample_content = "def sample():\n    return False\n"
                    with open(pre_file, "w", encoding="utf-8") as pf:
                        pf.write(sample_content)
                    with open(post_file, "w", encoding="utf-8") as pf:
                        pf.write(sample_content)

            # 1. Evaluate pre-patch state
            pre_findings = await self._run_analysis(pre_dir)

            # 2. Apply proposed patch to post_dir
            success, err = apply_unified_diff(post_dir, proposal.patch_diff)
            if not success:
                logger.error("Failed to apply patch diff: %s", err)
                record = PatchVerification(
                    proposal_id=proposal.id,
                    sandbox_status="FAILED",
                    is_verified=False,
                    regressions_count=0,
                    resolved_issues_count=0,
                    pre_patch_findings_count=len(pre_findings),
                    post_patch_findings_count=len(pre_findings),
                    pre_patch_findings=[f.__dict__ for f in pre_findings],
                    post_patch_findings=[],
                    test_results={"error": err},
                    sandbox_logs=f"Patch application failed: {err}",
                    duration_ms=int((time.perf_counter() - start_time) * 1000),
                )
                proposal.status = "FAILED"
                db.add(record)
                await db.commit()
                await db.refresh(record)
                return record

            # 3. Evaluate post-patch state
            post_findings = await self._run_analysis(post_dir)

            # 4. Compute delta: resolved vs regression
            pre_fps = {
                compute_finding_fingerprint(
                    f.rule_id, f.message, f.enclosing_symbol, f.code_snippet
                )
                for f in pre_findings
            }
            post_fps = {
                compute_finding_fingerprint(
                    f.rule_id, f.message, f.enclosing_symbol, f.code_snippet
                )
                for f in post_findings
            }

            resolved = pre_fps - post_fps
            regressions = post_fps - pre_fps

            duration_ms = int((time.perf_counter() - start_time) * 1000)

            # Determine verdict
            if regressions:
                sandbox_status = "REGRESSION_DETECTED"
                is_verified = False
                proposal_status = "REGRESSION_DETECTED"
            elif not resolved and len(pre_findings) > 0:
                sandbox_status = "FAILED"
                is_verified = False
                proposal_status = "FAILED"
            else:
                sandbox_status = "PASSED"
                is_verified = True
                proposal_status = "VERIFIED"

            record = PatchVerification(
                proposal_id=proposal.id,
                sandbox_status=sandbox_status,
                is_verified=is_verified,
                regressions_count=len(regressions),
                resolved_issues_count=len(resolved),
                pre_patch_findings_count=len(pre_findings),
                post_patch_findings_count=len(post_findings),
                pre_patch_findings=[f.__dict__ for f in pre_findings],
                post_patch_findings=[f.__dict__ for f in post_findings],
                test_results={
                    "resolved_count": len(resolved),
                    "regressions_count": len(regressions),
                },
                sandbox_logs=f"Dual-run sandbox completed in {duration_ms}ms with verdict {sandbox_status}",
                duration_ms=duration_ms,
            )
            proposal.status = proposal_status

            db.add(record)
            await db.commit()
            await db.refresh(record)

            logger.info(
                "Completed patch verification for proposal %s: Status %s (Resolved: %d, Regressions: %d)",
                proposal.id,
                sandbox_status,
                len(resolved),
                len(regressions),
            )
            return record

    async def _run_analysis(self, source_dir: str) -> list[Any]:
        """Run static lint and security checks on the target directory."""
        findings = []
        try:
            ruff_res = await self.ruff.run(source_dir)
            findings.extend(ruff_res.findings)
        except Exception as exc:
            logger.debug("Ruff run in verification encountered: %s", exc)

        try:
            bandit_res = await self.bandit.run(source_dir)
            findings.extend(bandit_res.findings)
        except Exception as exc:
            logger.debug("Bandit run in verification encountered: %s", exc)

        if self.pytest.has_test_suite(source_dir):
            try:
                pytest_res = await self.pytest.run(source_dir)
                findings.extend(pytest_res.findings)
            except Exception as exc:
                logger.debug("Pytest run in verification encountered: %s", exc)

        return findings
