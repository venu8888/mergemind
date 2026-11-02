# capstone_content_ch1_ch3.py
"""
Content definitions for:
- Chapter 1: Introduction
- Chapter 2: Problem Definition and Requirements Analysis
- Chapter 3: Literature Review and Technical Foundations
"""

CHAPTER_1_CONTENT = {
    "title": "Introduction",
    "sections": [
        {
            "num": "1.1",
            "title": "Background of Modern Software Engineering",
            "body": (
                "The software engineering landscape has undergone profound systemic changes over the past decade. "
                "The emergence of agile development methodologies, microservice architectures, and continuous "
                "delivery models has accelerated the velocity of source code commits, pull requests, and production "
                "deployments. Development teams no longer operate within the paradigm of monolithic annual release "
                "cycles; instead, modern software organizations commit code dozens or even hundreds of times daily. "
                "Central to this operational velocity is the Git version control system and cloud-hosted collaboration "
                "platforms, among which GitHub has achieved uncontested dominance with over 100 million active developers "
                "and hundreds of millions of public and private repositories.\n\n"
                "In this distributed paradigm, the repository represents the ultimate single source of truth for an "
                "organization's intellectual property, operational runtime specifications, dependency topologies, "
                "and continuous integration / continuous deployment (CI/CD) pipelines. Every pull request serves as "
                "both a collaborative nexus where architectural decisions are reviewed and a gatekeeping checkpoint "
                "where automated linters, vulnerability scanners, and regression test suites are executed. However, "
                "as repositories expand in modularity and team distribution widens, maintaining codebase health, "
                "preventing architectural erosion, and enforcing rigorous security governance across disparate projects "
                "has emerged as one of the most pressing engineering bottlenecks of the contemporary cloud era."
            )
        },
        {
            "num": "1.2",
            "title": "Evolution of the Git and GitHub Ecosystem",
            "body": (
                "Distributed Version Control Systems (DVCS), pioneered by Git in 2005, replaced centralized versioning "
                "models by granting each developer a complete local cryptographic history of commits modeled as a Directed "
                "Acyclic Graph (DAG) of SHA-hashed objects (blobs, trees, commits, and annotated tags). The integration of "
                "cloud-based hosting layers—most notably GitHub—transformed basic version control into a collaborative socio-technical "
                "ecosystem. GitHub introduced Pull Requests (PRs), code review workflows, issue trackers, GitHub Actions CI/CD runners, "
                "and webhook-driven event pub/sub architectures.\n\n"
                "Despite these monumental advances, GitHub's native user interface remains fundamentally transaction-oriented "
                "rather than intelligence-oriented. Repositories are represented primarily through file trees, commit logs, "
                "and textual pull request diffs. The platform does not natively synthesize holistic code quality telemetry, "
                "cross-repository security posture compliance, or automated root-cause diagnostics when continuous integration "
                "workflows terminate with non-zero exit codes. Consequently, engineering organizations are forced to stitch "
                "together external dashboards, third-party software as a service (SaaS) linters, security scanners, and "
                "monitoring plugins, leading to severe cognitive fragmentation."
            )
        },
        {
            "num": "1.3",
            "title": "Challenges in Enterprise Repository Management",
            "body": (
                "Enterprise software engineering organizations face an escalating set of systemic challenges when "
                "managing modern repository portfolios:\n\n"
                "1. Fragmented Developer Toolchains: Software development teams regularly interact with separate, siloed "
                "tools for code hosting (GitHub), code quality analysis (SonarQube), static security analysis (Bandit, Snyk), "
                "dependency management (Dependabot), CI/CD orchestration (GitHub Actions), and error monitoring. Developers "
                "waste significant cognitive bandwidth context-switching across disjointed web dashboards, each presenting "
                "incompatible metrics, divergent terminology, and uncoordinated alerting thresholds.\n\n"
                "2. Invisible Code Quality and Architectural Debt: As codebases evolve rapidly under tight product deadlines, "
                "structural quality degrades invisibly. Complex conditional branching increases McCabe cyclomatic complexity, "
                "docstring coverage diminishes, and dead or repetitive code patterns proliferate. Conventional code review "
                "rarely catches subtle maintainability decay because human reviewers are naturally focused on business logic "
                "and immediate feature behavior rather than holistic architectural entropy.\n\n"
                "3. Software Supply Chain Vulnerabilities and Governance Gaps: With modern applications depending on hundreds "
                "or thousands of open-source third-party dependencies, modern repositories are susceptible to transitive "
                "vulnerabilities (known CVEs) and insecure repository configurations. Inadequate branch protection rules, "
                "missing CODEOWNERS policies, excessive repository administration privileges, insecure plaintext webhook URLs, "
                "and over-permissioned CI/CD execution tokens (GITHUB_TOKEN with write or admin scopes) represent pervasive "
                "attack vectors that standard linters fail to audit.\n\n"
                "4. Cognitive Fatigue in Pull Request Code Reviews: Senior engineers spend up to 25% of their working hours "
                "manually reviewing pull request diffs. Much of this time is expended on repetitive syntactic checks, "
                "formatting disputes, and basic test verification, leaving inadequate energy for verifying race conditions, "
                "security boundary validations, and edge-case handling.\n\n"
                "5. The Remediation Gap in CI/CD Failures: When automated build and test pipelines fail, continuous integration "
                "runners emit thousands of lines of verbose console logs. Developers must manually parse these logs, mentally "
                "reconstruct the execution call stack, locate the offending source file and line number, author a corrective "
                "patch, re-execute the test suite locally, and push an incremental commit. This manual loop represents a "
                "massive sink of engineering productivity, with an average industry Mean Time to Remediation (MTTR) spanning "
                "hours or even days."
            )
        },
        {
            "num": "1.4",
            "title": "The Emergence of Artificial Intelligence in Software Engineering",
            "body": (
                "The advent of large language models (LLMs) trained on massive corpora of source code—such as OpenAI's GPT-4, "
                "Anthropic's Claude, and Google's Gemini family—has demonstrated that neural network models can understand "
                "programming language syntax, semantic intent, algorithmic paradigms, and execution context. Automated "
                "Program Repair (APR), previously confined to academic search-based or template-driven constraint solvers, "
                "has transformed into a generative task capable of interpreting stack traces, reasoning over code diffs, "
                "and synthesizing multi-line source code patches.\n\n"
                "However, applying generative LLMs directly to enterprise source code introduces profound risks: hallucinations, "
                "syntactically invalid code generation, inadvertent credential leakage (transmitting proprietary API keys "
                "and secrets in prompt contexts), and lack of deterministic verification. An LLM might produce a plausible-looking "
                "patch that silently fails downstream unit tests or introduces subtle regression bugs. Therefore, an autonomous "
                "remediation platform cannot treat the LLM as an unconstrained oracle; instead, generative intelligence must be "
                "rigorously bounded by deterministic static analysis, strict regex token scrubbing, AST grammar parsing, and "
                "isolated Docker sandbox test verification."
            )
        },
        {
            "num": "1.5",
            "title": "Introduction to MergeMind",
            "body": (
                "MergeMind is an AI-powered GitHub repository intelligence, security governance, and automated code remediation "
                "platform designed to address the aforementioned dilemmas through an integrated, deterministic, and self-hosted "
                "system architecture. MergeMind bridges the chasm between raw repository metadata, deterministic static analysis "
                "engines, enterprise security posture governance, and state-of-the-art generative language models.\n\n"
                "Implemented as an enterprise-grade modular monolith comprising a high-performance FastAPI backend, a responsive "
                "React 18 single-page application (SPA), an enterprise PostgreSQL relational database, and an isolated Docker "
                "sandbox runner, MergeMind acts as an intelligent repository co-pilot. It connects directly to GitHub via an "
                "authoritative GitHub App architecture, unlocking elevated 5,000 requests/hour API quotas and consuming real-time "
                "repository events via cryptographically verified webhooks."
            )
        },
        {
            "num": "1.6",
            "title": "Project Motivation",
            "body": (
                "The core motivation behind MergeMind stems from the realization that developer productivity and software "
                "reliability are fundamentally constrained by human triage overhead. Modern software teams are inundated with "
                "telemetry—linters scream about PEP 8 violations, security scanners flag CVEs, and CI runners fail with cryptic "
                "assertion errors—yet developers remain stranded without automated synthesis or actionable remedies.\n\n"
                "MergeMind was conceived to transform passive diagnostic logs into proactive, verified engineering actions. "
                "By unifying multi-factor repository health telemetry (Ruff, Bandit, Radon, pip-audit, Pytest), enterprise security "
                "governance (a 43-check policy suite), AI-assisted pull request reviews, and autonomous CI/CD failure localization "
                "with sandbox-verified patch synthesis, MergeMind empowers software teams to achieve higher code quality, robust "
                "security compliance, and dramatically reduced MTTR."
            )
        },
        {
            "num": "1.7",
            "title": "Project Objectives",
            "body": (
                "The research and engineering objectives of the MergeMind capstone project are as follows:\n\n"
                "1. Develop an Authoritative GitHub Integration: Implement a secure GitHub App architecture utilizing RSA PEM "
                "private key signing and RS256 JSON Web Tokens to mint installation access tokens with a 5,000 requests/hour "
                "rate limit quota and process real-time events via HMAC-SHA256 signature verification.\n\n"
                "2. Design a Deterministic Multi-Factor Health Telemetry Engine: Construct a mathematical health scoring "
                "framework combining code style (Ruff 25%), static AST security (Bandit 25%), dependency vulnerability (pip-audit 20%), "
                "cyclomatic complexity/maintainability (Radon 10%), and test health (Pytest 20%) with dynamic weight re-normalization "
                "and an authoritative qualification gating threshold (≥80% completeness).\n\n"
                "3. Formulate an Enterprise Security Posture Governance Suite: Design and implement 43 deterministic policy checks "
                "spanning Branch Protection (12 checks), Security Features (9 checks), Access Control (8 checks), and Repository "
                "Settings (14 checks) to compute an objective Security Posture Index (SPI).\n\n"
                "4. Architect an AI-Assisted CI/CD Remediation Pipeline: Integrate Google Gemini 3.6 Flash within a strictly "
                "controlled pipeline featuring regex credential redaction, AST stack frame localization, unified diff generation, "
                "AST syntax validation, Docker sandbox re-verification, and automated GitHub Draft PR creation.\n\n"
                "5. Build an Intuitive, Responsive Presentation Dashboard: Deliver a modern React 18 single-page application "
                "with real-time telemetry visualizations, interactive diff viewers, and security compliance matrices.\n\n"
                "6. Empirically Verify the Platform: Validate all system capabilities through a comprehensive 185-test automated "
                "suite and evaluate performance across real-world production repositories (including YOLO26n, mergemind-test-sandbox, "
                "and AI-Proctoring)."
            )
        },
        {
            "num": "1.8",
            "title": "Project Scope and Intended Audience",
            "body": (
                "The scope of MergeMind encompasses full-stack repository intelligence for Python-based ecosystems, integrating "
                "with GitHub's cloud-hosted platform. The system operates locally or within self-hosted cloud environments "
                "via Docker Compose. Future extensions contemplate polyglot language support (TypeScript, Go, Rust), GitLab "
                "integration, and continuous background mutation testing.\n\n"
                "Intended Users include: Software Engineers seeking instant root-cause diagnostics and verified CI patches; "
                "Tech Leads and Engineering Managers requiring objective codebase health telemetry and maintainability trends; "
                "DevSecOps and Security Engineers enforcing enterprise branch protection, secret hygiene, and dependency policies; "
                "and Open-Source Maintainers managing high volumes of external pull requests."
            )
        },
        {
            "num": "1.9",
            "title": "Organization of the Report",
            "body": (
                "This capstone dissertation is organized into 14 distinct academic chapters:\n\n"
                "• Chapter 1: Introduction establishes the background, challenges, motivation, objectives, and scope.\n"
                "• Chapter 2: Problem Definition and Requirements Analysis details existing workflow limitations, problem formulation, and functional/non-functional requirements.\n"
                "• Chapter 3: Literature Review and Technical Foundations reviews the theoretical and technical literature underpinning static analysis, complexity metrics, vulnerability scanning, and generative APR.\n"
                "• Chapter 4: Proposed System and Architecture details the multi-tier system topology, service interactions, and data flow.\n"
                "• Chapter 5: Multi-Factor Health Telemetry and Scoring Methodology presents the mathematical formulation and dynamic calibration of the 5-factor scoring engine.\n"
                "• Chapter 6: Enterprise Security Posture and Governance Engine formalizes the 43-check governance framework and Security Posture Index.\n"
                "• Chapter 7: System Implementation and Module Breakdown provides an exhaustive file-by-file audit of the 8 core backend modules.\n"
                "• Chapter 8: Database Design and Data Dictionary presents the relational ER schema, table definitions, indexes, and constraints.\n"
                "• Chapter 9: API Design and Interface Specifications provides a comprehensive reference of all REST endpoints, payloads, and error codes.\n"
                "• Chapter 10: AI Integration and Prompt Engineering details LLM orchestration, prompt construction, credential redaction, and diff parsing.\n"
                "• Chapter 11: Testing, Verification and Quality Assurance documents the 185 passing tests, error-injection scenarios, and rate limit resilience.\n"
                "• Chapter 12: Results, Discussion and Comparative Evaluation analyzes empirical results across real repositories and benchmarks against conventional tools.\n"
                "• Chapter 13: Security, Reliability, Limitations and Future Scope reviews the threat model, known edge cases, and future research avenues.\n"
                "• Chapter 14: Conclusion summarizes key contributions and academic conclusions.\n"
                "• Appendices and IEEE Bibliography provide supplementary data, complete API specs, and academic citations."
            )
        }
    ]
}

