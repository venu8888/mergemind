"""Tests for CI/CD Failure Intelligence Engine (WP 4.B)."""

import pytest

from app.core.database import AsyncSessionLocal
from app.models.installation import Installation
from app.models.repository import Repository
from app.services.ci_intelligence.classifier import CIFailureClassifier
from app.services.ci_intelligence.localizer import CIRootCauseLocalizer
from app.services.ci_intelligence.parser import CILogParser
from app.services.ci_intelligence.service import CIFailureService


@pytest.fixture
def parser():
    return CILogParser()


@pytest.fixture
def classifier():
    return CIFailureClassifier()


@pytest.fixture
def localizer():
    return CIRootCauseLocalizer()


def test_parser_sanitizes_secrets(parser):
    """Verify that credentials and tokens are thoroughly sanitized from logs."""
    raw_log = (
        "Starting job with GITHUB_TOKEN=ghp_ABC1234567890abcdef1234567890abcdef\n"
        "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-zCw\n"
        "password = 'secretPassword123!'\n"
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0\n-----END RSA PRIVATE KEY-----\n"
    )

    sanitized = parser.sanitize_logs(raw_log)

    assert "ghp_ABC" not in sanitized
    assert "secretPassword123!" not in sanitized
    assert "MIIEowIBAAKCAQEA0" not in sanitized
    assert "[REDACTED_CREDENTIAL]" in sanitized


def test_parser_extracts_stack_frames(parser):
    """Verify python traceback and pytest failure extraction."""
    traceback_log = (
        "Traceback (most recent call last):\n"
        '  File "/workspace/app/services/calculator.py", line 42, in calculate_discount\n'
        "    return price * (1 - discount_rate)\n"
        "FAILED tests/test_calculator.py::test_discount - AssertionError: assert 70 == 80\n"
    )

    parsed = parser.parse(traceback_log)
    locs = parsed["localized_files"]

    assert len(locs) >= 2
    assert any("calculator.py" in f["file_path"] and f["line_number"] == 42 for f in locs)
    assert any("test_calculator.py" in f["file_path"] for f in locs)
    assert "AssertionError" in parsed["primary_error"] or "test_discount" in parsed["primary_error"]


def test_classifier_categorizes_pytest_failure(classifier):
    """Verify TEST_FAILURE classification."""
    log = (
        "============================= FAILURES =============================\n"
        "____________________ test_user_authentication _____________________\n"
        "FAILED tests/test_auth.py::test_user_authentication - AssertionError: assert True is False\n"
    )

    category = classifier.classify("AssertionError: assert True is False", log)
    assert category == "TEST_FAILURE"


def test_classifier_categorizes_lint_error(classifier):
    """Verify LINT_ERROR classification."""
    log = "ruff check failed with SyntaxError: unexpected indent in app/main.py"
    category = classifier.classify("SyntaxError: unexpected indent", log)
    assert category == "LINT_ERROR"


def test_classifier_categorizes_security_violation(classifier):
    """Verify SECURITY_VIOLATION classification."""
    log = "Bandit found B101:assert_used security vulnerability detected in auth.py"
    category = classifier.classify("security vulnerability detected", log)
    assert category == "SECURITY_VIOLATION"


def test_classifier_categorizes_dependency_conflict(classifier):
    """Verify DEPENDENCY_CONFLICT classification."""
    log = "ResolutionImpossible: Conflicting versions found for fastapi and pydantic"
    category = classifier.classify("ResolutionImpossible: Conflicting versions found", log)
    assert category == "DEPENDENCY_CONFLICT"


def test_classifier_categorizes_timeout(classifier):
    """Verify TIMEOUT classification."""
    log = "The job exceeded maximum timeout of 60m. Execution timed out."
    category = classifier.classify("timed out", log)
    assert category == "TIMEOUT"


def test_classifier_categorizes_infrastructure_failure(classifier):
    """Verify INFRASTRUCTURE_FAILURE classification."""
    log = "Error: Cannot connect to the Docker daemon. Is the docker daemon running?"
    category = classifier.classify("Cannot connect to the Docker daemon", log)
    assert category == "INFRASTRUCTURE_FAILURE"


def test_root_cause_localizer_correlates_files(localizer):
    """Verify localizer correlates stack frames with changed PR files."""
    locations = [
        {
            "file_path": "app/services/payment.py",
            "line_number": 54,
            "enclosing_symbol": "process_charge",
        },
        {
            "file_path": "tests/test_payment.py",
            "line_number": 22,
            "enclosing_symbol": "test_charge_failure",
        },
    ]
    changed_files = ["app/services/payment.py", "README.md"]

    result = localizer.localize(
        failure_category="TEST_FAILURE",
        primary_error="ZeroDivisionError: division by zero",
        localized_files=locations,
        changed_files=changed_files,
    )

    rca = result["root_cause_analysis"]
    hypothesis = result["ai_advisory_hypothesis"]

    assert rca["primary_file"] == "app/services/payment.py"
    assert rca["direct_match_with_diff"] is True
    assert "payment.py" in hypothesis


@pytest.mark.asyncio
async def test_ci_failure_service_lifecycle():
    """Verify end-to-end CIFailureService ingestion and analysis."""
    async with AsyncSessionLocal() as session:
        inst = Installation(
            github_installation_id=98765,
            account_login="mergemind-org",
            account_type="Organization",
        )
        session.add(inst)
        await session.flush()

        repo = Repository(
            github_repo_id=123456,
            installation_id=inst.id,
            name="mergemind-sample",
            full_name="mergemind-org/mergemind-sample",
            default_branch="main",
        )
        session.add(repo)
        await session.commit()
        await session.refresh(repo)

        service = CIFailureService()

        raw_log = (
            "Run pytest\n"
            "FAILED tests/test_sample.py::test_addition - AssertionError: 5 != 4\n"
            '  File "/workspace/sample/calc.py", line 10, in add\n'
            "    return x + y + 1\n"
            "SECRET_TOKEN=ghp_1234567890abcdef1234567890abcdef123456\n"
        )

        record = await service.ingest_failure(
            db=session,
            repository_id=repo.id,
            workflow_run_id=101,
            workflow_name="CI Test Suite",
            job_name="pytest-job",
            commit_sha="a1b2c3d4e5f6",
            branch="main",
            raw_logs=raw_log,
        )

        assert record.id is not None
        assert record.failure_category == "TEST_FAILURE"
        assert record.status == "ANALYZED"
        assert "ghp_1234567890abcdef" not in record.log_excerpt
        assert len(record.localized_files) > 0
        assert record.ai_advisory_hypothesis is not None

        # Verify query
        failures = await service.list_failures(db=session, repository_id=repo.id)
        assert len(failures) == 1
        assert failures[0].id == record.id
