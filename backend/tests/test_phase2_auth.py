"""Tests for GitHub RS256 Authentication and Installation Token Management."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.services.github.auth import InstallationTokenManager, generate_app_jwt
from app.services.github.exceptions import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubPermissionError,
    InstallationNotFoundError,
    InstallationSuspendedError,
)


@pytest.fixture(scope="session")
def rsa_test_keys():
    """Generates a valid 2048-bit RSA key pair for testing RS256 JWTs."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )

    return private_pem, public_pem


def test_generate_app_jwt_success(rsa_test_keys):
    """Verifies RS256 JWT generation with 60s leeway and 9-minute validity."""
    private_pem, public_pem = rsa_test_keys
    app_id = "test-app-12345"

    token = generate_app_jwt(app_id=app_id, private_key_pem=private_pem, expire_minutes=9)
    assert token is not None

    decoded = jwt.decode(
        token,
        public_pem,
        algorithms=["RS256"],
        options={"require": ["exp", "iat", "iss"]},
    )
    assert decoded["iss"] == app_id
    now = datetime.now(UTC).timestamp()
    # Leeway checks: iat should be around 60 seconds in the past
    assert decoded["iat"] <= now - 50
    # Expire checks: exp should be around 9 minutes in the future
    assert decoded["exp"] > now + 400


def test_generate_app_jwt_invalid_key():
    """Verifies that an invalid private key raises GitHubAuthError."""
    with pytest.raises(GitHubAuthError) as exc_info:
        generate_app_jwt(app_id="123", private_key_pem="INVALID PEM DATA")
    assert "Failed to parse" in str(exc_info.value) or "Failed to sign" in str(exc_info.value)


@pytest.mark.asyncio
async def test_installation_token_caching_and_refresh(rsa_test_keys):
    """Verifies token caching and proactive refresh within 5 minutes of expiration."""
    private_pem, _ = rsa_test_keys
    manager = InstallationTokenManager(
        app_id="app-123",
        private_key_pem=private_pem,
    )

    mock_resp = {
        "token": "ghs_test_token_111",
        "expires_at": (datetime.now(UTC) + timedelta(minutes=60)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "permissions": {"pull_requests": "read"},
    }

    with patch.object(manager, "_request_new_token", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = (mock_resp["token"], datetime.now(UTC) + timedelta(minutes=60))

        # First fetch: should make API call
        t1 = await manager.get_token(123456)
        assert t1 == "ghs_test_token_111"
        assert mock_request.call_count == 1

        # Second fetch: should hit cache
        t2 = await manager.get_token(123456)
        assert t2 == "ghs_test_token_111"
        assert mock_request.call_count == 1

        # Now simulate cache entry within 4 minutes of expiry (< 5 min margin)
        manager._cache[123456] = (
            "ghs_old_token",
            datetime.now(UTC) + timedelta(minutes=4),
        )
        mock_request.return_value = (
            "ghs_fresh_token",
            datetime.now(UTC) + timedelta(minutes=60),
        )

        t3 = await manager.get_token(123456)
        assert t3 == "ghs_fresh_token"
        assert mock_request.call_count == 2


@pytest.mark.asyncio
async def test_installation_token_concurrency_double_checked_lock(rsa_test_keys):
    """Verifies double-checked locking: concurrent requests for same installation result in single mint."""
    private_pem, _ = rsa_test_keys
    manager = InstallationTokenManager(
        app_id="app-123",
        private_key_pem=private_pem,
    )

    call_count = 0

    async def fake_request_new_token(install_id, **kwargs):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)  # Simulate network latency
        return f"token_for_{install_id}", datetime.now(UTC) + timedelta(minutes=60)

    with patch.object(manager, "_request_new_token", side_effect=fake_request_new_token):
        # Fire 10 simultaneous coroutines for the same installation
        results = await asyncio.gather(*[manager.get_token(999) for _ in range(10)])
        assert len(results) == 10
        assert all(r == "token_for_999" for r in results)
        assert call_count == 1  # Exactly one API request made!


@pytest.mark.asyncio
async def test_installation_token_error_discrimination(rsa_test_keys):
    """Verifies distinct error handling for 401, 403 (suspended/unauthorized), 404, 500."""
    private_pem, _ = rsa_test_keys
    manager = InstallationTokenManager(app_id="app-123", private_key_pem=private_pem)

    def create_mock_response(status_code: int, json_data: dict):
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = json_data
        resp.text = str(json_data)
        return resp

    # 1. 401 Bad Credentials
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = create_mock_response(401, {"message": "Bad credentials"})
        with pytest.raises(GitHubAuthError):
            await manager._request_new_token(100)

    # 2. 403 Suspended
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = create_mock_response(
            403, {"message": "Installation has been suspended"}
        )
        with pytest.raises(InstallationSuspendedError):
            await manager._request_new_token(101)

    # 3. 403 Permission denied
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = create_mock_response(
            403, {"message": "Resource not accessible by integration"}
        )
        with pytest.raises(GitHubPermissionError):
            await manager._request_new_token(102)

    # 4. 404 Not Found (Uninstalled)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = create_mock_response(404, {"message": "Not Found"})
        with pytest.raises(InstallationNotFoundError):
            await manager._request_new_token(103)

    # 5. 500 GitHub Server Error
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = create_mock_response(500, {"message": "Internal Server Error"})
        with pytest.raises(GitHubAPIError):
            await manager._request_new_token(104)
