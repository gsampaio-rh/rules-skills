"""JWT token validation."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, TypedDict

from src.auth import SECRET, _b64url_decode, _b64url_encode


class ValidTokenBody(TypedDict):
    valid: bool
    sub: str


class InvalidTokenBody(TypedDict):
    error: str


TokenValidationBody = ValidTokenBody | InvalidTokenBody
VerifyTokenResult = tuple[int, TokenValidationBody]


def verify_token(token: str) -> VerifyTokenResult:
    """Verify JWT and return (status_code, body)."""
    try:
        header_b64, payload_b64, signature = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected_sig = _b64url_encode(
            hmac.new(SECRET.encode(), signing_input, hashlib.sha256).digest()
        )
        if not hmac.compare_digest(signature, expected_sig):
            return 401, {"error": "invalid_token"}

        payload: dict[str, Any] = json.loads(_b64url_decode(payload_b64))
        if payload.get("exp", 0) < int(time.time()):
            return 401, {"error": "token_expired"}
        return 200, {"valid": True, "sub": payload["sub"]}
    except (ValueError, KeyError, json.JSONDecodeError):
        return 401, {"error": "invalid_token"}
