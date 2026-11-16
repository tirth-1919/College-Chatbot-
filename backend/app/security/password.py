"""Password Hashing and Verification Module.

Uses direct bcrypt with work factor (12 rounds) for secure, timing-attack resistant credential storage.
Compliant with modern bcrypt 4+ and Python 3.11/3.12/3.13 without passlib wrap-around bugs.
"""

import bcrypt


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt with automatic 12-round salting."""
    pwd_bytes = password.encode("utf-8")[:72]  # Truncate to 72 bytes as per bcrypt specification
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies that a plaintext password matches an existing bcrypt hash in constant time."""
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False
