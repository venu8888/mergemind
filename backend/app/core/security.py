"""Security utilities for webhook verification and secret sanitization."""

import hashlib
import hmac


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


def sanitize_secret(secret_value: str, visible_chars: int = 4) -> str:
    """Redacts secrets for safe logging and status reporting."""
    if not secret_value or len(secret_value) <= visible_chars:
        return "****"
    return f"{secret_value[:visible_chars]}...****"
