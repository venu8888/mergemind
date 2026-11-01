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


def test_verify_github_signature_tampered_payload():
    secret = "super_secret_key"
    payload = b'{"action": "opened", "number": 1}'
    tampered_payload = b'{"action": "tampered", "number": 1}'
    mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    valid_header = f"sha256={mac.hexdigest()}"

    assert verify_github_signature(tampered_payload, valid_header, secret) is False


def test_verify_github_signature_edge_cases():
    secret = "test_secret"
    payload = b'{"key": "value"}'
    mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    valid_hex = mac.hexdigest()

    # Missing sha256= prefix
    assert verify_github_signature(payload, valid_hex, secret) is False

    # Empty signature header or empty secret
    assert verify_github_signature(payload, "", secret) is False
    assert verify_github_signature(payload, None, secret) is False
    assert verify_github_signature(payload, f"sha256={valid_hex}", "") is False

    # Empty payload handling
    empty_mac = hmac.new(secret.encode("utf-8"), msg=b"", digestmod=hashlib.sha256)
    assert verify_github_signature(b"", f"sha256={empty_mac.hexdigest()}", secret) is True


def test_sanitize_secret():
    assert sanitize_secret("ghp_1234567890abcdef") == "ghp_...****"
    assert sanitize_secret("abc") == "****"
    assert sanitize_secret("") == "****"
    assert sanitize_secret("1234") == "****"
    assert sanitize_secret("12345") == "1234...****"
