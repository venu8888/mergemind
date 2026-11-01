"""Tests for AI-Assisted Remediation Engine & Verification (WP 4.C, 4.D, 4.E)."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.core.database import AsyncSessionLocal
from app.models.ci_failure import CIFailureRecord
from app.models.installation import Installation
from app.models.repository import Repository
from app.services.remediation.base import RemediationContext
from app.services.remediation.diff_validator import UnifiedDiffValidator
from app.services.remediation.llm_provider import LLMRemediationProvider
from app.services.remediation.mock_provider import MockRemediationProvider
from app.services.remediation.patch_verifier import PatchVerifier, apply_unified_diff
from app.services.remediation.pr_manager import RemediationPRManager
from app.services.remediation.service import RemediationService


def test_unified_diff_validator_security():
    """Verify UnifiedDiffValidator blocks path traversal and malicious patches."""
    validator = UnifiedDiffValidator(max_lines=100)

    # Path traversal attack diff
    malicious_diff = (
        "--- a/../../../../etc/passwd\n"
        "+++ b/../../../../etc/passwd\n"
        "@@ -1,1 +1,2 @@\n"
        " root:x:0:0:root:/root:/bin/bash\n"
        "+hacker:x:0:0::/root:/bin/bash\n"
    )
    is_valid, reason, _ = validator.validate(malicious_diff)
    assert not is_valid
    assert (
        "traversal" in reason.lower()
        or "invalid path" in reason.lower()
        or "safety" in reason.lower()
    )

    # Oversized diff exceeding limits
    oversized_lines = ["--- a/test.py", "+++ b/test.py", "@@ -1,1 +1,150 @@"] + ["+x = 1"] * 150
    is_valid, reason, _ = validator.validate("\n".join(oversized_lines))
    assert not is_valid
    assert "exceeds" in reason.lower() or "limit" in reason.lower()


def test_unified_diff_validator_valid():
    """Verify UnifiedDiffValidator accepts standard clean diffs."""
    validator = UnifiedDiffValidator()
    valid_diff = (
        "--- a/calc.py\n"
        "+++ b/calc.py\n"
        "@@ -10,3 +10,3 @@\n"
        " def add(x, y):\n"
        "-    return x + y + 1\n"
        "+    return x + y\n"
    )
    is_valid, _, affected = validator.validate(valid_diff)
    assert is_valid
    assert "calc.py" in affected


def test_apply_unified_diff_to_disk():
    """Verify apply_unified_diff cleanly updates target file contents."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        target_file = workspace / "sample.py"
        target_file.write_text("def multiply(a, b):\n    return a * b + 1\n", encoding="utf-8")

        diff = (
            "--- a/sample.py\n"
            "+++ b/sample.py\n"
            "@@ -1,2 +1,2 @@\n"
            " def multiply(a, b):\n"
            "-    return a * b + 1\n"
            "+    return a * b\n"
        )

        success, err = apply_unified_diff(str(workspace), diff)
        assert success, f"Failed with {err}"
        updated_content = target_file.read_text(encoding="utf-8")
        assert "return a * b" in updated_content
        assert "return a * b + 1" not in updated_content


@pytest.mark.asyncio
async def test_mock_remediation_provider():
    """Verify MockRemediationProvider returns deterministic, well-formed patch."""
    provider = MockRemediationProvider()
    context = RemediationContext(
        repository_id="repo-123",
        repository_name="sample-org/sample-repo",
        target_commit_sha="abcdef123456",
        target_branch="main",
        error_message="AssertionError: assert 5 == 4",
        failure_category="TEST_FAILURE",
        target_file="calc.py",
        target_line=10,
        log_excerpt="AssertionError: 5 != 4 in calc.py",
    )

    result = await provider.generate_proposal(context)
    assert result.confidence_score > 0.7
    assert "calc.py" in result.patch_diff
    assert "calc.py" in result.affected_files


@pytest.mark.asyncio
async def test_llm_remediation_provider_zero_secret_leakage():
    """Verify LLMRemediationProvider sanitizes any secrets before network transit."""
    provider = LLMRemediationProvider(api_key="mock-key", model_name="gemini-2.0-flash")

    context = RemediationContext(
        repository_id="repo-sec",
        repository_name="sample-org/sample-repo",
        target_commit_sha="fedcba654321",
        target_branch="main",
        error_message="Failed job with GITHUB_TOKEN=ghp_ultraSecretKey1234567890abcdef",
        failure_category="TEST_FAILURE",
        target_file="auth.py",
        target_line=25,
        log_excerpt="Error: ghp_ultraSecretKey1234567890abcdef",
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": (
                            "```diff\n"
                            "--- a/auth.py\n"
                            "+++ b/auth.py\n"
                            "@@ -25,2 +25,2 @@\n"
                            "-    return False\n"
                            "+    return True\n"
                            "```\n"
                        )
                    }
                }
            ]
        }

        result = await provider.generate_proposal(context)

        # Assert no raw secret in outgoing payload
        called_args, called_kwargs = mock_post.call_args
        payload_str = str(called_kwargs.get("json", ""))
        assert "ghp_ultraSecretKey1234567890abcdef" not in payload_str
        assert result.confidence_score >= 0.7


