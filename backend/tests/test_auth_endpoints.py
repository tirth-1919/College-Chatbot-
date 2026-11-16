"""Authentication & Token Validation Unit Tests."""

from app.security.jwt import create_access_token, decode_token
from app.security.password import hash_password, verify_password


def test_password_hashing():
    """Verify that bcrypt hashing produces valid, non-plaintext, verifiable hashes."""
    raw_password = "SecurePassword@12345"
    hashed = hash_password(raw_password)

    assert hashed != raw_password
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword@999", hashed) is False


def test_jwt_token_claims_and_decoding():
    """Verify JWT access token issuance, tenant claim persistence, and decoding."""
    user_id = "12345678-1234-5678-1234-567812345678"
    role = "COLLEGE_ADMIN"
    college_id = "99999999-9999-9999-9999-999999999999"

    token = create_access_token(
        subject=user_id,
        role=role,
        college_id=college_id,
        additional_claims={"email": "admin@college.edu"},
    )

    assert token is not None
    assert isinstance(token, str)

    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["role"] == role
    assert payload["college_id"] == college_id
    assert payload["email"] == "admin@college.edu"


def test_invalid_token_decoding():
    """Verify that tampered or invalid tokens return None."""
    assert decode_token("invalid.tampered.token") is None
    assert decode_token("") is None

