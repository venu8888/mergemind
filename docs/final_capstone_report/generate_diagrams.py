import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Output directory
out_dir = r"C:\Users\lucky\Downloads\mergemind\docs\final_capstone_report\MergeMind_Diagrams"
os.makedirs(out_dir, exist_ok=True)

plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 9

def save_fig(fig, filename):
    p = os.path.join(out_dir, filename)
    fig.savefig(p, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Generated: {p}")

# -------------------------------------------------------------
# Diagram 1: Overall System Architecture
# -------------------------------------------------------------
def gen_diag_1():
    fig, ax = plt.subplots(figsize=(11, 7.5))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # Title
    ax.text(50, 97, "MergeMind System Architecture (High-Level Architecture)", 
            ha='center', va='center', fontsize=14, fontweight='bold', color='#0f172a')
    
    # Layer 1: Presentation Layer
    r1 = patches.FancyBboxPatch((5, 78), 90, 14, boxstyle="round,pad=1", ec="#3b82f6", fc="#eff6ff", lw=1.5)
    ax.add_patch(r1)
    ax.text(7, 89, "PRESENTATION LAYER (Single Page Application)", fontsize=10, fontweight='bold', color='#1e40af')
    boxes_l1 = [
        ("React 18 SPA (Vite)", 10, 80, 16, 7),
        ("Tailwind CSS UI", 28, 80, 15, 7),
        ("Lucide React Icons", 45, 80, 15, 7),
        ("REST API Client (Axios)", 62, 80, 16, 7),
        ("Telemetry Dashboards", 80, 80, 13, 7)
    ]
    for name, x, y, w, h in boxes_l1:
        ax.add_patch(patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5", ec="#93c5fd", fc="#ffffff", lw=1))
        ax.text(x + w/2, y + h/2, name, ha='center', va='center', fontsize=8, color='#1e3a8a')

    # Arrow Down
    ax.annotate('', xy=(50, 71), xytext=(50, 78),
                arrowprops=dict(facecolor='#64748b', edgecolor='#64748b', width=1.5, headwidth=6))
    ax.text(51, 74.5, "HTTPS / REST (JSON) + X-API-Key Auth", fontsize=8, color='#475569', va='center')

    # Layer 2: API Gateway & Application Layer (FastAPI)
    r2 = patches.FancyBboxPatch((5, 38), 90, 32, boxstyle="round,pad=1", ec="#059669", fc="#ecfdf5", lw=1.5)
    ax.add_patch(r2)
    ax.text(7, 67, "APPLICATION BACKEND & CORE SERVICES LAYER (FastAPI Monolith)", fontsize=10, fontweight='bold', color='#065f46')

    submodules = [
        ("GitHub App Auth\nJWT / PEM / 5000 req/h", 8, 54, 18, 10),
        ("Webhook Ingestion\nHMAC-SHA256 Signatures", 28, 54, 18, 10),
        ("Health Engine\nTarball / Ruff / Bandit / Radon", 48, 54, 20, 10),
        ("Security Posture\n43 Deterministic Checks", 70, 54, 22, 10),
        ("CI Failure Ingest\nRegex AST / Redaction", 8, 41, 18, 10),
        ("AI Remediation\nGemini 3.6 Flash / Prompts", 28, 41, 20, 10),
        ("Sandbox Runner\nIsolated Verification", 50, 41, 19, 10),
        ("PR Automation\nUnified Diff / Draft PR", 71, 41, 21, 10)
    ]
    for name, x, y, w, h in submodules:
        ax.add_patch(patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5", ec="#6ee7b7", fc="#ffffff", lw=1))
        ax.text(x + w/2, y + h/2, name, ha='center', va='center', fontsize=7.5, color='#047857', multialignment='center')

    # Layer 3: Persistence & External Systems
    r3 = patches.FancyBboxPatch((5, 5), 90, 26, boxstyle="round,pad=1", ec="#d97706", fc="#fffbeb", lw=1.5)
    ax.add_patch(r3)
    ax.text(7, 28, "DATA STORAGE & EXTERNAL ECOSYSTEM INTEGRATIONS", fontsize=10, fontweight='bold', color='#92400e')

    ext_boxes = [
        ("PostgreSQL 18 DB\nSQLAlchemy / Asyncpg\nRepositories, CI, PRs, Scans", 8, 8, 25, 17),
        ("GitHub REST API / Webhooks\nInstallation Tokens (177642105)\nApp ID 5571829 / Tarball Stream", 37, 8, 26, 17),
        ("Google Gemini API\ngemini-3.6-flash\nStructured Reasoning / Remediation", 66, 8, 26, 17)
    ]
    for name, x, y, w, h in ext_boxes:
        ax.add_patch(patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5", ec="#fcd34d", fc="#ffffff", lw=1))
        ax.text(x + w/2, y + h/2, name, ha='center', va='center', fontsize=8, color='#78350f', multialignment='center')

    # Connecting Arrows
    ax.annotate('', xy=(20, 26), xytext=(20, 38), arrowprops=dict(facecolor='#059669', edgecolor='#059669', width=1.2, headwidth=5))
    ax.annotate('', xy=(50, 26), xytext=(50, 38), arrowprops=dict(facecolor='#059669', edgecolor='#059669', width=1.2, headwidth=5))
    ax.annotate('', xy=(80, 26), xytext=(80, 38), arrowprops=dict(facecolor='#059669', edgecolor='#059669', width=1.2, headwidth=5))

    save_fig(fig, "arch_01_system_overview.png")

# -------------------------------------------------------------
# Diagram 2: Component Interaction Flow
# -------------------------------------------------------------
def gen_diag_2():
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    ax.text(50, 96, "MergeMind Component Interaction & Data Flow Architecture", 
            ha='center', va='center', fontsize=13, fontweight='bold', color='#0f172a')

    # 4 Vertical Columns: Frontend, API Gateway, Service Layer, External/DB
    cols = [
        ("Client Tier\n(React 18 SPA)", 15, "#e0f2fe", "#0284c7"),
        ("API Routing Tier\n(FastAPI Endpoints)", 40, "#ede9fe", "#7c3aed"),
        ("Core Engine Services\n(Domain Logic)", 65, "#fef3c7", "#d97706"),
        ("Persistence & LLM\n(PostgreSQL / Gemini)", 90, "#dcfce7", "#16a34a")
    ]
    for title, x, fc, ec in cols:
        ax.add_patch(patches.FancyBboxPatch((x-10, 80), 20, 10, boxstyle="round,pad=0.5", ec=ec, fc=fc, lw=1.5))
        ax.text(x, 85, title, ha='center', va='center', fontsize=8.5, fontweight='bold', color='#0f172a')
        ax.plot([x, x], [10, 79], linestyle='--', color='#94a3b8', lw=1.2)

    # Sequence steps
    steps = [
        (75, 15, 40, "1. User initiates repository assessment (GET /health-assessment)", "#0284c7"),
        (65, 40, 65, "2. Check cached score or trigger live tarball pull", "#7c3aed"),
        (55, 65, 90, "3. Query GitHub App API with installation token (Tarball stream)", "#d97706"),
        (45, 90, 65, "4. Extract tarball to temp sandbox & execute static linters (Ruff/Bandit/Radon)", "#16a34a"),
        (35, 65, 90, "5. Persist AssessmentRun record in PostgreSQL DB", "#d97706"),
        (25, 65, 40, "6. Calibrate 5-dimension weighted score & qualification gating", "#7c3aed"),
        (15, 40, 15, "7. Return HealthAssessmentResponse (Qualified / Score / Checks)", "#0284c7")
    ]

    for y, x1, x2, msg, col in steps:
        direction = 1 if x2 > x1 else -1
        ax.annotate('', xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(facecolor=col, edgecolor=col, width=1.2, headwidth=5))
        ax.text((x1 + x2)/2, y + 2.5, msg, ha='center', va='bottom', fontsize=7.5, color='#1e293b')

    save_fig(fig, "arch_02_component_interaction.png")

# -------------------------------------------------------------
# Diagram 3: GitHub App Auth & Webhook Flow
# -------------------------------------------------------------
def gen_diag_3():
    fig, ax = plt.subplots(figsize=(10.5, 7))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    ax.text(50, 96, "GitHub App Authentication, Token Minting & Webhook Security Flow", 
            ha='center', va='center', fontsize=13, fontweight='bold', color='#0f172a')

    # Columns
    cols = [
        ("GitHub Servers\n(App & Webhooks)", 15, "#f1f5f9", "#334155"),
        ("GitHub App Auth\n(RSA PEM / JWT)", 40, "#fee2e2", "#dc2626"),
        ("Token Cache\n(Installation Tokens)", 65, "#fef3c7", "#d97706"),
        ("FastAPI Backend\n(Protected Endpoints)", 90, "#e0f2fe", "#0284c7")
    ]
    for title, x, fc, ec in cols:
        ax.add_patch(patches.FancyBboxPatch((x-10, 80), 20, 10, boxstyle="round,pad=0.5", ec=ec, fc=fc, lw=1.5))
        ax.text(x, 85, title, ha='center', va='center', fontsize=8, fontweight='bold', color='#0f172a')
        ax.plot([x, x], [10, 79], linestyle='--', color='#cbd5e1', lw=1.2)

    flows = [
        (74, 90, 40, "1. Request GitHub API access (App ID: 5571829)", "#0284c7"),
        (66, 40, 40, "2. Sign RS256 JWT using private PEM key (10 min expiry)", "#dc2626"),
        (58, 40, 15, "3. POST /app/installations/177642105/access_tokens", "#dc2626"),
        (50, 15, 65, "4. Return Bearer Token (ghs_***, 5,000 req/hr quota)", "#334155"),
        (42, 65, 90, "5. Inject token into GitHubClient session headers", "#d97706"),
        (32, 15, 90, "6. Incoming Webhook: POST /api/v1/webhooks/github (HMAC Header)", "#334155"),
        (24, 90, 90, "7. Verify HMAC-SHA256 signature using GITHUB_WEBHOOK_SECRET", "#0284c7"),
        (16, 90, 90, "8. Async Event Dispatch: push / pull_request / workflow_run", "#0284c7")
    ]

    for y, x1, x2, msg, col in flows:
        if x1 == x2:
            # Self loop
            ax.annotate('', xy=(x1, y-3), xytext=(x1+8, y),
                        arrowprops=dict(facecolor=col, edgecolor=col, width=1, headwidth=4))
            ax.plot([x1, x1+8], [y, y], color=col, lw=1)
            ax.text(x1 + 10, y, msg, ha='left', va='center', fontsize=7.5, color='#1e293b')
        else:
            ax.annotate('', xy=(x2, y), xytext=(x1, y),
                        arrowprops=dict(facecolor=col, edgecolor=col, width=1.2, headwidth=5))
            ax.text((x1 + x2)/2, y + 2, msg, ha='center', va='bottom', fontsize=7.5, color='#1e293b')

    save_fig(fig, "arch_03_github_app_auth_flow.png")

# -------------------------------------------------------------
# Diagram 4: Health Scoring Pipeline
# -------------------------------------------------------------
def gen_diag_4():
    fig, ax = plt.subplots(figsize=(11, 7.5))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    ax.text(50, 96, "Repository Health Scoring & Multi-Factor Telemetry Pipeline", 
            ha='center', va='center', fontsize=13, fontweight='bold', color='#0f172a')

    # Stage 1: Ingestion
    ax.add_patch(patches.FancyBboxPatch((5, 74), 25, 16, boxstyle="round,pad=0.5", ec="#3b82f6", fc="#eff6ff", lw=1.2))
    ax.text(17.5, 87, "1. TARBALL INGESTION", fontsize=8.5, fontweight='bold', color='#1d4ed8', ha='center')
    ax.text(17.5, 79, "• GET /repos/{owner}/{repo}/tarball\n• Stream to Temporary Directory\n• Safe Extraction & Manifest Scan", 
            fontsize=7.5, color='#1e3a8a', ha='center')

    # Stage 2: Parallel Linters
    ax.add_patch(patches.FancyBboxPatch((35, 60), 30, 30, boxstyle="round,pad=0.5", ec="#059669", fc="#ecfdf5", lw=1.2))
    ax.text(50, 87, "2. DETERMINISTIC SCAN ENGINES", fontsize=8.5, fontweight='bold', color='#047857', ha='center')
    linters = [
        "Ruff (Code Quality & Style) — W: 25%",
        "Bandit (AST Security Vulnerabilities) — W: 25%",
        "pip-audit (Dependency CVEs) — W: 20%",
        "Radon (Cyclomatic Complexity) — W: 10%",
        "Pytest (Coverage & Pass Rate) — W: 20%"
    ]
    for idx, l in enumerate(linters):
        ax.text(50, 81 - idx*4.5, f"• {l}", fontsize=7.2, color='#065f46', ha='center')

    # Stage 3: Dynamic Calibration
    ax.add_patch(patches.FancyBboxPatch((70, 74), 26, 16, boxstyle="round,pad=0.5", ec="#d97706", fc="#fffbeb", lw=1.2))
    ax.text(83, 87, "3. NORMALIZATION ENGINE", fontsize=8.5, fontweight='bold', color='#b45309', ha='center')
    ax.text(83, 79, "• Dynamic Weight Re-normalization\n• S_total = sum(W_i * S_i) / sum(W_i)\n• Missing Scanners Omitted Safely", 
            fontsize=7.5, color='#78350f', ha='center')

    # Connectors Top
    ax.annotate('', xy=(35, 82), xytext=(30, 82), arrowprops=dict(facecolor='#64748b', edgecolor='#64748b', width=1.2, headwidth=5))
    ax.annotate('', xy=(70, 82), xytext=(65, 82), arrowprops=dict(facecolor='#64748b', edgecolor='#64748b', width=1.2, headwidth=5))

    # Stage 4: Qualification Gating
    ax.add_patch(patches.FancyBboxPatch((20, 28), 60, 24, boxstyle="round,pad=0.5", ec="#6366f1", fc="#eef2ff", lw=1.5))
    ax.text(50, 48, "4. QUALIFICATION GATING LOGIC & TELEMETRY CLASSIFICATION", fontsize=9, fontweight='bold', color='#4338ca', ha='center')
    ax.text(50, 39, "Assessment Completeness C = sum(Available Weights) / 100\n"
                    "IF C >= 80% AND Ruff + Bandit Operational:\n"
                    "    Status = QUALIFIED (Authoritative Health Telemetry)\n"
                    "ELSE:\n"
                    "    Status = PROVISIONAL / NOT ASSESSED (Requires Additional Tooling Config)", 
            fontsize=8, color='#312e81', ha='center')

    ax.annotate('', xy=(50, 52), xytext=(50, 60), arrowprops=dict(facecolor='#64748b', edgecolor='#64748b', width=1.2, headwidth=5))

    # Stage 5: Output Presentation
    ax.add_patch(patches.FancyBboxPatch((15, 6), 70, 14, boxstyle="round,pad=0.5", ec="#0284c7", fc="#f0f9ff", lw=1.2))
    ax.text(50, 16, "5. PERSISTENCE & USER DASHBOARD PRESENTATION", fontsize=8.5, fontweight='bold', color='#0369a1', ha='center')
    ax.text(50, 9.5, "Save AssessmentRun in PostgreSQL -> Expose via GET /api/v1/repositories/{id}/health-assessment\nRender Score Card, Completeness Pill, Scanner Status Badges, and Run History",
            fontsize=7.5, color='#075985', ha='center')

    ax.annotate('', xy=(50, 20), xytext=(50, 28), arrowprops=dict(facecolor='#64748b', edgecolor='#64748b', width=1.2, headwidth=5))

    save_fig(fig, "arch_04_health_scoring_pipeline.png")

# -------------------------------------------------------------
# Diagram 5: 43-Check Security Posture Architecture
# -------------------------------------------------------------
def gen_diag_5():
    fig, ax = plt.subplots(figsize=(11, 7.5))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    ax.text(50, 96, "Enterprise Security Posture Suite (43 Deterministic Checks)", 
            ha='center', va='center', fontsize=13, fontweight='bold', color='#0f172a')

    quads = [
        ("BRANCH PROTECTION (12 Checks)", 5, 52, 43, 38, "#fee2e2", "#b91c1c", [
            "1. Protection enabled on default branch",
            "2. Required pull request reviews count",
            "3. Dismiss stale pull request approvals",
            "4. Require code owner reviews (CODEOWNERS)",
            "5. Required approving review count >= 1",
            "6. Admin bypass restrictions enforced",
            "7. Required status checks before merging",
            "8. Require branches up to date before merge",
            "9. Force push restrictions active",
            "10. Branch deletion restrictions active",
            "11. Conversation resolution required",
            "12. Signed commits / linear history enforced"
        ]),
        ("SECURITY FEATURES (9 Checks)", 52, 52, 43, 38, "#fef3c7", "#b45309", [
            "1. Security policy present (SECURITY.md)",
            "2. Dependabot security alerts enabled",
            "3. Dependabot version updates configured",
            "4. Code scanning active (CodeQL / SARIF)",
            "5. Secret scanning enabled across commits",
            "6. Secret scanning push protection active",
            "7. Critical/High vulnerability alerts zero",
            "8. Private vulnerability reporting enabled",
            "9. Automated security fixes enabled"
        ]),
        ("ACCESS CONTROL (8 Checks)", 5, 8, 43, 38, "#ede9fe", "#6d28d9", [
            "1. Public repo visibility risk audit",
            "2. Repository administrator count hygiene",
            "3. Outside collaborator permissions check",
            "4. Deploy keys write access restricted",
            "5. Stale deploy keys (>90 days) eliminated",
            "6. Insecure plaintext webhook URLs audit",
            "7. Webhook secret cryptographic validation",
            "8. Team permission least-privilege review"
        ]),
        ("REPOSITORY SETTINGS & ACTIONS (14 Checks)", 52, 8, 43, 38, "#dcfce7", "#15803d", [
            "1. Wiki disabled on public repos",
            "2. Issues tracking enabled & healthy",
            "3. README.md file documentation present",
            "4. LICENSE file verified against SPDX",
            "5. CODEOWNERS file syntactically valid",
            "6. Actions execution permissions restricted",
            "7. GITHUB_TOKEN permissions set to read-only",
            "8. Actions prohibited from approving PRs",
            "9. Fork PR Actions workflows require approval",
            "10. Private repository forking policy",
            "11. Unprotected environment secrets audit",
            "12. Squash / rebase merge policy enforced",
            "13. Auto-delete head branches enabled",
            "14. Git LFS / repository size bounds"
        ])
    ]

    for title, x, y, w, h, fc, ec, items in quads:
        ax.add_patch(patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5", ec=ec, fc=fc, lw=1.2))
        ax.text(x + w/2, y + h - 3, title, fontsize=8.5, fontweight='bold', color=ec, ha='center')
        for i, item in enumerate(items):
            ax.text(x + 2, y + h - 7 - i*2.4, item, fontsize=6.8, color='#1e293b', va='center')

    save_fig(fig, "arch_05_security_posture_governance.png")

# -------------------------------------------------------------
# Diagram 6: AI PR Review Pipeline
# -------------------------------------------------------------
def gen_diag_6():
    fig, ax = plt.subplots(figsize=(10.5, 7))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    ax.text(50, 96, "AI-Assisted Pull Request Review & Diff Intelligence Pipeline", 
            ha='center', va='center', fontsize=13, fontweight='bold', color='#0f172a')

    blocks = [
        ("PR Webhook / Poll\n(GitHub App)", 6, 45, 16, 16, "#f1f5f9", "#475569"),
        ("Diff Parsing & AST\n(File Chunking & Token Cap)", 26, 45, 18, 16, "#e0f2fe", "#0284c7"),
        ("Gemini 3.6 Flash\n(Structured Analysis Prompt)", 48, 45, 19, 16, "#fef3c7", "#d97706"),
        ("Review Synthesis\n(Risk, Bugs, Optimizations)", 71, 45, 18, 16, "#ecfdf5", "#059669")
    ]
    for title, x, y, w, h, fc, ec in blocks:
        ax.add_patch(patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5", ec=ec, fc=fc, lw=1.2))
        ax.text(x + w/2, y + h/2, title, ha='center', va='center', fontsize=8, fontweight='bold', color='#1e293b')

    # Arrows
    ax.annotate('', xy=(26, 53), xytext=(22, 53), arrowprops=dict(facecolor='#64748b', edgecolor='#64748b', width=1.2, headwidth=5))
    ax.annotate('', xy=(48, 53), xytext=(44, 53), arrowprops=dict(facecolor='#64748b', edgecolor='#64748b', width=1.2, headwidth=5))
    ax.annotate('', xy=(71, 53), xytext=(67, 53), arrowprops=dict(facecolor='#64748b', edgecolor='#64748b', width=1.2, headwidth=5))

    # Bottom Callouts
    ax.add_patch(patches.FancyBboxPatch((10, 12), 80, 24, boxstyle="round,pad=0.5", ec="#6366f1", fc="#f5f3ff", lw=1))
    ax.text(50, 31, "PROMPT ARCHITECTURE & SECURITY SAFEGUARDS", fontsize=8.5, fontweight='bold', color='#4338ca', ha='center')
    ax.text(50, 20, "• Secret Sanitization: Regex filters scrub tokens (ghp_, sk-, aws_) before prompt serialization\n"
                    "• Contextual Budgeting: Diffs exceeding 40,000 characters chunked with AST symbol indexing\n"
                    "• Output Schema: Strict JSON parsing extracting findings by Severity (CRITICAL, HIGH, MEDIUM, LOW)\n"
                    "• Human Oversight: Reviews posted as advisory comments without auto-approving merges",
            fontsize=7.5, color='#312e81', ha='center')

    save_fig(fig, "arch_06_ai_pr_review_pipeline.png")

# -------------------------------------------------------------
# Diagram 7: CI Failure Localization
# -------------------------------------------------------------
def gen_diag_7():
    fig, ax = plt.subplots(figsize=(10.5, 7))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    ax.text(50, 96, "CI/CD Failure Ingestion, Sanitization & Root-Cause Localization", 
            ha='center', va='center', fontsize=13, fontweight='bold', color='#0f172a')

    stages = [
        ("Raw CI Logs\n(GitHub Actions / Direct Ingest)", 5, 55, 20, 16, "#fee2e2", "#dc2626"),
        ("Token & Key Sanitizer\n(Regex Redaction Engine)", 28, 55, 20, 16, "#fef3c7", "#d97706"),
        ("Stack Trace AST Parser\n(Frame & Line Localization)", 52, 55, 20, 16, "#e0f2fe", "#0284c7"),
        ("Structured CIFailure\n(DB Entity & Error Frame)", 76, 55, 20, 16, "#dcfce7", "#16a34a")
    ]
    for title, x, y, w, h, fc, ec in stages:
        ax.add_patch(patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5", ec=ec, fc=fc, lw=1.2))
        ax.text(x + w/2, y + h/2, title, ha='center', va='center', fontsize=8, fontweight='bold', color='#1e293b')

    ax.annotate('', xy=(28, 63), xytext=(25, 63), arrowprops=dict(facecolor='#64748b', edgecolor='#64748b', width=1.2, headwidth=5))
    ax.annotate('', xy=(52, 63), xytext=(48, 63), arrowprops=dict(facecolor='#64748b', edgecolor='#64748b', width=1.2, headwidth=5))
    ax.annotate('', xy=(76, 63), xytext=(72, 63), arrowprops=dict(facecolor='#64748b', edgecolor='#64748b', width=1.2, headwidth=5))

    ax.add_patch(patches.FancyBboxPatch((10, 15), 80, 28, boxstyle="round,pad=0.5", ec="#475569", fc="#f8fafc", lw=1))
    ax.text(50, 37, "INGESTION PAYLOAD SANITIZATION & MATCHING CRITERIA", fontsize=8.5, fontweight='bold', color='#334155', ha='center')
    ax.text(50, 24, "Payload schema accepts dual fields: raw_log or raw_logs via @model_validator\n"
                    "Automated scrubbing: GITHUB_TOKEN, AWS_SECRET, SLACK_WEBHOOK -> [REDACTED]\n"
                    "Failure Classification: Unit test failure, Dependency resolution error, Timeout, Build crash\n"
                    "Identifies exact source file path, line number, and offending symbol from assertion diff",
            fontsize=7.5, color='#1e293b', ha='center')

    save_fig(fig, "arch_07_ci_failure_localization.png")

# -------------------------------------------------------------
# Diagram 8: Remediation & Sandbox Verification Loop
# -------------------------------------------------------------
def gen_diag_8():
    fig, ax = plt.subplots(figsize=(11, 7.5))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    ax.text(50, 96, "AI Code Remediation & Docker Sandbox Verification Loop", 
            ha='center', va='center', fontsize=13, fontweight='bold', color='#0f172a')

    # Central Loop
    ax.add_patch(patches.FancyBboxPatch((8, 62), 22, 16, boxstyle="round,pad=0.5", ec="#0284c7", fc="#e0f2fe", lw=1.2))
    ax.text(19, 70, "1. Remediation Prompt\nGemini 3.6 Flash\nTarget File + CI Trace", ha='center', va='center', fontsize=8, fontweight='bold', color='#0369a1')

    ax.add_patch(patches.FancyBboxPatch((40, 62), 22, 16, boxstyle="round,pad=0.5", ec="#d97706", fc="#fffbeb", lw=1.2))
    ax.text(51, 70, "2. Diff Generation\nUnified Patch Format\nStrict AST Syntax Check", ha='center', va='center', fontsize=8, fontweight='bold', color='#b45309')

    ax.add_patch(patches.FancyBboxPatch((72, 62), 22, 16, boxstyle="round,pad=0.5", ec="#7c3aed", fc="#ede9fe", lw=1.2))
    ax.text(83, 70, "3. Sandbox Execution\nDocker Container\nApply Patch & Run Pytest", ha='center', va='center', fontsize=8, fontweight='bold', color='#6d28d9')

    ax.annotate('', xy=(40, 70), xytext=(30, 70), arrowprops=dict(facecolor='#64748b', edgecolor='#64748b', width=1.2, headwidth=5))
    ax.annotate('', xy=(72, 70), xytext=(62, 70), arrowprops=dict(facecolor='#64748b', edgecolor='#64748b', width=1.2, headwidth=5))

    # Decision diamond
    ax.add_patch(patches.FancyBboxPatch((40, 28), 24, 18, boxstyle="round,pad=0.5", ec="#059669", fc="#ecfdf5", lw=1.5))
    ax.text(52, 37, "Verification Result?\nTests Passed & Exit Code 0?", ha='center', va='center', fontsize=8.5, fontweight='bold', color='#047857')

    # Down from Sandbox to Decision
    ax.annotate('', xy=(64, 37), xytext=(83, 62), arrowprops=dict(facecolor='#64748b', edgecolor='#64748b', width=1.2, headwidth=5))

    # Success: Draft PR
    ax.add_patch(patches.FancyBboxPatch((72, 10), 22, 14, boxstyle="round,pad=0.5", ec="#16a34a", fc="#dcfce7", lw=1.2))
    ax.text(83, 17, "SUCCESS:\nCreate GitHub Draft PR\n(e.g., PR #101 Verified)", ha='center', va='center', fontsize=8, fontweight='bold', color='#15803d')
    ax.annotate('', xy=(72, 17), xytext=(64, 30), arrowprops=dict(facecolor='#16a34a', edgecolor='#16a34a', width=1.2, headwidth=5))
    ax.text(70, 26, "YES", fontsize=8, fontweight='bold', color='#16a34a')

    # Failure: Re-prompt
    ax.add_patch(patches.FancyBboxPatch((8, 10), 22, 14, boxstyle="round,pad=0.5", ec="#dc2626", fc="#fee2e2", lw=1.2))
    ax.text(19, 17, "FAILURE:\nLog Diagnostics &\nRefine Prompt Context", ha='center', va='center', fontsize=8, fontweight='bold', color='#b91c1c')
    ax.annotate('', xy=(20, 24), xytext=(40, 32), arrowprops=dict(facecolor='#dc2626', edgecolor='#dc2626', width=1.2, headwidth=5))
    ax.text(28, 30, "NO", fontsize=8, fontweight='bold', color='#dc2626')
    ax.annotate('', xy=(19, 62), xytext=(19, 24), arrowprops=dict(facecolor='#dc2626', edgecolor='#dc2626', width=1.2, headwidth=5))

    save_fig(fig, "arch_08_remediation_sandbox_verification.png")

# -------------------------------------------------------------
# Diagram 9: Docker Deployment Topology
# -------------------------------------------------------------
def gen_diag_9():
    fig, ax = plt.subplots(figsize=(10.5, 7))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    ax.text(50, 96, "MergeMind Docker Container Topology & Network Isolation", 
            ha='center', va='center', fontsize=13, fontweight='bold', color='#0f172a')

    # Host & Bridge Network boundary
    ax.add_patch(patches.FancyBboxPatch((4, 8), 92, 82, boxstyle="round,pad=1", ec="#475569", fc="#f8fafc", lw=1.5, ls='--'))
    ax.text(7, 86, "DOCKER HOST: Isolated Bridge Network (mergemind-network)", fontsize=9, fontweight='bold', color='#334155')

    # 3 Containers
    c1 = ("mergemind-frontend\nNode 20 / Nginx\nPort 3000 -> 3000\nReact 18 + Vite SPA", 8, 42, 25, 34, "#e0f2fe", "#0284c7")
    c2 = ("mergemind-backend\nPython 3.11-slim\nPort 8000 -> 8000\nFastAPI + Async Worker", 38, 42, 26, 34, "#ecfdf5", "#059669")
    c3 = ("mergemind-db\nPostgreSQL 18-alpine\nPort 5433 -> 5432\nPersistent Named Volume", 69, 42, 24, 34, "#fef3c7", "#d97706")

    for title, x, y, w, h, fc, ec in [c1, c2, c3]:
        ax.add_patch(patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5", ec=ec, fc=fc, lw=1.5))
        ax.text(x + w/2, y + h/2, title, ha='center', va='center', fontsize=8, fontweight='bold', color='#1e293b')

    # Links between containers
    ax.annotate('', xy=(38, 59), xytext=(33, 59), arrowprops=dict(facecolor='#0284c7', edgecolor='#0284c7', width=1.5, headwidth=6))
    ax.annotate('', xy=(69, 59), xytext=(64, 59), arrowprops=dict(facecolor='#059669', edgecolor='#059669', width=1.5, headwidth=6))
    ax.text(35.5, 62, "API", ha='center', fontsize=7.5, fontweight='bold', color='#0284c7')
    ax.text(66.5, 62, "SQL", ha='center', fontsize=7.5, fontweight='bold', color='#059669')

    # Docker Volumes and Secrets below
    ax.add_patch(patches.FancyBboxPatch((8, 14), 40, 20, boxstyle="round,pad=0.5", ec="#cbd5e1", fc="#ffffff", lw=1))
    ax.text(28, 27, "Secure Key & Secret Mounting", fontsize=8, fontweight='bold', color='#334155', ha='center')
    ax.text(28, 19, "• backend/keys/github-app.pem (chmod 400)\n• .env credentials (DATABASE_URL, API_KEY)\n• Temporary sandbox workspaces (/tmp/mergemind)",
            fontsize=7, color='#475569', ha='center')

    ax.add_patch(patches.FancyBboxPatch((52, 14), 41, 20, boxstyle="round,pad=0.5", ec="#cbd5e1", fc="#ffffff", lw=1))
    ax.text(72.5, 27, "Container Storage Volumes", fontsize=8, fontweight='bold', color='#334155', ha='center')
    ax.text(72.5, 19, "• postgres_data -> /var/lib/postgresql/data\n• Safe non-root container user execution\n• Ephemeral tarball unpack directories",
            fontsize=7, color='#475569', ha='center')

    save_fig(fig, "arch_09_docker_container_topology.png")

# -------------------------------------------------------------
# Diagram 10: Database ER Diagram
# -------------------------------------------------------------
def gen_diag_10():
    fig, ax = plt.subplots(figsize=(11, 7.5))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    ax.text(50, 96, "MergeMind Relational Database Entity-Relationship (ER) Schema", 
            ha='center', va='center', fontsize=13, fontweight='bold', color='#0f172a')

    # Entities
    tables = [
        ("repositories", 6, 52, 26, 38, [
            "PK: id (UUID / Int)",
            "github_repo_id (BigInt)",
            "name, full_name (String)",
            "owner, default_branch",
            "is_private (Boolean)",
            "installation_id (BigInt)",
            "created_at, updated_at"
        ], "#e0f2fe", "#0284c7"),

        ("health_assessments", 38, 52, 26, 38, [
            "PK: id (UUID / Int)",
            "FK: repository_id (Int)",
            "commit_sha (String)",
            "overall_score (Float)",
            "completeness (Float)",
            "qualification (String)",
            "ruff, bandit, radon, pip",
            "created_at (DateTime)"
        ], "#dcfce7", "#16a34a"),

        ("ci_failures", 70, 52, 26, 38, [
            "PK: id (UUID / Int)",
            "FK: repository_id (Int)",
            "workflow_name (String)",
            "commit_sha (String)",
            "raw_log_sanitized (Text)",
            "error_summary (String)",
            "status (String)",
            "created_at (DateTime)"
        ], "#fee2e2", "#dc2626"),

        ("remediation_proposals", 20, 8, 28, 36, [
            "PK: id (UUID / Int)",
            "FK: ci_failure_id (Int)",
            "unified_diff (Text)",
            "explanation (Text)",
            "verification_status (String)",
            "draft_pr_url (String)",
            "created_at (DateTime)"
        ], "#fef3c7", "#d97706"),

        ("pull_request_reviews", 56, 8, 28, 36, [
            "PK: id (UUID / Int)",
            "FK: repository_id (Int)",
            "pr_number (Integer)",
            "head_sha, base_sha",
            "ai_summary (Text)",
            "findings_json (JSONB)",
            "created_at (DateTime)"
        ], "#ede9fe", "#7c3aed")
    ]

    for name, x, y, w, h, cols_list, fc, ec in tables:
        ax.add_patch(patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5", ec=ec, fc=fc, lw=1.2))
        ax.text(x + w/2, y + h - 3, name.upper(), fontsize=8.5, fontweight='bold', color=ec, ha='center')
        for i, col in enumerate(cols_list):
            ax.text(x + 2, y + h - 7 - i*3.4, col, fontsize=6.8, color='#1e293b')

    # Relationships
    # Repo -> Health
    ax.annotate('', xy=(38, 71), xytext=(32, 71), arrowprops=dict(facecolor='#0284c7', edgecolor='#0284c7', width=1.2, headwidth=5))
    ax.text(35, 73, "1:N", fontsize=7, fontweight='bold', color='#0284c7', ha='center')

    # Repo -> CI Failure
    ax.annotate('', xy=(70, 71), xytext=(64, 71), arrowprops=dict(facecolor='#0284c7', edgecolor='#0284c7', width=1.2, headwidth=5))
    ax.text(67, 73, "1:N", fontsize=7, fontweight='bold', color='#0284c7', ha='center')

    # CI Failure -> Remediation
    ax.annotate('', xy=(34, 44), xytext=(70, 56), arrowprops=dict(facecolor='#dc2626', edgecolor='#dc2626', width=1.2, headwidth=5))
    ax.text(53, 49, "1:N", fontsize=7, fontweight='bold', color='#dc2626', ha='center')

    # Repo -> PR Review
    ax.annotate('', xy=(66, 44), xytext=(22, 52), arrowprops=dict(facecolor='#7c3aed', edgecolor='#7c3aed', width=1.2, headwidth=5))
    ax.text(43, 44, "1:N", fontsize=7, fontweight='bold', color='#7c3aed', ha='center')

    save_fig(fig, "arch_10_database_er_diagram.png")

if __name__ == "__main__":
    print("Generating 10 Academic Architecture Diagrams...")
    gen_diag_1()
    gen_diag_2()
    gen_diag_3()
    gen_diag_4()
    gen_diag_5()
    gen_diag_6()
    gen_diag_7()
    gen_diag_8()
    gen_diag_9()
    gen_diag_10()
    print("All 10 diagrams successfully generated!")
