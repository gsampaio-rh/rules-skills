from src.auth import create_access_token, create_token, hash_password, verify_password
from src.token_validation import verify_token


def test_valid_token_returns_200() -> None:
    token = create_token("user1", role="user")
    status, body = verify_token(token)
    assert status == 200
    assert body == {"valid": True, "sub": "user1", "role": "user", "typ": "access"}


def test_access_token_helper() -> None:
    token = create_access_token("user1", "clinician")
    status, body = verify_token(token)
    assert status == 200
    assert body["role"] == "clinician"


def test_expired_token_returns_401() -> None:
    token = create_token("user1", exp_offset=-3600)
    status, body = verify_token(token)
    assert status == 401
    assert body == {"error": "token_expired"}


def test_token_expires_when_exp_reached() -> None:
    token = create_token("user1", exp_offset=0)
    status, body = verify_token(token)
    assert status == 401
    assert body == {"error": "token_expired"}


def test_invalid_token_returns_401() -> None:
    status, body = verify_token("not.a.jwt")
    assert status == 401
    assert body == {"error": "invalid_token"}


def test_refresh_type_rejected_for_access_validation() -> None:
    token = create_token("user1", token_type="refresh")
    status, body = verify_token(token, expected_type="access")
    assert status == 401
    assert body == {"error": "invalid_token_type"}


def test_password_hash_round_trip() -> None:
    password_hash = hash_password("password123")

    assert verify_password(password_hash, "password123") is True
    assert verify_password(password_hash, "wrong-password") is False
