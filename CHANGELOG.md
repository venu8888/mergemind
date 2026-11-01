# MergeMind — Changelog

All notable changes to the MergeMind project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] - Phase 2: Complete GitHub Integration & Ingestion Pipeline

### Added
- **Work Package 2.A — Schema Reconciliation & Migration 002:**
  - Added `Installation` model with UUID primary key, `sync_version`, `state`, and JSON permissions.
  - Linked `Repository` to `Installation` with optimistic concurrency guard and `github_updated_at`.
  - Added durable queue fields to `WebhookDelivery`: `processing_status`, `attempts`, `max_attempts`, `scheduled_at`, `locked_at`, `locked_by`, `lease_token`, `lease_generation`, and `last_error`.
  - Created Alembic migration `002_phase2_schema_enhancements` verified against PostgreSQL 18.
- **Work Package 2.B — Security, RS256 Authentication & Installation Token Manager:**
  - Cryptographic RS256 JWT generation with 60s past leeway and 9m forward expiration.
  - Per-installation `InstallationTokenManager` with concurrency control via `asyncio.Lock` and proactive 5-minute pre-expiration margin.
  - Comprehensive error discrimination (`InstallationNotFoundError`, `InstallationSuspendedError`, `GitHubPermissionError`, `GitHubRateLimitError`, `GitHubAuthError`).
- **Work Package 2.C — Webhook Ingress & Fenced Durable Queue Worker:**
  - HMAC-SHA256 constant-time webhook signature verification and atomic delivery deduplication.
  - High-throughput asynchronous ingress returning `202 Accepted` immediately.
  - Fenced PostgreSQL durable queue worker with dialect-aware lease cutoff, heartbeat lease renewal, and strict atomic failure/completion fencing (`locked_at >= NOW() - INTERVAL '5 minutes'`).
  - Unified atomic dead-letter reaper preventing poisoned jobs from blocking queue processing.
- **Work Package 2.D — GitHub REST API Client & Optimistic Installation Synchronization:**
  - Resilient `GitHubClient` with automatic rate-limit tracking and `Retry-After` secondary backoff.
  - Installation lifecycle handlers (`created`, `deleted`, `suspend`, `unsuspend`).
  - Microsecond optimistic installation synchronization guarded by `sync_version` and `db.expire_all()`.
  - Pull request synchronization with out-of-order event rejection and row-locked monotonic analysis run counter.
  - REST endpoints for installations, repositories, and pull requests.
- **Work Package 2.E — Unified Diff Parser, File Classifier & Source Retriever:**
  - Streaming unified diff parser with strict 5 MB / 5,000 line bounds capping.
  - Multi-category file classifier (`PYTHON_SOURCE`, `TEST_SUITE`, `CONFIGURATION`, `DOCUMENTATION`, `SENSITIVE_SECURITY`, `BINARY_UNSUPPORTED`).
  - Complete source code retrieval at immutable commit SHAs with Git object SHA-1 hash verification (`sha1("blob " + len + "\0" + content)`).
  - Truncation fallback via recursive tree fetching for large repositories.
- **Automated Test Suite & Verification:**
  - 57 passing tests covering all 37 formal test scenarios (T-01 through T-37).
  - 90% test coverage across the application codebase.
  - Clean linting (Ruff: 0 errors) and static security scanning (Bandit: 0 vulnerabilities).
  - Verified Docker Compose runtime with PostgreSQL and healthy backend services.

---

## [0.1.0] - Phase 1: Foundation & Infrastructure

### Added
- Multi-tier evidence verification architecture.
- Core database schema and initial Alembic migration (`001_initial_schema`).
- Ephemeral execution sandbox engine with container isolation.
- FastAPI REST backend with health and delivery endpoints.
- React 19 + TypeScript frontend with Tailwind CSS.
- Automated GitHub Actions CI pipeline and Docker Compose stack.
