# capstone_content_ch7_ch9.py
"""
Content definitions for:
- Chapter 7: System Implementation and Module Breakdown
- Chapter 8: Database Design and Data Dictionary
- Chapter 9: API Design and Interface Specifications
"""

CHAPTER_7_CONTENT = {
    "title": "System Implementation and Module Breakdown",
    "sections": [
        {
            "num": "7.1",
            "title": "Module 1: GitHub App Authentication and Token Management Service",
            "body": (
                "Implementation File: `backend/app/services/github/auth.py` and `client.py`\n\n"
                "The GitHub authentication service is responsible for minting secure installation access tokens and managing rate limits. "
                "The module initializes by loading the GitHub App private RSA key from `backend/keys/github-app.pem`. When invoked, "
                "`create_jwt()` generates an RS256-signed JSON Web Token with a 10-minute validity window containing the App ID (`5571829`).\n\n"
                "The `get_installation_token(installation_id)` function requests a short-lived bearer token (`ghs_***`) from GitHub's API. "
                "Crucially, to prevent rate limit exhaustion when endpoints invoke repository queries without user-supplied tokens, "
                "MergeMind implements `get_default_token()`. This function automatically resolves the active installation ID (`177642105`) "
                "and injects the installation access token into `GitHubClient` session headers. Consequently, all repository queries "
                "operate against GitHub's authoritative 5,000 requests/hour enterprise pool (verified with 4,986 remaining quota)."
            )
        },
        {
            "num": "7.2",
            "title": "Module 2: Webhook Signature Verification and Event Dispatcher",
            "body": (
                "Implementation File: `backend/app/api/v1/endpoints/webhooks.py`\n\n"
                "The webhook dispatcher receives asynchronous HTTP POST callbacks from GitHub at `/api/v1/webhooks/github`. "
                "To guarantee cryptographic non-repudiation and prevent spoofing attacks, incoming requests are validated against "
                "the `X-Hub-Signature-256` header. The raw request body bytes are hashed using HMAC-SHA256 parameterized with "
                "`settings.GITHUB_WEBHOOK_SECRET`:\n\n"
                "expected_signature = 'sha256=' + hmac.new(secret_bytes, body_bytes, hashlib.sha256).hexdigest()\n"
                "if not hmac.compare_digest(expected_signature, request_signature):\n"
                "    raise HTTPException(status_code=401, detail='Invalid webhook signature')\n\n"
                "Verified payloads are parsed to extract the event type (`X-GitHub-Event`). The service asynchronously routes events: "
                "`push` events trigger repository cache invalidation; `pull_request` events trigger automated AI PR review pipelines; "
                "and `workflow_run` events (with `conclusion: 'failure'`) automatically trigger CI failure ingestion and remediation loops."
            )
        },
        {
            "num": "7.3",
            "title": "Module 3: Dynamic Tarball Ingestion and Sandbox Extractor",
            "body": (
                "Implementation File: `backend/app/api/v1/endpoints/health_assessment.py`\n\n"
                "To eliminate cross-repository directory contamination, the health assessment module dynamically pulls the target repository's "
                "source archive directly from GitHub's REST endpoint `GET /repos/{owner}/{repo}/tarball/{branch}`. "
                "The streaming response is processed in chunks and decompressed in-memory via Python's `tarfile` module into an ephemeral "
                "temporary directory created via `tempfile.mkdtemp(prefix='mergemind_repo_')`.\n\n"
                "Security validation ensures that no extracted tar member escapes the temporary directory boundary (mitigating Zip Slip "
                "path traversal attacks). The extracted root folder is passed as the isolated `source_dir` parameter to the static analysis "
                "orchestrator. Once static analysis completes, a `finally` block invokes `shutil.rmtree(temp_dir, ignore_errors=True)` "
                "to completely scrub extracted files from disk."
            )
        },
        {
            "num": "7.4",
            "title": "Module 4: Deterministic Static Code Analysis Harness",
            "body": (
                "Implementation File: `backend/app/services/health_assessment/runner.py`\n\n"
                "This module coordinates the execution of deterministic static analysis tools across the extracted repository snapshot:\n"
                "• Ruff Harness: Executes `ruff check --output-format=json {source_dir}`, parsing JSON diagnostics to calculate linting violations.\n"
                "• Bandit Harness: Executes `bandit -r {source_dir} -f json`, parsing findings by severity and confidence levels.\n"
                "• pip-audit Harness: Detects `requirements.txt`, `Pipfile.lock`, or `poetry.lock`. If found, runs `pip-audit -r {manifest} -f json` "
                "to map vulnerable dependencies against the OSV database.\n"
                "• Radon Harness: Executes `radon cc {source_dir} -j` and `radon mi {source_dir} -j` to compute McCabe cyclomatic complexity and "
                "Maintainability Index distributions.\n"
                "• Scoring Engine: Applies dynamic weight re-normalization and evaluates qualification gating (Completeness >= 80%)."
            )
        },
        {
            "num": "7.5",
            "title": "Module 5: Enterprise Security Posture Evaluator",
            "body": (
                "Implementation File: `backend/app/services/security_posture/evaluator.py`\n\n"
                "The Security Posture Evaluator implements the 43-check governance framework. It queries GitHub's REST API using the authenticated "
                "installation token across multiple endpoints:\n"
                "• `GET /repos/{owner}/{repo}/branches/{default_branch}/protection` (12 branch protection checks)\n"
                "• `GET /repos/{owner}/{repo}/community/profile`, `/dependabot/alerts`, `/code-scanning/alerts`, `/secret-scanning/alerts` (9 security feature checks)\n"
                "• `GET /repos/{owner}/{repo}/collaborators`, `/keys`, `/hooks` (8 access control checks)\n"
                "• `GET /repos/{owner}/{repo}`, `/actions/permissions`, `/actions/permissions/workflow` (14 repository settings checks)\n\n"
                "The evaluator constructs a structured dictionary containing check statuses (`PASS`, `FAIL`, `WARN`), severity tags, "
                "evidence descriptions, and remediation guidance, while computing the composite Security Posture Index (SPI)."
            )
        },
        {
            "num": "7.6",
            "title": "Module 6: CI Failure Ingestion, Payload Reconciliation and Token Redactor",
            "body": (
                "Implementation File: `backend/app/schemas/ci_failure.py` and `backend/app/api/v1/endpoints/ci_failures.py`\n\n"
                "When CI/CD pipelines fail, execution logs are ingested either via automated webhooks or manual developer upload. "
                "To resolve payload schema discrepancies between legacy frontend versions (which sent `raw_logs`) and backend schemas (expecting `raw_log`), "
                "MergeMind implements a robust Pydantic `@model_validator(mode='before')` in `CIFailureIngestRequest`:\n\n"
                "@model_validator(mode='before')\n"
                "@classmethod\n"
                "def reconcile_log_fields(cls, data):\n"
                "    if isinstance(data, dict):\n"
                "        if 'raw_logs' in data and 'raw_log' not in data:\n"
                "            data['raw_log'] = data.pop('raw_logs')\n"
                "    return data\n\n"
                "Before persistence or LLM transmission, the raw log passes through a regex token sanitizer that strips sensitive tokens:\n"
                "• GitHub Tokens: `gh[pousr]_[A-Za-z0-9_]{36,255}` -> `[REDACTED_GITHUB_TOKEN]`\n"
                "• AWS Secret Keys: `(?i)aws_secret_access_key\\s*=\\s*[A-Za-z0-9/+=]{40}` -> `[REDACTED_AWS_KEY]`\n"
                "• Generic Bearer Tokens: `Bearer\\s+[A-Za-z0-9\\-_\\.]{20,}` -> `Bearer [REDACTED_TOKEN]`"
            ),
            "figure_id": "fig_ci_failure_ingestion_modal.jpg",
            "figure_caption": "Figure 7.1: CI Failure Ingestion Modal with Real-Time Regex Secret Redaction"
        },
        {
            "num": "7.7",
            "title": "Module 7: AI Remediation Engine and Prompt Synthesis",
            "body": (
                "Implementation File: `backend/app/services/remediation/engine.py`\n\n"
                "The remediation engine leverages Google Gemini 3.6 Flash (`REMEDIATION_MODEL=gemini-3.6-flash`) via an OpenAI-compatible "
                "endpoint. The engine parses the sanitized CI failure log to identify the failing assertion or exception trace, extracts the "
                "target source file and enclosing function, and constructs a structured system prompt:\n\n"
                "• System Directives: Instructs the model to act as a principal software engineer, requiring patches in standard Unified Diff format.\n"
                "• Context Injection: Injects the exact source code of the failing file alongside the sanitized stack trace.\n"
                "• Strict Diff Constraints: Requires valid `--- a/file` and `+++ b/file` headers with accurate line hunk offsets (`@@ -l,s +l,s @@`).\n\n"
                "Upon receiving the LLM completion, the engine validates the diff using Python's `patch` parser and compiles the patched code "
                "using Python's `ast.parse()` to guarantee syntactic validity before sandbox execution."
            ),
            "figure_id": "arch_08_remediation_sandbox_verification.png",
            "figure_caption": "Figure 7.2: AI Remediation Pipeline and Sandbox Verification Execution Loop"
        },
        {
            "num": "7.8",
            "title": "Module 8: Isolated Docker Sandbox Re-Verification and Draft PR Creator",
            "body": (
                "Implementation File: `backend/app/services/sandbox/runner.py` and `backend/app/services/remediation/pr_creator.py`\n\n"
                "To eliminate hallucinations and prevent untested code merges, candidate patches must pass sandbox re-verification:\n"
                "1. Sandbox Initialization: MergeMind spawns an ephemeral Docker container based on `python:3.11-slim` with dropped Linux "
                "capabilities (`--cap-drop=ALL`), non-root user execution, memory limits (512MB), and read-only container root.\n"
                "2. Patch Application: The candidate unified diff is applied to the repository snapshot via `git apply` or `patch -p1`.\n"
                "3. Regression Execution: Pytest executes the test suite inside the container. The runner captures stdout, stderr, and exit codes.\n"
                "4. Automated Draft PR Authoring: If and only if the sandbox test suite exits with code 0 (all tests pass), MergeMind authenticates "
                "via the GitHub App installation token, pushes a new remote branch (`mergemind/fix-ci-{failure_id}`), and opens an official "
                "GitHub Draft Pull Request (e.g., Pull Request #101) containing the diff and AI remediation explanation."
            ),
            "figure_id": "fig_remediation_diff_viewer.jpg",
            "figure_caption": "Figure 7.3: MergeMind AI Remediation Diff Viewer and Verification Output"
        }
    ]
}

