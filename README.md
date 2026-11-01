# MergeMind

**An Intelligent Pull Request Analysis and Verification Framework**

MergeMind is an evidence-backed software change verification system designed to improve pull request quality and security across GitHub workflows. Rather than emitting speculative AI commentary, MergeMind enforces an evidentiary hierarchy distinguishing deterministic static analysis, empirical sandbox test execution, security scans, and contextual AI advisories.

---

## Architecture Overview

* **Backend:** FastAPI (Python 3.13) + Async SQLAlchemy 2.0 + Alembic + Pydantic v2.
* **Frontend:** React 19 + TypeScript + Vite + Tailwind CSS + Lucide Icons.
* **Database:** PostgreSQL (with SQLite compatibility for zero-setup local dev/test).
* **Deterministic Analysis:** Ruff (AST linting & syntax checks) + Bandit (security scanning).
* **Isolated Runner:** Ephemeral container sandbox (`--network none`, dropped Linux capabilities, non-root user, memory & CPU quotas, 60s hard timeout) with fail-closed guarantees.
* **CI/CD:** GitHub Actions workflow executing deterministic checks, Bandit security scans, Pytest with coverage, and TypeScript build checks.

---

## Project Structure

```
mergemind/
├── .github/
│   └── workflows/
│       └── ci.yml               # Automated CI pipeline
├── backend/
│   ├── alembic/                 # Database migration scripts
│   ├── app/
│   │   ├── api/v1/              # Versioned API routers & endpoints
│   │   ├── core/                # Configuration, database engine & security
│   │   ├── models/              # Normalized SQLAlchemy ORM models
│   │   └── schemas/             # Pydantic v2 schemas
│   ├── tests/                   # Pytest automated test suite
│   ├── alembic.ini              # Alembic configuration
│   ├── Dockerfile               # Production multi-stage Dockerfile
│   ├── pyproject.toml           # Python package & tool configuration
│   └── requirements.txt         # Production dependencies
├── frontend/
│   ├── src/
│   │   ├── components/          # Reusable React UI components
│   │   ├── services/            # API client service
│   │   └── types/               # TypeScript domain interfaces
│   ├── Dockerfile               # Multi-stage Nginx container build
│   └── package.json             # Frontend dependencies & scripts
├── docker-compose.yml           # Local multi-service development compose
├── .env.example                 # Environment configuration template
└── .gitignore                   # Version control exclusion rules
```

---

## Windows 11 Setup & Production Execution Instructions

### Prerequisites on Windows 11
1. **PowerShell 7+** or Windows PowerShell 5.1 running with Administrator privileges.
2. **Docker Desktop for Windows** (WSL 2 backend enabled and running).
3. **Node.js v20+** and `npm` installed.
4. **Python 3.11 - 3.13** installed (e.g. Anaconda or standalone Python).
5. **Git for Windows** configured.

---

### Step 1: Environment & GitHub App Credentials Setup

1. Copy the environment configuration template:
   ```powershell
   Copy-Item .env.example backend\.env
   ```
2. Configure `backend/.env` with your credentials:
   ```ini
   # Database & Secrets
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/mergemind
   API_KEY=<generate_secure_random_key>
   SECRET_KEY=<generate_secure_random_key>

   # GitHub App Authentication
   GITHUB_APP_ID=<your_github_app_id>
   GITHUB_APP_PRIVATE_KEY_PATH=keys/github-app.pem
   GITHUB_WEBHOOK_SECRET=<your_webhook_secret>

   # Gemini LLM Provider (Google AI Studio)
   GEMINI_API_KEY=<your_gemini_api_key>
   REMEDIATION_MODEL=gemini-3.6-flash
   REMEDIATION_ENDPOINT=https://generativelanguage.googleapis.com/v1beta/openai/chat/completions

   # Deterministic Sandbox Policies
   SANDBOX_EXECUTION_TIMEOUT_SECONDS=60
   SANDBOX_MAX_MEMORY_MB=512
   SANDBOX_CPU_QUOTA=1.0
   SCORING_POLICY_VERSION=v2.2-calibrated
   ```
3. Place your GitHub App private key at `backend/keys/github-app.pem` (this file is excluded from Git and Docker build contexts).

---

### Step 2: Launch Live Webhook Forwarder (Smee)

In a dedicated PowerShell terminal, launch the webhook forwarder:
```powershell
npx -p smee-client smee -u https://smee.io/<your-channel-id> -t http://localhost:8000/api/v1/webhooks/github
```
*Leave this terminal running in the background.*

---

### Step 3: Run MergeMind via Docker Compose

From the repository root, start all application services:
```powershell
docker compose up -d --build
```

Verify service status:
```powershell
docker compose ps
```
The stack will spin up:
- **`mergemind-db`**: PostgreSQL on host port `5433` (healthy).
- **`mergemind-backend`**: FastAPI application on host port `8000` (healthy).
- **`mergemind-frontend`**: Nginx static client on host port `3000`.

Check endpoints:
- Web Dashboard: `http://localhost:3000`
- REST API Documentation: `http://localhost:8000/api/v1/docs`
- Health Endpoint: `http://localhost:8000/healthz`

---

### Step 4: Running the Automated Test Suite

Run all 185 unit, integration, and security audit tests:
```powershell
cd backend
python -m pytest tests -v
```

---

## Live End-to-End Workflow Verification

MergeMind includes complete end-to-end support for live GitHub repositories:

1. **Repository Synchronization**: Synchronizes repository metadata and baseline target branch commits.
2. **Quality Health Assessment**: Generates calibrated five-factor quality and security health scores (code quality, security, dependencies, test health, maintainability).
3. **Deterministic Sandbox Verification**: Executes static analysis (Ruff) and security scans (Bandit) within ephemeral, zero-network sandboxes.
4. **CI/CD Failure Intelligence**: Ingests `workflow_job` webhooks, securely streams job logs (with sensitive header stripping on redirect), sanitizes secrets, classifies failure categories, and localizes defect coordinates.
5. **Gemini LLM Remediation**: Synthesizes verified unified git diffs targeting localized defects using `gemini-3.6-flash`, strictly bounded to 1500 tokens with automated SHA-256 prompt deduplication.
6. **Dual-Run Sandbox Patch Verification**: Tests pre-patch vs. post-patch states in the container sandbox to detect any regressions before code push.
7. **Corrective GitHub Draft Pull Requests**: Pushes validated patches to branches (`mergemind/fix-...`) and opens genuine Draft PRs, ensuring human maintainers retain complete merge control.
8. **Post-Merge Health Reassessment**: Detects genuine merges and updates repository health scores *strictly after* merge confirmation (unmerged proposals never artificially inflate health scores).

---

## Engineering Guarantees & Constraints

1. **Token & Cost Optimization:** Strict prompt truncation (max 50 lines for snippets and logs), response caching, and deterministic fallbacks prevent unnecessary Gemini API consumption.
2. **Fail-Closed Sandbox:** Untrusted code execution operates in isolated non-root containers without host Docker socket access.
3. **Zero Secret Leakage:** Webhook payloads, CI job logs, and stack traces are scrubbed of tokens, passwords, and private keys prior to persistence and AI prompting.
4. **Audit Immutability:** Evidence records and verification history are cryptographically referenced by commit SHA.


