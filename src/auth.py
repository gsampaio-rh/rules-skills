"""JWT authentication helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from werkzeug.security import check_password_hash, generate_password_hash

SECRET: str = "dev-secret"
DEFAULT_EXPIRATION_SECONDS: int = 1 * 3600


def hash_password(password: str) -> str:
    """Return a salted password hash."""
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Return True when the password matches the stored hash."""
    return check_password_hash(password_hash, password)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_token(subject: str, exp_offset: int | None = None) -> str:
    """Create a signed JWT for the given subject."""
    now = int(time.time())
    exp = now + (exp_offset if exp_offset is not None else DEFAULT_EXPIRATION_SECONDS)
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": subject, "exp": exp, "iat": now}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = _b64url_encode(hmac.new(SECRET.encode(), signing_input, hashlib.sha256).digest())
    return f"{header_b64}.{payload_b64}.{signature}"
