"""JWT authentication helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from werkzeug.security import check_password_hash, generate_password_hash

SECRET: str = "dev-secret"
ACCESS_EXPIRATION_SECONDS: int = 1 * 3600
REFRESH_TOKEN_EXPIRATION_SECONDS: int = 7 * 24 * 3600
DEFAULT_EXPIRATION_SECONDS: int = ACCESS_EXPIRATION_SECONDS


def hash_password(password: str) -> str:
    """Return a salted password hash."""
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Return True when the password matches the stored hash."""
    return check_password_hash(password_hash, password)


def hash_refresh_token(token: str) -> str:
    """Return a stable hash for storing refresh tokens."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_refresh_token() -> str:
    """Return a cryptographically secure opaque refresh token."""
    return secrets.token_urlsafe(48)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_token(
    subject: str,
    *,
    role: str = "user",
    token_type: str = "access",
    exp_offset: int | None = None,
) -> str:
    """Create a signed JWT for the given subject."""
    now = int(time.time())
    if exp_offset is None:
        exp_offset = (
            ACCESS_EXPIRATION_SECONDS
            if token_type == "access"
            else REFRESH_TOKEN_EXPIRATION_SECONDS
        )
    exp = now + exp_offset
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "role": role,
        "typ": token_type,
        "exp": exp,
        "iat": now,
    }
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = _b64url_encode(hmac.new(SECRET.encode(), signing_input, hashlib.sha256).digest())
    return f"{header_b64}.{payload_b64}.{signature}"


def create_access_token(subject: str, role: str) -> str:
    """Create a short-lived access JWT."""
    return create_token(subject, role=role, token_type="access")