CHAPTER_8_CONTENT = {
    "title": "Database Design and Data Dictionary",
    "sections": [
        {
            "num": "8.1",
            "title": "Conceptual and Logical Relational Schema",
            "body": (
                "MergeMind's persistence layer is engineered around an ACID-compliant relational schema implemented in PostgreSQL 18. "
                "The schema enforces strict referential integrity, foreign key cascading delete policies, unique constraints, and B-tree indexes "
                "optimized for high-frequency lookup queries (e.g., repository ID, commit SHA, and webhook delivery IDs).\n\n"
                "Figure 8.1 depicts the complete Entity-Relationship (ER) diagram representing all 8 relational tables and their cardinalities."
            ),
            "figure_id": "arch_10_database_er_diagram.png",
            "figure_caption": "Figure 8.1: MergeMind Relational Database Entity-Relationship (ER) Schema Diagram"
        },
        {
            "num": "8.2",
            "title": "Comprehensive Data Dictionary",
            "body": (
                "The data dictionary defines the physical table definitions, columns, data types, nullability constraints, and descriptions "
                "for all core database tables, as detailed in Tables 8.1 through 8.5."
            ),
            "table_id": "DATA_DICT_REPOS"
        },
        {
            "num": "8.3",
            "title": "Health Assessments and Telemetry Data Models",
            "body": (
                "Table 8.2 specifies the physical schema for the `health_assessments` and `assessment_runs` entities, recording historical "
                "score trajectories and individual scanner metrics."
            ),
            "table_id": "DATA_DICT_HEALTH"
        },
        {
            "num": "8.4",
            "title": "CI Failures and Remediation Proposals Data Models",
            "body": (
                "Tables 8.3 and 8.4 specify the physical schemas governing CI/CD failure ingestion, sanitized stack traces, AI-generated "
                "unified diffs, sandbox verification results, and draft pull request metadata."
            ),
            "table_id": "DATA_DICT_CI_REMED"
        },
        {
            "num": "8.5",
            "title": "Database Migrations and Schema Versioning via Alembic",
            "body": (
                "Database schema evolution is managed deterministically using Alembic migration scripts located in `backend/alembic/versions/`. "
                "Each migration script defines reversible `upgrade()` and `downgrade()` routines. Migrations are executed automatically during "
                "container boot via an entrypoint shell script (`alembic upgrade head`), ensuring consistent schema states across local development "
                "and production deployment environments."
            )
        }
    ]
}

