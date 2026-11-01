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

## Quickstart (Local Development)

### 1. Backend Setup

```bash
cd backend
python -m pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
pytest -v
uvicorn app.main:app --reload --port 8000
```

The interactive OpenAPI documentation is available at `http://localhost:8000/api/v1/docs`.

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The development interface is accessible at `http://localhost:5173`.

---

## Engineering Guarantees

1. **Evidence-Backed Verification:** Every finding is cryptographically tied to the commit SHA and classified by its verifiable source.
2. **Fail-Closed Security:** Untrusted pull-request code is never executed on the host. If an isolated container runner is offline, untrusted tests are explicitly disabled.
3. **Decoupled Quality Gates:** Quality Score and Verification Completeness are evaluated independently. Critical vulnerabilities or failing tests block merges regardless of numerical score.
