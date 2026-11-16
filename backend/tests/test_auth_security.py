"""Authentication & Password Security Automated Unit Tests."""

import time
import uuid
import pytest
from app.security.password import hash_password, verify_password
from app.security.jwt import create_access_token, decode_token
from app.middleware.rate_limit import InMemoryRateLimiter
from datetime import timedelta


def test_password_hashing_and_salting():
    """Verifies that bcrypt produces secure, unique salted hashes and verifies accurately."""
    pwd = "SecureStudentPass@2026"
    hash1 = hash_password(pwd)
    hash2 = hash_password(pwd)

    # Different salts must yield different hash strings
    assert hash1 != hash2
    assert hash1.startswith("$2b$") or hash1.startswith("$2a$")

    # Correct password verifies
    assert verify_password(pwd, hash1) is True
    assert verify_password(pwd, hash2) is True

    # Incorrect password fails
    assert verify_password("WrongPassword@123", hash1) is False
    assert verify_password("", hash1) is False


def test_jwt_generation_and_claims():
    """Verifies JWT access token generation, role preservation, and claim extraction."""
    user_id = str(uuid.uuid4())
    college_id = str(uuid.uuid4())
    role = "COLLEGE_ADMIN"

    token = create_access_token(
        subject=user_id,
        role=role,
        college_id=college_id,
        additional_claims={"email": "dean@campus.edu", "full_name": "Dean Sharma"},
    )

    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["role"] == role
    assert payload["college_id"] == college_id
    assert payload["email"] == "dean@campus.edu"
    assert "exp" in payload
    assert "iat" in payload


def test_jwt_expiration_handling():
    """Verifies that expired JWT tokens are rejected cleanly and return None."""
    user_id = str(uuid.uuid4())

    # Create token expired 10 minutes ago
    expired_token = create_access_token(
        subject=user_id,
        role="STUDENT",
        expires_delta=timedelta(minutes=-10),
    )

    payload = decode_token(expired_token)
    assert payload is None, "Expired JWT token must not be accepted"


def test_jwt_tampered_signature():
    """Verifies that tokens with modified payloads or invalid signatures are rejected."""
    user_id = str(uuid.uuid4())
    token = create_access_token(subject=user_id, role="STUDENT")

    parts = token.split(".")
    assert len(parts) == 3

    # Tamper with the payload segment
    tampered_token = f"{parts[0]}.eyJhZG1pbiI6dHJ1ZX0.{parts[2]}"
    assert decode_token(tampered_token) is None

    # Invalid random string
    assert decode_token("invalid.jwt.token") is None


def test_rate_limiter_sliding_window():
    """Verifies the in-memory sliding window rate limiter blocks brute force attempts."""
    limiter = InMemoryRateLimiter()
    client_key = "192.168.1.100:/api/v1/auth/login"
    max_requests = 3
    window_seconds = 2

    # First 3 requests must succeed
    assert limiter.is_allowed(client_key, max_requests, window_seconds) is True
    assert limiter.is_allowed(client_key, max_requests, window_seconds) is True
    assert limiter.is_allowed(client_key, max_requests, window_seconds) is True

    # 4th request within window must be blocked
    assert limiter.is_allowed(client_key, max_requests, window_seconds) is False

    # Different IP is not blocked
    other_client = "192.168.1.101:/api/v1/auth/login"
    assert limiter.is_allowed(other_client, max_requests, window_seconds) is True

    # After window expires, client is allowed again
    time.sleep(2.1)
    assert limiter.is_allowed(client_key, max_requests, window_seconds) is True

