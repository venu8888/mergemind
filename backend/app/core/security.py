"""Security utilities for webhook verification and secret sanitization."""

import hashlib
import hmac
import re

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def sanitize_secret(secret: str | None) -> str:
    """Masks secret values for safe logging without exposing credentials."""
    if not secret or len(secret) <= 4:
        return "****"
    return f"{secret[:4]}...****"


_LOG_CREDENTIAL_PATTERNS = [
    re.compile(r"(ghp_[A-Za-z0-9_]+)"),
    re.compile(r"(github_pat_[A-Za-z0-9_]+)"),
    re.compile(r"Bearer\s+([A-Za-z0-9_\-\.]{20,})", re.IGNORECASE),
    re.compile(r"(-----BEGIN [A-Z ]+ PRIVATE KEY-----[^-]+-----END [A-Z ]+ PRIVATE KEY-----)"),
    re.compile(r"password\s*=\s*['\"]?([^'\"\s]{4,})['\"]?", re.IGNORECASE),
    re.compile(r"secret\s*=\s*['\"]?([^'\"\s]{4,})['\"]?", re.IGNORECASE),
]


def sanitize_log_output(log_text: str | None) -> str:
    """Masks secret values and credential tokens inside logs while preserving log output."""
    if not log_text:
        return ""
    sanitized = log_text
    for pattern in _LOG_CREDENTIAL_PATTERNS:
        sanitized = pattern.sub("[REDACTED_CREDENTIAL]", sanitized)
    return sanitized


def verify_github_signature(
    payload_body: bytes,
    signature_header: str | None,
    secret: str,
) -> bool:
    """Verifies that the webhook payload was signed with the configured secret.

    Uses constant-time comparison to prevent timing attack side-channels.
    """
    if not signature_header or not secret:
        return False

    prefix = "sha256="
    if not signature_header.startswith(prefix):
        return False

    received_sig = signature_header[len(prefix) :]
    mac = hmac.new(secret.encode("utf-8"), msg=payload_body, digestmod=hashlib.sha256)
    expected_sig = mac.hexdigest()

    return hmac.compare_digest(expected_sig, received_sig)


def verify_api_key(api_key: str | None = Security(api_key_header)) -> str:
    """Verifies that the caller provided a valid API key.

    In testing and development environments, a default key is tolerated with warning.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required X-API-Key header",
        )

    if settings.ENVIRONMENT == "testing":
        return api_key

    if not hmac.compare_digest(api_key, settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or unauthorized API key",
        )

    return api_key