@pytest.mark.asyncio
async def test_patch_verifier_workflow():
    """Verify PatchVerifier runs dual evaluation and records results."""
    verifier = PatchVerifier()

    from app.services.analysis.base import RawFinding

    sample_finding = RawFinding(
        rule_id="B101",
        message="Use of assert detected",
        severity="MEDIUM",
        file_path="calc.py",
        start_line=1,
        end_line=1,
        enclosing_symbol="sample",
        code_snippet="assert True",
        tool_source="bandit",
    )

    with patch.object(verifier, "_run_analysis", new_callable=AsyncMock) as mock_analysis:
        # Baseline: 1 finding. Patched: 0 findings (resolved).
        mock_analysis.side_effect = [
            [sample_finding],
            [],
        ]

        async with AsyncSessionLocal() as session:
            inst = Installation(
                github_installation_id=88112, account_login="org-test", account_type="Organization"
            )
            session.add(inst)
            await session.flush()

            repo = Repository(
                github_repo_id=987123,
                installation_id=inst.id,
                name="verifier-repo",
                full_name="org-test/verifier-repo",
                default_branch="main",
            )
            session.add(repo)
            await session.flush()

            from app.models.remediation import RemediationProposal

            proposal = RemediationProposal(
                repository_id=repo.id,
                title="Fix test_calc",
                description="Fix bug",
                target_commit_sha="c1",
                target_branch="main",
                status="PROPOSED",
                provider_name="mock",
                confidence_score=0.9,
                patch_diff=(
                    "--- a/calc.py\n"
                    "+++ b/calc.py\n"
                    "@@ -1,2 +1,2 @@\n"
                    "-return x + y + 1\n"
                    "+return x + y\n"
                ),
                affected_files=["calc.py"],
                rationale="test",
                evidence_records={},
            )
            session.add(proposal)
            await session.commit()
            await session.refresh(proposal)

            verification = await verifier.verify_proposal(session, proposal.id)
            assert verification.is_verified is True
            assert verification.sandbox_status in ["PASSED", "VERIFIED"]
            assert proposal.status == "VERIFIED"


def test_remediation_pr_manager_markdown_evidence():
    """Verify RemediationPRManager generates structured verification evidence markdown."""
    manager = RemediationPRManager()

    from app.models.remediation import PatchVerification, RemediationProposal

    proposal = RemediationProposal(
        id="prop-abc-123",
        repository_id="repo-1",
        title="Fix division by zero in calculator",
        description="Prevents zero denominator when computing discounts",
        target_commit_sha="c123",
        target_branch="main",
        status="VERIFIED",
        provider_name="mock",
        confidence_score=0.95,
        patch_diff="--- a/calc.py\n+++ b/calc.py\n",
        affected_files=["calc.py"],
        rationale="Adds zero check",
        evidence_records={},
    )

    verif = PatchVerification(
        proposal_id=proposal.id,
        sandbox_status="VERIFIED",
        is_verified=True,
        regressions_count=0,
        resolved_issues_count=1,
        pre_patch_findings_count=1,
        post_patch_findings_count=0,
        pre_patch_findings=[],
        post_patch_findings=[],
        test_results={},
        sandbox_logs="All 5 tests passed",
        duration_ms=1200,
    )

    body = manager._generate_pr_body(proposal, verif, "test-org/repo")

    assert "MergeMind Automated Corrective Patch" in body
    assert "Description & Rationale" in body
    assert "Dual-Run Sandbox Verification Evidence" in body
    assert "Developer Action Required" in body
    assert "VERIFIED" in body
    assert "Health Invariant" in body


@pytest.mark.asyncio
async def test_remediation_service_end_to_end():
    """Verify full RemediationService flow: propose -> verify -> create_pr."""
    async with AsyncSessionLocal() as session:
        inst = Installation(
            github_installation_id=54321,
            account_login="remediation-test-org",
            account_type="Organization",
        )
        session.add(inst)
        await session.flush()

        repo = Repository(
            github_repo_id=999888,
            installation_id=inst.id,
            name="test-remediation-repo",
            full_name="remediation-test-org/test-remediation-repo",
            default_branch="main",
        )
        session.add(repo)
        await session.flush()

        failure = CIFailureRecord(
            repository_id=repo.id,
            workflow_run_id=202,
            workflow_name="PR Checks",
            job_name="pytest",
            commit_sha="112233445566",
            branch="main",
            failure_category="TEST_FAILURE",
            status="ANALYZED",
            error_message="AssertionError in test_subtraction",
            log_excerpt="FAILED test_subtraction",
            localized_files=[{"file_path": "math_ops.py", "line_number": 15}],
            root_cause_analysis={"primary_error": "AssertionError"},
        )
        session.add(failure)
        await session.commit()
        await session.refresh(failure)

        service = RemediationService()

        # 1. Propose
        proposal = await service.propose_for_ci_failure(session, failure.id)
        assert proposal.id is not None
        assert proposal.status == "PROPOSED"
        assert "math_ops.py" in proposal.patch_diff

        # 2. Verify
        verifier = PatchVerifier()
        from app.services.analysis.base import RawFinding

        sample_finding = RawFinding(
            rule_id="B101",
            message="Assert used",
            severity="MEDIUM",
            file_path="math_ops.py",
            start_line=15,
            end_line=15,
            enclosing_symbol="test",
            code_snippet="assert 1 == 2",
            tool_source="bandit",
        )
        with patch.object(verifier, "_run_analysis", new_callable=AsyncMock) as mock_analysis:
            mock_analysis.side_effect = [
                [sample_finding],
                [],
            ]
            verification = await verifier.verify_proposal(session, proposal.id)
            assert verification.is_verified is True
            assert proposal.status == "VERIFIED"

        # 3. Create Draft PR
        pr_manager = RemediationPRManager()
        pr_record = await pr_manager.create_corrective_pr(session, proposal.id)
        assert pr_record.pr_number is not None
        assert "mergemind/fix-" in pr_record.branch_name
        assert proposal.status == "PR_CREATED"