CHAPTER_9_CONTENT = {
    "title": "API Design and Interface Specifications",
    "sections": [
        {
            "num": "9.1",
            "title": "RESTful API Architectural Principles",
            "body": (
                "MergeMind's application programming interface adheres strictly to RESTful architectural principles. All endpoints are versioned "
                "under the `/api/v1` namespace. Requests and responses communicate via UTF-8 encoded JSON payloads with appropriate HTTP status "
                "codes (200 OK, 201 Created, 400 Bad Request, 401 Unauthorized, 404 Not Found, 422 Unprocessable Entity, 500 Internal Server Error).\n\n"
                "Authentication is enforced via custom API key governance (`X-API-Key: mergemind-dev-insecure-key`) across protected internal "
                "routes, while public webhook receivers authenticate via GitHub's HMAC-SHA256 signature headers."
            )
        },
        {
            "num": "9.2",
            "title": "Comprehensive REST Endpoint Reference",
            "body": (
                "Table 9.1 documents the primary REST API endpoints exposed by the MergeMind backend service, detailing HTTP methods, "
                "URI paths, authentication requirements, input schemas, and expected responses."
            ),
            "table_id": "API_ENDPOINT_TABLE"
        },
        {
            "num": "9.3",
            "title": "Error Handling and Validation Responses",
            "body": (
                "All API endpoints utilize Pydantic v2 schemas for strict request body and query parameter validation. If an incoming payload "
                "violates schema constraints (e.g., missing required fields, invalid UUID formats), FastAPI automatically returns an RFC 7807 "
                "compliant JSON error response with HTTP 422 Unprocessable Entity. Backend services wrap third-party API exceptions (such as "
                "GitHub network timeouts or Gemini rate limits) into structured HTTP 502/503 responses with informative diagnostics."
            )
        }
    ]
}

