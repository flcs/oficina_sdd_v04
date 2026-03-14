"""Contract tests for 503 + Retry-After when auth service is unavailable.

Validates:
  - POST /auth/login returns 503 when a transient dependency failure occurs
  - Response includes Retry-After header with a valid positive integer value
  - Response body uses the standard error schema

TDD: written before T046 (update auth_controller to catch DB errors → 503).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from domain.entities.account import Account, AccountRole, AuthSession, Email, LoginAttempt
from application.ports.auth_ports import (
    AuditLogPort,
    Clock,
    PasswordHasher,
    TokenService,
    UserAccountRepository,
    UnitOfWork,
)
from adapters.http.error_handlers import register_error_handlers


# ── Fakes ─────────────────────────────────────────────────────────────────────

_FIXED_NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)


class _FakeClock(Clock):
    def utc_now(self) -> datetime:
        return _FIXED_NOW


class _FakeHasher(PasswordHasher):
    def hash(self, plain: str) -> str:
        return f"hashed:{plain}"

    def verify(self, plain: str, hashed: str) -> bool:
        return False  # never succeeds; we test infrastructure failure path


class _FakeTokenSvc(TokenService):
    def create_access_token(
        self,
        account_id: uuid.UUID,
        role: str,
        must_change_password: bool,
        token_version: int,
    ) -> AuthSession:
        return AuthSession(
            account_id=account_id,
            access_token="test-token",
            issued_at=_FIXED_NOW,
            expires_at=_FIXED_NOW + timedelta(minutes=30),
            must_change_password=must_change_password,
        )

    def decode_access_token(self, token: str) -> dict:  # type: ignore[override]
        return {}


class _FakeAuditLog(AuditLogPort):
    def log_login_attempt(self, attempt: LoginAttempt) -> None:
        pass


class _UnavailableRepo(UserAccountRepository):
    """Simulates a database that raises OperationalError on every call."""

    def find_by_email(self, email: str) -> Optional[Account]:
        import psycopg
        raise psycopg.OperationalError("Connection refused (simulated)")

    def find_by_id(self, account_id: uuid.UUID) -> Optional[Account]:
        import psycopg
        raise psycopg.OperationalError("Connection refused (simulated)")

    def save(self, account: Account) -> None:
        pass

    def increment_failed_attempts(
        self, account_id: uuid.UUID, locked_until: Optional[datetime]
    ) -> None:
        pass

    def reset_failed_attempts(self, account_id: uuid.UUID) -> None:
        pass

    def bootstrap_admin(
        self,
        email: str,
        password_hash: str,
        role: str,
    ) -> str:
        return "preserved"

    def record_login_attempt(self, attempt: LoginAttempt) -> None:
        pass


def _make_unavailable_app() -> FastAPI:
    from application.use_cases.authenticate_user import AuthenticateUser
    from adapters.http.auth_controller import router as auth_router

    app = FastAPI()
    register_error_handlers(app)

    repo = _UnavailableRepo()
    app.state.authenticate_user = AuthenticateUser(
        repo=repo,
        hasher=_FakeHasher(),
        token_svc=_FakeTokenSvc(),
        clock=_FakeClock(),
        audit_log=_FakeAuditLog(),
    )
    app.include_router(auth_router, prefix="/auth")
    return app


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestServiceUnavailableContract:
    """503 with Retry-After when a transient infrastructure failure occurs."""

    def setup_method(self) -> None:
        self.client = TestClient(_make_unavailable_app(), raise_server_exceptions=False)

    def test_503_status_code(self) -> None:
        resp = self.client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "somepassword"},
        )
        assert resp.status_code == 503, (
            f"Expected 503 for unavailable dependency, got {resp.status_code}"
        )

    def test_retry_after_header_present(self) -> None:
        resp = self.client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "somepassword"},
        )
        assert "retry-after" in resp.headers, (
            "503 response must include Retry-After header"
        )

    def test_retry_after_is_positive_integer(self) -> None:
        resp = self.client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "somepassword"},
        )
        retry_after = resp.headers.get("retry-after", "")
        assert retry_after.isdigit() and int(retry_after) > 0, (
            f"Retry-After must be a positive integer, got '{retry_after}'"
        )

    def test_response_has_detail_field(self) -> None:
        resp = self.client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "somepassword"},
        )
        assert "detail" in resp.json()

    def test_response_does_not_disclose_error_internals(self) -> None:
        resp = self.client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "somepassword"},
        )
        body_text = resp.text.lower()
        for leak in ("traceback", "operationalerror", "psycopg", "connection refused"):
            assert leak not in body_text, (
                f"503 response must not disclose internal error: '{leak}' found"
            )
