"""Unit tests for src/app/core/security.py"""

import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_password_returns_string(self) -> None:
        result = hash_password("secret123")
        assert isinstance(result, str)
        assert result != "secret123"

    def test_hash_password_not_equal_plain(self) -> None:
        result = hash_password("secret123")
        assert result != "secret123"

    def test_hash_is_different_each_call(self) -> None:
        h1 = hash_password("secret123")
        h2 = hash_password("secret123")
        assert h1 != h2  # bcrypt uses random salt

    def test_verify_password_correct(self) -> None:
        hashed = hash_password("my_password")
        assert verify_password("my_password", hashed) is True

    def test_verify_password_wrong(self) -> None:
        hashed = hash_password("my_password")
        assert verify_password("wrong_password", hashed) is False

    def test_verify_password_empty_string(self) -> None:
        hashed = hash_password("my_password")
        assert verify_password("", hashed) is False


class TestAccessToken:
    def test_create_access_token_returns_string(self) -> None:
        token = create_access_token(subject="user-123")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token_returns_subject(self) -> None:
        token = create_access_token(subject="user-abc")
        payload = decode_access_token(token)
        assert payload["sub"] == "user-abc"

    def test_decode_access_token_has_type_claim(self) -> None:
        token = create_access_token(subject="user-abc")
        payload = decode_access_token(token)
        assert payload["type"] == "access"

    def test_decode_access_token_has_exp_claim(self) -> None:
        token = create_access_token(subject="user-abc")
        payload = decode_access_token(token)
        assert "exp" in payload

    def test_decode_access_token_extra_claims(self) -> None:
        token = create_access_token(subject="user-abc", extra_claims={"role": "admin"})
        payload = decode_access_token(token)
        assert payload["role"] == "admin"

    def test_decode_access_token_invalid_raises(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token("not.a.valid.token")
        assert exc_info.value.status_code == 401

    def test_decode_access_token_tampered_raises(self) -> None:
        from fastapi import HTTPException

        token = create_access_token(subject="user-abc")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(HTTPException):
            decode_access_token(tampered)

    def test_decode_access_token_expired_raises(self) -> None:
        from fastapi import HTTPException

        # Create token that expires immediately
        token = create_access_token(subject="user-abc", expire_minutes=-1)
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token)
        assert exc_info.value.status_code == 401
