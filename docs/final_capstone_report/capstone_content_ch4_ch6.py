# capstone_content_ch4_ch6.py
"""
Content definitions for:
- Chapter 4: Proposed System and Architecture
- Chapter 5: Multi-Factor Health Telemetry and Scoring Methodology
- Chapter 6: Enterprise Security Posture and Governance Engine
"""

CHAPTER_4_CONTENT = {
    "title": "Proposed System and Architecture",
    "sections": [
        {
            "num": "4.1",
            "title": "High-Level Architecture Overview",
            "body": (
                "The MergeMind architecture is structured as a resilient, enterprise-grade modular monolith that balances "
                "rapid developer feedback, deterministic execution isolation, and scalable external service integrations. "
                "The system comprises four decoupled primary tiers:\n\n"
                "1. Presentation Tier (Client SPA): Implemented using React 18, TypeScript, Vite, and Tailwind CSS, providing "
                "a responsive, low-latency single-page application for repository health exploration, security posture compliance, "
                "pull request analysis, and remediation diff inspection.\n\n"
                "2. Application and Routing Tier (FastAPI Backend): Built on Python 3.11 and the asynchronous FastAPI web framework, "
                "serving as the centralized business logic orchestration layer, API gateway, cryptographic authenticator, and webhook handler.\n\n"
                "3. Relational Persistence Tier (PostgreSQL 18): An enterprise ACID-compliant relational database accessed via "
                "SQLAlchemy 2.0 ORM and Asyncpg, managing repository metadata, health snapshots, CI failure traces, AI remediation proposals, "
                "and audit logs.\n\n"
                "4. Sandboxed Execution and AI Intelligence Tier: Comprising isolated ephemeral Docker execution containers for "
                "code evaluation and regression verification, combined with the Google Gemini 3.6 Flash generative API for automated "
                "code reasoning, stack trace triage, and unified diff synthesis.\n\n"
                "Figure 4.1 illustrates the overarching multi-tier system topology and data flow pathways across all system layers."
            ),
            "figure_id": "arch_01_system_overview.png",
            "figure_caption": "Figure 4.1: MergeMind High-Level System Architecture and Multi-Tier Topology"
        },
        {
            "num": "4.2",
            "title": "Presentation Tier: React 18 Single-Page Application",
            "body": (
                "The frontend client is engineered as a modern Single-Page Application (SPA) leveraging React 18 with strict TypeScript "
                "typing, bundled via Vite for optimized hot-module replacement and production tree-shaking. Visual presentation is "
                "styled using Tailwind CSS, featuring an enterprise dark-mode aesthetic with accessible contrast ratios, bespoke iconography "
                "via Lucide React, and responsive grid layouts.\n\n"
                "Key frontend architectural modules include:\n"
                "• App Routing and State Management: Client-side routing managed via React Router, maintaining synchronized view states "
                "across the Overview Dashboard, Health Telemetry View, Security Posture Governance View, CI Failure Management View, and "
                "AI Remediation Workspace.\n"
                "• Unified API Client Service: Implemented in `frontend/src/services/api.ts`, encapsulating Axios HTTP instances with "
                "automated request header injection (`X-API-Key` authentication), unified error interceptors, and robust payload normalization.\n"
                "• Interactive Telemetry Visualizers: Bespoke UI components for rendering 0–100 health radial/metric cards, status badge "
                "indicators (QUALIFIED vs PROVISIONAL), 43-check security posture domain accordions, and syntax-highlighted unified diff comparisons."
            ),
            "figure_id": "fig_dashboard_overview.jpg",
            "figure_caption": "Figure 4.2: MergeMind Frontend Repository Overview and Health Dashboard Interface"
        },
        {
            "num": "4.3",
            "title": "Application Tier: FastAPI Modular Monolith",
            "body": (
                "The backend application is implemented in Python 3.11 utilizing FastAPI, ASGI server Uvicorn, and Pydantic v2 data validation. "
                "FastAPI was selected due to its native asynchronous event loop (asyncio), enabling non-blocking I/O operations when streaming "
                "large repository tarballs, polling external GitHub endpoints, and invoking generative LLM APIs.\n\n"
                "The backend is decomposed into specialized functional subpackages within `backend/app/`:\n"
                "• `api/v1/endpoints/`: Decoupled REST controllers handling route declarations, dependency injection, and HTTP status codes.\n"
                "• `core/`: Application settings, environment configuration (`pydantic-settings`), and security key loaders.\n"
                "• `services/github/`: GitHub App authentication, RSA PEM signing, installation access token caching, and REST client abstractions.\n"
                "• `services/health_assessment/`: Deterministic static analysis harnesses (Ruff, Bandit, Radon, pip-audit, Pytest) and scoring calculators.\n"
                "• `services/security_posture/`: The 43-check deterministic security evaluation engine.\n"
                "• `services/ci_failure/`: CI failure ingestion, payload reconciliation, regex token scrubbing, and stack frame localizers.\n"
                "• `services/remediation/`: Google Gemini 3.6 Flash prompt construction, unified diff parsing, and patch application.\n"
                "• `services/sandbox/`: Docker container automation and isolated test execution runners."
            ),
            "figure_id": "arch_02_component_interaction.png",
            "figure_caption": "Figure 4.3: Component Interaction and Asynchronous Data Flow Model"
        },
        {
            "num": "4.4",
            "title": "GitHub Integration Subsystem: GitHub App Architecture",
            "body": (
                "Conventional GitHub integrations rely on personal access tokens (PATs) or OAuth apps, which suffer from severe limitations: "
                "PATs are tied to individual user accounts, lack granular least-privilege scoping, and are capped at an unauthenticated rate limit "
                "of 60 requests per hour per IP. When multiple developers or test suites invoke the API, unauthenticated quotas are rapidly exhausted "
                "(HTTP 403 / 500 Primary Rate Limit Exhausted).\n\n"
                "MergeMind overcomes this bottleneck by implementing an authoritative GitHub App integration (`App ID: 5571829`):\n"
                "1. Asymmetric Cryptographic Authentication: An RSA private key in PEM format (`backend/keys/github-app.pem`) is mounted with strict "
                "read-only permissions (chmod 400). The backend generates JSON Web Tokens (JWT) signed with the RS256 algorithm and an expiration of 10 minutes.\n"
                "2. Installation Access Token Minting: Using the JWT, MergeMind authenticates against `POST /app/installations/{installation_id}/access_tokens`, "
                "minting short-lived installation bearer tokens (`ghs_***`).\n"
                "3. Elevated Quota Pool: Installation tokens grant MergeMind a dedicated, authoritative quota of 5,000 requests per hour per installation. "
                "The client automatically injects these tokens into all outbound GitHub REST requests, completely eliminating unauthenticated 60 req/hr exhaustion.\n"
                "4. Cryptographic Webhook Validation: Inbound webhook payloads from GitHub are signed with HMAC-SHA256 in the `X-Hub-Signature-256` header. "
                "MergeMind's webhook service verifies this signature using constant-time byte comparisons before initiating event processing."
            ),
            "figure_id": "arch_03_github_app_auth_flow.png",
            "figure_caption": "Figure 4.4: GitHub App Authentication, Token Minting, and Webhook Security Flow"
        },
        {
            "num": "4.5",
            "title": "Dynamic Repository Ingestion via Streamed Tarball Decompression",
            "body": (
                "A critical architectural challenge in repository intelligence platforms is cross-repository directory contamination. In naive "
                "implementations, static analysis tools execute against the backend server's working directory (`os.getcwd()`), causing every target "
                "repository to evaluate the backend's own source code and return identical, erroneous scores (e.g., an identical 91/100 score across all projects).\n\n"
                "MergeMind resolves this defect through a dynamic streamed tarball extraction pipeline implemented in `backend/app/api/v1/endpoints/health_assessment.py`:\n"
                "1. Tarball Retrieval: The backend invokes `GET /repos/{owner}/{repo}/tarball/{branch}` authenticated with the GitHub App installation token.\n"
                "2. Stream Decompression: GitHub streams a gzip-compressed tar archive (`application/x-gzip`). MergeMind streams the archive into memory "
                "and decompresses it safely into an ephemeral, uniquely generated temporary directory (`tempfile.mkdtemp(prefix='mergemind_repo_')`).\n"
                "3. Path Traversal Safeguards: During extraction, the tar unpacker validates that every relative file path resolves strictly within "
                "the target sandbox root, neutralizing Zip Slip / Tar Slip arbitrary file overwrite vulnerabilities.\n"
                "4. Multi-Tool Analysis: Deterministic scanners execute directly against the isolated unpacked directory.\n"
                "5. Ephemeral Cleanup: Upon assessment completion, the temporary directory is recursively unlinked and purged from disk inside a `finally` block, "
                "preventing local disk exhaustion and guaranteeing zero cross-repository data contamination."
            ),
            "figure_id": "arch_04_health_scoring_pipeline.png",
            "figure_caption": "Figure 4.5: Dynamic Repository Health Telemetry and Scored Tarball Pipeline"
        },
        {
            "num": "4.6",
            "title": "Docker Topology and Network Boundary Isolation",
            "body": (
                "MergeMind is containerized using Docker Compose, orchestrating three core services within an isolated bridge network (`mergemind-network`):\n"
                "• `mergemind-frontend`: Serving the built Vite/React assets via an optimized web server listening on port 3000.\n"
                "• `mergemind-backend`: Running the FastAPI application via Uvicorn workers on port 8000.\n"
                "• `mergemind-db`: Running PostgreSQL 18-alpine on internal port 5432 (mapped to host 5433 to avoid local port conflicts) backed by "
                "a named persistent Docker volume (`postgres_data`).\n\n"
                "To ensure strict runtime security, backend services operate with unprivileged non-root user permissions, read-only volume mounts "
                "for cryptographic keys, and strict network boundaries that prohibit direct external access to the relational database."
            ),
            "figure_id": "arch_09_docker_container_topology.png",
            "figure_caption": "Figure 4.6: Docker Container Topology and Network Boundary Architecture"
        }
    ]
}

