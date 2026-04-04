"""Unit tests for Pydantic schemas validation."""

import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest
from app.schemas.common import APIResponse, err, ok


class TestRegisterRequest:
    def test_valid_input(self) -> None:
        r = RegisterRequest(email="alice@example.com", username="alice", password="Secret123!")
        assert r.email == "alice@example.com"
        assert r.username == "alice"

    def test_email_is_lowercased(self) -> None:
        r = RegisterRequest(email="ALICE@EXAMPLE.COM", username="alice", password="Secret123!")
        assert r.email == "alice@example.com"

    def test_invalid_email_raises(self) -> None:
        with pytest.raises(ValidationError):
            RegisterRequest(email="not-an-email", username="alice", password="Secret123!")

    def test_username_too_short_raises(self) -> None:
        with pytest.raises(ValidationError):
            RegisterRequest(email="a@b.com", username="ab", password="Secret123!")

    def test_username_invalid_chars_raises(self) -> None:
        with pytest.raises(ValidationError):
            RegisterRequest(email="a@b.com", username="ali ce!", password="Secret123!")

    def test_password_too_short_raises(self) -> None:
        with pytest.raises(ValidationError):
            RegisterRequest(email="a@b.com", username="alice", password="Sh0rt")

    def test_password_no_uppercase_raises(self) -> None:
        with pytest.raises(ValidationError):
            RegisterRequest(email="a@b.com", username="alice", password="secret123!")

    def test_password_no_lowercase_raises(self) -> None:
        with pytest.raises(ValidationError):
            RegisterRequest(email="a@b.com", username="alice", password="SECRET123!")

    def test_password_no_digit_raises(self) -> None:
        with pytest.raises(ValidationError):
            RegisterRequest(email="a@b.com", username="alice", password="SecretPass!")


class TestAPIResponse:
    def test_ok_sets_success_true(self) -> None:
        resp = ok(data={"key": "value"})
        assert resp.success is True
        assert resp.data == {"key": "value"}

    def test_ok_with_message(self) -> None:
        resp = ok(data="hello", message="done")
        assert resp.message == "done"

    def test_err_sets_success_false(self) -> None:
        resp = err("something went wrong")
        assert resp.success is False
        assert resp.message == "something went wrong"
        assert resp.data is None

    def test_err_with_errors_list(self) -> None:
        resp = err("validation failed", errors=["field required", "too short"])
        assert resp.errors == ["field required", "too short"]

    def test_api_response_generic_none_data(self) -> None:
        resp: APIResponse[None] = APIResponse(success=True, data=None)
        assert resp.data is None
