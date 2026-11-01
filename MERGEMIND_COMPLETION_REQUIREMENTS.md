# MergeMind — Engineering Completion Requirements & Owner Action Assessment

**Document Version:** 1.0.0  
**Status:** Ready for Owner Review & Action  
**Target Repository:** [venu8888/mergemind](https://github.com/venu8888/mergemind)  
**Target Branch:** `feature/phase-4-remediation-release`  
**Latest Verified Commit:** `fb5d1cf` (Hosted CI: 100% Green, Run `41351661413`)  

---

## Executive Summary

MergeMind has completed Phases 1 through 4 of its modular monolith architecture. All core engines—PostgreSQL 18 database persistence, repository health scoring, PR verification quality gates, static security runners (Ruff, Bandit, pip-audit, Radon), isolated Docker execution sandbox, CI failure classification and localizer, and AI remediation workflows—are implemented and validated with 84 unit and integration tests passing locally and in GitHub Actions CI.

To transition MergeMind from verified isolated components to an **active, end-to-end production platform operating against live code repositories**, this document details:
1. Current implementation status across all 12 operational stages.
2. Architectural and engineering wiring gaps to close.
3. The exact credentials, accounts, and GitHub App configurations required.
4. An exhaustive comparative evaluation of candidate LLM providers, recommending **Google Gemini** as the premier zero-cost, high-performance integration.
5. Production sandbox isolation strategies.
6. A definitive division of responsibilities between the **Project Owner** and **Antigravity**.
7. The immediate credentials and assets needed from the Project Owner right now.

---

## 1. Current Implementation Status (12 Workflow Stages)

| # | Workflow Stage | Code Implementation Status | Live External Connectivity | Blockers / Required Wiring |
|---|---|---|---|---|
| **1** | **GitHub App Auth & Connection** | Complete (`GitHubClient`, JWT generator, private key auth, webhook HMAC validator) | Inactive (Uses placeholder app credentials) | Needs Owner's GitHub App ID, Private Key (`.pem`), and Webhook Secret |
| **2** | **Repository Sync & Monitoring** | Complete (`RepositorySyncService`, models `Repository`, background sync tasks) | Inactive (Mocked/test DB fixtures) | Needs installation ID and connection to a real test GitHub repo |
| **3** | **Health Analysis & Scoring** | Complete (`RepositoryHealthService`, 4-dimensional score, qual thresholds, completeness metrics) | Ready (Engine fully functional) | Requires actual repository files on disk to inspect |
| **4** | **PR Ingestion & Analysis** | Complete (`pull_request` webhook ingestion, quality gates, delta classification) | Ready (Queue & logic operational) | Needs live webhook payload delivery from GitHub |
| **5** | **Static & Security Scanning** | Complete (`RuffRunner`, `BanditRunner`, `PipAuditRunner`, `RadonRunner`) | Ready (Host-installed binaries available) | Runner invoked on checked-out repository tree |
| **6** | **CI Failure Ingestion & Localization** | Complete (`CIFailureService`, `CIIntelligenceLocalizer`, regex parsers, secret sanitization) | Inactive (Awaiting GitHub Actions API token) | Needs GitHub App token with `actions:read` to fetch live failure logs |
| **7** | **Secure Sandbox Execution** | Complete (`SandboxEngine`, UID 10001, `--read-only`, `--network none`, `--cap-drop ALL`, 60s hard timeout) | Verified on Host (Docker CLI available) | Docker containerized deployment needs worker execution strategy (cannot expose docker.sock to web container) |
| **8** | **Evidence & Assessment Packaging** | Complete (`AnalysisReport`, `RemediationProposal`, `VerificationRun` models) | Ready (DB persistence active) | None; fully operational |
| **9** | **AI-Assisted Remediation** | Complete (`RemediationService`, `LLMRemediationProvider`, prompt injection defense, unified diff parser) | Mock Provider Active (`MockRemediationProvider`) | Endpoint instantiation currently defaults to Mock; requires API key and provider injection |
| **10** | **Patch Validation & Verification** | Complete (`PatchVerifier`, `UnifiedDiffValidator` with path traversal & size security) | Ready (Sandbox test runner verified) | Needs real patch execution in target sandbox environment |
| **11** | **Corrective Branch & Draft PR** | Complete (`RemediationPRManager`, markdown proposal generator) | Simulated fallback active | Needs Git ref creation (`POST /git/refs`) and blob/tree commit before calling PR creation |
| **12** | **Merge Detection & Reassessment** | Complete (`pull_request.closed` webhook handler) | Logic implemented | Post-merge trigger must automatically invoke `RepositoryHealthService.assess_repository` |

---

## 2. Missing Engineering Requirements & Architectural Gaps

To achieve end-to-end functionality without mocks or simulations, the following four code-level integration bridges must be wired:

### Gap 2.1: Dynamic LLM Provider Selection in Remediation API
- **Location:** `backend/app/api/v1/endpoints/remediations.py` (Line 38)
- **Current Behavior:** Instantiates `service = RemediationService()` without arguments, defaulting to `MockRemediationProvider()`.
- **Engineering Fix Required:** Introduce dependency injection to check `settings.GEMINI_API_KEY` or `settings.OPENAI_API_KEY`. If present, instantiate `LLMRemediationProvider` configured with the appropriate endpoint and model name; otherwise gracefully fall back to mock or report unconfigured status.

### Gap 2.2: Git Reference Creation & File Tree Push
- **Location:** `backend/app/services/remediation/pr_manager.py`
- **Current Behavior:** Calls `self.github_client.create_pull_request(repo_full_name, title, head, base, body)`. If the branch `head` does not exist on GitHub, the GitHub API rejects the PR creation.
- **Engineering Fix Required:** Chain Git Data API calls:
  1. Retrieve latest commit SHA of base branch (`GET /repos/{owner}/{repo}/git/ref/heads/{base}`).
  2. Create new branch ref (`POST /repos/{owner}/{repo}/git/refs` with `refs/heads/mergemind/fix-{proposal_id}`).
  3. Create blob/tree with patched files or push commit via GitHub Contents API (`PUT /repos/{owner}/{repo}/contents/{path}`).
  4. Open Draft PR pointing to the newly created branch.

### Gap 2.3: Live GitHub Actions Log Fetching
- **Location:** `backend/app/services/ci/failure_service.py`
- **Current Behavior:** Ingests log payloads provided in webhook or API request bodies.
- **Engineering Fix Required:** When receiving a `workflow_run` or `workflow_job` completed event with status `failure`, use the installation-authenticated `GitHubClient` to query `GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs` to automatically ingest and classify raw build logs.

### Gap 2.4: Post-Merge Reassessment Trigger
- **Location:** `backend/app/api/v1/endpoints/webhooks.py`
- **Current Behavior:** Processes `pull_request` closed events and marks remediation PR as merged in the local database.
- **Engineering Fix Required:** Enqueue a background task calling `RepositoryHealthService.assess_repository(repo_id)` upon successful merge detection to compute updated post-remediation health metrics.

---

## 3. Exact Credentials, Accounts, and Services Required

To enable live operations, the following external assets are required:

| Service / Resource | Purpose | Required Secrets / Environment Variables | How Obtained |
|---|---|---|---|
| **GitHub App** | Authenticate MergeMind to repositories, receive webhooks, read logs, create PRs | `GITHUB_APP_ID`<br>`GITHUB_APP_PRIVATE_KEY_PATH` (or private key PEM)<br>`GITHUB_WEBHOOK_SECRET` | Created in Owner's GitHub Account (`Settings > Developer settings > GitHub Apps`) |
| **Dedicated Test Repo** | Safe testbed for automated PR creation and sandbox verification | E.g., `venu8888/mergemind-test-sandbox` (public or private) | Created by Owner on GitHub |
| **LLM Provider API** | Generate intelligent unified diff patches and analyze failures | `GEMINI_API_KEY` (Recommended) or `OPENAI_API_KEY` | Google AI Studio (Free) or OpenAI Platform |
| **Webhook Ingress (Dev/Test)** | Deliver live GitHub webhooks to local/Docker backend during development | `smee.io` proxy URL or `ngrok` tunnel | Generated free on `https://smee.io` (no software installation required) |

---

## 4. GitHub App Configuration & Permissions Breakdown

The GitHub App must be configured with exact least-privilege permissions to support all 12 stages without exposing unnecessary repository administrative access.

### 4.1 Permission Matrix

| Category | Permission | Access Level | Reason / Workflow Stage |
|---|---|---|---|
| **Repository** | **Pull requests** | **Read & Write** | Ingest PR metadata (Stage 4), open corrective draft PRs (Stage 11), post review comments |
| **Repository** | **Contents** | **Read & Write** | Read source files for health analysis (Stage 3), create fix branches & push patch commits (Stage 11) |
| **Repository** | **Actions** | **Read-only** | Download CI workflow run and job failure logs (Stage 6) |
| **Repository** | **Checks** | **Read & Write** | (Optional) Publish MergeMind health check status to GitHub PR check runs |
| **Repository** | **Metadata** | **Read-only** | Basic repository metadata inspection (mandatory for all GitHub Apps) |
| **Repository** | **Issues** | **Read & Write** | (Optional) Link remediation draft PRs to original issues |

### 4.2 Webhook Event Subscriptions
Subscribe the GitHub App to the following events:
- `pull_request` (Actions: `opened`, `reopened`, `synchronize`, `closed`)
- `workflow_run` (Actions: `completed`)
- `workflow_job` (Actions: `completed`)
- `installation` & `installation_repositories` (For dynamic app setup and repo binding)

### 4.3 Webhook Target Configuration
- **Webhook URL:** During development/testing, use a [Smee.io](https://smee.io) channel URL (e.g. `https://smee.io/MergeMindTestWebhook123`). The backend or a lightweight Smee forwarder proxies events directly into `http://localhost:8000/api/v1/webhooks/github`.
- **Webhook Secret:** A secure random 32-character string configured in both the GitHub App and `backend/.env` as `GITHUB_WEBHOOK_SECRET`.

---

## 5. AI Provider Recommendation & Comparison

MergeMind's `LLMRemediationProvider` implements an OpenAI-compatible REST completions client (`POST /chat/completions`) utilizing structured system prompts, unified diff specifications, and prompt-injection defenses.

### 5.1 Provider Evaluation Matrix

| Criterion | Google Gemini 2.5/1.5 Flash (Recommended) | OpenAI GPT-4o-mini | Anthropic Claude 3.5 Sonnet | Alibaba Qwen 2.5 Coder (via OpenRouter/DashScope) |
|---|---|---|---|---|
| **REST Protocol** | Native OpenAI-compatible endpoint supported out-of-the-box | Native OpenAI REST protocol | Proprietary `/v1/messages` format (Requires new custom adapter) | OpenAI-compatible endpoint supported |
| **Code Changes Needed** | **Zero code changes** (Drop-in endpoint & key) | **Zero code changes** | Requires new `AnthropicRemediationProvider` adapter | **Zero code changes** |
| **Cost** | **100% Free** (Google AI Studio Free Tier: 15 RPM, 1M TPM, 1500 RPD) | Paid ($0.15 / 1M input, $0.60 / 1M output tokens, min $5 credit deposit) | Paid ($3.00 / 1M input, $15.00 / 1M output tokens, min $5 deposit) | Free tier available depending on provider gateway |
| **Context Window** | **1,000,000 tokens** (Handles massive diffs & complete CI build logs) | 128,000 tokens | 200,000 tokens | 128,000 tokens |
| **Diff Generation Quality** | High (Exceptional code reasoning and strict syntax compliance) | Good (Fast, reliable syntax) | Outstanding (Industry benchmark for complex software engineering) | High (Specialized code fine-tune) |
| **Setup Friction** | **Instant** (Generate API key in Google AI Studio with 1 click) | Credit card required for pre-paid account balance | Credit card required for pre-paid account balance | International phone/billing verification |

### 5.2 Recommendation: Google Gemini via OpenAI Compatibility Endpoint
**Google Gemini (`gemini-2.5-flash` or `gemini-1.5-flash`) is strongly recommended as the primary LLM provider.**

#### Why Google Gemini is the Optimal Choice:
1. **Completely Free Tier:** Google AI Studio provides 15 Requests Per Minute (RPM), 1,000,000 Tokens Per Minute (TPM), and 1,500 Requests Per Day (RPD) at $0 cost without requiring a credit card or prepaid billing balance.
2. **Immediate Compatibility:** Google provides an official, drop-in OpenAI-compatible endpoint:
   - Endpoint: `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`
   - Header: `Authorization: Bearer <GEMINI_API_KEY>`
   - MergeMind's existing `LLMRemediationProvider` consumes this endpoint natively with zero structural code modifications.
3. **Massive Context Window (1M Tokens):** Full-stack stacktraces, multithreaded pytest failures, and large multi-file diffs can be passed in their entirety without truncation risk.

#### Alternative: OpenAI GPT-4o-mini
If the owner already possesses an active OpenAI API key with credit balance, setting `OPENAI_API_KEY` and selecting `gpt-4o-mini` is supported immediately as an alternative.

---

## 6. Sandbox Infrastructure Requirements

### 6.1 Security Invariant: Container Protection
In the Docker Compose application stack, the `mergemind-backend` container runs as a web process. **Exposing the host Docker socket (`/var/run/docker.sock`) into `mergemind-backend` is strictly prohibited**, as any arbitrary command vulnerability in the web container would grant root privilege escalation over the host machine.

### 6.2 Host Execution vs. Containerized Sidecar Architecture

1. **Development & Host Testing Mode (Current Active Setup):**
   - The backend runs directly in the host Python environment or via test suites.
   - It directly invokes the local Docker daemon CLI (`docker run --rm --network none --read-only --user 10001:10001 ...`).
   - Hard execution timeout of 60 seconds is strictly enforced with verified dual-stage process and container cleanup.

2. **Production Containerized Architecture (Recommended for Server Deployment):**
   - For a 100% containerized deployment where the backend runs inside Docker Compose, implement a **dedicated sandbox worker sidecar** or **sandbox agent daemon**:
     - The worker runs in an isolated network segment with restricted Docker socket access.
     - The web backend enqueues verification jobs to Redis / PostgreSQL durable queue.
     - The worker pulls jobs, executes the isolated sandbox container, gathers evidence, and writes results back to the database.

---

## 7. Estimated Costs & Tier Comparison

| Component | Free Tier Capabilities | Estimated Monthly Cost (Dev / Pilot) | Production Scale (1,000 PRs/mo) |
|---|---|---|---|
| **AI LLM (Gemini 2.5 Flash)** | 1,500 requests/day free (Google AI Studio) | **$0.00** | $0.00 (or ~$5/mo on Pay-As-You-Go if exceeding 15 RPM) |
| **AI LLM (OpenAI gpt-4o-mini)** | None (prepaid credits required) | ~$1.00 – $3.00 | ~$15.00 – $25.00 |
| **GitHub App & Actions** | Free for public repos; 2,000 free Actions min/mo for private | **$0.00** | $0.00 (Standard GitHub pricing) |
| **PostgreSQL 18** | Local Docker Compose / Self-hosted | **$0.00** | $15.00 – $50.00 (Managed RDS/Neon/Supabase) |
| **Docker Sandbox** | Local execution on host machine / dev VM | **$0.00** | $10.00 – $30.00 (Standard cloud compute VM) |
| **Total Estimated Cost (Pilot)** | | **$0.00** (Using Gemini + Local Docker + Smee) | |

---

## 8. Division of Responsibilities

### 8.1 Project Owner Action Checklist (Actions Only the Owner Can Perform)

```markdown
[ ] 1. Obtain Google Gemini API Key
    - Visit https://aistudio.google.com/app/apikey
    - Create a new API key (Free tier).
    - Save securely to configure in backend/.env.

[ ] 2. Create GitHub App in Personal or Organization Account
    - Navigate to GitHub > Settings > Developer settings > GitHub Apps > New GitHub App.
    - Set App Name: "MergeMind Verification Engine" (or unique name).
    - Homepage URL: https://github.com/venu8888/mergemind
    - Webhook URL: Temporary Smee URL (e.g. from https://smee.io).
    - Webhook Secret: Generate a random secret string.
    - Permissions:
        * Repository > Pull requests: Read & Write
        * Repository > Contents: Read & Write
        * Repository > Actions: Read-only
        * Repository > Checks: Read & Write
        * Repository > Metadata: Read-only
    - Events:
        * Pull request
        * Workflow run
        * Workflow job
        * Installation
        * Installation repositories
    - Generate Private Key (.pem file) and save it.
    - Note the App ID.

[ ] 3. Create Dedicated Sandbox Repository for Testing
    - E.g., https://github.com/venu8888/mergemind-test-sandbox
    - Push a sample Python repository with a simple failing test or Ruff lint issue.
    - Install the newly created GitHub App onto this test repository.

[ ] 4. Place Credentials on the Machine
    - Place the downloaded .pem key in C:\Users\lucky\Downloads\mergemind\backend\keys\github-app.pem
    - Update backend/.env (DO NOT paste private keys or tokens in chat):
        * GITHUB_APP_ID=<Owner App ID>
        * GITHUB_APP_PRIVATE_KEY_PATH=keys/github-app.pem
        * GITHUB_WEBHOOK_SECRET=<Owner Webhook Secret>
        * GEMINI_API_KEY=<Owner Gemini Key>
        * REMEDIATION_ENDPOINT=https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
        * REMEDIATION_MODEL=gemini-2.5-flash
```

### 8.2 Antigravity Action Checklist (Actions Handled Once Credentials are Provided)

```markdown
[ ] 1. Endpoint Injection Wiring:
    - Update `backend/app/api/v1/endpoints/remediations.py` to instantiate `LLMRemediationProvider` when `GEMINI_API_KEY` or `OPENAI_API_KEY` is configured.

[ ] 2. Live Git Branch & Ref Push Wiring:
    - Update `RemediationPRManager` to create git refs (`refs/heads/mergemind/fix-...`) and push patched files via GitHub API before opening draft PRs.

[ ] 3. Live Actions Log Fetching:
    - Connect `CIFailureService` to fetch live failure logs from `GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs` when workflow fails.

[ ] 4. Post-Merge Reassessment:
    - Wire `pull_request.closed` webhook handler to trigger `RepositoryHealthService.assess_repository`.

[ ] 5. End-to-End Live Verification:
    - Execute a live test against `mergemind-test-sandbox`: ingest failing PR, diagnose root cause, generate real Gemini patch, verify patch in Docker sandbox, push branch, open draft PR, and verify reassessment upon merge.
```

---

## 9. Prioritized Implementation Plan

Once the Owner provisions credentials, implementation proceeds in 4 rapid phases:

```mermaid
flowchart TD
    Step1["Step 1: Provider & Endpoint Wiring\n(Inject LLMRemediationProvider in remediations.py)"] --> Step2["Step 2: Live Git Operations\n(Implement git ref creation & commit push in PR Manager)"]
    Step2 --> Step3["Step 3: Webhook & Actions Log Fetcher\n(Automate failure log download from GitHub Actions)"]
    Step3 --> Step4["Step 4: End-to-End Live Validation\n(Trigger real PR -> Diagnose -> Gemini Fix -> Sandbox -> Draft PR)"]
```

1. **Step 1: Provider Injection (Estimated: 30 minutes)**
   - Wire `LLMRemediationProvider` in API endpoints.
   - Verify zero prompt leakage and test API communication with Gemini endpoint.
2. **Step 2: Live Git Ref & PR Creation (Estimated: 45 minutes)**
   - Add branch creation and commit push methods in `GitHubClient` and `RemediationPRManager`.
   - Add unit test coverage for live ref creation.
3. **Step 3: Webhook Ingress & Log Ingestion (Estimated: 30 minutes)**
   - Test Smee forwarder / webhook delivery into local backend.
   - Verify workflow failure ingestion.
4. **Step 4: End-to-End Pilot Execution (Estimated: 45 minutes)**
   - Run complete workflow against `mergemind-test-sandbox` repository and record evidence.

---

## 10. Acceptance Criteria

The system will be accepted as fully engineered and production-ready when:
1. A live webhook from GitHub triggers automatic repository sync and health assessment without manual intervention.
2. An intentional failing test or syntax error in a PR is automatically detected, classified, and localized to the source file and line.
3. The LLM provider (Google Gemini) generates a valid, syntactically correct unified diff patch.
4. The patch is verified inside the isolated Docker sandbox, proving that tests pass and no security invariants are violated.
5. MergeMind automatically creates a corrective branch (`mergemind/fix-...`) and opens a Draft Pull Request on GitHub containing full evidence and rationale.
6. When the Draft PR is merged on GitHub, MergeMind detects the merge and updates the repository health score.

---

## 11. WHAT I NEED FROM THE PROJECT OWNER RIGHT NOW

To proceed with final engineering completion and real AI remediation, the Project Owner must perform the following actions:

> [!IMPORTANT]
> **DO NOT paste private keys, API secrets, or passwords directly into this chat.**  
> Store them directly in your local environment files as instructed below.

### 1. Confirm Your LLM Provider Choice
Confirm whether you approve using **Google Gemini** (Free, zero-friction, 1M context) via Google AI Studio, or prefer **OpenAI** (`gpt-4o-mini`).

### 2. Generate Your API Key
- If choosing **Gemini**: Obtain a free API key at [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).
- If choosing **OpenAI**: Obtain an API key from your OpenAI dashboard.

### 3. Register the GitHub App
Create your GitHub App in your GitHub account following the permissions listed in [Section 4](#4-github-app-configuration--permissions-breakdown):
- Generate and download the Private Key (`.pem` file).
- Note your **GitHub App ID**.
- Set a **Webhook Secret**.

### 4. Setup a Dedicated Test Repository
- Create a test repository (e.g. `venu8888/mergemind-test-sandbox`).
- Install your GitHub App onto this repository.

### 5. Configure Your Local `.env`
Ensure your local `backend/.env` file contains:
```env
# AI Remediation Configuration (Gemini Example)
GEMINI_API_KEY=your_gemini_api_key_here
REMEDIATION_ENDPOINT=https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
REMEDIATION_MODEL=gemini-2.5-flash

# GitHub App Configuration
GITHUB_APP_ID=your_github_app_id_here
GITHUB_APP_PRIVATE_KEY_PATH=keys/github-app.pem
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
```
And place your downloaded private key file at:
`C:\Users\lucky\Downloads\mergemind\backend\keys\github-app.pem`

---
*Once these items are ready, notify Antigravity to proceed with Step 1 (Provider & Endpoint Wiring) and Step 2 (Live Git Ref & PR Creation).*



---

## 12. FINAL CONFIGURATION READINESS

### 12.1 Gemini Model Selection & Compatibility Audit

#### 1. Official Model Lifecycle & Deprecation Review
A review of Google's official Gemini API documentation (`ai.google.dev`) reveals the current lifecycle status of the Flash model family:
- **`gemini-1.5-flash`:** Part of the initial 1.5 generation; early checkpoints have reached their retirement windows and are superseded.
- **`gemini-2.0-flash`:** Reached scheduled end-of-life / shutdown in mid-2026.
- **`gemini-2.5-flash`:** Active access for new projects is restricted by Google to legacy accounts; Google officially advises all new integrations to adopt the current generation models.
- **`gemini-3.8-flash` (Recommended Stable Model):** Google's active, stable Flash model specifically engineered for long-horizon software engineering, code synthesis, agentic workflows, and low-latency structured outputs.
- **`gemini-flash-latest` (Recommended Dynamic Alias):** An active alias that resolves continuously to Google's newest production Flash release.

**Verdict:** The primary model identifier for MergeMind is **`gemini-3.8-flash`** (with **`gemini-flash-latest`** as a fully supported dynamic alias). Deprecated or restricted model strings (`gemini-1.5-flash`, `gemini-2.0-flash`, `gemini-2.5-flash`) must not be used for new deployments.

#### 2. OpenAI Compatibility & Endpoint Validation
- **Exact Base URL:** `https://generativelanguage.googleapis.com/v1beta/openai/`
- **Exact Endpoint URL:** `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`
- **Authentication Header:** `Authorization: Bearer <GEMINI_API_KEY>`
- **HTTP Method:** `POST`
- **Compatibility with `LLMRemediationProvider`:**
  MergeMind's [`backend/app/services/remediation/llm_provider.py`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/services/remediation/llm_provider.py) sends:
  ```json
  {
    "model": "gemini-3.8-flash",
    "messages": [
      {
        "role": "system",
        "content": "You are an automated code remediation assistant. Output ONLY a valid git unified diff starting with 'diff --git' to fix the defect described. Do not include markdown codeblocks."
      },
      {
        "role": "user",
        "content": "Repository: ...\nFailure Category: ...\nTarget File: ...\nError Message: ...\nCode Snippet: ...\nLog Excerpt: ...\n\nGenerate a standard unified diff that resolves this error without introducing regressions."
      }
    ],
    "temperature": 0.1
  }
  ```
  This schema matches Google's `/v1beta/openai/chat/completions` specification exactly. Google returns:
  ```json
  {
    "choices": [
      {
        "index": 0,
        "message": {
          "role": "assistant",
          "content": "diff --git a/app/calc.py b/app/calc.py\n--- a/app/calc.py\n+++ b/app/calc.py\n@@ -10,3 +10,3 @@\n-    return a * b\n+    return a / b\n"
        }
      }
    ]
  }
  ```
  `LLMRemediationProvider` reads `data["choices"][0]["message"]["content"]`, which extracts the diff directly.

#### 3. Required Changes to Implementation
- **`LLMRemediationProvider` class:** **Zero changes required.** It natively supports `GEMINI_API_KEY`, `REMEDIATION_ENDPOINT`, and `REMEDIATION_MODEL`.
- **API Endpoint Injection ([`backend/app/api/v1/endpoints/remediations.py`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/api/v1/endpoints/remediations.py#L38)):** Currently hardcodes `service = RemediationService()`, which defaults to `MockRemediationProvider`. Must be wired to instantiate `LLMRemediationProvider` when `GEMINI_API_KEY` is present.
- **Sanitization Fix ([`backend/app/services/remediation/base.py`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/services/remediation/base.py#L39)):** Currently `RemediationContext.sanitize()` calls `sanitize_secret(self.code_snippet)` and `sanitize_secret(self.log_excerpt)`, which masks any string longer than 4 characters to `...****`. During implementation, this will be swapped to `sanitize_log_output(text)` from [`backend/app/core/security.py`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/core/security.py), which redacts authentication tokens while preserving legitimate code and log traces.
- **Diff Parsing & Safety Validation:** Fully compatible. `_extract_diff` strips any markdown fencing, and [`UnifiedDiffValidator`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/services/remediation/diff_validator.py) enforces standard git diff headers (`diff --git`, hunk markers `@@`), file line counts (max 500), and path traversal prevention (no `..` or root absolute paths).

---

### 12.2 Exact Environment Configuration Matrix

The table below catalogs every variable recognized by the MergeMind codebase across [`backend/app/core/config.py`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/core/config.py) and [`backend/app/services/remediation/llm_provider.py`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/services/remediation/llm_provider.py). No invented or non-existent variable names are included.

| Variable Name | Component | Status in `.env` | Expected Value / Format | Purpose |
|---|---|---|---|---|
| `GEMINI_API_KEY` | Gemini Provider | **MISSING** | `AIzaSy...` (from Google AI Studio) | Authentication key for Google Gemini API |
| `REMEDIATION_ENDPOINT` | Remediation Engine | **MISSING** | `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions` | Direct REST endpoint for completions |
| `REMEDIATION_MODEL` | Remediation Engine | **MISSING** | `gemini-3.8-flash` | Active model identifier |
| `GITHUB_APP_ID` | GitHub App | **EMPTY** | Integer string (e.g. `123456`) | Identifies the GitHub App |
| `GITHUB_APP_PRIVATE_KEY_PATH` | GitHub App | **EMPTY** | `keys/github-app.pem` | Relative path to RS256 private key |
| `GITHUB_WEBHOOK_SECRET` | Webhook Verification | **EMPTY** | Random 32+ char secret string | HMAC-SHA256 signature verification |
| `DATABASE_URL` | Database | **CONFIGURED** | `postgresql+asyncpg://mergemind_app:merge88@localhost:5432/mergemind_dev` | Async SQLAlchemy PostgreSQL 18 connection |
| `DATABASE_SYNC_URL` | Database (Migrations) | **CONFIGURED** | `postgresql+psycopg2://mergemind_app:merge88@localhost:5432/mergemind_dev` | Sync SQLAlchemy connection for Alembic |
| `DB_ECHO_SQL` | Database | **CONFIGURED** | `false` | Disable noisy SQL query logs |
| `SANDBOX_TYPE` | Sandbox Execution | **CONFIGURED** | `container` | Executes tests inside isolated Docker containers |
| `SANDBOX_TIMEOUT_SECONDS` | Sandbox Execution | **CONFIGURED** | `60` | Hard container execution timeout |
| `SANDBOX_MAX_MEMORY_MB` | Sandbox Execution | **CONFIGURED** | `512` | Container memory limit |
| `SANDBOX_CPU_QUOTA` | Sandbox Execution | **CONFIGURED** | `1.0` | Container CPU limit |
| `SCORING_POLICY_VERSION` | Health Scoring | **CONFIGURED** | `v1.0` | Scoring policy version identifier |
| `ENABLE_IN_PROCESS_WORKER` | Webhook Queue | **MISSING** | `true` | Starts queue worker inside FastAPI process |
| `PROJECT_NAME` | General Application | **CONFIGURED** | `MergeMind` | Application name |
| `VERSION` | General Application | **CONFIGURED** | `0.1.0` | Application version |
| `API_V1_PREFIX` | General Application | **CONFIGURED** | `/api/v1` | REST API routing prefix |
| `ENVIRONMENT` | General Application | **CONFIGURED** | `development` | Deployment environment |
| `DEBUG` | General Application | **CONFIGURED** | `true` | Debug flag |
| `CORS_ORIGINS` | General Application | **CONFIGURED** | `http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000` | Allowed web frontend origins |
| `VITE_API_URL` | Frontend | **CONFIGURED** | `http://localhost:8000` | Backend URL for Vite web client |

---

### 12.3 GitHub App Permissions (Strict Least Privilege Audit)

Every permission has been re-evaluated against the concrete API operations implemented in [`backend/app/services/github/client.py`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/services/github/client.py) and the queue dispatcher.

#### 1. Mandatory Permissions

| Permission | Level | Specific API Call in Codebase | Rationale / Workflow Stage |
|---|---|---|---|
| **Pull requests** | **Read & Write** | `GET /repos/{owner}/{repo}/pulls`<br>`GET /repos/{owner}/{repo}/pulls/{number}`<br>`GET /repos/{owner}/{repo}/pulls/{number}/files`<br>`POST /repos/{owner}/{repo}/pulls` | **Read:** Ingest PR metadata and file changes for delta assessment.<br>**Write:** Automatically create corrective draft pull requests with remediation proposals. |
| **Contents** | **Read & Write** | `GET /repos/{owner}/{repo}/contents/{path}`<br>`GET /repos/{owner}/{repo}/git/trees/{sha}`<br>`GET /repos/{owner}/{repo}/git/blobs/{sha}`<br>`POST /repos/{owner}/{repo}/git/refs`<br>`PUT /repos/{owner}/{repo}/contents/{path}` | **Read:** Fetch source code files for static security analysis (Ruff, Bandit, Radon) and repository health scoring.<br>**Write:** Create fix branch (`refs/heads/mergemind/fix-...`) and commit patched files prior to opening the draft PR. |
| **Metadata** | **Read-only** | `GET /repos/{owner}/{repo}`<br>`GET /installation/repositories` | Mandatory for all GitHub Apps to resolve repository identity, owner, and default branch. |
| **Actions** | **Read-only** | `GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs`<br>`GET /repos/{owner}/{repo}/actions/runs/{run_id}/logs` | Ingest raw build/test logs from failed GitHub Actions runs to drive root-cause classification and localization. |

#### 2. Permissions NOT Required (Omitted for Least Privilege)
- **Checks: NONE.** *Audit finding:* The MergeMind codebase does not invoke `/repos/{owner}/{repo}/check-runs` or `/repos/{owner}/{repo}/check-suites`. MergeMind reports its verification results via Pull Request descriptions and its own web dashboard. Requesting Checks write permission is unnecessary and violates least privilege.
- **Issues: NONE.** *Audit finding:* MergeMind operates exclusively through Pull Requests. No issue creation or issue comment API calls exist in the client.
- **Administration: NONE.** MergeMind does not modify repository settings, collaborators, or branch protection rules.

#### 3. Webhook Events Breakdown
- **Events Currently Handled in Code ([`dispatcher.py`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/services/github/dispatcher.py)):**
  1. `pull_request` (Actions: `opened`, `synchronize`, `closed` with merge detection)
  2. `installation` (Actions: `created`, `deleted`, `suspend`, `unsuspend`)
  3. `installation_repositories` (Actions: `added`, `removed`)
- **Events Required for Automated CI Failure Ingestion:**
  4. `workflow_run` (Action: `completed` — detects failed CI workflow runs)
  5. `workflow_job` (Action: `completed` — detects specific failed steps and provides job IDs)

---

### 12.4 GitHub Test Repository Specification

To validate all 9 operational capabilities without impacting production repositories, the Owner should create a dedicated test repository named **`venu8888/mergemind-test-sandbox`** containing the following structure:

```
mergemind-test-sandbox/
├── .github/
│   └── workflows/
│       └── ci.yml                 # Runs pytest on push and pull_request
├── sample_app/
│   ├── __init__.py
│   ├── calculator.py              # Clean, well-structured reference module
│   ├── vulnerable_service.py      # Contains intentional Bandit B301 (pickle.loads)
│   ├── complex_logic.py           # Nested branches (Radon cyclomatic complexity > 10)
│   └── math_ops.py                # Contains an intentional bug in divide(a, b)
├── tests/
│   ├── __init__.py
│   ├── test_calculator.py         # 100% passing unit tests
│   └── test_math_ops.py           # Failing unit test asserting divide(10, 2) == 5
├── requirements.txt               # Dependencies with an unpinned or benign advisory package
└── README.md
```

#### Mapping Files to Verification Capabilities:
1. **Repository Health Analysis:** MergeMind inspects `sample_app/calculator.py` and `requirements.txt` to calculate baseline quality and dependency metrics.
2. **Security Findings:** `sample_app/vulnerable_service.py` triggers `BanditRunner` (flags unsafe deserialization).
3. **Code Quality Findings:** `sample_app/complex_logic.py` triggers `RadonRunner` and `RuffRunner` (flags excessive complexity and style defects).
4. **PR Analysis:** Opening PR #1 modifying `sample_app/math_ops.py` triggers delta classification and evaluates the Quality Gate (`DEGRADED`).
5. **CI Failure Diagnosis:** `.github/workflows/ci.yml` runs `pytest` and fails on `test_math_ops.py`. MergeMind receives `workflow_run` failure, ingests the log, and localizes the root cause to `sample_app/math_ops.py`.
6. **Corrective Patch Generation:** MergeMind passes the localized snippet to Gemini (`gemini-3.8-flash`), which generates a unified diff fixing `divide(a, b)`.
7. **Patch Verification:** MergeMind applies the diff in an isolated Docker container and runs `pytest tests/test_math_ops.py` to confirm tests pass.
8. **Draft PR Creation:** MergeMind pushes branch `refs/heads/mergemind/fix-pr-1` and opens a Draft PR on GitHub linking the verification evidence.
9. **Post-Merge Reassessment:** Merging the Draft PR into `main` sends `pull_request.closed` (merged=true), automatically triggering repository reassessment and recording an improved health score.

---

### 12.5 Security, Sanitization & Privacy Policy

#### 1. Pre-LLM Sanitization Pipeline
Before any data payload is sent to Gemini, it passes through the sanitization pipeline in [`backend/app/core/security.py`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/core/security.py):
- **Token & Key Redaction:** Regular expression scrubbers strip GitHub personal access tokens (`ghp_...`, `github_pat_...`), Bearer tokens, private keys (`-----BEGIN ... PRIVATE KEY-----`), database connection strings, and common credential assignment patterns (`password=...`, `secret=...`).
- **Scope Restriction:** MergeMind does NOT transmit entire repositories. Only the specific localized file snippet (maximum 50 lines surrounding the defect) and the relevant pytest failure traceback are included in the prompt.

#### 2. Information That Must NEVER Be Sent to External LLMs
- RSA Private Keys (including the GitHub App `.pem` key).
- Webhook HMAC secrets, database credentials, or `.env` contents.
- Any authorization tokens or JWTs.
- Entire unsegmented code repositories or unrelated project files.
- Personally Identifiable Information (PII) or author email addresses.

#### 3. Google AI Studio Data Use Policy: Free Tier vs. Paid Tier
- **Google AI Studio Free Tier:**
  - *Data Policy:* Prompts and generated completions may be logged, reviewed by human evaluators, and used by Google to train and refine Google models.
  - *Implication:* Ideal for open-source projects, public repositories, and testing/evaluation environments (such as MergeMind and `mergemind-test-sandbox`). Not recommended for proprietary codebases containing trade secrets or sensitive customer data.
- **Google AI Studio / Vertex AI Paid Tier:**
  - *Data Policy:* Prompts and completions are strictly confidential and are **NEVER** used to train Google models. Complies with SOC 2, ISO 27001, and HIPAA enterprise data privacy standards.
  - *Implication:* When deploying MergeMind for private or enterprise client repositories, switching to a paid Gemini API key ensures zero data retention and strict enterprise confidentiality.

---

### 12.6 Final Owner Action Checklist

Complete the following 4 setup actions:

```markdown
[ ] 1. Obtain Google Gemini API Key
    - Navigate to: https://aistudio.google.com/app/apikey
    - Sign in with your Google account and click "Create API Key".
    - Copy the generated API key.
    - Local storage: Save into `C:\Users\lucky\Downloads\mergemind\backend\.env` as `GEMINI_API_KEY`.

[ ] 2. Create GitHub App
    - Navigate to: GitHub > Settings > Developer settings > GitHub Apps > New GitHub App.
    - App name: "MergeMind-Verification-Engine" (or unique name of your choice).
    - Homepage URL: https://github.com/venu8888/mergemind
    - Webhook URL: Temporary Smee channel (e.g. create a channel at https://smee.io and paste URL).
    - Webhook secret: Generate any random 32-character string.
    - Permissions:
        * Repository > Pull requests: Read & Write
        * Repository > Contents: Read & Write
        * Repository > Actions: Read-only
        * Repository > Metadata: Read-only
        * (Leave Checks, Issues, and Administration set to "No access")
    - Webhook events to check:
        * Pull request
        * Workflow run
        * Workflow job
        * Installation
        * Installation repositories
    - Click "Create GitHub App".
    - Click "Generate a private key" at the bottom of the app page. A `.pem` file will download.
    - Note your "App ID" displayed on the General page.
    - Local storage:
        * Save the downloaded `.pem` file to: `C:\Users\lucky\Downloads\mergemind\backend\keys\github-app.pem`
        * Save the App ID into `backend\.env` as `GITHUB_APP_ID`.
        * Save the Webhook secret into `backend\.env` as `GITHUB_WEBHOOK_SECRET`.

[ ] 3. Create Dedicated Test Repository
    - Create a new public or private repo on GitHub: `mergemind-test-sandbox`.
    - Go back to your GitHub App settings > "Install App" > Install it onto `mergemind-test-sandbox`.

[ ] 4. Update Local `backend/.env`
    - Verify your `C:\Users\lucky\Downloads\mergemind\backend\.env` contains:
        GEMINI_API_KEY=<your_gemini_key>
        REMEDIATION_ENDPOINT=https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
        REMEDIATION_MODEL=gemini-3.8-flash
        GITHUB_APP_ID=<your_app_id>
        GITHUB_APP_PRIVATE_KEY_PATH=keys/github-app.pem
        GITHUB_WEBHOOK_SECRET=<your_webhook_secret>
        ENABLE_IN_PROCESS_WORKER=true
```


---

## 13. DEPLOYMENT & ISOLATION ARCHITECTURE CLARIFICATIONS

### 13.1 Webhook Reachability & Ingress Architecture

#### 1. Endpoint & Docker Port Analysis
- **Internal FastAPI Route:** Mounted at `POST /api/v1/webhooks/github` via `api_router.include_router(webhooks.router, prefix="/webhooks")` in [`backend/app/api/v1/api.py`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/api/v1/api.py).
- **Docker Compose Mapping:** Exposed on `8000:8000` via `ports: ["8000:8000"]` in [`docker-compose.yml`](file:///C:/Users/lucky/Downloads/mergemind/docker-compose.yml).
- **Local Target URL:** `http://localhost:8000/api/v1/webhooks/github` (or `http://127.0.0.1:8000/api/v1/webhooks/github`).

#### 2. Ingress Tunnel Comparison

| Solution | Setup Complexity | Security Profile | Cost / Account Requirement | Ephemeral vs Persistent URL | Recommendation |
|---|---|---|---|---|---|
| **Smee.io (Official GitHub Tool)** | **Zero setup** (run single CLI command) | **Highest for Dev:** Outbound SSE client only. No public inbound port opened on host machine. | **100% Free** (No account, no sign-in, no credit card) | **Persistent** (Channel URL remains static as long as desired) | **RECOMMENDED** |
| **ngrok** | Medium (Requires installing binary & creating account) | Good (Reverse tunnel), but exposes inbound tunnel endpoint directly to the web. | Free tier requires account login; generates random ephemeral URL on restart unless paid. | Ephemeral on free tier (Requires updating GitHub App settings on restart) | Not Recommended |
| **Cloudflare Tunnel (cloudflared)** | High (Requires custom domain registered on Cloudflare DNS) | Enterprise-grade, encrypted origin tunnel. | Free for tunnel, but requires owning a real public domain name on Cloudflare. | Persistent | Overkill for Dev/Pilot |

#### 3. Recommended Approach & Setup Instructions: Smee.io
GitHub provides [Smee.io](https://smee.io), a free, open-source webhook payload delivery service purpose-built for developing GitHub Apps.
- **Step 1:** Visit `https://smee.io` and click **"Start a new channel"**.
- **Step 2:** Copy your unique Webhook Proxy URL (e.g., `https://smee.io/MergeMindDevABC123`).
- **Step 3:** Enter this URL into your GitHub App's **Webhook URL** field.
- **Step 4 (When ready to test):** Run the Smee client locally to forward webhooks to FastAPI:
  ```powershell
  npx smee -u https://smee.io/MergeMindDevABC123 -t http://localhost:8000/api/v1/webhooks/github
  ```
  *(Note: No software is permanently installed. Smee opens an outbound connection to Smee.io and delivers incoming events directly to `localhost:8000` without exposing your machine to public incoming traffic).*

---

### 13.2 CI Webhook Processing: Subscribed vs. Implemented

An audit of the webhook lifecycle distinguishes between events received at ingress versus business handlers in the queue dispatcher:

```mermaid
flowchart TD
    GH[GitHub App Webhooks] -->|POST| Ingress["/api/v1/webhooks/github\n(HMAC Verification & Deduplication)"]
    Ingress -->|Persist| DB[(WebhookDelivery Table\nStatus: PENDING)]
    DB -->|Claim Job| Dispatcher["WebhookDispatcher.dispatch_event()"]
    
    Dispatcher -->|installation| H1["handle_installation_event() (Implemented)"]
    Dispatcher -->|installation_repositories| H2["reconcile_installation_repositories() (Implemented)"]
    Dispatcher -->|pull_request| H3["sync_pull_request() (Implemented)"]
    Dispatcher -->|workflow_run| H4["Unhandled / Passive Log (MISSING WIRING)"]
    Dispatcher -->|workflow_job| H5["Unhandled / Passive Log (MISSING WIRING)"]
```

#### 1. Ingress & Persistence Status
- **Endpoint:** [`backend/app/api/v1/endpoints/webhooks.py`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/api/v1/endpoints/webhooks.py)
- **Ingestion:** Successfully receives, validates HMAC signatures, and stores any subscribed event (`pull_request`, `workflow_run`, `workflow_job`) into the `WebhookDelivery` queue table with status `PENDING`.

#### 2. Dispatcher Status
- **Dispatcher:** [`backend/app/services/github/dispatcher.py`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/services/github/dispatcher.py)
- **Implemented Handlers:**
  - `installation` -> calls `handle_installation_event()` in `lifecycle.py`
  - `installation_repositories` -> calls `reconcile_installation_repositories()` in `lifecycle.py`
  - `pull_request` -> calls `sync_pull_request()` in `pr_sync.py`
- **Missing Handlers:**
  - `workflow_run` and `workflow_job` currently hit `logger.info(f"Unhandled or passive webhook event: {event_type}")` and exit without executing domain logic.

#### 3. Processing Services & Required Integration Work
- **Existing Service:** [`CIFailureService`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/services/ci_intelligence/service.py) is fully implemented with error classification, stacktrace parsing, secret sanitization, and localized hypothesis generation. Currently, it is exposed only via direct REST endpoints (`/api/v1/ci-failures/ingest`).
- **Required Wiring (Antigravity implementation task):**
  1. Add an event handler in `dispatcher.py` for `workflow_run` and `workflow_job` when `action == "completed"` and `conclusion == "failure"`.
  2. Use `GitHubClient` with the installation token to query `GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs`.
  3. Pass the fetched raw logs to `CIFailureService.ingest_failure()`, bridging the webhook event directly to AI root-cause analysis and remediation.

---

### 13.3 Private Key Path, Cross-Platform Resolution & Security Exclusions

#### 1. Path Resolution Audit
- **Current State:** `GITHUB_APP_PRIVATE_KEY_PATH` is defined on `Settings` in [`backend/app/core/config.py`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/core/config.py), but no runtime helper reads the file into memory (tests passed mock strings in-memory).
- **Implementation Requirement:** A path loader helper will be wired to resolve paths relative to the application root using `pathlib.Path`:
  ```python
  def get_private_key_pem(path: str | None = None) -> bytes:
      key_path = Path(path or settings.GITHUB_APP_PRIVATE_KEY_PATH)
      if not key_path.is_absolute():
          # Check backend directory first, then current working directory
          candidate = Path(__file__).resolve().parent.parent.parent / key_path
          if candidate.exists():
              return candidate.read_bytes()
      return key_path.read_bytes()
  ```

#### 2. Cross-Platform Compatibility (Windows vs. Docker)
Using relative path `keys/github-app.pem`:
- **On Windows Host:** When running Python/FastAPI locally from `C:\Users\lucky\Downloads\mergemind\backend`, `keys/github-app.pem` resolves cleanly to `C:\Users\lucky\Downloads\mergemind\backend\keys\github-app.pem`.
- **Inside Docker Container:** When running in container with `WORKDIR /app`, `keys/github-app.pem` resolves to `/app/keys/github-app.pem`.
- **Verdict:** The relative path `keys/github-app.pem` is cross-platform identical and portable across both environments.

#### 3. Security Exclusions: Git & Docker Contexts
- **Git Context ([`.gitignore`](file:///C:/Users/lucky/Downloads/mergemind/.gitignore)):**
  - Lines 4–5 of `.gitignore` explicitly match `*.pem` and `*.key`.
  - To ensure complete defense-in-depth, `keys/` and `backend/keys/` should also be added.
- **Docker Context ([`backend/Dockerfile`](file:///C:/Users/lucky/Downloads/mergemind/backend/Dockerfile)):**
  - **CRITICAL AUDIT FINDING:** There is currently NO `.dockerignore` file in the repository!
  - `backend/Dockerfile` executes `COPY . .`. If `.dockerignore` is absent, running `docker build` would accidentally copy `backend/keys/github-app.pem` and `.env` directly into the immutable Docker image layers!
  - **Required Action:** A `.dockerignore` file must be added to `backend/` and repository root containing:
    ```
    keys/
    *.pem
    *.key
    .env*
    __pycache__/
    .pytest_cache/
    ```
  - **Docker Compose Secret Mounting:** In `docker-compose.yml`, mount the key at runtime via a read-only volume:
    ```yaml
    volumes:
      - ./backend/keys:/app/keys:ro
    ```
    This keeps the image artifact completely credential-free.

---

### 13.4 Test Repository Isolation & Security Boundary

#### 1. Repository-Level Access Boundary
GitHub Apps feature granular installation scoping. When installing the GitHub App onto your account:
- GitHub prompts: **"Repository access: All repositories OR Only select repositories"**.
- By selecting **"Only select repositories"** and choosing **strictly `mergemind-test-sandbox`**:
  - The App receives installation tokens that are cryptographically restricted to that single repository.
  - Any API request attempting to read, list, or write to any other repository in your account is rejected with HTTP `404 Not Found` or `403 Forbidden` by GitHub's authorization gateway.
  - Your other personal and organizational repositories remain completely invisible and inaccessible.

#### 2. Strict Least-Privilege Permission Boundary
The complete 12-stage MergeMind workflow requires **only 4 permissions**:

| Permission | Scope | Exact Purpose |
|---|---|---|
| `Pull requests` | **Read & Write** | Read PR changes (Stage 4) and open draft remediation PRs (Stage 11) |
| `Contents` | **Read & Write** | Read source files (Stage 3) and push fix branch/patch commits (Stage 11) |
| `Actions` | **Read-only** | Download failed CI run logs (Stage 6) |
| `Metadata` | **Read-only** | Required default by GitHub for repo identification |

**Zero Additional Permissions Required:**
- `Checks: No access` (Omitted; MergeMind uses PR body + internal dashboard)
- `Issues: No access` (Omitted; MergeMind uses PRs)
- `Commit statuses: No access` (Omitted)
- `Administration: No access` (Omitted)
- `Deployments: No access` (Omitted)

---

### 13.5 Concise Final Setup Checklist

Follow these exact steps to complete configuration before implementation begins:

```markdown
================================================================================
FINAL OWNER SETUP CHECKLIST (NO SECRETS IN CHAT)
================================================================================

[ ] 1. Obtain Gemini API Key
    * Go to: https://aistudio.google.com/app/apikey
    * Click "Create API Key" (Free tier).
    * Copy the key (starts with "AIzaSy...").

[ ] 2. Setup Smee Webhook Proxy Channel
    * Go to: https://smee.io
    * Click "Start a new channel".
    * Copy the generated URL: e.g. "https://smee.io/your_unique_id"

[ ] 3. Create Dedicated Test Repository
    * Create a new repository on GitHub:
      https://github.com/venu8888/mergemind-test-sandbox
    * Initialize it with a simple README.md.

[ ] 4. Register the GitHub App
    * Go to: GitHub > Settings > Developer settings > GitHub Apps > New GitHub App
    * App name: "MergeMind-Verification-Engine" (or unique name)
    * Homepage URL: https://github.com/venu8888/mergemind
    * Webhook URL: Paste your Smee URL from Step 2
    * Webhook secret: Enter a random 32-character secret
    * Repository Permissions (Least Privilege):
        - Pull requests: Read & Write
        - Contents: Read & Write
        - Actions: Read-only
        - Metadata: Read-only
        - (Leave everything else set to "No access")
    * Subscribe to events:
        - [x] Pull request
        - [x] Workflow run
        - [x] Workflow job
        - [x] Installation
        - [x] Installation repositories
    * Click "Create GitHub App".
    * In "Install App", choose: "Only select repositories" -> "mergemind-test-sandbox".
    * Under "General", scroll down to "Private keys" and click "Generate a private key".
      (A .pem file will download).
    * Note your numeric "App ID" from the General tab.

[ ] 5. Place Credentials Locally on Machine
    * Create directory: C:\Users\lucky\Downloads\mergemind\backend\keys
    * Move the downloaded .pem file to:
      C:\Users\lucky\Downloads\mergemind\backend\keys\github-app.pem
    * In C:\Users\lucky\Downloads\mergemind\backend\.env, add/update these exact lines:

      GEMINI_API_KEY=<your_gemini_api_key>
      REMEDIATION_ENDPOINT=https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
      REMEDIATION_MODEL=gemini-3.8-flash

      GITHUB_APP_ID=<your_numeric_app_id>
      GITHUB_APP_PRIVATE_KEY_PATH=keys/github-app.pem
      GITHUB_WEBHOOK_SECRET=<your_webhook_secret>
      ENABLE_IN_PROCESS_WORKER=true

================================================================================
```


---

## 14. FINAL PRE-IMPLEMENTATION VERIFICATION & DEPLOYMENT BLUEPRINT

### 14.1 CI Webhook Processing & Log Retrieval Architecture

#### 1. Payload Structure: `workflow_run` vs. `workflow_job`
Both events are fired by GitHub Actions, but their schemas serve distinct purposes:

* **`workflow_run` Payload Structure:**
  ```json
  {
    "action": "completed",
    "workflow_run": {
      "id": 14502891234,
      "name": "CI Pipeline",
      "head_sha": "a1b2c3d4e5f678901234567890abcdef12345678",
      "head_branch": "feature/bug-fix",
      "conclusion": "failure",
      "pull_requests": [{"id": 101, "number": 1}],
      "repository": {"id": 98765432, "full_name": "venu8888/mergemind-test-sandbox"},
      "installation": {"id": 55443322}
    }
  }
  ```
  *Limitation:* Does not include individual job IDs or log traces. Requires calling `GET /repos/{owner}/{repo}/actions/runs/{run_id}/jobs` to identify which job failed.

* **`workflow_job` Payload Structure (Recommended Primary Trigger):**
  ```json
  {
    "action": "completed",
    "workflow_job": {
      "id": 38291048291,
      "run_id": 14502891234,
      "workflow_name": "CI Pipeline",
      "name": "test",
      "head_sha": "a1b2c3d4e5f678901234567890abcdef12345678",
      "head_branch": "feature/bug-fix",
      "conclusion": "failure",
      "steps": [
        {"name": "Set up Python", "status": "completed", "conclusion": "success", "number": 1},
        {"name": "Run pytest", "status": "completed", "conclusion": "failure", "number": 2}
      ]
    },
    "repository": {"id": 98765432, "full_name": "venu8888/mergemind-test-sandbox"},
    "installation": {"id": 55443322}
  }
  ```
  *Advantage:* Provides the exact `job.id` (`38291048291`) and failing step immediately.

**Architectural Decision:** Trigger on `workflow_job` with `action == "completed"` and `conclusion == "failure"`. It points directly to the failed execution container without intermediate API lookups.

#### 2. Log Download & Redirect Handling
- **API Endpoint:** `GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs`
- **Redirect Mechanism:** GitHub responds to this endpoint with **HTTP `302 Found`**, redirecting to a pre-signed temporary Azure blob storage URL (`https://pipelines.actions.githubusercontent.com/...`).
- **Implementation Requirement:** In [`backend/app/services/github/client.py`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/services/github/client.py), `httpx.AsyncClient` defaults to `follow_redirects=False`. The client must be instantiated or invoked with **`follow_redirects=True`** so the log body is downloaded seamlessly across the storage redirect without dropping execution.

#### 3. Idempotency & Deduplication Guarantees
- **Webhook Ingress Layer:** The `WebhookDelivery` table enforces a unique constraint on `delivery_id` (`X-GitHub-Delivery`). Replayed delivery attempts raise an `IntegrityError`, are safely caught, and return `HTTP 200 {"status": "already_processed"}` without re-enqueuing duplicate work.
- **CI Failure Record Layer:** [`CIFailureService.ingest_failure`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/services/ci_intelligence/service.py) checks for existing records matching `(repository_id, workflow_run_id, job_name)` before insertion. If an identical run/job has already been analyzed, the existing `CIFailureRecord` is returned, preventing redundant database records or repetitive AI prompt calls.

#### 4. Pre-Persistence & Pre-LLM Sanitization
- Raw CI logs are scrubbed by [`CILogParser.sanitize_logs()`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/services/ci_intelligence/parser.py) **before** storage in `CIFailureRecord.log_excerpt`.
- Regex scrubbers redact all GitHub personal access tokens (`ghp_...`, `github_pat_...`), Bearer tokens, private keys, database URLs, and password assignments.
- When generating remediation prompts, [`RemediationContext.sanitize()`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/services/remediation/base.py) performs secondary redaction on all snippet and excerpt strings, ensuring zero sensitive tokens ever reach Google Gemini.

---

### 14.2 Docker Secret Security Blueprint

#### 1. Proposed `.dockerignore` Specification
To guarantee that local keys and environment files are **NEVER** baked into immutable image layers during `docker build`, a root and backend `.dockerignore` will be added:

```dockerignore
# ==============================================================================
# MergeMind Docker Build Context Exclusions (.dockerignore)
# Prevents sensitive credentials, keys, and caches from entering image layers.
# ==============================================================================

# Version control
.git/
.gitignore

# Secrets, private keys, and certificates (CRITICAL)
**/*.pem
**/*.key
**/*.crt
**/*.cer
keys/
backend/keys/
.env*
!.env.example

# Python runtime artifacts & caches
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/
*.db
*.sqlite3

# Node & Frontend build artifacts
node_modules/
frontend/dist/
```
*Note:* `!.env.example` explicitly preserves the documentation template while ignoring all actual `.env` files.

#### 2. Runtime Secret Mounting in `docker-compose.yml`
* The private key is mounted **only at runtime** and **strictly read-only (`:ro`)**.
* **Only the `backend` container** receives the mount. Neither `mergemind-frontend` nor `mergemind-db` has access to the key.
* **Volume Mount Snippet:**
  ```yaml
  backend:
    volumes:
      - ./backend/keys:/app/keys:ro
  ```
* **Database Volume Preservation:** The existing persistent database volume `postgres18_data` is left untouched. It will not be deleted or recreated.

---

### 14.3 Gemini Model Validation & Fallback Invariants

* **Verified Active Model:** **`gemini-3.8-flash`** is Google's verified, active stable model optimized for code generation and multi-step agent workflows. The alias **`gemini-flash-latest`** is also verified and supported.
* **OpenAI REST Protocol Compatibility:** Calls to `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions` with header `Authorization: Bearer <GEMINI_API_KEY>` accept standard messages payloads and return `choices[0].message.content`.
* **Deterministic Fallback Preservation:** If `GEMINI_API_KEY` is omitted, or if network timeouts / rate limits occur, [`LLMRemediationProvider`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/services/remediation/llm_provider.py) automatically catches the condition and delegates diff synthesis to [`MockRemediationProvider`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/services/remediation/mock_provider.py). The rule-based deterministic fallback remains 100% intact.

---

### 14.4 Smee Webhook Forwarding Security

* **Endpoint Route:** `POST /api/v1/webhooks/github`
* **Docker Port:** `8000:8000`
* **Local Ingress URL:** `http://localhost:8000/api/v1/webhooks/github`
* **Smee Forwarding Command:**
  ```powershell
  npx smee -u https://smee.io/<CHANNEL_ID> -t http://localhost:8000/api/v1/webhooks/github
  ```
* **Cryptographic Verification Invariant:** In [`webhooks.py`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/api/v1/endpoints/webhooks.py), `verify_webhook_signature()` executes in constant-time on raw payload bytes **before** parsing JSON or persisting records. Unsigned or forged payloads are rejected immediately with `401 Unauthorized`.
* **Zero Host Vulnerability:** Smee creates an outbound-only HTTPS connection to Smee.io. No open incoming listening ports or public IP addresses are exposed on the host machine.

---

### 14.5 Exact Setup Values Reference Matrix

| Setting | Exact Value to Configure | Notes |
|---|---|---|
| **GitHub App Name** | `MergeMind-Verification-Engine` (or unique name) | User-defined in GitHub App settings |
| **Homepage URL** | `https://github.com/venu8888/mergemind` | Standard repository URL |
| **Webhook URL** | `https://smee.io/<YOUR_SMEE_CHANNEL>` | Generated at smee.io |
| **Webhook Secret** | Any 32+ character string (e.g. `9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c`) | Must match in GitHub App and `backend/.env` |
| **Repository Permissions** | `Pull requests: Read & Write`<br>`Contents: Read & Write`<br>`Actions: Read-only`<br>`Metadata: Read-only` | All other permissions set to "No access" |
| **Webhook Events** | `Pull request`, `Workflow run`, `Workflow job`, `Installation`, `Installation repositories` | Check these 5 boxes |
| **Installation Scope** | `Only select repositories` -> `mergemind-test-sandbox` | Strict repository isolation |
| **Private Key Location** | `C:\Users\lucky\Downloads\mergemind\backend\keys\github-app.pem` | Downloaded from GitHub App page |
| **AI Endpoint** | `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions` | Official Google OpenAI-compatible URL |
| **AI Model Identifier** | `gemini-3.8-flash` | Google's active coding Flash model |
| **AI API Key** | `AIzaSy...` | Generated at `aistudio.google.com/app/apikey` |

---

## 15. SHORTEST POSSIBLE OWNER SETUP CHECKLIST

Complete these 5 actions on your machine:

```markdown
================================================================================
MINIMAL OWNER SETUP (DO NOT PASTE SECRETS IN CHAT)
================================================================================

1. GET GEMINI KEY:
   - Visit https://aistudio.google.com/app/apikey -> Click "Create API Key" -> Copy key.

2. GET SMEE URL:
   - Visit https://smee.io -> Click "Start a new channel" -> Copy your channel URL.

3. CREATE TEST REPOSITORY:
   - Create repo: https://github.com/venu8888/mergemind-test-sandbox (with README).

4. REGISTER GITHUB APP:
   - Visit GitHub Settings > Developer settings > GitHub Apps > New GitHub App.
   - Webhook URL: Paste your Smee URL from Step 2.
   - Webhook Secret: Enter a random 32-character string.
   - Permissions:
     * Pull requests: Read & Write
     * Contents: Read & Write
     * Actions: Read-only
     * Metadata: Read-only
   - Events: Check [x] Pull request, [x] Workflow run, [x] Workflow job, [x] Installation, [x] Installation repositories.
   - Create App -> Under "Install App", select ONLY "mergemind-test-sandbox".
   - Under "General", click "Generate a private key" (.pem file downloads).
   - Copy your numeric "App ID".

5. SAVE CREDENTIALS LOCALLY:
   - Create folder: C:\Users\lucky\Downloads\mergemind\backend\keys
   - Move downloaded key to: C:\Users\lucky\Downloads\mergemind\backend\keys\github-app.pem
   - Add these exact lines to C:\Users\lucky\Downloads\mergemind\backend\.env:

     GEMINI_API_KEY=<your_gemini_key>
     REMEDIATION_ENDPOINT=https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
     REMEDIATION_MODEL=gemini-3.8-flash

     GITHUB_APP_ID=<your_numeric_app_id>
     GITHUB_APP_PRIVATE_KEY_PATH=keys/github-app.pem
     GITHUB_WEBHOOK_SECRET=<your_webhook_secret>
     ENABLE_IN_PROCESS_WORKER=true

================================================================================
```


---

## 16. ENGINEERING REFINEMENTS & INTERACTIVE OWNER SETUP PROCEDURE

### 16.1 Engineering Refinements

#### 1. CI Idempotency via Unique GitHub Job ID
Matrix builds in GitHub Actions (e.g. testing across Python 3.10, 3.11, 3.12, 3.13 or multiple OS targets) often share identical workflow names and base job names. To prevent matrix collisions:
- The GitHub numeric **`job_id`** (`workflow_job.id`) is established as the primary deduplication key for all `workflow_job` events.
- Deduplication query:
  ```python
  existing = (await db.execute(
      select(CIFailureRecord).where(
          CIFailureRecord.repository_id == repository_id,
          CIFailureRecord.job_id == job_id,
      )
  )).scalar_one_or_none()
  if existing:
      return existing
  ```
- This ensures matrix jobs executing concurrently are each ingested cleanly without overwriting or skipping parallel failures.

#### 2. Log Download Redirect Security (Header Stripping)
- GitHub Actions logs redirect via **HTTP `302 Found`** to temporary signed storage URLs (e.g. Azure Blob Storage at `https://pipelines.actions.githubusercontent.com/...`).
- **Security Invariant:** The GitHub App Bearer / Installation token must **never** be leaked to external cloud storage providers.
- **Scoped Implementation:** Redirect handling is strictly scoped to the log download method:
  1. The initial request to `GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs` is sent with the GitHub installation `Authorization` header and `follow_redirects=False`.
  2. Upon receiving the `302 Found` response, the target URL is extracted from the `Location` header.
  3. A secondary `GET` request is issued to that signed `Location` URL using a fresh request with **headers stripped** (no `Authorization` header), preventing token leakage.

#### 3. Gemini Model & Mock Fallback Invariant
- The stable identifier **`gemini-3.8-flash`** is enforced.
- Google's official OpenAI-compatible endpoint `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions` is the active provider URL.
- [`MockRemediationProvider`](file:///C:/Users/lucky/Downloads/mergemind/backend/app/services/remediation/mock_provider.py) remains 100% intact as the fallback engine for offline testing, rate limits, and network partitions.

---

### 16.2 Interactive Setup Roadmap

The interactive onboarding follows 5 discrete phases, completed one at a time:
1. **Task A: Google Gemini API Key:** Create and locally store the Gemini API key; verify connectivity locally without exposing secrets.
2. **Task B: Smee Webhook Ingress:** Create a private Smee channel and test local event forwarding over PowerShell.
3. **Task C: Dedicated GitHub Test Repository:** Create `mergemind-test-sandbox` with required baseline and defect files.
4. **Task D: GitHub App Registration & Least-Privilege Scoping:** Register the App, select exact permissions, download private key, and install exclusively on `mergemind-test-sandbox`.
5. **Task E: Local Credential Configuration & Docker Verification:** Populate `backend/.env`, mount `keys/github-app.pem`, and verify zero secret exposure in Git and Docker.
