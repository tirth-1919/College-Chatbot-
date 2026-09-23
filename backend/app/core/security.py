import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from backend.app.core.config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def generate_secure_temporary_password(length: int = 16) -> str:
    """Generates a cryptographically strong, policy-compliant temporary password."""
    import secrets
    import string
    
    uppers = string.ascii_uppercase
    lowers = string.ascii_lowercase
    digits = string.digits
    symbols = "!@#$%^&*"
    
    # Ensure at least 2 of each required character group
    password = [
        secrets.choice(uppers),
        secrets.choice(uppers),
        secrets.choice(lowers),
        secrets.choice(lowers),
        secrets.choice(digits),
        secrets.choice(digits),
        secrets.choice(symbols),
        secrets.choice(symbols),
    ]
    all_chars = uppers + lowers + digits + symbols
    for _ in range(max(length - len(password), 0)):
        password.append(secrets.choice(all_chars))
    
    secrets.SystemRandom().shuffle(password)
    return "".join(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None

# --- 2FA / MFA Utilities (TOTP RFC 6238 compliant) ---
import base64
import hashlib
import hmac
import os
import struct
import time

def generate_totp_secret() -> str:
    """Generates a standard 16-character base32 secret string."""
    random_bytes = os.urandom(10)
    return base64.b32encode(random_bytes).decode("utf-8").replace("=", "")

def generate_totp_code(secret: str, for_time: Optional[int] = None) -> str:
    """Generates a 6-digit TOTP code for the given secret and unix timestamp."""
    try:
        if for_time is None:
            for_time = int(time.time())
        time_step = 30
        counter = int(for_time // time_step)
        
        # Pad secret to valid base32 length if needed
        padded_secret = secret.upper()
        missing_padding = len(padded_secret) % 8
        if missing_padding:
            padded_secret += "=" * (8 - missing_padding)
            
        key = base64.b32decode(padded_secret)
        counter_bytes = struct.pack(">Q", counter)
        hmac_digest = hmac.new(key, counter_bytes, hashlib.sha1).digest()
        offset = hmac_digest[-1] & 0x0F
        code_int = struct.unpack(">I", hmac_digest[offset:offset + 4])[0] & 0x7FFFFFFF
        return f"{code_int % 1000000:06d}"
    except Exception:
        return "000000"

def verify_totp_code(secret: str, code: str, window: int = 1) -> bool:
    """
    Verifies a 6-digit TOTP code against the secret with drift tolerance (+/- window intervals).
    RFC 6238 compliant. No development bypass codes are permitted in any environment.
    """
    if not secret or not code:
        return False
    
    clean_code = str(code).strip()
    if len(clean_code) != 6 or not clean_code.isdigit():
        return False

    now = int(time.time())
    for offset in range(-window, window + 1):
        target_time = now + (offset * 30)
        if generate_totp_code(secret, target_time) == clean_code:
            return True
    return False

