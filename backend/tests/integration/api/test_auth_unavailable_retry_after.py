"""Integration tests for 503 + Retry-After propagation on transient unavailability.

Validates the full FastAPI app stack (including error handlers) with a real
psycopg OperationalError being raised by the repository, ensuring:
  - The HTTP response is 503
  - Retry-After header is present and a valid positive integer
  - Error internals are not exposed in the response body

These tests use actual FastAPI TestClient (no DB needed; OperationalError is
simulated by the fake repo injected into app.state).

TDD: written before T046 (update auth_controller to catch psycopg errors).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_app_with_unavailable_repo() -> FastAPI:
    """Wire a FastAPI app whose repository always raises OperationalError."""
    import psycopg

    from domain.entities.account import Account, AuthSession, LoginAttempt
    from application.ports.auth_ports import (
        AuditLogPort,
        Clock,
        PasswordHasher,
        TokenService,
        UserAccountRepository,
    )
    from adapters.http.error_handlers import register_error_handlers
    from application.use_cases.authenticate_user import AuthenticateUser
    from adapters.http.auth_controller import router as auth_router

    _FIXED_NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)

    class _FakeClock(Clock):
        def utc_now(self) -> datetime:
            return _FIXED_NOW

    class _FakeHasher(PasswordHasher):
        def hash(self, plain: str) -> str:
            return f"hashed:{plain}"

        def verify(self, plain: str, hashed: str) -> bool:
            return False

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
                access_token="tok",
                issued_at=_FIXED_NOW,
                expires_at=_FIXED_NOW + timedelta(minutes=30),
                must_change_password=False,
            )

        def decode_access_token(self, token: str) -> dict:  # type: ignore[override]
            return {}

    class _FakeAudit(AuditLogPort):
        def log_login_attempt(self, attempt: LoginAttempt) -> None:
            pass

    class _BrokenRepo(UserAccountRepository):
        def find_by_email(self, email: str) -> Optional[Account]:
            raise psycopg.OperationalError("DB unavailable")

        def find_by_id(self, account_id: uuid.UUID) -> Optional[Account]:
            raise psycopg.OperationalError("DB unavailable")

        def save(self, account: Account) -> None:
            pass

        def increment_failed_attempts(
            self, account_id: uuid.UUID, locked_until: Optional[datetime]
        ) -> None:
            pass

        def reset_failed_attempts(self, account_id: uuid.UUID) -> None:
            pass

        def bootstrap_admin(self, email: str, password_hash: str, role: str) -> str:
            return "preserved"

        def record_login_attempt(self, attempt: LoginAttempt) -> None:
            pass

    app = FastAPI()
    register_error_handlers(app)
    app.state.authenticate_user = AuthenticateUser(
        repo=_BrokenRepo(),
        hasher=_FakeHasher(),
        token_svc=_FakeTokenSvc(),
        clock=_FakeClock(),
        audit_log=_FakeAudit(),
    )
    app.include_router(auth_router, prefix="/auth")
    return app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(_build_app_with_unavailable_repo(), raise_server_exceptions=False)


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestRetryAfterPropagation:
    """Full-stack test: OperationalError → 503 + Retry-After."""

    def test_returns_503(self, client: TestClient) -> None:
        resp = client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "any"},
        )
        assert resp.status_code == 503

    def test_retry_after_header_present(self, client: TestClient) -> None:
        resp = client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "any"},
        )
        assert "retry-after" in resp.headers

    def test_retry_after_is_valid_positive_integer(self, client: TestClient) -> None:
        resp = client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "any"},
        )
        value = resp.headers.get("retry-after", "")
        assert value.isdigit() and int(value) > 0

    def test_no_internal_error_in_body(self, client: TestClient) -> None:
        resp = client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "any"},
        )
        body_text = resp.text.lower()
        for forbidden in ("traceback", "psycopg", "operationalerror", "db unavailable"):
            assert forbidden not in body_text
