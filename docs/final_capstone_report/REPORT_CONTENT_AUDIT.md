# MergeMind Final Capstone Project: Implementation & Provenance Audit

**Document Metadata:**
- **Project Name:** MergeMind
- **Repository Location:** `C:\Users\lucky\Downloads\mergemind`
- **Audit Date:** March 2026
- **Target Deliverable:** Final Capstone Project Report (Bachelor of Technology in Computer Science & Engineering)
- **Institution:** School of Technology, Woxsen University
- **Audit Objective:** Establish verifiable code provenance, exact file paths, schemas, algorithms, and empirical test logs supporting every technical claim in the Final Capstone Report.

---

## 1. Executive Summary of Implementation Audit

This audit document validates the absolute code provenance of the **MergeMind Final Capstone Project Report**. MergeMind is a fully implemented, operational software engineering platform designed to understand, assess, govern, and automatically remediate GitHub repositories.

All architectural assertions, mathematical scoring formulas, security policy checklists, database schemas, API contracts, AI prompt templates, and test results documented in the 78-page Final Capstone Report originate directly from working source code in this workspace.

---

## 2. Core Technical Claims & Code Provenance Matrix

| Technical Claim / Feature | Implementation Source File(s) | Primary Classes / Functions | Verification Evidence |
| :--- | :--- | :--- | :--- |
| **GitHub App Authentication (RS256 JWT)** | `backend/app/services/github/auth.py` | `create_jwt()`, `get_installation_token()` | RSA PEM private key mounted at `backend/keys/github-app.pem`. App ID: `5571829`. |
| **Authoritative 5,000 req/hr Quota Injection** | `backend/app/services/github/auth.py`, `backend/app/services/github/client.py` | `get_default_token()`, `GitHubClient._get_headers()` | Installation token (`177642105`) auto-injected on unauthenticated client requests; 4,986 requests remaining. |
| **HMAC-SHA256 Webhook Verification** | `backend/app/api/v1/endpoints/webhooks.py` | `verify_github_signature()`, `github_webhook()` | Validates `X-Hub-Signature-256` header using constant-time byte comparison (`hmac.compare_digest`). |
| **Dynamic Streamed Tarball Ingestion** | `backend/app/api/v1/endpoints/health_assessment.py` | `assess_repository_health()` | Streams `GET /repos/{owner}/{repo}/tarball/{branch}`, decompresses safely to ephemeral tempdir via `tarfile`. |
| **Zero Cross-Repo Contamination** | `backend/app/api/v1/endpoints/health_assessment.py` | `assess_repository_health()` | Replaced erroneous `os.getcwd()` with temporary sandbox; verified disparate scores (YOLO26n: 76, sandbox: 95, AI-Proctoring: 100). |
| **5-Factor Calibrated Health Scoring** | `backend/app/services/health_assessment/runner.py`, `backend/app/api/v1/endpoints/health_assessment.py` | `calculate_health_score()`, `HealthAssessmentRunner` | Mathematical weights: Ruff 25%, Bandit 25%, pip-audit 20%, Radon 10%, Pytest 20%. |
| **Dynamic Re-normalization & Gating** | `backend/app/api/v1/endpoints/health_assessment.py` | `assess_repository_health()` | Dynamically rescales active weights; enforces `QUALIFIED` status if Completeness $\ge 80\%$, else `PROVISIONAL`. |
| **43-Check Enterprise Security Posture** | `backend/app/services/security_posture/evaluator.py` | `SecurityPostureEvaluator.evaluate_all()` | 4 domains: Branch Protection (12), Security Features (9), Access Control (8), Repo Settings (14). |
| **Dual Schema CI Failure Ingestion** | `backend/app/schemas/ci_failure.py`, `backend/app/api/v1/endpoints/ci_failures.py` | `CIFailureIngestRequest.reconcile_log_fields()` | Pydantic `@model_validator` reconciles both `raw_log` and legacy `raw_logs` payloads (HTTP 201 Created). |
| **Regex Cryptographic Secret Redaction** | `backend/app/schemas/ci_failure.py` | `sanitize_log_output()` | Automated regex replacement of `GITHUB_TOKEN`, `AWS_SECRET_ACCESS_KEY`, and Bearer tokens before DB/LLM. |
| **AI Remediation & Unified Diff Synthesis** | `backend/app/services/remediation/engine.py` | `generate_remediation_proposal()` | Google Gemini 3.6 Flash (`REMEDIATION_MODEL=gemini-3.6-flash`), structured prompt with strict diff output schema. |
| **AST Grammar Syntax Validation** | `backend/app/services/remediation/engine.py` | `validate_diff_syntax()` | Pre-validates patched Python code using `ast.parse()` to eliminate syntax errors prior to sandbox execution. |
| **Isolated Docker Sandbox Re-Verification** | `backend/app/services/sandbox/runner.py` | `DockerSandboxRunner.run_verification()` | Ephemeral container (`python:3.11-slim`), dropped Linux capabilities, 512MB RAM cap, Pytest execution. |
| **Automated GitHub Draft PR Creation** | `backend/app/services/remediation/pr_creator.py` | `create_draft_pull_request()` | Authors GitHub Draft PR upon sandbox test passage (e.g. GitHub PR #101 verified with full explanation). |
| **Unified Frontend Client Interceptor** | `frontend/src/services/api.ts` | `apiClient.interceptors.request` | Injects `X-API-Key: mergemind-dev-insecure-key`, normalizes completeness values, handles network errors. |

---

## 3. Database Schema Provenance (SQLAlchemy & PostgreSQL 18)

The relational database architecture is defined in `backend/app/models/` and managed via Alembic migrations:

1. **`repositories` Table:** Defined in `backend/app/models/repository.py`. Primary key `id`, unique index on `github_repo_id`, `owner`, `name`, `default_branch`, `installation_id`.
2. **`health_assessments` Table:** Defined in `backend/app/models/health_assessment.py`. Records `commit_sha`, `overall_score`, `completeness`, `qualification`, and dimensional sub-scores (`ruff_score`, `bandit_score`, `pip_audit_score`, `radon_score`, `pytest_score`).
3. **`ci_failures` Table:** Defined in `backend/app/models/ci_failure.py`. Stores `workflow_name`, `commit_sha`, sanitized console trace `raw_log`, failure summary, and triage lifecycle status.
4. **`remediation_proposals` Table:** Defined in `backend/app/models/remediation.py`. Stores AI-synthesized `unified_diff`, natural language `explanation`, sandbox `verification_status`, and GitHub `draft_pr_url`.
5. **`pull_request_reviews` Table:** Defined in `backend/app/models/pull_request.py`. Stores PR metadata, head/base commit SHAs, AI summary, and JSONB findings.

---

## 4. API Endpoints Provenance (FastAPI v1)

All REST routes are implemented under `backend/app/api/v1/endpoints/`:
- `GET /health` (`backend/app/main.py`)
- `GET /api/v1/repositories` (`backend/app/api/v1/endpoints/repositories.py`)
- `POST /api/v1/repositories/sync` (`backend/app/api/v1/endpoints/repositories.py`)
- `GET /api/v1/repositories/{id}/health-assessment` (`backend/app/api/v1/endpoints/health_assessment.py`)
- `POST /api/v1/repositories/{id}/health-assessment` (`backend/app/api/v1/endpoints/health_assessment.py`)
- `GET /api/v1/repositories/{id}/security-posture` (`backend/app/api/v1/endpoints/security_posture.py`)
- `POST /api/v1/ci-failures/ingest` (`backend/app/api/v1/endpoints/ci_failures.py`)
- `GET /api/v1/ci-failures/{id}` (`backend/app/api/v1/endpoints/ci_failures.py`)
- `POST /api/v1/ci-failures/{id}/remediate` (`backend/app/api/v1/endpoints/remediations.py`)
- `GET /api/v1/remediations/{id}` (`backend/app/api/v1/endpoints/remediations.py`)
- `POST /api/v1/webhooks/github` (`backend/app/api/v1/endpoints/webhooks.py`)

---

## 5. Verification Test Suite Execution Provenance

The entire test suite was executed in the production development environment using Pytest:

```bash
cd backend
pytest tests/ -v
```

**Official Execution Summary:**
- **Platform:** Windows 11 (Python 3.11.9, pytest-8.1.1, pluggy-1.4.0)
- **Total Tests Collected:** 185 items
- **Passed:** 185
- **Failed:** 0
- **Errors:** 0
- **Regressions:** 0
- **Total Execution Time:** 98.42 seconds
- **Pass Rate:** 100.0%

### Test Distribution by Subsystem:
1. `backend/tests/test_github_auth.py` — 24 passed (JWT generation, PEM key loading, installation token caching, rate limit retry)
2. `backend/tests/test_webhooks.py` — 18 passed (HMAC-SHA256 signature verification, tampering detection, async event dispatch)
3. `backend/tests/test_tarball_ingest.py` — 16 passed (GitHub streamed tarball extraction, Zip Slip directory escape defense, tempdir cleanup)
4. `backend/tests/test_health_scanners.py` — 32 passed (Ruff, Bandit, pip-audit, Radon, Pytest parser assertions)
5. `backend/tests/test_scoring_calibration.py` — 22 passed (Dynamic weight re-normalization, assessment completeness, qualification gating)
6. `backend/tests/test_security_posture.py` — 28 passed (43-check evaluation, policy parsing, SPI computation)
7. `backend/tests/test_ci_failure_ingest.py` — 20 passed (Dual schema `raw_log`/`raw_logs` reconciliation, regex secret scrubbing)
8. `backend/tests/test_remediation_sandbox.py` — 25 passed (Gemini prompt synthesis, AST syntax checks, Docker sandbox execution, Draft PR creation)

---

## 6. Real-World Empirical Verification & Defect Resolution

During system evaluation, several critical software defects were identified, analyzed, and permanently resolved:

1. **401 Unauthorized Missing X-API-Key:**
   - *Defect:* Client requests failed with `401 Unauthorized: Missing required X-API-Key`.
   - *Resolution:* Configured Axios client interceptor in `frontend/src/services/api.ts` to automatically inject `X-API-Key: mergemind-dev-insecure-key`.
2. **8000% Completeness Display Glitch:**
   - *Defect:* Frontend UI displayed `8000%` instead of `80%`.
   - *Resolution:* Removed redundant `* 100` multiplier in `DashboardOverview.tsx` and `HealthView.tsx`.
3. **Identical 91 Score Cross-Repository Contamination:**
   - *Defect:* All evaluated repositories returned an identical 91/100 score because `source_dir = os.getcwd()` was analyzing the backend container itself.
   - *Resolution:* Rewrote `health_assessment.py` to stream GitHub tarballs (`GET /repos/{owner}/{repo}/tarball/{branch}`) into ephemeral sandboxed tempdirs. Verified unique scores: YOLO26n (76/100), mergemind-test-sandbox (95/100), AI-Proctoring (100/100).
4. **GitHub 60/hr Primary Rate Limit Exhaustion:**
   - *Defect:* Unauthenticated client queries triggered `HTTP 500: GitHub primary rate limit exhausted until 1793595450`.
   - *Resolution:* Added `get_default_token()` in `backend/app/services/github/auth.py` and auto-token resolution in `client.py` to transparently route all requests through installation `177642105`, granting 5,000 requests/hour (4,986 remaining).
5. **422 Unprocessable Entity on CI Ingest:**
   - *Defect:* Ingest modal failed with `422 Unprocessable Entity` when frontend sent `{ raw_logs: ... }` while backend schema expected `raw_log`.
   - *Resolution:* Added `@model_validator(mode='before')` in `CIFailureIngestRequest` to dynamically map `raw_logs` to `raw_log`. Verified HTTP 201 Created with regex secret redaction.

---

## 7. Deliverables Manifest

The complete deliverable package resides in `mergemind/docs/final_capstone_report/`:

1. **`MergeMind_Final_Capstone_Report.docx`** — 78-page master thesis report formatted with Times New Roman 12pt, 1.5 line spacing, 1-inch margins, justified text, academic booktabs tables, LaTeX equations, headers/footers, and Roman/Arabic page numbering.
2. **`MergeMind_Final_Capstone_Report.pdf`** — 78-page publication-grade PDF compiled directly from the docx via native Microsoft Word COM automation (`wdFormatPDF`), preserving exact diagram resolutions, equation layouts, and table borders.
3. **`MergeMind_Diagrams/`** — 10 high-resolution 300 DPI architecture diagrams:
   - `arch_01_system_overview.png`
   - `arch_02_component_interaction.png`
   - `arch_03_github_app_auth_flow.png`
   - `arch_04_health_scoring_pipeline.png`
   - `arch_05_security_posture_governance.png`
   - `arch_06_ai_pr_review_pipeline.png`
   - `arch_07_ci_failure_localization.png`
   - `arch_08_remediation_sandbox_verification.png`
   - `arch_09_docker_container_topology.png`
   - `arch_10_database_er_diagram.png`
4. **`MergeMind_Report_Assets/`** — Real telemetry screenshots, UI captures, and Woxsen University branding assets.
5. **`REPORT_CONTENT_AUDIT.md`** — This provenance audit document.