CHAPTER_2_CONTENT = {
    "title": "Problem Definition and Requirements Analysis",
    "sections": [
        {
            "num": "2.1",
            "title": "Existing Software Development and Maintenance Workflow",
            "body": (
                "In a standard continuous integration software development lifecycle, an engineer creates a feature branch "
                "locally, writes code and unit tests, and pushes commits to GitHub. This triggers an automated GitHub Actions "
                "workflow that spins up virtual machine runners to execute dependency installation, linting, security scans, "
                "and test suites. If all checks pass, a pull request is opened and assigned to human peers for code review. "
                "Once approved, the branch is merged into the default branch (main or master), triggering downstream deployment.\n\n"
                "While conceptually elegant, this workflow breaks down catastrophically in practice when any pipeline stage fails. "
                "If a test fails or a linter rejects a commit, the developer must leave their IDE, open GitHub Actions in a browser, "
                "scroll through dense console logs, locate the failure, attempt to reproduce it locally, author a fix, commit, and "
                "re-run the entire pipeline. If a security vulnerability is introduced, it is often detected days or weeks later "
                "by an asynchronous security scanner, requiring expensive context-switching."
            )
        },
        {
            "num": "2.2",
            "title": "Shortcomings of Conventional Toolchains",
            "body": (
                "Conventional software development toolchains suffer from fundamental architectural deficiencies:\n\n"
                "1. Disconnected Telemetry: Linters (Flake8, Pylint), security analyzers (Bandit, Snyk), and coverage tools (Coverage.py) "
                "output disparate, uncoordinated formats (text, JSON, SARIF, XML). There is no unified metric that synthesizes "
                "these signals into an authoritative, actionable health score.\n\n"
                "2. Static Analysis False Positives and Noise: Raw static scanners emit dozens of minor stylistic warnings, "
                "obscuring critical security bugs and causing developer alert fatigue.\n\n"
                "3. Passive Diagnostics without Remediation: Existing tools are exclusively diagnostic. They identify that an "
                "assertion failed or a SQL injection vulnerability exists, but provide zero assistance in synthesizing a verified patch.\n\n"
                "4. Unmonitored Governance Configuration: Security posture settings—such as branch protection rules, required reviews, "
                "signed commits, and token permission boundaries—are configured across fragmented GitHub administrative menus, "
                "leaving repositories vulnerable to configuration drift and administrative bypass."
            )
        },
        {
            "num": "2.3",
            "title": "Formal Problem Statement",
            "body": (
                "Modern distributed software development lacks an integrated, deterministic, and autonomous platform capable of:\n"
                "(a) synthesizing heterogeneous code quality, security vulnerability, dependency risk, complexity, and test signals into an authoritative health score;\n"
                "(b) enforcing enterprise-grade repository security governance across branch protection, access control, and runner permissions;\n"
                "(c) autonomously parsing and sanitizing CI/CD failure logs to localize root causes; and\n"
                "(d) generating syntactically valid code remediation patches that are rigorously pre-verified inside an isolated execution sandbox before human review.\n\n"
                "The core engineering challenge addressed in this capstone is the design, implementation, and empirical verification "
                "of an architectural framework that unifies these capabilities into a scalable, secure, and developer-friendly system."
            )
        },
        {
            "num": "2.4",
            "title": "Proposed Solution: The MergeMind Platform",
            "body": (
                "MergeMind resolves the problem statement by establishing a closed-loop intelligence and remediation architecture:\n\n"
                "• Cryptographically Secured GitHub Ingestion: Connecting as a GitHub App with installation-scoped tokens (5,000 req/hr) "
                "and listening to live events via HMAC-SHA256 verified webhooks.\n"
                "• Dynamic Multi-Factor Health Telemetry: Fetching fresh repository snapshots via streamed tarball decompression "
                "and executing a calibrated 5-factor scoring engine (Ruff, Bandit, pip-audit, Radon, Pytest) with dynamic weight "
                "re-normalization and qualification gating (≥80% completeness).\n"
                "• Enterprise Security Posture Suite: Executing 43 deterministic policy audits across 4 operational domains to calculate "
                "an objective Security Posture Index (SPI).\n"
                "• Autonomous AI Remediation Pipeline: Ingesting CI failure logs, redacting credentials, prompting Gemini 3.6 Flash "
                "to produce unified diffs, validating diff syntax via Python AST, executing regression tests inside an isolated "
                "Docker container sandbox, and publishing verified fixes as GitHub Draft Pull Requests."
            )
        },
        {
            "num": "2.5",
            "title": "Functional Requirements Specification",
            "body": (
                "The functional requirements of the MergeMind platform are rigorously specified in Table 2.1 below, defining "
                "the precise operational capabilities implemented across all system tiers."
            ),
            "table_id": "FR_TABLE"
        },
        {
            "num": "2.6",
            "title": "Non-Functional Requirements Specification",
            "body": (
                "The non-functional requirements define the architectural quality attributes, performance constraints, and security "
                "guarantees enforced by the MergeMind implementation, as detailed in Table 2.2."
            ),
            "table_id": "NFR_TABLE"
        },
        {
            "num": "2.7",
            "title": "System Constraints and Environment Requirements",
            "body": (
                "1. Hardware Requirements: Minimum 4-core x86_64 or ARM64 CPU, 8 GB RAM (16 GB recommended for concurrent Docker sandboxes), "
                "20 GB available SSD storage for container images and temporary tarball extraction workspaces.\n\n"
                "2. Software Requirements: Docker Engine 24.0+ and Docker Compose v2; Python 3.11+; Node.js 20+; PostgreSQL 15+ "
                "(PostgreSQL 18 utilized in production deployment); Modern web browser supporting ES2022 and WebSockets.\n\n"
                "3. External Dependencies: Active GitHub App credentials (App ID, Private RSA PEM Key, Webhook Secret); Google Gemini "
                "API Key (for gemini-3.6-flash access); Inbound network connectivity for GitHub webhook receipt (or local webhook proxy)."
            )
        }
    ]
}

