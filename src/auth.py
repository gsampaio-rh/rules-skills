"""JWT authentication helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

SECRET = "dev-secret"
DEFAULT_EXPIRATION_SECONDS = 24 * 3600


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


def verify_token(token: str) -> tuple[int, dict[str, Any]]:
    """Verify JWT and return (status_code, body)."""
    try:
        header_b64, payload_b64, signature = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected_sig = _b64url_encode(hmac.new(SECRET.encode(), signing_input, hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected_sig):
            return 401, {"error": "invalid_token"}

        payload = json.loads(_b64url_decode(payload_b64))
        if payload.get("exp", 0) < int(time.time()):
            return 401, {"error": "token_expired"}
        return 200, {"valid": True, "sub": payload["sub"]}
    except (ValueError, KeyError, json.JSONDecodeError):
        return 401, {"error": "invalid_token"}