# Tables definitions for Chapter 8 & 9
DATA_DICT_REPOS_ROWS = [
    ("Column Name", "Data Type", "Constraints", "Description"),
    ("id", "INTEGER / UUID", "PK, NOT NULL, AUTO_INCREMENT", "Unique internal primary key identifier for the repository."),
    ("github_repo_id", "BIGINT", "NOT NULL, UNIQUE, INDEX", "GitHub authoritative repository ID assigned by GitHub API."),
    ("name", "VARCHAR(255)", "NOT NULL", "Repository short name (e.g., 'YOLO26n')."),
    ("full_name", "VARCHAR(512)", "NOT NULL, UNIQUE", "Complete namespaced repository slug (e.g., 'owner/repo')."),
    ("owner", "VARCHAR(255)", "NOT NULL", "GitHub user or organization username owning the repository."),
    ("default_branch", "VARCHAR(128)", "NOT NULL, DEFAULT 'main'", "Default production git branch name."),
    ("is_private", "BOOLEAN", "NOT NULL, DEFAULT FALSE", "Boolean flag indicating whether repository visibility is private."),
    ("installation_id", "BIGINT", "NOT NULL, INDEX", "GitHub App installation identifier authorizing API access."),
    ("created_at", "TIMESTAMP WITH TIME ZONE", "NOT NULL, DEFAULT NOW()", "Timestamp recording initial repository registration."),
    ("updated_at", "TIMESTAMP WITH TIME ZONE", "NOT NULL, DEFAULT NOW()", "Timestamp of most recent repository metadata update.")
]

DATA_DICT_HEALTH_ROWS = [
    ("Column Name", "Data Type", "Constraints", "Description"),
    ("id", "INTEGER / UUID", "PK, NOT NULL, AUTO_INCREMENT", "Unique primary key identifier for the health assessment record."),
    ("repository_id", "INTEGER", "FK -> repositories.id, NOT NULL", "Foreign key referencing the parent repository."),
    ("commit_sha", "VARCHAR(40)", "NOT NULL, INDEX", "Git commit SHA-1 hash evaluated during this assessment run."),
    ("overall_score", "DOUBLE PRECISION", "NOT NULL", "Final dynamically re-normalized composite health score (0–100)."),
    ("completeness", "DOUBLE PRECISION", "NOT NULL", "Proportion of total evaluation weights active (0.0 to 1.0)."),
    ("qualification", "VARCHAR(32)", "NOT NULL", "Qualification gating status ('QUALIFIED', 'PROVISIONAL', 'NOT_ASSESSED')."),
    ("ruff_score", "DOUBLE PRECISION", "NULLABLE", "Normalized Code Quality score evaluated via Astral Ruff (0–100)."),
    ("bandit_score", "DOUBLE PRECISION", "NULLABLE", "Normalized Static Security score evaluated via Bandit (0–100)."),
    ("pip_audit_score", "DOUBLE PRECISION", "NULLABLE", "Normalized Dependency Vulnerability score via pip-audit (0–100)."),
    ("radon_score", "DOUBLE PRECISION", "NULLABLE", "Normalized Maintainability score evaluated via Radon (0–100)."),
    ("pytest_score", "DOUBLE PRECISION", "NULLABLE", "Normalized Test Health score evaluated via Pytest (0–100)."),
    ("created_at", "TIMESTAMP WITH TIME ZONE", "NOT NULL, DEFAULT NOW()", "Timestamp recording when the assessment was completed.")
]