CHAPTER_3_CONTENT = {
    "title": "Literature Review and Technical Foundations",
    "sections": [
        {
            "num": "3.1",
            "title": "Foundations of Distributed Version Control and Webhook Topologies",
            "body": (
                "Distributed Version Control Systems (DVCS) model code history as an immutable directed acyclic graph (DAG) of "
                "cryptographic objects hashed using SHA-1 or SHA-256 (Chacon and Straub, 2014). Each commit object references its "
                "parent commit(s), an author identity, a timestamp, and a root tree object pointing to nested trees and leaf blobs. "
                "This mathematical structure ensures tamper-evident integrity: any modification to a single character in a source "
                "file alters the blob hash, cascading through ancestor tree objects and altering all subsequent commit SHAs.\n\n"
                "In modern cloud ecosystems, collaborative workflows rely on event-driven publish-subscribe mechanisms powered by "
                "webhooks. When developers push commits, open pull requests, or complete CI workflow runs, GitHub dispatches an "
                "HTTP POST payload containing event metadata to configured webhook endpoints. To guarantee payload authenticity "
                "and prevent spoofing or replay attacks, GitHub signs the payload body using an HMAC-SHA256 algorithm parameterized "
                "by a shared secret key (RFC 2104). The receiving server must independently compute the HMAC digest over the raw "
                "request bytes and perform constant-time byte comparison (e.g., using Python's hmac.compare_digest) to prevent "
                "timing side-channel attacks."
            )
        },
        {
            "num": "3.2",
            "title": "Theory and Mechanics of Deterministic Static Code Analysis",
            "body": (
                "Static Application Security Testing (SAST) and static code analysis inspect source code without executing the "
                "underlying binary or runtime interpreter (Chess and McGraw, 2004). Static analyzers operate by parsing raw source text "
                "into an Abstract Syntax Tree (AST)—a structural, hierarchical representation of program grammar containing nodes "
                "for function definitions, control flow branches, expressions, and variable assignments.\n\n"
                "In the Python ecosystem, modern linters have transitioned from legacy interpreted architectures (such as Flake8 and Pylint) "
                "to high-performance compiled architectures. Astral Ruff, implemented in Rust, parses Python source code into an AST "
                "at over 100,000 lines per second—10 to 100 times faster than traditional Python-based linters. Ruff enforces hundreds "
                "of rules covering syntax errors, stylistic conformance (PEP 8), undefined variables (Pyflakes), import hygiene (isort), "
                "and anti-patterns. By incorporating Ruff into MergeMind, codebase linting and formatting compliance are evaluated in "
                "sub-second execution times even across large repositories."
            )
        },
        {
            "num": "3.3",
            "title": "Software Complexity Metrics: McCabe Cyclomatic Complexity",
            "body": (
                "Software maintainability and defect density correlate strongly with structural code complexity. Thomas J. McCabe (1976) "
                "introduced Cyclomatic Complexity (M) based on graph theory, defining the number of linearly independent paths through a "
                "program's control flow graph G = (V, E), where V is the number of vertices (basic blocks of code) and E is the number "
                "of edges (transfers of control). For a graph with P connected components (typically P = 1 for a single subroutine), "
                "McCabe complexity is formally computed as:\n\n"
                "M = E - V + 2P\n\n"
                "Equivalently, for structured programs, M equals the number of decision points (if, while, for, except) plus one. "
                "Empirical software engineering research indicates that functions with M > 10 exhibit significantly higher defect rates, "
                "lower testability, and higher maintenance costs. In MergeMind, Radon is employed to statically compute McCabe complexity "
                "and Halstead Volume, deriving the Maintainability Index (MI) metric to penalize excessively convoluted subroutines."
            )
        },
        {
            "num": "3.4",
            "title": "Static Security Analysis and AST Vulnerability Traversal",
            "body": (
                "While linters focus on code quality and style, static security analyzers traverse the AST to identify security "
                "vulnerabilities classified under the Common Weakness Enumeration (CWE) and OWASP Top 10 guidelines (Open Web "
                "Application Security Project, 2021). Bandit, an established Python security analysis engine, models security vulnerabilities "
                "by defining visitor patterns over Python AST nodes.\n\n"
                "Bandit detects high-risk programming patterns including: hardcoded API keys and plaintext passwords (CWE-798), insecure "
                "cryptographic ciphers (e.g., MD5 or SHA-1 for hashing, DES for encryption; CWE-327), unsafe deserialization via pickle "
                "or yaml.load (CWE-502), SQL injection via unescaped string formatting in database queries (CWE-89), and execution of shell "
                "subprocesses with shell=True (CWE-78). Bandit scores each detected issue by Severity (LOW, MEDIUM, HIGH) and Confidence "
                "(LOW, MEDIUM, HIGH), enabling MergeMind to compute a deterministic security health score."
            )
        },
        {
            "num": "3.5",
            "title": "Software Supply Chain Security and Dependency Vulnerability Auditing",
            "body": (
                "Contemporary software development relies heavily on third-party open-source libraries. Modern applications routinely "
                "incorporate hundreds of transitive dependencies, creating an expansive software supply chain attack surface. Vulnerabilities "
                "in open-source packages are cataloged in public databases including the National Vulnerability Database (NVD) and the "
                "GitHub Advisory Database, tagged with unique Common Vulnerabilities and Exposures (CVE) identifiers and CVSS severity scores.\n\n"
                "Software Composition Analysis (SCA) tools audit lockfiles (e.g., requirements.txt, Pipfile.lock, poetry.lock) to map installed "
                "package versions against known CVE databases. In MergeMind, pip-audit is integrated to scan pinned package graphs "
                "against PyPI and OSV vulnerability feeds. Incorporating SCA into repository health scoring guarantees that repositories "
                "are penalized for harboring unpatched, exploitable third-party dependencies."
            )
        },
        {
            "num": "3.6",
            "title": "Large Language Models in Automated Program Repair (APR)",
            "body": (
                "Automated Program Repair (APR) aims to automatically rectify software bugs without human intervention (Goues et al., 2019). "
                "Classical APR techniques relied on genetic programming (GenProg) or constraint-based symbolic synthesis. While theoretically "
                "rigorous, classical approaches were computationally expensive, required extensive test suites, and frequently produced "
                "'plausible but nonsensical' patches that passed tests by deleting functionality.\n\n"
                "The emergence of transformer-based Large Language Models (Vaswani et al., 2017) revolutionized APR. Pretrained on vast "
                "corpora of open-source source code and commit histories, LLMs possess deep representations of programming idioms, type systems, "
                "and API usage patterns. Models such as Google Gemini 3.6 Flash exhibit remarkable capabilities in zero-shot and few-shot "
                "code synthesis, explaining complex error traces, and generating standardized unified diff patches. However, unconstrained LLM "
                "output suffers from stochastic variance and hallucination. Consequently, modern software architecture requires wrapping "
                "generative models within deterministic validation harnesses."
            )
        },
        {
            "num": "3.7",
            "title": "Isolated Execution and Containerized Sandboxing",
            "body": (
                "Executing untrusted code or automated AI patches on host infrastructure introduces critical security and stability risks. "
                "A flawed patch could execute malicious subprocesses, wipe host directories, or exhaust memory. Operating-system-level "
                "virtualization—implemented via Linux kernel namespaces (pid, net, ipc, mnt, uts, user) and control groups (cgroups)—provides "
                "lightweight, isolated execution boundaries (Merkel, 2014).\n\n"
                "Docker containers encapsulate file systems, dependencies, and process spaces. In MergeMind, all AI remediation verification "
                "is delegated to ephemeral Docker containers with read-only root filesystems, strict CPU/memory limits, dropped Linux capabilities, "
                "and non-root user execution. This ensures that even if an AI patch contains defective or hostile code, host infrastructure remains "
                "completely safeguarded."
            )
        },
        {
            "num": "3.8",
            "title": "Comparative Analysis Matrix: Conventional Tools vs MergeMind",
            "body": (
                "Table 3.1 synthesizes a comprehensive comparative analysis contrasting conventional standalone software engineering "
                "tools against the unified MergeMind platform architecture."
            ),
            "table_id": "COMPARE_TABLE"
        }
    ]
}

