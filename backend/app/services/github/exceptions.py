"""GitHub Integration Domain Exceptions."""

from __future__ import annotations


class GitHubError(Exception):
    """Base exception for all GitHub integration operations."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class GitHubAuthError(GitHubError):
    """Raised when authentication fails (JWT signing, invalid credentials)."""


class InstallationNotFoundError(GitHubError):
    """Raised when an installation ID does not exist or has been deleted (HTTP 404)."""


class InstallationSuspendedError(GitHubError):
    """Raised when an installation is suspended by the user or org (HTTP 403)."""


class GitHubPermissionError(GitHubError):
    """Raised when the GitHub App lacks required scopes/permissions for an action."""


class GitHubRateLimitError(GitHubError):
    """Raised when primary or secondary rate limits are reached."""

    def __init__(
        self,
        message: str,
        reset_at: int | None = None,
        retry_after: int | None = None,
        status_code: int = 429,
    ):
        super().__init__(message)
        self.message = message
        self.reset_at = reset_at
        self.retry_after = retry_after
        self.status_code = status_code


class GitHubAPIError(GitHubError):
    """Raised when a non-retryable or fatal GitHub API error occurs."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class SourceIntegrityError(GitHubError):
    """Raised when retrieved source content fails Git blob hash verification."""


class LeaseFencingError(Exception):
    """Raised when a queue worker attempts to update a job with an expired or invalid lease."""