DATA_DICT_CI_REMED_ROWS = [
    ("Column Name", "Data Type", "Constraints", "Description"),
    ("ci_failures.id", "INTEGER / UUID", "PK, NOT NULL", "Unique primary key identifier for the CI failure event."),
    ("ci_failures.repo_id", "INTEGER", "FK -> repositories.id", "Foreign key linking failure to the target repository."),
    ("ci_failures.workflow", "VARCHAR(255)", "NOT NULL", "GitHub Actions workflow name (e.g., 'CI / Verification')."),
    ("ci_failures.commit_sha", "VARCHAR(40)", "NOT NULL", "Commit SHA-1 hash that triggered the failing workflow run."),
    ("ci_failures.raw_log", "TEXT", "NOT NULL", "Sanitized raw console output with secrets and tokens redacted."),
    ("ci_failures.status", "VARCHAR(32)", "NOT NULL", "Triage status ('OPEN', 'TRIAGED', 'REMEDIATING', 'RESOLVED')."),
    ("remed.id", "INTEGER / UUID", "PK, NOT NULL", "Unique primary key identifier for the remediation proposal."),
    ("remed.ci_failure_id", "INTEGER", "FK -> ci_failures.id", "Foreign key referencing the parent CI failure event."),
    ("remed.unified_diff", "TEXT", "NOT NULL", "AI-synthesized unified diff patch conforming to patch specifications."),
    ("remed.explanation", "TEXT", "NOT NULL", "Natural language technical rationale generated by the LLM."),
    ("remed.verif_status", "VARCHAR(32)", "NOT NULL", "Sandbox verification state ('VERIFIED', 'FAILED', 'PENDING')."),
    ("remed.draft_pr_url", "VARCHAR(512)", "NULLABLE", "URL of the created GitHub Draft Pull Request upon verification pass.")
]

API_ENDPOINT_TABLE_ROWS = [
    ("HTTP Method", "Endpoint URI Path", "Auth Required", "Description"),
    ("GET", "/api/v1/health", "None", "Liveness and readiness health check probe returning service uptime."),
    ("GET", "/api/v1/repositories", "X-API-Key", "List all tracked GitHub repositories synchronized with installation."),
    ("POST", "/api/v1/repositories/sync", "X-API-Key", "Trigger immediate re-synchronization of repositories from GitHub App."),
    ("GET", "/api/v1/repositories/{id}/health-assessment", "X-API-Key", "Retrieve latest cached health telemetry or trigger live tarball assessment."),
    ("POST", "/api/v1/repositories/{id}/health-assessment", "X-API-Key", "Force execution of a fresh multi-factor health assessment on HEAD commit."),
    ("GET", "/api/v1/repositories/{id}/security-posture", "X-API-Key", "Execute and return complete 43-check security posture governance evaluation."),
    ("POST", "/api/v1/ci-failures/ingest", "X-API-Key", "Ingest raw CI failure logs with automated regex credential scrubbing."),
    ("GET", "/api/v1/ci-failures/{id}", "X-API-Key", "Retrieve detailed CI failure record, parsed stack trace, and triage status."),
    ("POST", "/api/v1/ci-failures/{id}/remediate", "X-API-Key", "Trigger Gemini 3.6 Flash AI remediation and sandbox verification loop."),
    ("GET", "/api/v1/remediations/{id}", "X-API-Key", "Retrieve remediation proposal, unified diff, verification log, and Draft PR URL."),
    ("POST", "/api/v1/webhooks/github", "HMAC-SHA256", "Inbound GitHub webhook handler for push, pull_request, and workflow_run events.")
]

