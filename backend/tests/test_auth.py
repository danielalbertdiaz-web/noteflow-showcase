import pytest
from fastapi import HTTPException

from app.core.security import (
    create_access_token,
    create_magic_link_token,
    create_refresh_token,
    hash_password,
    verify_magic_link_token,
    verify_password,
    verify_token,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "secure_password_123"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correct_password")
        assert not verify_password("wrong_password", hashed)


class TestJWT:
    def test_create_and_verify_access_token(self):
        token = create_access_token("user-123", extra_claims={"role": "clinician"})
        payload = verify_token(token, expected_type="access")
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["role"] == "clinician"

    def test_invalid_token_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            verify_token("invalid.token.here")
        assert exc_info.value.status_code == 401

    def test_refresh_token_type_mismatch(self):
        token = create_refresh_token("user-123")
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token, expected_type="access")
        assert exc_info.value.status_code == 401


class TestMagicLink:
    def test_create_and_verify_magic_link(self):
        token = create_magic_link_token("user@example.com")
        email = verify_magic_link_token(token)
        assert email == "user@example.com"

    def test_invalid_magic_link_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            verify_magic_link_token("bad-token")
        assert exc_info.value.status_code == 401
