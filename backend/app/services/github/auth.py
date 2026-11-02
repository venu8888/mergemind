"""GitHub App Authentication, RS256 JWT Generation, and Token Management."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
import jwt
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from app.services.github.exceptions import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubPermissionError,
    GitHubRateLimitError,
    InstallationNotFoundError,
    InstallationSuspendedError,
)


def generate_app_jwt(
    app_id: str,
    private_key_pem: str | bytes,
    expiration_seconds: int = 540,
    expire_minutes: int | None = None,
) -> str:
    """Generates an RS256 signed JSON Web Token for GitHub App authentication."""
    if not app_id:
        raise GitHubAuthError("GitHub App ID must be provided")

    if not private_key_pem:
        raise GitHubAuthError("GitHub App private key must be provided")

    if expire_minutes is not None:
        expiration_seconds = expire_minutes * 60

    pem_bytes = (
        private_key_pem.encode("utf-8") if isinstance(private_key_pem, str) else private_key_pem
    )

    try:
        private_key = load_pem_private_key(pem_bytes, password=None)
    except Exception as exc:
        raise GitHubAuthError("Failed to parse GitHub App RSA private key") from exc

    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + min(expiration_seconds, 600),
        "iss": str(app_id),
    }

    try:
        token = jwt.encode(payload, private_key, algorithm="RS256")
        return token if isinstance(token, str) else token.decode("utf-8")
    except Exception as exc:
        raise GitHubAuthError("Failed to sign GitHub App JWT with RS256") from exc


@dataclass(frozen=True)
class CachedToken:
    """Represents an active, cached GitHub installation access token."""

    token: str
    expires_at: datetime
    installation_id: int


class InstallationTokenManager:
    """Manages installation access tokens with caching, renewal, and concurrency locks."""

    def __init__(
        self,
        app_id: str | None = None,
        private_key_pem: str | bytes | None = None,
        renewal_margin_minutes: int = 5,
    ):
        self.app_id = str(app_id) if app_id else ""
        self.private_key_pem = private_key_pem
        self._tokens: dict[int, CachedToken] = {}
        self._locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._renewal_margin = timedelta(minutes=renewal_margin_minutes)
        self._cache = self._tokens

    def is_token_valid(self, installation_id: int) -> bool:
        """Returns True if the cached token exists and has not reached the renewal margin."""
        cached = self._tokens.get(installation_id)
        if not cached:
            return False
        if isinstance(cached, tuple):
            tok, exp = cached
            return datetime.now(UTC) < (exp - self._renewal_margin)
        return datetime.now(UTC) < (cached.expires_at - self._renewal_margin)

    def invalidate_token(self, installation_id: int) -> None:
        """Purges cached token for an installation."""
        self._tokens.pop(installation_id, None)

    async def get_token(self, installation_id: int) -> str:
        """Convenience method using instance-level configuration."""
        return await self.get_installation_token(
            installation_id=installation_id,
            app_id=self.app_id,
            private_key_pem=self.private_key_pem or "",
        )

    async def _request_new_token(
        self,
        installation_id: int,
        client: httpx.AsyncClient | None = None,
    ) -> tuple[str, datetime]:
        """Internal token exchange helper returning (token, expires_at)."""
        app_jwt = generate_app_jwt(self.app_id, self.private_key_pem or "")
        token_data = await self._exchange_token(
            installation_id=installation_id,
            app_jwt=app_jwt,
            client=client,
            base_url="https://api.github.com",
        )
        return token_data.token, token_data.expires_at

    async def get_installation_token(
        self,
        installation_id: int,
        app_id: str | None = None,
        private_key_pem: str | bytes | None = None,
        client: httpx.AsyncClient | None = None,
        base_url: str = "https://api.github.com",
    ) -> str:
        """Retrieves or exchanges a valid installation access token with double-checked locking."""
        if app_id:
            self.app_id = app_id
        if private_key_pem:
            self.private_key_pem = private_key_pem

        # Fast path without acquiring lock
        if self.is_token_valid(installation_id):
            cached = self._tokens[installation_id]
            return cached[0] if isinstance(cached, tuple) else cached.token

        async with self._locks[installation_id]:
            # Double-check inside lock
            if self.is_token_valid(installation_id):
                cached = self._tokens[installation_id]
                return cached[0] if isinstance(cached, tuple) else cached.token

            tok, exp = await self._request_new_token(installation_id, client=client)
            self._tokens[installation_id] = CachedToken(
                token=tok,
                expires_at=exp,
                installation_id=installation_id,
            )
            return tok

    async def get_default_token(self) -> str | None:
        """Fetch an active installation token for authenticated default GitHub API calls."""
        for inst_id in list(self._tokens.keys()):
            if self.is_token_valid(inst_id):
                cached = self._tokens[inst_id]
                return cached[0] if isinstance(cached, tuple) else cached.token

        try:
            from app.core.database import AsyncSessionLocal
            from app.models.installation import Installation
            from sqlalchemy import select

            async with AsyncSessionLocal() as db:
                res = await db.execute(
                    select(Installation.github_installation_id)
                    .where(Installation.state == "ACTIVE")
                    .limit(1)
                )
                row = res.first()
                if row and row[0]:
                    return await self.get_installation_token(row[0])
        except Exception:
            pass
        return None

    async def _exchange_token(
        self,
        installation_id: int,
        app_jwt: str,
        client: httpx.AsyncClient | None,
        base_url: str,
    ) -> CachedToken:
        """Performs HTTP POST exchange against GitHub API for an installation token."""
        url = f"{base_url.rstrip('/')}/app/installations/{installation_id}/access_tokens"
        headers = {
            "Authorization": f"Bearer {app_jwt}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        should_close = False
        if client is None:
            client = httpx.AsyncClient(timeout=10.0)
            should_close = True

        try:
            response = await client.post(url, headers=headers)
        except (
            GitHubAuthError,
            GitHubPermissionError,
            InstallationNotFoundError,
            InstallationSuspendedError,
            GitHubRateLimitError,
            GitHubAPIError,
        ):
            raise
        except Exception as exc:
            raise GitHubAPIError(
                f"Network error during installation token exchange: {exc}"
            ) from exc
        finally:
            if should_close:
                await client.aclose()

        if response.status_code == 201:
            data = response.json()
            raw_expires = data.get("expires_at", "")
            try:
                expires_at = datetime.fromisoformat(raw_expires.replace("Z", "+00:00"))
            except ValueError:
                expires_at = datetime.now(UTC) + timedelta(hours=1)

            return CachedToken(
                token=data["token"],
                expires_at=expires_at,
                installation_id=installation_id,
            )

        if response.status_code == 404:
            raise InstallationNotFoundError(
                f"Installation {installation_id} was not found or was revoked by GitHub"
            )

        if response.status_code == 403:
            body = response.text.lower()
            if "rate limit" in body:
                raise GitHubRateLimitError(
                    f"Rate limit exceeded during token exchange for {installation_id}"
                )
            if "suspended" in body:
                raise InstallationSuspendedError(f"Installation {installation_id} is suspended")
            raise GitHubPermissionError(f"Permission denied during token exchange: {response.text}")

        if response.status_code == 401:
            raise GitHubAuthError("GitHub rejected App JWT credentials during token exchange")

        raise GitHubAPIError(
            f"GitHub token exchange returned unexpected HTTP {response.status_code}: {response.text}",
            status_code=response.status_code,
        )


def load_app_private_key_pem(key_path_str: str | None = None) -> bytes:
    """Load the GitHub App private key from configured path or fallback locations."""
    from pathlib import Path

    from app.core.config import settings

    target = key_path_str or settings.GITHUB_APP_PRIVATE_KEY_PATH
    if not target:
        return b""

    p = Path(target)
    if not p.is_absolute():
        candidates = [
            p,
            Path(__file__).resolve().parent.parent.parent.parent / p,
            Path(__file__).resolve().parent.parent.parent / p,
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                return c.read_bytes()
    elif p.exists() and p.is_file():
        return p.read_bytes()
    return b""


_shared_token_manager: InstallationTokenManager | None = None


def get_shared_token_manager() -> InstallationTokenManager:
    """Retrieve or create singleton InstallationTokenManager loaded from settings."""
    global _shared_token_manager
    if _shared_token_manager is None:
        from app.core.config import settings

        pem = load_app_private_key_pem()
        _shared_token_manager = InstallationTokenManager(
            app_id=settings.GITHUB_APP_ID,
            private_key_pem=pem,
        )
    return _shared_token_manager


async def get_github_client_for_installation(installation_id: int):
    """Convenience helper to obtain an authenticated GitHubClient for an installation ID."""
    from app.services.github.client import GitHubClient

    manager = get_shared_token_manager()
    token = await manager.get_token(installation_id)
    return GitHubClient(token=token, token_manager=manager)