# Tables definitions
FR_TABLE_ROWS = [
    ("FR-01", "GitHub App Authenticator", "Mint short-lived RS256 JWTs using private RSA PEM keys to obtain installation access tokens with 5,000 req/hr rate limits."),
    ("FR-02", "Webhook Ingestion & Verification", "Receive GitHub HTTP webhooks, verify HMAC-SHA256 signatures, and asynchronously dispatch push, pull_request, and workflow_run events."),
    ("FR-03", "Dynamic Repository Ingestion", "Stream target repository tarball archives from GitHub REST API and decompress into ephemeral sandboxed temporary directories."),
    ("FR-04", "Deterministic Linting & Quality Scan", "Execute Astral Ruff across ingested source files, computing an objective 0–100 Code Quality score (Weight: 25%)."),
    ("FR-05", "Static Security Vulnerability Scan", "Execute Bandit AST security analysis, classifying findings by Severity/Confidence and computing an objective 0–100 Security score (Weight: 25%)."),
    ("FR-06", "Dependency Vulnerability Audit", "Execute pip-audit against project dependency manifests, mapping pinned packages against known CVEs (Weight: 20%)."),
    ("FR-07", "Complexity & Maintainability Scan", "Execute Radon AST traversal, calculating McCabe cyclomatic complexity and Maintainability Index scores (Weight: 10%)."),
    ("FR-08", "Automated Test Execution", "Execute Pytest test runners inside isolated environments, recording test pass rate and code coverage metrics (Weight: 20%)."),
    ("FR-09", "Dynamic Health Calibration", "Re-normalize total health score dynamically when optional tools are unconfigured, ensuring unbiased health evaluations."),
    ("FR-10", "Qualification Gating", "Gate repository health classification: assign QUALIFIED status only when assessment completeness reaches >= 80% with primary linters active."),
    ("FR-11", "Enterprise Security Posture Audit", "Execute 43 deterministic policy checks across Branch Protection (12), Security Features (9), Access Control (8), and Repo Settings (14)."),
    ("FR-12", "CI/CD Failure Ingestion & Redaction", "Ingest raw CI build/test failure logs, reconciling raw_log/raw_logs payloads and redacting sensitive credentials via regex filters."),
    ("FR-13", "Stack Frame & Error Localization", "Parse assertion error traces and stack frames using regex AST matching to identify target source file, line number, and broken symbol."),
    ("FR-14", "AI Remediation Diff Synthesis", "Construct structured prompts to Google Gemini 3.6 Flash, enforcing unified diff output format adhering to standard patch specifications."),
    ("FR-15", "Docker Sandbox Patch Re-Verification", "Apply AI unified diff inside an isolated ephemeral Docker container sandbox and re-execute Pytest test suites to verify fix validity."),
    ("FR-16", "Automated Draft Pull Request Authoring", "Upon sandbox verification pass, authenticate via GitHub App to create an automated Draft Pull Request containing patch diff and AI reasoning.")
]

