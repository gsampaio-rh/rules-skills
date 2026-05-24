from src.auth import create_token, verify_token


def test_valid_token_returns_200() -> None:
    token = create_token("user1")
    status, body = verify_token(token)
    assert status == 200
    assert body == {"valid": True, "sub": "user1"}


def test_expired_token_returns_401() -> None:
    token = create_token("user1", exp_offset=-3600)
    status, body = verify_token(token)
    assert status == 401
    assert body == {"error": "token_expired"}


def test_invalid_token_returns_401() -> None:
    status, body = verify_token("not.a.jwt")
    assert status == 401
    assert body == {"error": "invalid_token"}
