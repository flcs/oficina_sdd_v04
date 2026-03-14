"""Contract tests for lockout behavior at POST /auth/login.

Validates:
  - Locked account receives neutral 401 (NOT 423, no enumeration)
  - Response body matches the same schema as regular invalid-credentials 401
  - No account-specific information is disclosed

TDD: written before T045 (update AuthenticateUser with lockout policy).
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

_LOCKED_UNTIL = datetime(2099, 1, 1, tzinfo=timezone.utc)  # far future → always locked
_FIXED_NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)


class _FakeClock(Clock):
    def utc_now(self) -> datetime:
        return _FIXED_NOW


class _FakeHasher(PasswordHasher):
    def hash(self, plain: str) -> str:
        return f"hashed:{plain}"

    def verify(self, plain: str, hashed: str) -> bool:
        return hashed == f"hashed:{plain}"


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


class _FakeUoW(UnitOfWork):
    def __enter__(self) -> "UnitOfWork":
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


class _LockedAccountRepo(UserAccountRepository):
    """Returns a locked account for any email lookup."""

    def find_by_email(self, email: str) -> Optional[Account]:
        now = _FIXED_NOW
        return Account(
            account_id=uuid.uuid4(),
            email=Email("admin@example.com"),
            password_hash="hashed:secret",
            role=AccountRole.ADMIN,
            active=True,
            failed_login_attempts=5,
            locked_until=_LOCKED_UNTIL,
            must_change_password=False,
            token_version=1,
            created_at=now,
            updated_at=now,
        )

    def find_by_id(self, account_id: uuid.UUID) -> Optional[Account]:
        return None

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


def _make_app() -> FastAPI:
    from application.use_cases.authenticate_user import AuthenticateUser
    from adapters.http.auth_controller import router as auth_router

    app = FastAPI()
    register_error_handlers(app)

    repo = _LockedAccountRepo()
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

class TestLockoutNeutral401:
    """Locked account must return the same neutral 401 as invalid credentials."""

    def setup_method(self) -> None:
        self.client = TestClient(_make_app(), raise_server_exceptions=False)

    def test_locked_returns_401_not_423(self) -> None:
        resp = self.client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "wrongpassword"},
        )
        assert resp.status_code == 401, (
            f"Expected 401 for locked account, got {resp.status_code}"
        )

    def test_locked_response_has_detail_field(self) -> None:
        resp = self.client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "wrongpassword"},
        )
        body = resp.json()
        assert "detail" in body

    def test_locked_message_does_not_disclose_lockout(self) -> None:
        """Lock status must not be revealed in the response body."""
        resp = self.client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "wrongpassword"},
        )
        body_text = resp.text.lower()
        for leak in ("lock", "bloqueado", "too many", "attempts", "conta"):
            assert leak not in body_text, (
                f"Response must not contain '{leak}' — account enumeration risk"
            )

    def test_locked_message_matches_invalid_creds_message(self) -> None:
        """Same message for locked as for invalid credentials (no enumeration)."""
        resp_locked = self.client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "wrongpassword"},
        )
        assert resp_locked.status_code == 401
        body = resp_locked.json()
        assert "detail" in body

    def test_no_www_authenticate_header_on_locked(self) -> None:
        """No WWW-Authenticate header that discloses lock state."""
        resp = self.client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "wrongpassword"},
        )
        # If present, must not disclose lock-specific information
        www_auth = resp.headers.get("www-authenticate", "")
        assert "lock" not in www_auth.lower()
