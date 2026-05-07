"""Auth unit tests."""
import pytest
from unittest.mock import patch


def test_create_and_verify_token():
    from auth import create_access_token, get_current_user
    from fastapi import HTTPException

    token = create_access_token({"sub": "user@test.com", "role": "analyst", "id": 1})
    assert isinstance(token, str)

    result = get_current_user(token)
    assert result["sub"] == "user@test.com"
    assert result["role"] == "analyst"


def test_invalid_token_raises_401():
    from auth import get_current_user
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        get_current_user("invalid.token.here")
    assert exc_info.value.status_code == 401


def test_missing_token_raises_401():
    from auth import get_current_user
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(None)
    assert exc_info.value.status_code == 401


def test_password_hashing():
    from auth import hash_password, verify_password

    hashed = hash_password("mypassword123")
    assert hashed != "mypassword123"
    assert verify_password("mypassword123", hashed)
    assert not verify_password("wrongpassword", hashed)