NFR_TABLE_ROWS = [
    ("NFR-01", "Security & Credential Redaction", "All raw CI logs and LLM prompts must undergo regex secret scrubbing before transmission. Asymmetric RSA keys must reside with 400 file permissions."),
    ("NFR-02", "Deterministic Health Scoring", "Given the identical commit SHA and environment state, static health scoring algorithms must produce 100% reproducible numerical outputs."),
    ("NFR-03", "Sandbox Isolation Boundary", "Remediation patch testing must execute within unprivileged Docker containers with dropped capabilities, bounded CPU/RAM, and no host volume mounts."),
    ("NFR-04", "API Latency & Throughput", "Read endpoints (GET health-assessment, GET security-posture) must respond in < 150ms under cached conditions and < 4.0s during live tarball extraction."),
    ("NFR-05", "Rate Limit Quota Resilience", "GitHub REST API requests must automatically utilize GitHub App installation tokens, maintaining a 5,000 req/hr quota with automated backoff retry."),
    ("NFR-06", "Payload Schema Flexibility", "CI failure ingestion endpoints must accept diverse CI payload schemas (raw_log, raw_logs) without raising 422 Unprocessable Entity errors."),
    ("NFR-07", "Data Integrity & Concurrency", "Relational database must enforce foreign key integrity and transactional isolation across asynchronous concurrent webhook ingestions."),
    ("NFR-08", "User Interface Responsiveness", "Frontend SPA must provide responsive layout across desktop and tablet viewports, rendering telemetry dashboards and code diffs without UI lag.")
]

