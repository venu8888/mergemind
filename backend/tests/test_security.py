"""Unit tests for security utilities."""

import hashlib
import hmac

from app.core.security import sanitize_secret, verify_github_signature


def test_verify_github_signature_valid():
    secret = "super_secret_key"
    payload = b'{"action": "opened", "number": 1}'
    mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    valid_header = f"sha256={mac.hexdigest()}"

    assert verify_github_signature(payload, valid_header, secret) is True


def test_verify_github_signature_invalid():
    secret = "super_secret_key"
    payload = b'{"action": "opened", "number": 1}'
    tampered_payload = b'{"action": "tampered", "number": 1}'
    mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    valid_header = f"sha256={mac.hexdigest()}"

    assert verify_github_signature(tampered_payload, valid_header, secret) is False
    assert verify_github_signature(payload, "invalid_format", secret) is False
    assert verify_github_signature(payload, None, secret) is False


def test_sanitize_secret():
    assert sanitize_secret("ghp_1234567890abcdef") == "ghp_...****"
    assert sanitize_secret("abc") == "****"
    assert sanitize_secret("") == "****"
