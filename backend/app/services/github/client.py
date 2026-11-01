"""GitHub REST API Client with Rate Limiting, Retries, and Stream Handlers."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any

import httpx

from app.services.github.exceptions import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubPermissionError,
    GitHubRateLimitError,
    InstallationNotFoundError,
)

logger = logging.getLogger(__name__)


class GitHubClient:
    """Async client communicating with GitHub REST API v3/v4 with bounded backoff."""

    def __init__(
        self,
        token: str | None = None,
        base_url: str = "https://api.github.com",
        timeout: float = 15.0,
        max_retries: int = 3,
        client: httpx.AsyncClient | None = None,
        token_manager: Any = None,
    ):
        self.token = token
        self.token_manager = token_manager
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._external_client = client is not None
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self.rate_limit_remaining: int | None = None
        self.rate_limit_reset: int | None = None

    async def close(self) -> None:
        """Closes the underlying HTTP client if internally managed."""
        if not self._external_client:
            await self._client.aclose()

    async def __aenter__(self) -> GitHubClient:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    def _build_headers(self, accept: str = "application/vnd.github+json") -> dict[str, str]:
        headers = {
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "MergeMind-Verification-Framework/0.1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def request(
        self,
        method: str,
        path: str,
        accept: str = "application/vnd.github+json",
        params: dict[str, Any] | None = None,
        installation_id: int | None = None,
    ) -> httpx.Response:
        """Public request interface with token manager support."""
        if installation_id and self.token_manager:
            if hasattr(self.token_manager, "get_token"):
                self.token = await self.token_manager.get_token(installation_id)
            elif hasattr(self.token_manager, "get_installation_token"):
                self.token = await self.token_manager.get_installation_token(installation_id)
        return await self._request(method=method, path=path, accept=accept, params=params)

    async def _request(
        self,
        method: str,
        path: str,
        accept: str = "application/vnd.github+json",
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Executes HTTP request with rate-limit tracking and bounded jittered retries."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = self._build_headers(accept=accept)

        for attempt in range(self.max_retries):
            try:
                response = await self._client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                )
            except (TimeoutError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
                if attempt == self.max_retries - 1:
                    raise GitHubAPIError(
                        f"GitHub request timed out after {self.max_retries} attempts: {exc}",
                        status_code=408,
                    ) from exc
                backoff = (2**attempt) * 0.5 + random.uniform(0.1, 0.4)
                await asyncio.sleep(backoff)
                continue
            except httpx.ConnectError as exc:
                if attempt == self.max_retries - 1:
                    raise GitHubAPIError(
                        f"GitHub connection failed after {self.max_retries} attempts: {exc}"
                    ) from exc
                backoff = (2**attempt) * 0.5 + random.uniform(0.1, 0.4)
                logger.warning(
                    f"Transient network error on {method} {path}: {exc}. Retrying in {backoff:.2f}s"
                )
                await asyncio.sleep(backoff)
                continue

            headers_lower = {k.lower(): str(v) for k, v in response.headers.items()}

            # Update rate-limit tracking
            if "x-ratelimit-remaining" in headers_lower:
                try:
                    self.rate_limit_remaining = int(headers_lower["x-ratelimit-remaining"])
                except ValueError:
                    pass
            if "x-ratelimit-reset" in headers_lower:
                try:
                    self.rate_limit_reset = int(headers_lower["x-ratelimit-reset"])
                except ValueError:
                    pass

            # 1. Secondary Rate Limit / Explicit Retry-After
            if response.status_code in (403, 429) and "retry-after" in headers_lower:
                try:
                    retry_after = min(int(headers_lower["retry-after"]), 60)
                except ValueError:
                    retry_after = 10
                if attempt == self.max_retries - 1:
                    raise GitHubRateLimitError(
                        "Secondary rate limit exceeded and retry limit reached",
                        retry_after=retry_after,
                        status_code=response.status_code,
                    )
                logger.warning(f"Secondary rate limit triggered on {path}. Sleeping {retry_after}s")
                await asyncio.sleep(retry_after)
                continue

            # 2. Primary Rate Limit Exhausted
            if response.status_code == 403 and headers_lower.get("x-ratelimit-remaining") == "0":
                try:
                    reset_ts = int(headers_lower.get("x-ratelimit-reset", int(time.time()) + 60))
                except ValueError:
                    reset_ts = int(time.time()) + 60
                raise GitHubRateLimitError(
                    f"GitHub primary rate limit exhausted until {reset_ts}",
                    reset_at=reset_ts,
                    status_code=403,
                )

            # 3. Server Errors (502, 503, 504) -> Bounded Exponential Backoff
            if response.status_code in (502, 503, 504):
                if attempt == self.max_retries - 1:
                    raise GitHubAPIError(
                        f"GitHub server error {response.status_code} after {self.max_retries} retries",
                        status_code=response.status_code,
                    )
                backoff = (2**attempt) * 0.5 + random.uniform(0.1, 0.5)
                logger.warning(
                    f"GitHub HTTP {response.status_code} on {path}. Retrying in {backoff:.2f}s"
                )
                await asyncio.sleep(backoff)
                continue

            # 4. Fail-Fast Client Errors
            if response.status_code == 401:
                raise GitHubAuthError("GitHub authentication failed: Bad or expired credentials")

            if response.status_code == 404:
                raise InstallationNotFoundError(f"Resource not found on GitHub: {path}")

            if response.status_code == 403:
                body_lower = response.text.lower()
                if "rate limit" in body_lower or "secondary" in body_lower:
                    raise GitHubRateLimitError("Rate limit exceeded")
                raise GitHubPermissionError(f"Permission denied for {path}: {response.text}")

            if response.is_error:
                raise GitHubAPIError(
                    f"GitHub returned HTTP {response.status_code} for {path}: {response.text}",
                    status_code=response.status_code,
                )

            return response

        raise GitHubAPIError(f"Request to {path} failed after maximum retry attempts")

    async def get_installation_repositories(self) -> list[dict[str, Any]]:
        """Retrieves paginated list of all repositories accessible to the installation."""
        repositories: list[dict[str, Any]] = []
        page = 1
        per_page = 100

        while True:
            response = await self._request(
                method="GET",
                path="/installation/repositories",
                params={"page": page, "per_page": per_page},
            )
            data = response.json()
            repos_page = data.get("repositories", [])
            repositories.extend(repos_page)

            total_count = data.get("total_count", len(repositories))
            if len(repositories) >= total_count or not repos_page:
                break
            page += 1

        return repositories

    async def get_pull_request(
        self, owner: str, repo: str | None = None, pull_number: int | None = None
    ) -> dict[str, Any]:
        """Retrieves authoritative PR metadata from GitHub."""
        if repo is None and "/" in owner and pull_number is not None:
            owner_part, repo_part = owner.split("/", 1)
            response = await self._request(
                method="GET", path=f"/repos/{owner_part}/{repo_part}/pulls/{pull_number}"
            )
        else:
            response = await self._request(
                method="GET", path=f"/repos/{owner}/{repo}/pulls/{pull_number}"
            )
        return response.json()

    async def get_pull_request_diff(
        self, owner: str, repo: str | None = None, pull_number: int | None = None
    ) -> str:
        """Retrieves raw unified patch diff string for a pull request."""
        if repo is None and "/" in owner and pull_number is not None:
            owner_part, repo_part = owner.split("/", 1)
            response = await self._request(
                method="GET",
                path=f"/repos/{owner_part}/{repo_part}/pulls/{pull_number}",
                accept="application/vnd.github.diff",
            )
        else:
            response = await self._request(
                method="GET",
                path=f"/repos/{owner}/{repo}/pulls/{pull_number}",
                accept="application/vnd.github.diff",
            )
        return response.text

    async def get_tree(
        self,
        owner: str,
        repo: str | None = None,
        tree_sha: str | None = None,
        recursive: bool = True,
    ) -> dict[str, Any]:
        """Retrieves Git tree at the given commit or tree SHA."""
        if repo is not None and tree_sha is None:
            # Called as get_tree("owner/repo", "tree_sha")
            repo_full_name = owner
            actual_tree_sha = repo
            if "/" in repo_full_name:
                owner_part, repo_part = repo_full_name.split("/", 1)
            else:
                owner_part, repo_part = repo_full_name, repo_full_name
            actual_path = f"/repos/{owner_part}/{repo_part}/git/trees/{actual_tree_sha}"
        elif tree_sha is not None:
            actual_path = f"/repos/{owner}/{repo}/git/trees/{tree_sha}"
        else:
            actual_path = f"/repos/{owner}/git/trees"

        params = {"recursive": "1"} if recursive else None
        response = await self._request(
            method="GET",
            path=actual_path,
            params=params,
        )
        return response.json()

    async def get_blob(
        self, owner: str, repo: str | None = None, blob_sha: str | None = None
    ) -> dict[str, Any]:
        """Retrieves blob content via Git Blobs API."""
        if repo is not None and blob_sha is None:
            # Called as get_blob("owner/repo", "blob_sha")
            repo_full_name = owner
            actual_sha = repo
            if "/" in repo_full_name:
                owner_part, repo_part = repo_full_name.split("/", 1)
            else:
                owner_part, repo_part = repo_full_name, repo_full_name
            actual_path = f"/repos/{owner_part}/{repo_part}/git/blobs/{actual_sha}"
        else:
            actual_path = f"/repos/{owner}/{repo}/git/blobs/{blob_sha}"

        response = await self._request(
            method="GET",
            path=actual_path,
            accept="application/vnd.github+json",
        )
        return response.json()

    async def get_raw_content(
        self, owner: str, repo: str | None = None, path: str | None = None, ref: str | None = None
    ) -> bytes:
        """Retrieves raw file content at an exact immutable ref/commit SHA."""
        if "/" in owner and path is None:
            # Called as get_raw_content("owner/repo", "path/to/file", ref="commit_sha")
            owner_part, repo_part = owner.split("/", 1)
            actual_path_arg = repo or ""
            ref_param = ref
        elif path is not None:
            owner_part, repo_part = owner, repo or ""
            actual_path_arg = path
            ref_param = ref
        else:
            owner_part, repo_part = owner, repo or ""
            actual_path_arg = ""
            ref_param = ref

        actual_url = f"/repos/{owner_part}/{repo_part}/contents/{actual_path_arg.lstrip('/')}"
        response = await self._request(
            method="GET",
            path=actual_url,
            accept="application/vnd.github.raw+json",
            params={"ref": ref_param} if ref_param else None,
        )
        return response.content
