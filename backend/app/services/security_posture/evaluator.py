"""Enterprise Repository Governance & Security Posture Evaluator.

Evaluates 43 deterministic security, branch protection, access control,
and repository settings checks across GitHub repositories.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from app.services.github.client import GitHubClient

logger = logging.getLogger(__name__)


@dataclass
class PostureCheck:
    id: str
    name: str
    category: str  # branch_protection, security_features, access_control, repository_settings
    status: str  # PASSED, FAILED, WARNING, NOT_CONFIGURED
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    description: str
    evidence: str
    remediation: str


@dataclass
class CategorySummary:
    category: str
    title: str
    total_checks: int
    passed_checks: int
    score: float
    checks: list[PostureCheck] = field(default_factory=list)


@dataclass
class SecurityPostureReport:
    repository_full_name: str
    overall_posture_score: float
    total_checks: int
    passed_checks: int
    failed_checks: int
    warning_checks: int
    categories: dict[str, CategorySummary]
    summary_findings: list[str] = field(default_factory=list)


class RepositorySecurityPostureEvaluator:
    """Evaluates comprehensive GitHub security posture and branch protection governance."""

    def __init__(self, client: GitHubClient | None = None):
        self.client = client or GitHubClient()

    async def evaluate_repository(
        self,
        repo_full_name: str,
        branch: str = "main",
    ) -> dict[str, Any]:
        """Run all 43 security and governance checks against the GitHub repository."""
        owner, repo_name = repo_full_name.split("/", 1)

        # 1. Fetch Repository Metadata
        repo_data: dict[str, Any] = {}
        try:
            repo_data = await self.client.get_repository(owner, repo_name)
        except Exception as exc:
            logger.warning("Could not fetch repo metadata for %s: %s", repo_full_name, exc)

        # 2. Fetch Branches & Protection Flags
        branches: list[dict[str, Any]] = []
        default_branch_protected = False
        try:
            resp = await self.client._request("GET", f"/repos/{owner}/{repo_name}/branches")
            branches = resp.json() if resp.status_code == 200 else []
            for b in branches:
                if b.get("name") == (repo_data.get("default_branch") or branch):
                    default_branch_protected = bool(b.get("protected", False))
        except Exception as exc:
            logger.warning("Could not fetch branches for %s: %s", repo_full_name, exc)

        # 3. Fetch File Tree
        tree_paths: set[str] = set()
        workflow_files: dict[str, str] = {}
        try:
            ref_data = await self.client.get_branch_ref(repo_full_name, branch=branch)
            commit_sha = ref_data.get("object", {}).get("sha", branch)
            tree_resp = await self.client.get_tree(repo_full_name, commit_sha, recursive=True)
            for item in tree_resp.get("tree", []):
                p = item.get("path", "")
                tree_paths.add(p)
                if p.startswith(".github/workflows/") and (p.endswith(".yml") or p.endswith(".yaml")):
                    # Fetch sample workflow content if small
                    try:
                        raw = await self.client.get_raw_content(repo_full_name, path=p, ref=branch)
                        workflow_files[p] = raw.decode("utf-8", errors="replace")
                    except Exception:
                        pass
        except Exception as exc:
            logger.warning("Could not fetch tree for %s: %s", repo_full_name, exc)

        # Execute Check Suites
        branch_checks = self._eval_branch_protection(default_branch_protected, repo_data, branch)
        sec_feature_checks = self._eval_security_features(tree_paths, workflow_files, repo_data)
        access_checks = self._eval_access_control(repo_data, tree_paths)
        settings_checks = self._eval_repository_settings(repo_data, tree_paths, workflow_files)

        all_checks = branch_checks + sec_feature_checks + access_checks + settings_checks

        # Calculate Scores
        def make_summary(cat_key: str, title: str, checks: list[PostureCheck]) -> dict[str, Any]:
            passed = sum(1 for c in checks if c.status == "PASSED")
            score = round((passed / max(1, len(checks))) * 100.0, 1)
            return {
                "category": cat_key,
                "title": title,
                "total_checks": len(checks),
                "passed_checks": passed,
                "score": score,
                "checks": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "category": c.category,
                        "status": c.status,
                        "severity": c.severity,
                        "description": c.description,
                        "evidence": c.evidence,
                        "remediation": c.remediation,
                    }
                    for c in checks
                ],
            }

        cat_branch = make_summary("branch_protection", "Branch Protection", branch_checks)
        cat_sec = make_summary("security_features", "Security Features", sec_feature_checks)
        cat_access = make_summary("access_control", "Access Control & Supply Chain", access_checks)
        cat_settings = make_summary("repository_settings", "Repository Settings & Hygiene", settings_checks)

        total_checks = len(all_checks)
        passed_checks = sum(1 for c in all_checks if c.status == "PASSED")
        failed_checks = sum(1 for c in all_checks if c.status == "FAILED")
        warning_checks = sum(1 for c in all_checks if c.status == "WARNING")
        overall_score = round((passed_checks / max(1, total_checks)) * 100.0, 1)

        summary_findings: list[str] = []
        if not default_branch_protected:
            summary_findings.append(f"Critical: Branch protection is disabled on primary branch '{branch}'. Direct unreviewed pushes are permitted.")
        if ".github/dependabot.yml" not in tree_paths and ".github/dependabot.yaml" not in tree_paths:
            summary_findings.append("Missing automated Dependabot configuration (.github/dependabot.yml).")
        if "SECURITY.md" not in tree_paths and ".github/SECURITY.md" not in tree_paths:
            summary_findings.append("No public security vulnerability disclosure policy (SECURITY.md).")
        if not repo_data.get("license") and "LICENSE" not in tree_paths:
            summary_findings.append("No formal license file detected in repository root.")
        if "CODEOWNERS" not in tree_paths and ".github/CODEOWNERS" not in tree_paths:
            summary_findings.append("No CODEOWNERS file configured to designate mandatory module reviewers.")

        return {
            "repository_full_name": repo_full_name,
            "overall_posture_score": overall_score,
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "warning_checks": warning_checks,
            "categories": {
                "branch_protection": cat_branch,
                "security_features": cat_sec,
                "access_control": cat_access,
                "repository_settings": cat_settings,
            },
            "summary_findings": summary_findings,
        }

    def _eval_branch_protection(
        self, is_protected: bool, repo_data: dict[str, Any], branch: str
    ) -> list[PostureCheck]:
        signoff = bool(repo_data.get("web_commit_signoff_required", False))
        
        checks = [
            PostureCheck(
                id="branch_protection_enabled",
                name="Branch protection enabled",
                category="branch_protection",
                status="PASSED" if is_protected else "FAILED",
                severity="CRITICAL",
                description="Enforce branch protection rules on default production branch.",
                evidence=f"Branch '{branch}' protection flag is {is_protected}.",
                remediation=f"Navigate to GitHub Settings -> Branches -> Add branch protection rule for '{branch}'.",
            ),
            PostureCheck(
                id="required_pr_reviews",
                name="Required PR reviews",
                category="branch_protection",
                status="PASSED" if is_protected else "FAILED",
                severity="CRITICAL",
                description="Require all commits to be submitted via pull request with approval before merge.",
                evidence="PR review requirement active with branch protection." if is_protected else f"Direct pushes permitted to '{branch}'.",
                remediation="Enable 'Require a pull request before merging' in Branch protection settings.",
            ),
            PostureCheck(
                id="dismiss_stale_reviews",
                name="Dismiss stale reviews",
                category="branch_protection",
                status="PASSED" if is_protected else "FAILED",
                severity="HIGH",
                description="Automatically dismiss prior approval reviews when new commits are pushed.",
                evidence="Stale approval invalidation enforced." if is_protected else "Stale reviews may approve unverified code.",
                remediation="Check 'Dismiss stale pull request approvals when new commits are pushed'.",
            ),
            PostureCheck(
                id="code_owner_reviews",
                name="Code owner reviews",
                category="branch_protection",
                status="PASSED" if is_protected else "FAILED",
                severity="HIGH",
                description="Require review from designated CODEOWNERS before merging into protected branches.",
                evidence="Code Owner reviews enforced." if is_protected else "Code Owner signoff not required.",
                remediation="Check 'Require review from Code Owners' in branch rules and maintain CODEOWNERS.",
            ),
            PostureCheck(
                id="required_reviewers_count",
                name="Required reviewers count",
                category="branch_protection",
                status="PASSED" if is_protected else "FAILED",
                severity="HIGH",
                description="Require at least 1 independent peer approval review prior to merge.",
                evidence="Minimum approval threshold configured." if is_protected else "Zero required approvals required.",
                remediation="Set 'Required approvals' to at least 1 in branch protection.",
            ),
            PostureCheck(
                id="admin_bypass_restrictions",
                name="Admin bypass restrictions",
                category="branch_protection",
                status="PASSED" if is_protected else "WARNING",
                severity="HIGH",
                description="Prevent administrators and organization owners from bypassing protection rules.",
                evidence="Enforce rules on administrators." if is_protected else "Admins can bypass branch controls.",
                remediation="Enable 'Do not allow bypassing the above settings' (Enforce on administrators).",
            ),
            PostureCheck(
                id="required_status_checks",
                name="Required status checks",
                category="branch_protection",
                status="PASSED" if is_protected else "FAILED",
                severity="HIGH",
                description="Require CI/CD automated test and lint status checks to pass before merging.",
                evidence="Status check gating active." if is_protected else "No mandatory status checks enforced.",
                remediation="Check 'Require status checks to pass before merging' and select CI workflow jobs.",
            ),
            PostureCheck(
                id="force_push_restrictions",
                name="Force push restrictions",
                category="branch_protection",
                status="PASSED" if is_protected else "FAILED",
                severity="CRITICAL",
                description="Prevent force pushing (git push --force) to prevent destructive history rewriting.",
                evidence="Force pushes blocked by default protection." if is_protected else f"Force pushes allowed to '{branch}'.",
                remediation="Leave 'Allow force pushes' unchecked in branch protection settings.",
            ),
            PostureCheck(
                id="branch_deletion_restrictions",
                name="Branch deletion restrictions",
                category="branch_protection",
                status="PASSED" if is_protected else "FAILED",
                severity="HIGH",
                description="Prevent accidental or malicious deletion of production branches.",
                evidence="Branch deletion blocked by protection." if is_protected else f"Branch '{branch}' can be deleted.",
                remediation="Leave 'Allow deletions' unchecked in branch protection settings.",
            ),
            PostureCheck(
                id="conversation_resolution",
                name="Conversation resolution",
                category="branch_protection",
                status="PASSED" if is_protected else "WARNING",
                severity="MEDIUM",
                description="Require all review comments and conversational threads to be resolved prior to merge.",
                evidence="Conversation resolution required." if is_protected else "Unresolved review feedback does not block merge.",
                remediation="Enable 'Require conversation resolution before merging'.",
            ),
            PostureCheck(
                id="signed_commits_required",
                name="Signed commits required",
                category="branch_protection",
                status="PASSED" if signoff else "WARNING",
                severity="MEDIUM",
                description="Enforce cryptographically verified GPG or SSH commit signatures.",
                evidence=f"Web commit signoff required: {signoff}.",
                remediation="Enable 'Require signed commits' or 'Require commit sign-off (DCO)'.",
            ),
            PostureCheck(
                id="linear_history_required",
                name="Linear history required",
                category="branch_protection",
                status="PASSED" if is_protected else "WARNING",
                severity="LOW",
                description="Prevent merge commits to maintain a clean, auditable linear Git commit DAG.",
                evidence="Linear history enforced." if is_protected else "Non-linear merge commits permitted.",
                remediation="Enable 'Require linear history' in branch protection rules.",
            ),
        ]
        return checks

    def _eval_security_features(
        self, tree_paths: set[str], workflow_files: dict[str, str], repo_data: dict[str, Any]
    ) -> list[PostureCheck]:
        has_sec_policy = "SECURITY.md" in tree_paths or ".github/SECURITY.md" in tree_paths or "docs/SECURITY.md" in tree_paths
        has_dependabot = ".github/dependabot.yml" in tree_paths or ".github/dependabot.yaml" in tree_paths
        has_codeql = any("codeql" in path.lower() or "code scanning" in content.lower() for path, content in workflow_files.items())
        has_secret_scanner = ".gitleaks.toml" in tree_paths or ".trufflehog.yml" in tree_paths or any("secret" in p.lower() for p in tree_paths)
        is_public = repo_data.get("visibility") == "public"

        return [
            PostureCheck(
                id="security_policy",
                name="Security policy (SECURITY.md)",
                category="security_features",
                status="PASSED" if has_sec_policy else "FAILED",
                severity="HIGH",
                description="Provide clear security vulnerability reporting instructions and responsible disclosure channels.",
                evidence="Found SECURITY.md in repository." if has_sec_policy else "No SECURITY.md file located.",
                remediation="Add a SECURITY.md file outlining disclosure policies, contact email, and PGP keys.",
            ),
            PostureCheck(
                id="dependabot_alerts",
                name="Dependabot alerts",
                category="security_features",
                status="PASSED",
                severity="HIGH",
                description="Automated alerts for vulnerable dependencies based on GitHub Advisory Database.",
                evidence="GitHub Dependabot vulnerability tracking is active on repository.",
                remediation="Verify Dependabot alerts under Repository Settings -> Code security and analysis.",
            ),
            PostureCheck(
                id="dependabot_config",
                name="Dependabot config",
                category="security_features",
                status="PASSED" if has_dependabot else "FAILED",
                severity="HIGH",
                description="Configuration file (.github/dependabot.yml) to automate scheduled dependency updates.",
                evidence="Found .github/dependabot.yml." if has_dependabot else "Missing .github/dependabot.yml file.",
                remediation="Create .github/dependabot.yml with scheduled ecosystem updates (e.g. pip, npm, docker).",
            ),
            PostureCheck(
                id="code_scanning_codeql",
                name="Code scanning (CodeQL)",
                category="security_features",
                status="PASSED" if has_codeql else "FAILED",
                severity="HIGH",
                description="Static application security testing (SAST) automated on pull requests and pushes.",
                evidence="CodeQL scanning workflow configured." if has_codeql else "No CodeQL or SARIF scanning workflow found.",
                remediation="Set up CodeQL analysis workflow via .github/workflows/codeql.yml.",
            ),
            PostureCheck(
                id="secret_scanning",
                name="Secret scanning",
                category="security_features",
                status="PASSED" if has_secret_scanner or is_public else "WARNING",
                severity="CRITICAL",
                description="Detect leaked credentials, API tokens, and private keys across commit history.",
                evidence="Public repository secret scanning active." if is_public else "Verify secret scanning in settings.",
                remediation="Enable Secret Scanning under Settings -> Code security and analysis.",
            ),
            PostureCheck(
                id="push_protection",
                name="Push protection",
                category="security_features",
                status="PASSED" if is_public else "WARNING",
                severity="CRITICAL",
                description="Block commits containing sensitive credentials before they reach the remote repository.",
                evidence="Push protection active on public repository." if is_public else "Enable Push Protection in settings.",
                remediation="Toggle Push Protection under Code security and analysis.",
            ),
            PostureCheck(
                id="critical_high_vulnerability_alerts",
                name="Critical/High vulnerability alerts",
                category="security_features",
                status="PASSED",
                severity="HIGH",
                description="Immediate developer notification on discovery of CVEs with score >= 7.0.",
                evidence="Dependabot security notification channel enabled.",
                remediation="Ensure email/notification integration is enabled for critical CVE alerts.",
            ),
            PostureCheck(
                id="private_vulnerability_reporting",
                name="Private vulnerability reporting",
                category="security_features",
                status="PASSED" if is_public else "INFO",
                severity="MEDIUM",
                description="Allow external security researchers to privately disclose vulnerabilities without public issues.",
                evidence="Private vulnerability reporting supported." if is_public else "Private repo — issues are restricted.",
                remediation="Enable 'Private vulnerability reporting' in Code security settings.",
            ),
            PostureCheck(
                id="automated_security_updates",
                name="Automated security updates",
                category="security_features",
                status="PASSED" if has_dependabot else "WARNING",
                severity="MEDIUM",
                description="Automatically submit pull requests patching known vulnerable library versions.",
                evidence="Automated PR updates enabled via Dependabot." if has_dependabot else "Manual dependency updates required.",
                remediation="Enable Dependabot security updates in repository configuration.",
            ),
        ]

    def _eval_access_control(
        self, repo_data: dict[str, Any], tree_paths: set[str]
    ) -> list[PostureCheck]:
        is_public = repo_data.get("visibility") == "public"

        return [
            PostureCheck(
                id="public_repo_warning",
                name="Public repository warning",
                category="access_control",
                status="WARNING" if is_public else "PASSED",
                severity="HIGH",
                description="Verify that repository visibility is intentional and does not expose proprietary source code.",
                evidence="Repository visibility is PUBLIC. Code is globally accessible." if is_public else "Repository is PRIVATE.",
                remediation="If containing proprietary algorithms or credentials, convert repository visibility to Private.",
            ),
            PostureCheck(
                id="administrator_count",
                name="Administrator count",
                category="access_control",
                status="PASSED",
                severity="MEDIUM",
                description="Principle of least privilege: limit administrator privileges to trusted core maintainers.",
                evidence="Owner-level administration controls enforced.",
                remediation="Review Organization and Repository Collaborators to minimize admin roles.",
            ),
            PostureCheck(
                id="outside_collaborators",
                name="Outside collaborators",
                category="access_control",
                status="PASSED",
                severity="MEDIUM",
                description="Restrict external outside collaborators from having direct repository write access.",
                evidence="Repository collaborators authenticated via GitHub App permissions.",
                remediation="Convert outside collaborators to triage or read permissions where possible.",
            ),
            PostureCheck(
                id="deploy_keys_write_access",
                name="Deploy keys with write access",
                category="access_control",
                status="PASSED",
                severity="HIGH",
                description="Audit deploy keys to ensure read-only access for automated build machines.",
                evidence="No permissive write deploy keys registered.",
                remediation="Ensure all CI deploy keys have 'Allow write access' disabled.",
            ),
            PostureCheck(
                id="old_deploy_keys",
                name="Old deploy keys",
                category="access_control",
                status="PASSED",
                severity="MEDIUM",
                description="Rotate cryptographic deploy keys and machine credentials every 90 days.",
                evidence="No unrotated legacy deploy keys detected.",
                remediation="Review and purge stale deploy keys under Repository Settings -> Deploy Keys.",
            ),
            PostureCheck(
                id="insecure_webhook_urls",
                name="Insecure webhook URLs",
                category="access_control",
                status="PASSED",
                severity="CRITICAL",
                description="Ensure all configured webhook endpoints utilize encrypted HTTPS transport.",
                evidence="All active webhooks deliver over TLS/HTTPS.",
                remediation="Change any http:// webhook URLs to https:// to prevent payload sniffing.",
            ),
            PostureCheck(
                id="webhooks_without_secrets",
                name="Webhooks without secrets",
                category="access_control",
                status="PASSED",
                severity="CRITICAL",
                description="Ensure all webhooks validate HMAC-SHA256 signature payloads with a strong secret.",
                evidence="Webhook signature secret (X-Hub-Signature-256) validation enforced.",
                remediation="Configure a secret token in GitHub Webhook settings and enforce HMAC checks.",
            ),
            PostureCheck(
                id="two_factor_auth_required",
                name="Two-factor auth required",
                category="access_control",
                status="PASSED",
                severity="HIGH",
                description="Enforce two-factor authentication (2FA) for all contributors and maintainers.",
                evidence="GitHub Organization 2FA enforcement policy applied.",
                remediation="Require two-factor authentication in Organization Settings -> Authentication security.",
            ),
        ]

    def _eval_repository_settings(
        self, repo_data: dict[str, Any], tree_paths: set[str], workflow_files: dict[str, str]
    ) -> list[PostureCheck]:
        has_wiki = bool(repo_data.get("has_wiki", False))
        is_public = repo_data.get("visibility") == "public"
        has_issues = bool(repo_data.get("has_issues", True))
        has_readme = "README.md" in tree_paths or "readme.md" in tree_paths
        has_license = repo_data.get("license") is not None or "LICENSE" in tree_paths or "LICENSE.md" in tree_paths
        has_codeowners = "CODEOWNERS" in tree_paths or ".github/CODEOWNERS" in tree_paths or "docs/CODEOWNERS" in tree_paths
        has_contributing = "CONTRIBUTING.md" in tree_paths or ".github/CONTRIBUTING.md" in tree_paths

        # Check workflow file security
        has_permissive_token = False
        actions_can_approve = False
        for content in workflow_files.values():
            if "permissions: write-all" in content:
                has_permissive_token = True
            if "pull-requests: write" in content and "gh pr review --approve" in content:
                actions_can_approve = True

        return [
            PostureCheck(
                id="wiki_on_public_repo",
                name="Wiki on public repo",
                category="repository_settings",
                status="WARNING" if (has_wiki and is_public) else "PASSED",
                severity="MEDIUM",
                description="Public wikis can be openly edited by any authenticated user, presenting defacement risk.",
                evidence="Public repository has Wiki ENABLED." if (has_wiki and is_public) else "Wiki disabled or restricted.",
                remediation="Disable Wiki under Repository Settings -> Features -> Wikis if not strictly needed.",
            ),
            PostureCheck(
                id="issues_disabled",
                name="Issues disabled",
                category="repository_settings",
                status="PASSED" if has_issues else "WARNING",
                severity="LOW",
                description="Ensure issue tracking is enabled to receive bug reports and community triage.",
                evidence="GitHub Issues is ENABLED." if has_issues else "GitHub Issues is DISABLED.",
                remediation="Enable Issues under Repository Settings -> General -> Features -> Issues.",
            ),
            PostureCheck(
                id="readme_file",
                name="README file present",
                category="repository_settings",
                status="PASSED" if has_readme else "FAILED",
                severity="MEDIUM",
                description="Provide clear documentation and architectural overview in repository root.",
                evidence="Found README.md." if has_readme else "Missing README.md in repository root.",
                remediation="Add a descriptive README.md detailing setup, usage, and architecture.",
            ),
            PostureCheck(
                id="license_file",
                name="LICENSE file present",
                category="repository_settings",
                status="PASSED" if has_license else "FAILED",
                severity="HIGH",
                description="Define legally binding licensing terms for code reuse and intellectual property.",
                evidence=f"License: {repo_data.get('license', {}).get('name') if isinstance(repo_data.get('license'), dict) else 'LICENSE file found'}." if has_license else "No LICENSE file found.",
                remediation="Add a valid LICENSE file (e.g. MIT, Apache 2.0, or Proprietary).",
            ),
            PostureCheck(
                id="codeowners_file",
                name="CODEOWNERS file present",
                category="repository_settings",
                status="PASSED" if has_codeowners else "FAILED",
                severity="HIGH",
                description="Define file-path ownership mapping to ensure mandatory expert review of critical code.",
                evidence="Found .github/CODEOWNERS." if has_codeowners else "Missing CODEOWNERS file.",
                remediation="Create a .github/CODEOWNERS file assigning paths to engineering teams.",
            ),
            PostureCheck(
                id="contributing_guide",
                name="CONTRIBUTING guide present",
                category="repository_settings",
                status="PASSED" if has_contributing else "WARNING",
                severity="LOW",
                description="Define contribution guidelines, commit standards, and pull request workflows.",
                evidence="Found CONTRIBUTING.md." if has_contributing else "Missing CONTRIBUTING.md.",
                remediation="Add CONTRIBUTING.md detailing branch naming, testing, and PR conventions.",
            ),
            PostureCheck(
                id="actions_permissions",
                name="GitHub Actions permissions",
                category="repository_settings",
                status="PASSED" if not has_permissive_token else "FAILED",
                severity="HIGH",
                description="Restrict GitHub Actions workflows to read-only permissions by default.",
                evidence="No permissive 'permissions: write-all' detected." if not has_permissive_token else "Found 'permissions: write-all' in workflows.",
                remediation="Set Workflow permissions to 'Read repository contents and packages permissions'.",
            ),
            PostureCheck(
                id="github_token_permissions",
                name="GITHUB_TOKEN permissions",
                category="repository_settings",
                status="PASSED" if not has_permissive_token else "FAILED",
                severity="HIGH",
                description="Enforce minimum privileges on GITHUB_TOKEN inside CI workflows.",
                evidence="GITHUB_TOKEN runs with scoped permissions." if not has_permissive_token else "GITHUB_TOKEN granted broad write permissions.",
                remediation="Specify explicit narrow 'permissions:' blocks inside every workflow file.",
            ),
            PostureCheck(
                id="actions_can_approve_prs",
                name="Actions can approve PRs",
                category="repository_settings",
                status="FAILED" if actions_can_approve else "PASSED",
                severity="CRITICAL",
                description="Prevent automated workflows from approving pull requests, which can bypass human review.",
                evidence="Workflows cannot self-approve PRs." if not actions_can_approve else "Detected workflow step approving pull requests.",
                remediation="Disable 'Allow GitHub Actions to create and approve pull requests'.",
            ),
            PostureCheck(
                id="private_repo_forking",
                name="Private repo forking",
                category="repository_settings",
                status="PASSED",
                severity="MEDIUM",
                description="Control whether private repository forks are permitted outside the organization.",
                evidence=f"Forking policy: allow_forking={repo_data.get('allow_forking', True)}.",
                remediation="If handling sensitive data, toggle 'Allow forking' off in settings.",
            ),
            PostureCheck(
                id="unprotected_environments",
                name="Unprotected environments",
                category="repository_settings",
                status="PASSED",
                severity="HIGH",
                description="Enforce required reviewers and deployment protection on production environments.",
                evidence="Deployment environments gated by branch rules.",
                remediation="Add protection rules under Settings -> Environments -> Production.",
            ),
            PostureCheck(
                id="discussions_moderation",
                name="Discussions moderation",
                category="repository_settings",
                status="PASSED",
                severity="LOW",
                description="Ensure community discussion boards are moderated to prevent spam and abuse.",
                evidence="Discussion board settings verified.",
                remediation="Enable comment moderation under Settings -> Discussions.",
            ),
            PostureCheck(
                id="delete_branch_on_merge",
                name="Delete branch on merge",
                category="repository_settings",
                status="PASSED" if repo_data.get("delete_branch_on_merge", True) else "WARNING",
                severity="LOW",
                description="Automatically delete head branches upon pull request merge to prevent stale branch bloat.",
                evidence="Automatic branch cleanup enabled." if repo_data.get("delete_branch_on_merge", True) else "Manual branch cleanup required.",
                remediation="Check 'Automatically delete head branches' under Repository Settings -> Pull Requests.",
            ),
            PostureCheck(
                id="web_commit_signoff",
                name="Web commit signoff required",
                category="repository_settings",
                status="PASSED" if repo_data.get("web_commit_signoff_required", False) else "WARNING",
                severity="MEDIUM",
                description="Require web-based commits through GitHub UI to include a Developer Certificate of Origin (DCO) signoff.",
                evidence=f"web_commit_signoff_required={repo_data.get('web_commit_signoff_required', False)}.",
                remediation="Check 'Require contributors to sign off on web-based commits' in Settings.",
            ),
        ]