CHAPTER_5_CONTENT = {
    "title": "Multi-Factor Health Telemetry and Scoring Methodology",
    "sections": [
        {
            "num": "5.1",
            "title": "Mathematical Formulation of Multi-Factor Health",
            "body": (
                "A central contribution of MergeMind is its multi-factor, deterministic repository health scoring methodology. "
                "Rather than relying on qualitative heuristic grades, MergeMind models repository health as a bounded mathematical function "
                "evaluating five orthogonal software engineering dimensions:\n\n"
                "Let D = {d_1, d_2, d_3, d_4, d_5} represent the five evaluation dimensions:\n"
                "• d_1: Code Quality and Stylistic Conformance (evaluated via Astral Ruff), with nominal weight W_1 = 25%\n"
                "• d_2: Static AST Security Vulnerability Posture (evaluated via Bandit), with nominal weight W_2 = 25%\n"
                "• d_3: Dependency Software Supply Chain Hygiene (evaluated via pip-audit), with nominal weight W_3 = 20%\n"
                "• d_4: Cyclomatic Complexity and Maintainability (evaluated via Radon), with nominal weight W_4 = 10%\n"
                "• d_5: Test Suite Execution Health and Pass Rate (evaluated via Pytest), with nominal weight W_5 = 20%\n\n"
                "Each dimension d_i produces a bounded dimensional sub-score S_i in the closed interval [0, 100]. The baseline composite "
                "health score S_nominal is defined as the weighted linear combination:\n\n"
                "S_nominal = sum_{i=1}^{5} (W_i * S_i), where sum_{i=1}^{5} W_i = 100%"
            )
        },
        {
            "num": "5.2",
            "title": "Dimension Evaluation Mechanics",
            "body": (
                "Each of the five dimensions is computed via deterministic rules:\n\n"
                "1. Code Quality Dimension (S_1, Ruff, W=25%):\n"
                "Ruff statically inspects the codebase for syntax errors, formatting inconsistencies, and rule violations. Let N_err be the number "
                "of errors and N_warn be the number of warnings normalized per 1,000 Lines of Code (KLOC). The sub-score is computed as:\n"
                "S_1 = max(0, 100 - (10 * N_err + 2 * N_warn))\n"
                "A codebase with zero Ruff violations receives a perfect 100/100.\n\n"
                "2. Security Vulnerability Dimension (S_2, Bandit, W=25%):\n"
                "Bandit evaluates AST nodes for security risks. Let C_crit, C_high, C_med, and C_low represent findings weighted by severity:\n"
                "S_2 = max(0, 100 - (25 * C_crit + 15 * C_high + 5 * C_med + 1 * C_low))\n"
                "Any critical security vulnerability (such as hardcoded AWS keys or raw SQL injection) severely degrades the score.\n\n"
                "3. Dependency CVE Dimension (S_3, pip-audit, W=20%):\n"
                "pip-audit scans project manifests (e.g., requirements.txt) against known CVE feeds. If no manifest exists, the check is marked "
                "unconfigured. If dependencies exist, each unpatched CVE reduces the score according to its CVSS severity score:\n"
                "S_3 = max(0, 100 - sum(CVE_penalty_j))\n\n"
                "4. Maintainability Dimension (S_4, Radon, W=10%):\n"
                "Radon computes McCabe cyclomatic complexity M and Halstead Volume V across all functions, deriving the Maintainability Index (MI):\n"
                "MI = 171 - 5.2 * ln(V) - 0.23 * M - 16.2 * ln(LOC)\n"
                "The normalized Maintainability score S_4 maps the average codebase MI directly onto a 0–100 scale.\n\n"
                "5. Test Health Dimension (S_5, Pytest, W=20%):\n"
                "Pytest executes discovered unit tests inside an isolated sandbox. Let T_passed, T_total, and Cov represent passed tests and branch coverage:\n"
                "S_5 = 0.7 * ((T_passed / T_total) * 100) + 0.3 * Cov"
            )
        },
        {
            "num": "5.3",
            "title": "Dynamic Weight Re-Normalization and Completeness Gating",
            "body": (
                "In real-world software development, repositories vary widely in configuration: a small library may not have pinned dependency "
                "manifests, or a documentation repo may lack unit test suites. A naive scoring model that penalizes missing tools by setting "
                "unconfigured dimensions to 0 would unfairly penalize clean repositories.\n\n"
                "To resolve this, MergeMind implements dynamic mathematical weight re-normalization. Let A subseteq {1, 2, 3, 4, 5} represent the set "
                "of active, configured dimensions. The Assessment Completeness C is defined as the proportion of total weight actively evaluated:\n\n"
                "C = sum_{i in A} W_i / 100.0\n\n"
                "The final composite Repository Health Score S_final is then dynamically re-normalized exclusively over active weights:\n\n"
                "S_final = sum_{i in A} (W_i * S_i) / sum_{i in A} W_i\n\n"
                "This guarantees that if pip-audit and Pytest are unconfigured (available weight = 25% + 25% + 10% = 60%), the composite score is "
                "calculated proportionally over that 60% without artificially depressing the score."
            )
        },
        {
            "num": "5.4",
            "title": "Authoritative Qualification Gating Logic",
            "body": (
                "While dynamic re-normalization prevents artificial penalties, a score based on only 1 or 2 linters lacks statistical completeness. "
                "To prevent misleading evaluations, MergeMind enforces Authoritative Qualification Gating:\n\n"
                "• QUALIFIED Status: A repository is classified as QUALIFIED if and only if:\n"
                "  1. Assessment Completeness C >= 0.80 (at least 80% of total nominal weights evaluated); AND\n"
                "  2. Core baseline static linters (Ruff and Bandit) executed successfully with zero runtime execution crashes.\n\n"
                "• PROVISIONAL Status: If C < 0.80, or if primary static linters could not complete execution, the health score is labeled PROVISIONAL. "
                "The frontend UI displays a distinct cautionary badge and alerts developers that additional scanners must be configured to achieve "
                "authoritative qualification.\n\n"
                "Figures 5.1 and 5.2 demonstrate empirical UI telemetry captures from MergeMind showing a QUALIFIED repository (91/100, 80% completeness) "
                "versus a PROVISIONAL repository (100/100, 50% completeness)."
            ),
            "figure_id": "fig_health_telemetry_91_qualified.png",
            "figure_caption": "Figure 5.1: MergeMind Health Telemetry View displaying a Qualified 91/100 Repository Assessment (Completeness: 80%)"
        },
        {
            "num": "5.5",
            "title": "Empirical Health Score Variance Across Real Repositories",
            "body": (
                "Prior to MergeMind's tarball sandbox fix, static analysis evaluated the local backend container directory, returning an identical "
                "91/100 score across all repositories. Following the implementation of streamed tarball isolation, MergeMind was evaluated across "
                "three distinct open-source repositories, demonstrating realistic, highly discriminative variance as summarized in Table 5.1:\n\n"
                "• YOLO26n: Real-world computer vision repository containing legacy styling issues and deep nested loops. Score: 76/100 (QUALIFIED, Completeness: 80%). "
                "Ruff: 85/100, Bandit: 92/100, pip-audit: 100/100, Radon: 25/100 (high McCabe complexity).\n"
                "• mergemind-test-sandbox: Dedicated integration sandbox repository with clean formatting, zero security issues, and modest complexity. "
                "Score: 95/100 (QUALIFIED, Completeness: 80%). Ruff: 100/100, Bandit: 100/100, pip-audit: 100/100, Radon: 60/100.\n"
                "• AI-Proctoring: Educational machine learning project evaluated prior to dependency manifest addition. Score: 100/100 (PROVISIONAL, Completeness: 50%). "
                "Ruff: 100/100, Bandit: 100/100, pip-audit: Unconfigured."
            ),
            "table_id": "HEALTH_VARIANCE_TABLE",
            "figure_id": "fig_health_telemetry_provisional_100.png",
            "figure_caption": "Figure 5.2: Health Telemetry View showing Provisional Gating for Incompletely Configured Repository"
        }
    ]
}