COMPARE_TABLE_ROWS = [
    ("Capability Dimension", "Conventional SAST (SonarQube/Snyk)", "Native GitHub / Actions", "MergeMind Unified Platform"),
    ("Code Quality Linting", "Static rules, separate server", "Requires custom Action setup", "Built-in sub-second Ruff execution"),
    ("AST Security Scanning", "Proprietary rule engine", "CodeQL (slow, CI-heavy)", "Deterministic Bandit AST scan (sub-second)"),
    ("Dependency CVE Audits", "Paid SCA database dependency", "Dependabot alerts (async)", "Direct pip-audit manifest scan"),
    ("Unified Health Score", "Abstract 'A-E' grade letters", "None (pass/fail check runs)", "Calibrated 0-100 score + Gating"),
    ("43-Check Posture Suite", "Not supported (code only)", "Manual settings inspection", "Automated 4-domain governance engine"),
    ("CI Log Ingestion", "Not supported", "Raw unparsed console text", "Dual-schema ingestion + Regex secret redaction"),
    ("AI Failure Localization", "None", "None", "AST stack frame extraction"),
    ("Automated AI Patching", "None", "Experimental GitHub Copilot", "Gemini 3.6 Flash unified diff synthesis"),
    ("Sandbox Verification", "None", "None", "Isolated Docker container re-test"),
    ("Draft PR Creation", "None", "Manual developer creation", "Autonomous GitHub Draft PR authoring")
]