CHAPTER_6_CONTENT = {
    "title": "Enterprise Security Posture and Governance Engine",
    "sections": [
        {
            "num": "6.1",
            "title": "The Need for Deterministic Security Governance",
            "body": (
                "Code security analysis (SAST) evaluates vulnerabilities embedded within source code text. However, software supply chain security "
                "and repository governance are equally determined by administrative configurations governing how code is reviewed, approved, "
                "and deployed. A repository with flawless source code can be catastrophically compromised if branch protection rules permit direct "
                "force pushes to production branches, if CI/CD workflows run with unrestricted administrative token permissions, or if webhooks "
                "transmit sensitive payloads across insecure plaintext HTTP connections.\n\n"
                "To eliminate these organizational blindspots, MergeMind incorporates a comprehensive Enterprise Security Posture Suite executing "
                "43 deterministic policy checks across four foundational operational domains:\n"
                "1. Branch Protection Policies (12 checks)\n"
                "2. Security Features & Vulnerability Scanning (9 checks)\n"
                "3. Access Control & Secret Governance (8 checks)\n"
                "4. Repository Settings & Actions Permissions (14 checks)\n\n"
                "Figure 6.1 illustrates the architectural partitioning of the 43 security posture governance checks."
            ),
            "figure_id": "arch_05_security_posture_governance.png",
            "figure_caption": "Figure 6.1: Enterprise Security Posture Suite Architecture (43 Deterministic Policy Checks across 4 Domains)"
        },
        {
            "num": "6.2",
            "title": "Domain 1: Branch Protection Policies (12 Checks)",
            "body": (
                "Branch protection forms the first line of defense against unauthorized codebase tampering. MergeMind evaluates 12 rigorous checks "
                "against the default branch via GitHub's branch protection API:\n\n"
                "1. Branch Protection Enabled: Validates whether branch protection rules are active on the default branch.\n"
                "2. Required Pull Request Reviews: Enforces that changes must be submitted via pull requests rather than direct pushes.\n"
                "3. Dismiss Stale Approvals: Guarantees that existing PR approvals are automatically invalidated whenever new commits are pushed.\n"
                "4. Require Code Owner Reviews: Enforces that modifications to critical code paths must receive explicit approval from owners designated in CODEOWNERS.\n"
                "5. Approving Reviewers Count: Verifies that the required approving review threshold is configured to at least 1 (or organizationally 2).\n"
                "6. Admin Bypass Restrictions: Enforces that repository administrators cannot bypass branch protection and review requirements.\n"
                "7. Required Status Checks: Ensures automated CI checks (linters, test suites) must pass before a pull request can be merged.\n"
                "8. Require Branches Up to Date: Mandates that feature branches must be rebased or merged with the latest default branch before merging.\n"
                "9. Force Push Restrictions: Strictly blocks force pushes (git push --force) to protect commit history integrity.\n"
                "10. Branch Deletion Restrictions: Blocks branch deletion to prevent accidental loss of default branch references.\n"
                "11. Conversation Resolution: Mandates that all review comment threads must be explicitly resolved prior to merge.\n"
                "12. Signed Commits / Linear History: Requires GPG/SSH cryptographic commit signatures or enforces linear commit history (rebase/squash)."
            )
        },
        {
            "num": "6.3",
            "title": "Domain 2: Security Features and Vulnerability Scanning (9 Checks)",
            "body": (
                "Domain 2 evaluates automated vulnerability detection mechanisms integrated into the repository:\n\n"
                "1. Security Policy Present: Audits whether a formalized SECURITY.md document exists, defining responsible vulnerability disclosure protocols.\n"
                "2. Dependabot Security Alerts: Verifies whether automated GitHub alerts for vulnerable dependencies are enabled.\n"
                "3. Dependabot Version Updates: Audits whether .github/dependabot.yml exists to automatically generate dependency upgrade PRs.\n"
                "4. Code Scanning (CodeQL / SARIF): Confirms whether automated static analysis workflows (such as GitHub CodeQL) are active.\n"
                "5. Secret Scanning Enabled: Validates whether automated detection of committed credentials (API keys, private tokens) is enabled.\n"
                "6. Push Protection Active: Confirms whether secret scanning blocks commits containing plaintext secrets at push time.\n"
                "7. Critical / High Vulnerability Zero: Confirms that zero unaddressed critical or high-severity vulnerability alerts exist in the security feed.\n"
                "8. Private Vulnerability Reporting: Verifies whether external security researchers can privately disclose vulnerabilities to maintainers.\n"
                "9. Automated Security Fixes: Verifies whether Dependabot automated security pull requests are configured."
            )
        },
        {
            "num": "6.4",
            "title": "Domain 3: Access Control and Secret Governance (8 Checks)",
            "body": (
                "Domain 3 evaluates repository access surfaces and credential exposure risks:\n\n"
                "1. Public Repository Warning: Flags whether an enterprise or proprietary codebase is publicly accessible without authorization.\n"
                "2. Administrator Count Hygiene: Enforces least privilege by warning if the number of repository administrators exceeds safe thresholds (e.g., > 3 admins).\n"
                "3. Outside Collaborators Audit: Identifies external collaborators possessing write access outside organizational identity providers.\n"
                "4. Deploy Keys Write Access: Audits SSH deploy keys to ensure read-only access, flagging keys endowed with write privileges.\n"
                "5. Stale Deploy Keys: Detects and flags deploy keys that have not been rotated or utilized within 90 days.\n"
                "6. Insecure Webhook URLs: Audits webhook subscriber URLs to ensure encrypted transport (HTTPS), flagging plaintext HTTP endpoints.\n"
                "7. Webhook Cryptographic Secrets: Audits webhook configurations to guarantee that HMAC secret tokens are configured for payload signing.\n"
                "8. Team Permission Review: Audits whether access permissions are assigned via structured teams rather than ad-hoc individual grants."
            )
        },
        {
            "num": "6.5",
            "title": "Domain 4: Repository Settings and Actions Permissions (14 Checks)",
            "body": (
                "Domain 4 inspects operational repository settings and GitHub Actions execution boundaries:\n\n"
                "1. Wiki Disabled on Public Repos: Ensures public wikis are disabled to prevent spam and unreviewed malicious content hosting.\n"
                "2. Issues Tracking Enabled: Confirms issue tracking is enabled and operational for tracking defects and feature tasks.\n"
                "3. README.md Documentation: Confirms core project documentation exists and satisfies minimum content length requirements.\n"
                "4. LICENSE File Compliance: Audits project license files against recognized open-source SPDX identifiers.\n"
                "5. CODEOWNERS Syntax Validity: Validates the syntax and path mappings of the .github/CODEOWNERS file.\n"
                "6. Actions Execution Permissions: Restricts GitHub Actions execution permissions to prevent arbitrary third-party Action execution.\n"
                "7. GITHUB_TOKEN Permissions: Audits default workflow token permissions, ensuring read-only permissions are enforced by default.\n"
                "8. Actions PR Approval Restrictions: Prohibits GitHub Actions workflows from creating or approving pull requests to prevent privilege escalation.\n"
                "9. Fork PR Actions Approval: Requires explicit maintainer approval before executing Actions workflows triggered from forked repositories.\n"
                "10. Private Repository Forking Policy: Audits repository forking policies to prevent unauthorized intellectual property exfiltration.\n"
                "11. Unprotected Environment Secrets: Confirms that deployment environments containing production secrets enforce protection rules.\n"
                "12. Squash / Rebase Merge Policy: Verifies whether merge commit policies enforce clean git history.\n"
                "13. Auto-Delete Head Branches: Enforces automated deletion of merged feature branches to prevent branch sprawl.\n"
                "14. Git LFS / Repository Size Bounds: Audits repository storage limits and Git Large File Storage (LFS) usage."
            )
        },
        {
            "num": "6.6",
            "title": "Security Posture Index (SPI) Formulation",
            "body": (
                "To provide a single unified governance metric, MergeMind computes the Security Posture Index (SPI) as a weighted percentage "
                "across the four security domains. Let K_1, K_2, K_3, K_4 represent the number of passing checks in Branch Protection (12), "
                "Security Features (9), Access Control (8), and Repository Settings (14) respectively:\n\n"
                "SPI = ((K_1 / 12) * 0.35 + (K_2 / 9) * 0.30 + (K_3 / 8) * 0.20 + (K_4 / 14) * 0.15) * 100\n\n"
                "This formula assigns the highest weight to Branch Protection (35%) and Security Features (30%), reflecting their critical role "
                "in preventing direct supply chain compromise and vulnerability exploitation. Repositories scoring SPI >= 85% receive an "
                "EXCELLENT governance rating, while repositories scoring below 60% are flagged with CRITICAL GOVERNANCE DEFICIT."
            )
        }
    ]
}

# Tables definitions for Chapter 5
HEALTH_VARIANCE_TABLE_ROWS = [
    ("Repository Name", "Ruff (25%)", "Bandit (25%)", "pip-audit (20%)", "Radon (10%)", "Pytest (20%)", "Composite Score", "Status"),
    ("YOLO26n (Computer Vision)", "85 / 100", "92 / 100", "100 / 100", "25 / 100", "Unconfigured", "76 / 100", "QUALIFIED (80%)"),
    ("mergemind-test-sandbox", "100 / 100", "100 / 100", "100 / 100", "60 / 100", "Unconfigured", "95 / 100", "QUALIFIED (80%)"),
    ("AI-Proctoring (ML System)", "100 / 100", "100 / 100", "Unconfigured", "Unconfigured", "Unconfigured", "100 / 100", "PROVISIONAL (50%)")
]
